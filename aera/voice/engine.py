# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Voice system (``docs/08-VOICE-SYSTEM.md``).

Implements the orchestration half of the voice pipeline: session state, wake
word, emotion analysis and hologram synchronisation. Actual STT/TTS audio
processing is delegated to pluggable backends; the built-in backends are
no-audio stubs that keep the full pipeline functional and testable on a
headless server.
"""

from __future__ import annotations

import re
import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..core.config import VoiceSection
from ..core.events import EventBus, Topics
from ..core.logging import get_logger

logger = get_logger("voice.engine")


class Emotion(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    CALM = "calm"
    CONCERNED = "concerned"
    SAD = "sad"
    SERIOUS = "serious"
    CONFIDENT = "confident"
    CURIOUS = "curious"


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


class Transcript(BaseModel):
    text: str
    confidence: float = 1.0
    language: str = "en"
    duration_ms: float = 0.0
    is_final: bool = True


class SpeechRequest(BaseModel):
    text: str
    emotion: Emotion = Emotion.NEUTRAL
    speed: float = 1.0
    pitch: float = 1.0
    volume: int = 100
    language: str = "en"


class SpeechResult(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    text: str
    emotion: Emotion
    duration_ms: float
    visemes: list[dict[str, Any]] = Field(default_factory=list)
    #: Per-word timing, pitch and emphasis.
    prosody: list[dict[str, Any]] = Field(default_factory=list)
    #: 0..1 performance strength, after intensifiers and standing mood.
    intensity: float = 0.5
    #: The speaker's emotional baseline when this was said.
    mood: dict[str, Any] = Field(default_factory=dict)
    #: Emotion over time, one span per clause with millisecond bounds. The
    #: single ``emotion`` field above is the dominant one; a line that turns
    #: partway through ("It failed. But I fixed it!") needs both.
    emotion_timeline: list[dict[str, Any]] = Field(default_factory=list)
    audio_path: str | None = None
    engine: str = "builtin"


# --------------------------------------------------------------------------- #
# pluggable backends
# --------------------------------------------------------------------------- #
class STTBackend(ABC):
    name = "base"

    @abstractmethod
    async def transcribe(self, audio: bytes, *, language: str = "en") -> Transcript:
        ...


class TTSBackend(ABC):
    name = "base"

    @abstractmethod
    async def synthesize(self, request: SpeechRequest) -> SpeechResult:
        ...


class NullSTT(STTBackend):
    """Headless STT stub: accepts pre-transcribed text passed as UTF-8 bytes."""

    name = "null"

    async def transcribe(self, audio: bytes, *, language: str = "en") -> Transcript:
        text = audio.decode("utf-8", "replace").strip() if audio else ""
        return Transcript(
            text=text,
            confidence=1.0 if text else 0.0,
            language=language,
            duration_ms=len(text) * 60.0,
        )


class NullTTS(TTSBackend):
    """Headless TTS stub: produces timing and viseme data, no audio file."""

    name = "null"

    async def synthesize(self, request: SpeechRequest) -> SpeechResult:
        # Syllable-timed, not word-timed: text.split() returns one token
        # for a whole Chinese or Japanese line and timed it at a fraction
        # of what it takes to say.
        from .personas import speech_duration_ms

        duration = speech_duration_ms(request.text, rate=request.speed)
        return SpeechResult(
            text=request.text,
            emotion=request.emotion,
            duration_ms=round(duration, 2),
            visemes=generate_visemes(request.text, duration),
            engine=self.name,
        )


# --------------------------------------------------------------------------- #
# emotion analysis
# --------------------------------------------------------------------------- #
def detect_emotion(text: str) -> tuple[Emotion, float]:
    """Classify the emotion of an utterance.

    Delegates to ExpressionAnalyser, which understands negation, intensifiers
    and hedging -- the flat keyword match this replaced read "not great at
    all" as HAPPY. The stateless wrapper is kept because callers only want a
    label and a confidence; use the analyser directly for mood and prosody.
    """
    from .expression import ExpressionAnalyser

    reading = ExpressionAnalyser().analyse(text)
    return reading.emotion, reading.confidence


def generate_visemes(text: str, duration_ms: float, *, fps: int = 24) -> list[dict[str, Any]]:
    """Approximate lip-sync keyframes, spread evenly over the utterance.

    Used by the TTS backends, which know how long the audio is but not where
    the word boundaries fell. ``VoiceEngine.speak`` replaces the result with
    a track built from real prosody timing; this is what a caller driving a
    backend directly gets.

    Shapes come from ``scripts.shapes_for``, so every writing system is
    covered. This used to map Latin letters with its own table and returned a
    flat run of "neutral" for Devanagari, Cyrillic, Arabic, Kana, Hangul, Han
    and Thai -- the same defect that was fixed in ``word_to_visemes``, still
    live here because there were two viseme readers and only one was updated.
    """
    from .scripts import shapes_for

    shapes = shapes_for(text)
    if not shapes or duration_ms <= 0:
        return []

    # Collapse runs of the same shape. A mouth that is already open does not
    # re-open, and the formant synthesiser renders one segment per keyframe
    # with an attack and decay at each edge: leaving the repeats in chopped a
    # sustained vowel into 120 ramped segments, which amplitude-modulated the
    # tone at ~13 Hz and smeared the fundamental badly enough that anime-g's
    # 255 Hz measured weaker than a persona that was not speaking.
    # ``word_to_visemes`` had always collapsed; this one did not.
    collapsed: list[tuple[int, str]] = []
    for index, shape in enumerate(shapes):
        if not collapsed or collapsed[-1][1] != shape:
            collapsed.append((index, shape))

    # One keyframe per shape, thinned to what the frame rate can display.
    budget = max(1, int(duration_ms / 1000 * fps))
    step = max(1, len(collapsed) // budget)
    out: list[dict[str, Any]] = []
    for position in range(0, len(collapsed), step):
        index, shape = collapsed[position]
        out.append({"t": round(index / len(shapes) * duration_ms, 1), "shape": shape})
    return out[:600]


def _language_supported(language: str | None) -> bool:
    """Whether a real language pack exists, rather than the English fallback."""
    from .languages import is_supported

    return is_supported(language)


def _within_one_edit(target: str, candidate: str) -> bool:
    """True when one insertion, deletion or substitution bridges the two."""
    if abs(len(target) - len(candidate)) > 1:
        return False
    if target == candidate:
        return True

    longer, shorter = (target, candidate) if len(target) >= len(candidate) else (candidate, target)
    i = j = 0
    edited = False
    while i < len(longer) and j < len(shorter):
        if longer[i] != shorter[j]:
            if edited:
                return False
            edited = True
            if len(longer) == len(shorter):
                j += 1  # substitution
        else:
            j += 1
        i += 1
    return True


# --------------------------------------------------------------------------- #
# engine
# --------------------------------------------------------------------------- #
class VoiceEngine:
    """Coordinates STT, emotion, TTS and avatar synchronisation."""

    def __init__(
        self,
        config: VoiceSection | None = None,
        *,
        bus: EventBus | None = None,
        stt: STTBackend | None = None,
        tts: TTSBackend | None = None,
    ) -> None:
        self.config = config or VoiceSection()
        self.bus = bus
        self.stt = stt or NullSTT()
        self.tts = tts or NullTTS()
        self.state = VoiceState.IDLE
        # One analyser per engine, so its mood persists across turns rather
        # than resetting on every utterance.
        from .expression import ExpressionAnalyser

        self.expression = ExpressionAnalyser(language=self.config.language)
        self.session_id: str | None = None
        self.history: list[dict[str, Any]] = []

    # -- sessions --------------------------------------------------------- #
    async def start_listening(self) -> str:
        if not self.config.enabled:
            raise RuntimeError("voice system is disabled")
        self.session_id = uuid.uuid4().hex[:12]
        self.state = VoiceState.LISTENING
        if self.bus:
            await self.bus.publish(
                Topics.VOICE_LISTENING, {"session": self.session_id}, source="voice"
            )
        return self.session_id

    async def stop_listening(self) -> None:
        self.state = VoiceState.IDLE
        self.session_id = None

    def detect_wake_word(self, text: str) -> bool:
        """Whether the wake word was spoken.

        Matches whole words, so "area code" no longer triggers on "aera", and
        tolerates one edit so a mishearing like "ara" or "aira" still wakes
        it -- speech recognition rarely returns the exact spelling.
        """
        word = (self.config.wake_word or "").strip().lower()
        if not word:
            return False

        spoken = re.findall(r"[\w']+", (text or "").lower())
        if word in spoken:
            return True

        # One substitution, insertion or deletion. Only for words long enough
        # that a single edit does not collide with something unrelated.
        if len(word) < 4:
            return False
        return any(_within_one_edit(word, token) for token in spoken)

    # -- pipeline --------------------------------------------------------- #
    async def listen(self, audio: bytes, *, language: str | None = None) -> Transcript:
        """Speech-to-text step."""
        self.state = VoiceState.PROCESSING
        transcript = await self.stt.transcribe(audio, language=language or self.config.language)
        self.history.append(
            {"role": "user", "text": transcript.text, "at": time.time()}
        )
        self.state = VoiceState.IDLE
        return transcript

    async def speak(
        self,
        text: str,
        *,
        emotion: Emotion | str | None = None,
        speed: float | None = None,
    ) -> SpeechResult:
        """Emotion analysis + TTS + hologram sync."""
        if not text.strip():
            raise ValueError("nothing to speak")

        from .expression import prosody_for
        from .phonetics import normalise_for_speech

        # What the engine should actually say: "87%" -> "eighty seven percent".
        # Emotion is read from the original, since normalisation only expands
        # symbols and would not change the sentiment.
        language = self.config.language
        spoken = normalise_for_speech(text, language) or text

        # Expression is always on. Analysis runs even when the caller names an
        # emotion, so the standing mood keeps moving and the delivery still
        # has intensity behind it -- a forced label used to come out flat,
        # hardcoded at 0.6 and ignoring the mood entirely.
        reading = self.expression.analyse(text, language=language)

        if emotion is not None:
            # The caller decides *what* is felt; the analyser still decides
            # how strongly, from the words and the mood behind them.
            emotion_value = Emotion(emotion)
            confidence = 1.0
            intensity = reading.intensity
        else:
            emotion_value = reading.emotion
            confidence = reading.confidence
            intensity = reading.intensity

        self.state = VoiceState.SPEAKING
        result = await self.tts.synthesize(
            SpeechRequest(
                text=spoken,
                emotion=emotion_value,
                speed=speed or self.config.speech_speed,
                pitch=self.config.pitch,
                volume=self.config.volume,
                language=language,
            )
        )
        # Word-level timing, pitch and emphasis: what makes the delivery read
        # as composed rather than recited.
        words = prosody_for(spoken, emotion=emotion_value, intensity=intensity)
        result.prosody = [w.to_dict() for w in words]

        # Rebuild the mouth track from that timing. The backend's own visemes
        # spread evenly over the utterance and kept the mouth moving through
        # pauses; these follow the words and close in the gaps.
        from .phonetics import visemes_for_words

        aligned = visemes_for_words(result.prosody)
        if aligned:
            result.visemes = aligned
        result.intensity = round(intensity, 3)
        result.mood = self.expression.mood.to_dict()

        # Emotion over time, so the avatar can change expression mid-line
        # instead of holding the winner for the whole utterance.
        # Scaled onto the real audio length so the expression track and the
        # mouth stay in step.
        timeline = self.expression.timeline(
            text, language=language, total_ms=result.duration_ms
        )
        result.emotion_timeline = [span.to_dict() for span in timeline.spans]

        self.history.append({"role": "assistant", "text": text, "at": time.time()})
        self.state = VoiceState.IDLE

        if self.bus:
            await self.bus.publish(
                Topics.VOICE_SPOKE,
                {
                    "text": text,
                    "emotion": emotion_value.value,
                    "confidence": round(confidence, 2),
                    "duration_ms": result.duration_ms,
                },
                source="voice",
            )
            if self.config.hologram_sync:
                await self.bus.publish(
                    Topics.AVATAR_EMOTION,
                    {
                        "emotion": emotion_value.value,
                        "intensity": round(intensity, 2),
                        "confidence": round(confidence, 2),
                        "mood": self.expression.mood.to_dict(),
                        # The avatar drives its face from this, not from the
                        # single label above.
                        "emotion_timeline": result.emotion_timeline,
                        "visemes": result.visemes[:120],
                        "prosody": result.prosody[:120],
                        "duration_ms": result.duration_ms,
                    },
                    source="voice",
                )
        return result

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "state": self.state.value,
            "session": self.session_id,
            "wake_word": self.config.wake_word,
            "language": self.config.language,
            "language_supported": _language_supported(self.config.language),
            # Always on; the field remains for existing clients.
            "emotion_enabled": True,
            "hologram_sync": self.config.hologram_sync,
            "stt_backend": self.stt.name,
            "tts_backend": self.tts.name,
            "mood": self.expression.mood.to_dict(),
            "turns": len(self.history),
        }
