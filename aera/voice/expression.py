"""Human-like expression: mood, prosody and emotional nuance.

The original emotion layer classified a whole utterance as one of nine labels
and applied a fixed pitch offset. Real speech does not work that way. People
carry a mood between sentences, stress particular words, pause at commas,
lift into a question and fall at a full stop, and say "not great" to mean the
opposite of "great".

Three things live here:

``Mood``
    A slow-moving emotional baseline that persists across turns and decays
    back toward neutral. A run of failures leaves AERA subdued for a while;
    one good result does not instantly make it cheerful.

``ExpressionAnalyser``
    Sentence-level emotion detection that understands negation, intensifiers,
    hedging and punctuation, and returns a confidence it can justify.

``prosody_for``
    Word-level timing and pitch: pauses at punctuation, emphasis on stressed
    words, and a pitch contour across the sentence. This is what a real TTS
    engine consumes as SSML, and what the formant synthesiser renders
    directly.
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any

from ..core.logging import get_logger
from .engine import Emotion

logger = get_logger("voice.expression")

#: How strongly each emotion pulls the mood baseline. Distress registers more
#: than delight, which matches how people actually carry feeling between
#: turns -- a failure lingers longer than a success.
_MOOD_WEIGHT: dict[Emotion, float] = {
    Emotion.EXCITED: 0.85,
    Emotion.HAPPY: 0.65,
    Emotion.CONFIDENT: 0.35,
    Emotion.CURIOUS: 0.15,
    Emotion.NEUTRAL: 0.0,
    Emotion.CALM: 0.10,
    Emotion.CONCERNED: -0.55,
    Emotion.SERIOUS: -0.40,
    Emotion.SAD: -0.80,
}

#: Signals that are punctuation, not vocabulary, so they apply in every
#: language. These were lost when the cue tables moved into language packs:
#: the packs carry words only, and nothing replaced the "!!"  / "?" / ":)"
#: patterns, so "It worked!!" and "All done :)" both went back to reading
#: NEUTRAL in English.
_PUNCTUATION_CUES: tuple[tuple[Emotion, re.Pattern[str], float], ...] = (
    # Two or more exclamation marks read as excitement in any script.
    (Emotion.EXCITED, re.compile(r"[!！]{2,}"), 0.9),
    (Emotion.HAPPY, re.compile(r":\)|:-\)|:D|=\)|\U0001F600-\U0001F60F"), 0.7),
    (Emotion.SAD, re.compile(r":\(|:-\(|=\("), 0.8),
    # A question at the end of the utterance, in Latin, Arabic, Greek or
    # full-width punctuation.
    (Emotion.CURIOUS, re.compile(r"[?？؟;]\s*$"), 0.55),
)

#: How much each emotion's cues count. Distress outweighs delight, because a
#: warning missed matters more than a compliment missed.
_CUE_WEIGHT: dict[Emotion, float] = {
    Emotion.EXCITED: 1.0,
    Emotion.SERIOUS: 0.95,
    Emotion.SAD: 0.9,
    Emotion.CONCERNED: 0.85,
    Emotion.HAPPY: 0.8,
    Emotion.CONFIDENT: 0.7,
    Emotion.CURIOUS: 0.6,
    Emotion.CALM: 0.5,
    Emotion.NEUTRAL: 0.4,
}


#: Where negation sends each emotion. Negating "great" is not neutrality --
#: "not great" is mildly negative, which is why this is a map rather than a
#: simple sign flip.
_NEGATED: dict[Emotion, Emotion] = {
    Emotion.EXCITED: Emotion.CONCERNED,
    Emotion.HAPPY: Emotion.CONCERNED,
    Emotion.CONFIDENT: Emotion.CONCERNED,
    Emotion.CALM: Emotion.CONCERNED,
    Emotion.CURIOUS: Emotion.NEUTRAL,
    Emotion.CONCERNED: Emotion.CALM,
    Emotion.SAD: Emotion.NEUTRAL,
    Emotion.SERIOUS: Emotion.NEUTRAL,
    Emotion.NEUTRAL: Emotion.NEUTRAL,
}


@dataclass
class EmotionReading:
    """What was detected, and how sure we are."""

    emotion: Emotion
    #: 0..1. Reflects cue strength, count and hedging.
    confidence: float
    #: 0..1. How forcefully to perform it, after intensifiers and mood.
    intensity: float
    #: The cues that fired, so a caller can explain the decision.
    reasons: list[str] = field(default_factory=list)
    negated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "emotion": self.emotion.value,
            "confidence": round(self.confidence, 3),
            "intensity": round(self.intensity, 3),
            "reasons": self.reasons,
            "negated": self.negated,
        }


@dataclass
class Mood:
    """A slow emotional baseline that persists between utterances.

    ``valence`` runs -1 (low) to +1 (bright) and decays toward zero, so AERA
    recovers from a bad run rather than staying gloomy forever.
    """

    valence: float = 0.0
    #: Seconds for an unreinforced mood to fall to about a third.
    half_life: float = 240.0
    updated_at: float = field(default_factory=time.time)

    def decayed(self, now: float | None = None) -> float:
        """Current valence, after time has passed."""
        now = now if now is not None else time.time()
        elapsed = max(0.0, now - self.updated_at)
        return self.valence * math.exp(-elapsed / self.half_life)

    def observe(self, emotion: Emotion, intensity: float, now: float | None = None) -> float:
        """Fold one utterance into the baseline.

        Weighted so a single strong signal moves the mood but does not
        overwrite it; sustained tone is what actually shifts it.
        """
        now = now if now is not None else time.time()
        current = self.decayed(now)
        target = _MOOD_WEIGHT.get(emotion, 0.0) * max(0.0, min(1.0, intensity))
        self.valence = max(-1.0, min(1.0, current * 0.72 + target * 0.28))
        self.updated_at = now
        return self.valence

    def label(self, now: float | None = None) -> str:
        """A word for the current baseline, for display."""
        value = self.decayed(now)
        if value >= 0.45:
            return "bright"
        if value >= 0.15:
            return "warm"
        if value > -0.15:
            return "even"
        if value > -0.45:
            return "subdued"
        return "low"

    def to_dict(self, now: float | None = None) -> dict[str, Any]:
        return {
            "valence": round(self.decayed(now), 3),
            "label": self.label(now),
            "half_life_s": self.half_life,
        }

    def reset(self) -> None:
        self.valence = 0.0
        self.updated_at = time.time()


class ExpressionAnalyser:
    """Detects emotion with the nuance a flat keyword match misses.

    The vocabulary comes from a language pack; the machinery around it --
    clause-scoped negation, intensifier boosting, recency weighting -- is
    language-independent.
    """

    def __init__(self, mood: Mood | None = None, *, language: str = "en") -> None:
        self.mood = mood or Mood()
        self.language = language

    def analyse(
        self, text: str, *, now: float | None = None, language: str | None = None
    ) -> EmotionReading:
        """Classify one utterance.

        Splits into sentences and weights the last one highest: "It failed.
        But I fixed it." should not read as sad.

        ``language`` overrides the analyser's default for one call, which is
        what a mixed-language conversation needs.
        """
        from .languages import compiled, get_pack

        pack = get_pack(language or self.language)
        rules = compiled(pack)
        cleaned = (text or "").strip()
        if not cleaned:
            return EmotionReading(Emotion.NEUTRAL, 0.0, 0.0, ["empty"])

        sentences = [s for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
        scores: dict[Emotion, float] = {}
        reasons: list[str] = []
        negated_any = False

        for index, sentence in enumerate(sentences):
            # The closing sentence carries the most weight; earlier ones set up.
            recency = 0.5 + 0.5 * ((index + 1) / len(sentences))
            lowered = sentence.lower()
            boost = 1.0 + 0.35 * len(
                rules["intensifiers"].findall(lowered) if rules["intensifiers"] else []
            )
            hedged = bool(rules["hedges"] and rules["hedges"].search(lowered))
            # Where each negation sits, so it only flips cues that follow it.
            # Applying it sentence-wide made "Warning: it is not safe" read as
            # calm, because the "not" flipped "warning" as well as "safe".
            negation_at = (
                [m.end() for m in rules["negations"].finditer(lowered)]
                if rules["negations"]
                else []
            )

            for emotion, pattern, weight_hint in _PUNCTUATION_CUES:
                if not pattern.search(sentence):
                    continue
                score = weight_hint * recency * boost * (0.6 if hedged else 1.0)
                scores[emotion] = scores.get(emotion, 0.0) + score
                reasons.append(f"{emotion.value} from punctuation in sentence {index + 1}")

            # Collect every cue match first, then drop the ones that sit
            # inside a longer match. French "bien sûr" (confident) contains
            # "bien" (happy) and Chinese "好奇" (curious) contains "好"
            # (happy); counting both scored the phrase twice and the
            # heavier-weighted substring won, so "bien sûr" read as happy.
            # The longest match at a position is the one the writer meant.
            spans: list[tuple[int, int, Emotion]] = []
            for emotion, pattern in rules["cues"].items():
                for match in pattern.finditer(lowered):
                    spans.append((match.start(), match.end(), emotion))

            kept: list[tuple[int, int, Emotion]] = [
                span
                for span in spans
                if not any(
                    other is not span
                    and other[0] <= span[0]
                    and other[1] >= span[1]
                    and (other[1] - other[0]) > (span[1] - span[0])
                    for other in spans
                )
            ]

            by_emotion: dict[Emotion, list[int]] = {}
            for start, _, emotion in kept:
                by_emotion.setdefault(emotion, []).append(start)

            for emotion, positions in by_emotion.items():
                hits = len(positions)
                weight = _CUE_WEIGHT.get(emotion, 0.8)
                if not hits:
                    continue
                # A cue is negated only when a negation precedes it in the
                # same clause. Scope ends at "but" or a comma, so "not X, but
                # Y" leaves Y positive.
                effective = emotion
                breaks = rules["clause_breaks"]
                if any(
                    stop <= pos and not (breaks and breaks.search(lowered, stop, pos))
                    for pos in positions
                    for stop in negation_at
                ):
                    effective = _NEGATED.get(emotion, Emotion.NEUTRAL)
                    negated_any = True
                score = weight * hits * recency * boost * (0.6 if hedged else 1.0)
                scores[effective] = scores.get(effective, 0.0) + score
                reasons.append(
                    f"{emotion.value}"
                    f"{' (negated)' if effective is not emotion else ''}"
                    f" in sentence {index + 1}"
                )

        if not scores:
            # No cue fired. Let the standing mood colour an otherwise flat line.
            baseline = self.mood.decayed(now)
            if baseline <= -0.4:
                return EmotionReading(Emotion.SERIOUS, 0.35, 0.4, ["mood: low"])
            if baseline >= 0.4:
                return EmotionReading(Emotion.HAPPY, 0.35, 0.4, ["mood: bright"])
            return EmotionReading(Emotion.NEUTRAL, 0.5, 0.35, ["no cues"])

        emotion = max(scores, key=lambda key: scores[key])
        top = scores[emotion]
        total = sum(scores.values())

        # Confidence is how dominant the winner is, not how loud it was: two
        # emotions at equal strength is genuinely ambiguous.
        confidence = min(1.0, 0.45 + 0.5 * (top / total))
        intensity = min(1.0, 0.35 + 0.30 * top)

        # A standing mood nudges intensity: bad news lands harder when things
        # have already been going badly.
        baseline = self.mood.decayed(now)
        if baseline < 0 and emotion in (Emotion.SAD, Emotion.CONCERNED, Emotion.SERIOUS):
            intensity = min(1.0, intensity + 0.15 * abs(baseline))
        elif baseline > 0 and emotion in (Emotion.HAPPY, Emotion.EXCITED):
            intensity = min(1.0, intensity + 0.15 * baseline)

        self.mood.observe(emotion, intensity, now)
        return EmotionReading(
            emotion=emotion,
            confidence=confidence,
            intensity=intensity,
            reasons=reasons[:6],
            negated=negated_any,
        )


# --------------------------------------------------------------------------- #
# prosody
# --------------------------------------------------------------------------- #
#: Pause after a mark, in milliseconds at normal pace.
_PAUSES: dict[str, float] = {
    ",": 180.0, ";": 260.0, ":": 240.0, "—": 220.0, "…": 420.0,
    ".": 380.0, "!": 340.0, "?": 400.0,
}

#: Function words are unstressed in English; content words carry the beat.
_FUNCTION_WORDS = frozenset(
    """a an the and or but if of to in on at by for with from as is are was
    were be been being do does did have has had will would can could should
    may might must it its this that these those i you he she we they them
    my your his her our their me him us not no so than then there here""".split()
)


@dataclass
class ProsodyWord:
    """One word with its timing and pitch."""

    text: str
    start_ms: float
    duration_ms: float
    #: Multiplier on the persona's pitch for this word.
    pitch_scale: float
    #: 0..1 loudness, where 0.5 is unstressed.
    emphasis: float
    pause_after_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "start_ms": round(self.start_ms, 1),
            "duration_ms": round(self.duration_ms, 1),
            "pitch_scale": round(self.pitch_scale, 3),
            "emphasis": round(self.emphasis, 3),
            "pause_after_ms": round(self.pause_after_ms, 1),
        }


#: Pitch contour per emotion, as (start, end) multipliers across the sentence.
#: Statements fall, questions rise; excitement starts high and stays up.
_CONTOUR: dict[Emotion, tuple[float, float]] = {
    Emotion.EXCITED: (1.10, 1.06),
    Emotion.HAPPY: (1.05, 0.99),
    Emotion.CONFIDENT: (1.02, 0.93),
    Emotion.CURIOUS: (0.98, 1.14),
    Emotion.NEUTRAL: (1.00, 0.96),
    Emotion.CALM: (0.98, 0.94),
    Emotion.CONCERNED: (0.99, 0.95),
    Emotion.SERIOUS: (0.97, 0.90),
    Emotion.SAD: (0.95, 0.88),
}


def prosody_for(
    text: str,
    *,
    emotion: Emotion = Emotion.NEUTRAL,
    intensity: float = 0.5,
    words_per_minute: float = 165.0,
) -> list[ProsodyWord]:
    """Per-word timing, pitch and emphasis.

    This is the layer that makes speech sound composed rather than recited:
    content words get length and pitch, punctuation gets silence, and the
    sentence traces a contour instead of sitting on one note.
    """
    tokens = [t for t in re.findall(r"\S+", text or "") if t]
    if not tokens:
        return []

    # Time is allotted per syllable, then shared out by each token's own
    # syllable count. Chinese, Japanese, Korean and Thai are written without
    # spaces, so a whole sentence arrived as a single token and was given one
    # word's worth of time -- 418 ms for seven syllables, with the mouth
    # making one movement across all of them. Weighting alone did not fix
    # that: with one token it is its own average, so the total has to come
    # from the syllables too.
    from .music import syllables_in

    weights = [max(1, syllables_in(t)) for t in tokens]
    # The English default of 165 words a minute at ~1.4 syllables a word.
    syllables_per_minute = words_per_minute * 1.4
    per_syllable_ms = 60_000.0 / max(40.0, syllables_per_minute)
    start, end = _CONTOUR.get(emotion, (1.0, 0.96))
    # Intensity exaggerates the contour: a strong feeling has more range.
    span = (end - start) * (0.6 + 0.8 * intensity)

    words: list[ProsodyWord] = []
    cursor = 0.0
    for index, token in enumerate(tokens):
        position = index / max(1, len(tokens) - 1) if len(tokens) > 1 else 0.0
        bare = re.sub(r"[^\w']", "", token).lower()

        stressed = bool(bare) and bare not in _FUNCTION_WORDS
        # ALL CAPS is written emphasis; honour it.
        shouted = len(bare) > 1 and token.isupper()

        emphasis = 0.5
        if stressed:
            emphasis += 0.22
        if shouted:
            emphasis += 0.2
        emphasis = min(1.0, emphasis * (0.85 + 0.3 * intensity))

        # Stressed syllables are longer, function words are clipped, and a
        # long word takes longer than a short one.
        duration = per_syllable_ms * weights[index] * (1.15 if stressed else 0.8)
        if shouted:
            duration *= 1.1

        pitch = start + span * position
        if stressed:
            pitch *= 1.0 + 0.05 * intensity
        if shouted:
            pitch *= 1.06

        trailing = token[-1] if token and not token[-1].isalnum() else ""
        pause = _PAUSES.get(trailing, 0.0)
        if trailing in ".!?" and index == len(tokens) - 1:
            # No trailing silence at the very end; the utterance simply stops.
            pause = 0.0
        # Sadness draws pauses out; excitement runs words together.
        pause *= 1.0 + (0.5 if emotion is Emotion.SAD else -0.3 if emotion is Emotion.EXCITED else 0.0)

        words.append(
            ProsodyWord(
                text=token,
                start_ms=cursor,
                duration_ms=duration,
                pitch_scale=pitch,
                emphasis=emphasis,
                pause_after_ms=pause,
            )
        )
        cursor += duration + pause

    return words


def to_ssml(text: str, reading: EmotionReading, *, persona_pitch_hz: float | None = None) -> str:
    """Render prosody as SSML, for engines that speak it.

    Piper, Azure and Polly all accept a subset of this. Emitting it means the
    same expression analysis drives a real engine, not just the bundled one.
    """
    words = prosody_for(text, emotion=reading.emotion, intensity=reading.intensity)
    if not words:
        return "<speak></speak>"

    parts: list[str] = []
    for word in words:
        percent = round((word.pitch_scale - 1.0) * 100, 1)
        sign = "+" if percent >= 0 else ""
        emphasis = "strong" if word.emphasis > 0.75 else "moderate" if word.emphasis > 0.6 else "none"
        parts.append(
            f'<prosody pitch="{sign}{percent}%">'
            f'<emphasis level="{emphasis}">{_escape(word.text)}</emphasis></prosody>'
        )
        if word.pause_after_ms > 0:
            parts.append(f'<break time="{round(word.pause_after_ms)}ms"/>')

    body = " ".join(parts)
    pitch_attr = f' pitch="{round(persona_pitch_hz)}Hz"' if persona_pitch_hz else ""
    return f'<speak><prosody{pitch_attr}>{body}</prosody></speak>'


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
