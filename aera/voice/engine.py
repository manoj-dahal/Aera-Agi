"""Voice system (``docs/08-VOICE-SYSTEM.md``).

Implements the orchestration half of the voice pipeline: session state, wake
word, emotion analysis and hologram synchronisation. Actual STT/TTS audio
processing is delegated to pluggable backends; the built-in backends are
no-audio stubs that keep the full pipeline functional and testable on a
headless server.
"""

from __future__ import annotations

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
        words = request.text.split()
        # ~165 wpm baseline, scaled by the requested speed
        duration = (len(words) / 165.0) * 60_000 / max(0.25, request.speed)
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
_EMOTION_HINTS: list[tuple[Emotion, tuple[str, ...]]] = [
    (Emotion.EXCITED, (r"\b(amazing|awesome|fantastic|incredible|brilliant)\b", r"!{2,}")),
    (Emotion.HAPPY, (r"\b(great|good news|glad|happy|nice work|well done|success)\b", r":\)")),
    (Emotion.CONCERNED, (r"\b(warning|careful|risk|danger|caution|deprecated|breaking)\b",)),
    (Emotion.SAD, (r"\b(sorry|unfortunately|failed|regret|unable)\b",)),
    (Emotion.SERIOUS, (r"\b(critical|security|vulnerability|urgent|error|fatal)\b",)),
    (Emotion.CURIOUS, (r"\?\s*$", r"\b(interesting|wonder|curious)\b")),
    (Emotion.CONFIDENT, (r"\b(certainly|definitely|absolutely|confirmed|done)\b",)),
]


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


_VISEME_MAP = {
    **dict.fromkeys("aeiou", "open"),
    **dict.fromkeys("bmp", "closed"),
    **dict.fromkeys("fv", "teeth"),
    **dict.fromkeys("lnt d", "tongue"),
    **dict.fromkeys("swz", "narrow"),
}


def generate_visemes(text: str, duration_ms: float, *, fps: int = 24) -> list[dict[str, Any]]:
    """Approximate lip-sync keyframes for the hologram avatar."""
    letters = [c for c in text.lower() if c.isalpha()]
    if not letters or duration_ms <= 0:
        return []
    frames = max(1, int(duration_ms / 1000 * fps))
    step = max(1, len(letters) // frames)
    out: list[dict[str, Any]] = []
    for i in range(0, len(letters), step):
        out.append(
            {
                "t": round(i / len(letters) * duration_ms, 1),
                "shape": _VISEME_MAP.get(letters[i], "neutral"),
            }
        )
    return out[:600]


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

        self.expression = ExpressionAnalyser()
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
        word = (self.config.wake_word or "").strip().lower()
        return bool(word) and word in (text or "").lower()

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

        if emotion is None and self.config.emotion:
            reading = self.expression.analyse(text)
            emotion_value, confidence = reading.emotion, reading.confidence
            intensity = reading.intensity
        else:
            emotion_value = Emotion(emotion) if emotion else Emotion.NEUTRAL
            confidence = 1.0
            intensity = 0.6

        self.state = VoiceState.SPEAKING
        result = await self.tts.synthesize(
            SpeechRequest(
                text=text,
                emotion=emotion_value,
                speed=speed or self.config.speech_speed,
                pitch=self.config.pitch,
                volume=self.config.volume,
                language=self.config.language,
            )
        )
        # Word-level timing, pitch and emphasis: what makes the delivery read
        # as composed rather than recited.
        words = prosody_for(text, emotion=emotion_value, intensity=intensity)
        result.prosody = [w.to_dict() for w in words]
        result.intensity = round(intensity, 3)
        result.mood = self.expression.mood.to_dict()

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
            "emotion_enabled": self.config.emotion,
            "hologram_sync": self.config.hologram_sync,
            "stt_backend": self.stt.name,
            "tts_backend": self.tts.name,
            "mood": self.expression.mood.to_dict(),
            "turns": len(self.history),
        }
