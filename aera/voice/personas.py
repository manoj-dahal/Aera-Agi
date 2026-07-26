# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Voice personas for the avatar variants (docs/08-VOICE-SYSTEM.md).

The hologram ships two figures, ``anime-g`` and ``anime-b``. They need to
sound different, and the difference has to be described in parameters a real
TTS engine can honour rather than baked into one engine's private settings.

A persona is that description: pitch, speed, timbre and emotion response. Any
backend can consume it -- Piper takes speaker id and length scale, ElevenLabs
takes stability and similarity, and the bundled formant synthesiser takes the
fundamental frequency directly.

On the bundled synthesiser: it is a formant-based vocoder, not a text-to-speech
engine. It produces correctly pitched, correctly timed, viseme-synchronised
speech-like audio -- so lip-sync, timing and persona differences can be
developed and heard -- but it does not articulate words. That distinction is
stated wherever the audio surfaces; ``FORMANT_NOTE`` is the wording. Install a
real engine and register it, and the same personas drive it.
"""

from __future__ import annotations

import array
import hashlib
import math
import random
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.logging import get_logger
from .engine import Emotion, SpeechRequest, SpeechResult, TTSBackend, generate_visemes

logger = get_logger("voice.personas")

#: Said wherever bundled audio is offered, so nobody mistakes it for TTS.
FORMANT_NOTE = (
    "AERA bundles a formant synthesiser, not a speech engine: the audio carries "
    "the persona's pitch, pacing and lip-sync timing but does not articulate "
    "words. Register a TTS backend (Piper, Coqui, ElevenLabs) for real speech."
)


@dataclass(frozen=True)
class VoicePersona:
    """How one character sounds.

    ``base_pitch_hz`` is the speaking fundamental. Adult female speech centres
    around 200 Hz and male around 120 Hz; anime performance sits higher than
    both, which is why these are 255 and 145 rather than the natural averages.
    """

    id: str
    label: str
    description: str
    #: Avatar variant this belongs to, matching AvatarVariant.
    variant: str
    base_pitch_hz: float
    #: Multiplier on the engine's default rate. Above 1.0 is faster.
    speed: float = 1.0
    #: How far pitch moves with emotion. Expressive characters vary more.
    pitch_range: float = 0.18
    #: Relative strength of upper formants: brighter reads younger.
    brightness: float = 1.0
    #: Vibrato depth as a fraction of the fundamental.
    vibrato: float = 0.012
    #: Hints for real engines, passed through untouched.
    engine_hints: dict[str, Any] = field(default_factory=dict)

    def pitch_for(self, emotion: Emotion | str) -> float:
        """Speaking pitch for an emotion, in hertz.

        Excitement lifts pitch, sadness drops it. The shift is scaled by
        ``pitch_range`` so a reserved persona stays reserved.
        """
        shift = _EMOTION_PITCH.get(Emotion(emotion), 0.0)
        return self.base_pitch_hz * (1.0 + shift * self.pitch_range)

    def speed_for(self, emotion: Emotion | str) -> float:
        return self.speed * (1.0 + _EMOTION_SPEED.get(Emotion(emotion), 0.0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "variant": self.variant,
            "base_pitch_hz": self.base_pitch_hz,
            "speed": self.speed,
            "pitch_range": self.pitch_range,
            "brightness": self.brightness,
            "vibrato": self.vibrato,
            "engine_hints": self.engine_hints,
        }


#: Relative pitch shift per emotion, before persona scaling.
_EMOTION_PITCH: dict[Emotion, float] = {
    Emotion.EXCITED: 0.9,
    Emotion.HAPPY: 0.5,
    Emotion.CURIOUS: 0.35,
    Emotion.CONFIDENT: 0.1,
    Emotion.NEUTRAL: 0.0,
    Emotion.CALM: -0.15,
    Emotion.CONCERNED: -0.2,
    Emotion.SERIOUS: -0.35,
    Emotion.SAD: -0.5,
}

@dataclass(frozen=True)
class EmotionAcoustics:
    """How one emotion reshapes the voice, beyond pitch and pace.

    Pitch and speed alone give a chipmunk-and-slug range: the same voice fast
    and high, or slow and low. Real affect also changes how *steady* the voice
    is, how much breath is in it, and how bright the timbre sits. These are
    the dimensions phonetics research consistently ties to perceived emotion.
    """

    #: Cycle-to-cycle pitch instability, as a fraction of f0. Distress raises
    #: it; a composed voice is near-periodic.
    jitter: float = 0.004
    #: Aperiodic noise mixed in. Sadness and fear are breathy; anger is not.
    breathiness: float = 0.06
    #: Slow amplitude wobble, the audible shake in an upset voice.
    tremor: float = 0.0
    #: Vibrato speed in hertz. Excitement is fast, sadness slow and heavy.
    vibrato_rate: float = 5.2
    #: Multiplier on the persona's vibrato depth.
    vibrato_scale: float = 1.0
    #: Upper-formant gain. Bright reads alert, dark reads withdrawn.
    brightness_scale: float = 1.0
    #: Strength of the second harmonic: more gives a tenser, edgier tone.
    harmonic_tilt: float = 1.0
    #: Onset sharpness. A clipped attack sounds urgent, a soft one gentle.
    attack: float = 1.0

    def to_dict(self) -> dict[str, float]:
        return {
            "jitter": self.jitter,
            "breathiness": self.breathiness,
            "tremor": self.tremor,
            "vibrato_rate_hz": self.vibrato_rate,
            "vibrato_scale": self.vibrato_scale,
            "brightness_scale": self.brightness_scale,
            "harmonic_tilt": self.harmonic_tilt,
            "attack": self.attack,
        }


#: One acoustic profile per emotion. Values follow the direction reported in
#: the affective-speech literature: aroused states are brighter, faster and
#: tenser; low-mood states are breathier, darker and less steady.
EMOTION_ACOUSTICS: dict[Emotion, EmotionAcoustics] = {
    Emotion.EXCITED: EmotionAcoustics(
        jitter=0.009, breathiness=0.04, tremor=0.03, vibrato_rate=7.0,
        vibrato_scale=1.5, brightness_scale=1.22, harmonic_tilt=1.35, attack=1.5,
    ),
    Emotion.HAPPY: EmotionAcoustics(
        jitter=0.006, breathiness=0.05, tremor=0.015, vibrato_rate=6.2,
        vibrato_scale=1.25, brightness_scale=1.12, harmonic_tilt=1.15, attack=1.2,
    ),
    Emotion.CONFIDENT: EmotionAcoustics(
        # Deliberately the steadiest profile: certainty sounds periodic.
        jitter=0.002, breathiness=0.03, tremor=0.0, vibrato_rate=5.0,
        vibrato_scale=0.7, brightness_scale=1.05, harmonic_tilt=1.2, attack=1.35,
    ),
    Emotion.CURIOUS: EmotionAcoustics(
        jitter=0.005, breathiness=0.07, tremor=0.01, vibrato_rate=6.0,
        vibrato_scale=1.15, brightness_scale=1.1, harmonic_tilt=1.0, attack=1.1,
    ),
    Emotion.NEUTRAL: EmotionAcoustics(),
    Emotion.CALM: EmotionAcoustics(
        jitter=0.003, breathiness=0.10, tremor=0.0, vibrato_rate=4.4,
        vibrato_scale=0.8, brightness_scale=0.94, harmonic_tilt=0.85, attack=0.75,
    ),
    Emotion.CONCERNED: EmotionAcoustics(
        jitter=0.010, breathiness=0.09, tremor=0.035, vibrato_rate=5.6,
        vibrato_scale=1.1, brightness_scale=0.96, harmonic_tilt=1.1, attack=1.1,
    ),
    Emotion.SERIOUS: EmotionAcoustics(
        # Low breath and low tremor: gravity is controlled, not shaky.
        jitter=0.003, breathiness=0.02, tremor=0.0, vibrato_rate=4.2,
        vibrato_scale=0.55, brightness_scale=0.88, harmonic_tilt=1.3, attack=1.4,
    ),
    Emotion.SAD: EmotionAcoustics(
        jitter=0.012, breathiness=0.20, tremor=0.05, vibrato_rate=3.6,
        vibrato_scale=1.3, brightness_scale=0.80, harmonic_tilt=0.7, attack=0.55,
    ),
}


def acoustics_for(emotion: Emotion | str) -> EmotionAcoustics:
    """The acoustic profile for an emotion, defaulting to neutral."""
    try:
        return EMOTION_ACOUSTICS.get(Emotion(emotion), EMOTION_ACOUSTICS[Emotion.NEUTRAL])
    except ValueError:
        return EMOTION_ACOUSTICS[Emotion.NEUTRAL]


#: Relative speed change per emotion.
_EMOTION_SPEED: dict[Emotion, float] = {
    Emotion.EXCITED: 0.14,
    Emotion.HAPPY: 0.06,
    Emotion.CURIOUS: 0.02,
    Emotion.CONFIDENT: 0.0,
    Emotion.NEUTRAL: 0.0,
    Emotion.CALM: -0.08,
    Emotion.CONCERNED: -0.05,
    Emotion.SERIOUS: -0.06,
    Emotion.SAD: -0.16,
}


ANIME_GIRL = VoicePersona(
    id="anime-g",
    label="Anime Girl",
    description="Bright, light and expressive. Pairs with the anime-g avatar.",
    variant="feminine",
    # Above the ~200 Hz adult female average: anime delivery is pitched up.
    base_pitch_hz=255.0,
    speed=1.06,
    pitch_range=0.24,
    brightness=1.35,
    vibrato=0.018,
    engine_hints={
        "piper": {"voice": "en_US-amy-medium", "length_scale": 0.94},
        "coqui": {"speaker": "female-en-5", "style": "cheerful"},
        "elevenlabs": {"stability": 0.35, "similarity_boost": 0.75, "style": 0.6},
    },
)

ANIME_BOY = VoicePersona(
    id="anime-b",
    label="Anime Boy",
    description="Warm, steady and youthful. Pairs with the anime-b avatar.",
    variant="masculine",
    # Above the ~120 Hz adult male average, and deliberately not so low that
    # it reads as an adult man.
    base_pitch_hz=145.0,
    speed=1.0,
    pitch_range=0.17,
    brightness=1.05,
    vibrato=0.010,
    engine_hints={
        "piper": {"voice": "en_US-ryan-medium", "length_scale": 1.0},
        "coqui": {"speaker": "male-en-2", "style": "friendly"},
        "elevenlabs": {"stability": 0.5, "similarity_boost": 0.7, "style": 0.35},
    },
)

NEUTRAL = VoicePersona(
    id="aera",
    label="AERA",
    description="The default assistant voice: even, unhurried, no character.",
    variant="unspecified",
    base_pitch_hz=190.0,
    speed=1.0,
    pitch_range=0.12,
    brightness=1.0,
    vibrato=0.006,
    engine_hints={"piper": {"voice": "en_US-lessac-medium"}},
)

PERSONAS: dict[str, VoicePersona] = {p.id: p for p in (ANIME_GIRL, ANIME_BOY, NEUTRAL)}

#: Avatar variant -> persona, so selecting a model picks up its voice.
BY_VARIANT: dict[str, VoicePersona] = {
    "feminine": ANIME_GIRL,
    "masculine": ANIME_BOY,
    "neutral": NEUTRAL,
    "unspecified": NEUTRAL,
}


def get_persona(persona_id: str | None) -> VoicePersona:
    """Look up a persona, falling back to the neutral voice."""
    if not persona_id:
        return NEUTRAL
    return PERSONAS.get(persona_id.strip().lower(), NEUTRAL)


def persona_for_variant(variant: str | None) -> VoicePersona:
    """The voice that belongs with an avatar variant."""
    return BY_VARIANT.get((variant or "").strip().lower(), NEUTRAL)


# --------------------------------------------------------------------------- #
# formant synthesiser
# --------------------------------------------------------------------------- #
#: Formant pairs (F1, F2) in hertz for each viseme the engine emits. These are
#: the resonances that make a vowel identifiable; the values are the standard
#: measured centres for the nearest English vowel.
_VISEME_FORMANTS: dict[str, tuple[float, float]] = {
    "open": (730.0, 1090.0),    # "ah"
    "narrow": (390.0, 1990.0),  # "ee"/"oo" blend
    "teeth": (500.0, 1750.0),   # labiodental
    "tongue": (530.0, 1840.0),  # alveolar
    "closed": (300.0, 900.0),   # lips together, muffled
    "neutral": (500.0, 1500.0), # schwa
}

SAMPLE_RATE = 22_050


def _envelope(position: float, total: float, *, attack: float = 1.0) -> float:
    """Amplitude ramp, so segments do not click at their boundaries.

    ``attack`` sharpens or softens the onset: above 1.0 the sound arrives
    abruptly, which reads as urgency; below 1.0 it fades in, which reads as
    hesitance.
    """
    edge = min(0.15, total * 0.25)
    if edge <= 0:
        return 1.0
    rise = edge / max(0.2, attack)
    if position < rise:
        return position / rise
    if position > total - edge:
        return max(0.0, (total - position) / edge)
    return 1.0


#: Speaking rate as syllables per minute. English averages about 165 words a
#: minute at roughly 1.4 syllables a word. Counting syllables rather than
#: words is what makes this work outside Latin script: Chinese, Japanese,
#: Korean and Thai are written without spaces, so ``text.split()`` returned 1
#: for a whole line and a seven-syllable Japanese sentence was timed at
#: 364 ms -- about a third of what it takes to say.
SYLLABLES_PER_MINUTE = 240.0


def speech_duration_ms(text: str, *, rate: float = 1.0) -> float:
    """How long a line takes to say, in any script.

    Falls back to a word estimate only when the syllable counter returns
    nothing, which happens for text that is all digits or punctuation.
    """
    from .music import syllables_in

    syllables = syllables_in(text)
    if not syllables:
        # No countable syllables: approximate from words so a line of
        # numerals still gets a plausible duration rather than zero.
        syllables = max(1, len(text.split())) * 2
    return (syllables / SYLLABLES_PER_MINUTE) * 60_000 / max(0.3, rate)


def synthesize_wav(
    text: str,
    persona: VoicePersona,
    *,
    emotion: Emotion = Emotion.NEUTRAL,
    speed: float = 1.0,
    path: Path | None = None,
) -> tuple[Path | None, float, list[dict[str, Any]]]:
    """Render persona-pitched audio driven by the viseme track.

    Returns ``(path, duration_ms, visemes)``. This is a vocoder, not a speech
    engine -- see ``FORMANT_NOTE``. It exists so persona differences and
    lip-sync timing are audible and testable without a downloadable model.
    """
    rate = max(0.3, persona.speed_for(emotion) * speed)
    duration_ms = speech_duration_ms(text, rate=rate)
    visemes = generate_visemes(text, duration_ms)

    if path is None:
        return None, round(duration_ms, 2), visemes

    pitch = persona.pitch_for(emotion)
    voice = acoustics_for(emotion)
    # Deterministic noise: the same line must render identically every time.
    # blake2b rather than hash(), which Python randomises per process -- that
    # made renders stable within a run but different between runs, and the
    # jitter moved the measured pitch enough to fail a test intermittently.
    seed = hashlib.blake2b(
        f"{persona.id}|{emotion.value}|{text}".encode(), digest_size=8
    ).digest()
    rng = random.Random(int.from_bytes(seed, "big"))
    total_samples = int(SAMPLE_RATE * duration_ms / 1000.0)
    samples = array.array("h", bytes(2 * total_samples))

    # Walk the viseme track; each entry holds until the next one starts.
    track = visemes or [{"t": 0.0, "shape": "neutral"}]
    for index, frame in enumerate(track):
        start_ms = float(frame.get("t", 0.0))
        end_ms = float(track[index + 1]["t"]) if index + 1 < len(track) else duration_ms
        if end_ms <= start_ms:
            continue

        f1, f2 = _VISEME_FORMANTS.get(str(frame.get("shape", "neutral")), _VISEME_FORMANTS["neutral"])
        # Emotion shifts the formants as well as the persona: a withdrawn
        # voice is darker, an alert one brighter.
        f1 *= persona.brightness * voice.brightness_scale
        f2 *= persona.brightness * voice.brightness_scale

        begin = int(SAMPLE_RATE * start_ms / 1000.0)
        finish = min(total_samples, int(SAMPLE_RATE * end_ms / 1000.0))
        span = (finish - begin) / SAMPLE_RATE

        depth = persona.vibrato * voice.vibrato_scale
        for i in range(begin, finish):
            t = i / SAMPLE_RATE
            local = (i - begin) / SAMPLE_RATE

            # Vibrato keeps a sustained tone from sounding synthetic; jitter
            # is the cycle-to-cycle wobble that distress adds on top.
            wobble = math.sin(2 * math.pi * voice.vibrato_rate * t)
            unsteady = rng.uniform(-voice.jitter, voice.jitter)
            f0 = pitch * (1.0 + depth * wobble + unsteady)

            value = (
                0.45 * math.sin(2 * math.pi * f0 * t)
                + 0.22 * voice.harmonic_tilt * math.sin(2 * math.pi * f0 * 2 * t)
                + 0.28 * math.sin(2 * math.pi * f1 * t)
                + 0.16 * math.sin(2 * math.pi * f2 * t)
            )
            # Breath: aperiodic noise, which is what makes a voice sound
            # tired or fragile rather than merely lower.
            if voice.breathiness:
                value += voice.breathiness * rng.uniform(-1.0, 1.0)
            # Tremor: the slow amplitude shake of an upset voice.
            if voice.tremor:
                value *= 1.0 + voice.tremor * math.sin(2 * math.pi * 4.0 * t)

            value *= _envelope(local, span, attack=voice.attack)
            samples[i] = int(max(-1.0, min(1.0, value)) * 11_000)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(samples.tobytes())

    return path, round(duration_ms, 2), visemes


def audio_filename(text: str, persona_id: str, emotion: Emotion | str) -> str:
    """A stable filename for one rendered line.

    Content-addressed with blake2b, so the same request always maps to the
    same file and a cached render is actually reused. Three backends each
    built this name with ``hash()``, which Python randomises per process --
    the cache missed on every restart and the directory filled with
    duplicates of identical audio. ``synthesize_wav`` had already been fixed
    for exactly this; the filenames beside it had not.
    """
    value = emotion.value if isinstance(emotion, Emotion) else str(emotion)
    digest = hashlib.blake2b(
        f"{text}|{persona_id}|{value}".encode(), digest_size=8
    ).hexdigest()
    return f"{persona_id}-{digest}.wav"


class PersonaTTS(TTSBackend):
    """TTS backend that speaks with a persona.

    Writes a WAV when ``output_dir`` is set, and reports timing and visemes
    either way, so the hologram animates whether or not audio is produced.
    """

    name = "persona"

    def __init__(
        self,
        persona: VoicePersona | None = None,
        *,
        output_dir: Path | None = None,
    ) -> None:
        self.persona = persona or NEUTRAL
        self.output_dir = Path(output_dir) if output_dir else None

    def use(self, persona: VoicePersona) -> None:
        """Switch voice, e.g. when the active avatar changes."""
        self.persona = persona
        logger.info("voice persona: %s (%.0f Hz)", persona.label, persona.base_pitch_hz)

    async def synthesize(self, request: SpeechRequest) -> SpeechResult:
        target = None
        if self.output_dir is not None:
            target = self.output_dir / audio_filename(
                request.text, self.persona.id, request.emotion
            )

        path, duration_ms, visemes = synthesize_wav(
            request.text,
            self.persona,
            emotion=request.emotion,
            speed=request.speed,
            path=target,
        )

        return SpeechResult(
            text=request.text,
            emotion=request.emotion,
            duration_ms=duration_ms,
            visemes=visemes,
            audio_path=str(path) if path else None,
            engine=f"{self.name}:{self.persona.id}",
        )
