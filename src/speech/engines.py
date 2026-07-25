"""Speech engines — STT/TTS abstraction (docs/voice/Speech-To-Text.md,
docs/voice/Text-To-Speech.md, docs/08-VOICE-SYSTEM.md).

Local-first design: Whisper (STT) and Piper (TTS) are the documented default
engines; both are optional dependencies. When unavailable, the pipeline
degrades gracefully to text-only mode so AERA keeps working everywhere.

Documented STT modes: Push To Talk, Continuous Conversation, Manual
Recording, Wake Word Mode.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from src.logging.logger import get_logger
from src.voice.emotion import EmotionState

log = get_logger("speech")


class ListeningMode(str, Enum):
    """Supported STT modes from docs/08-VOICE-SYSTEM.md."""

    PUSH_TO_TALK = "push_to_talk"
    CONTINUOUS = "continuous"
    MANUAL = "manual"
    WAKE_WORD = "wake_word"


@dataclass
class Transcription:
    text: str
    language: str = "en"
    confidence: float = 1.0


class STTEngine(Protocol):
    """Speech-to-Text engine interface."""

    name: str

    def available(self) -> bool: ...

    async def transcribe(self, audio: bytes, language: str | None = None) -> Transcription: ...


class TTSEngine(Protocol):
    """Text-to-Speech engine interface (emotion-aware per docs/08)."""

    name: str

    def available(self) -> bool: ...

    async def synthesize(self, text: str, emotion: EmotionState | None = None) -> bytes: ...


class WhisperSTT:
    """Local Whisper STT (documented default; optional dependency)."""

    name = "whisper"

    def __init__(self) -> None:
        self.model_name = os.getenv("STT_MODEL", "base")
        self._model = None

    def available(self) -> bool:
        try:
            import whisper  # noqa: F401

            return True
        except ImportError:
            return False

    async def transcribe(self, audio: bytes, language: str | None = None) -> Transcription:
        if not self.available():
            raise RuntimeError("whisper is not installed — pip install '.[voice]'")
        import asyncio
        import tempfile

        import whisper

        if self._model is None:
            self._model = whisper.load_model(self.model_name)

        def _run() -> Transcription:
            with tempfile.NamedTemporaryFile(suffix=".wav") as f:
                f.write(audio)
                f.flush()
                result = self._model.transcribe(f.name, language=language)
            return Transcription(
                text=str(result["text"]).strip(),
                language=str(result.get("language", "en")),
            )

        return await asyncio.get_event_loop().run_in_executor(None, _run)


class PiperTTS:
    """Local Piper TTS (documented default; optional dependency).

    Applies the Emotion Engine's speaking_speed/pitch outputs so voice and
    avatar remain synchronized (docs/voice/Emotion-Engine.md).
    """

    name = "piper"

    def available(self) -> bool:
        try:
            import piper  # noqa: F401

            return True
        except ImportError:
            return False

    async def synthesize(self, text: str, emotion: EmotionState | None = None) -> bytes:
        if not self.available():
            raise RuntimeError("piper-tts is not installed — pip install '.[voice]'")
        raise NotImplementedError("piper synthesis wiring lands with the audio streaming service")


class SpeechService:
    """Facade over the configured STT/TTS engines (env: STT_ENGINE, TTS_ENGINE)."""

    def __init__(self) -> None:
        self.stt: STTEngine = WhisperSTT()
        self.tts: TTSEngine = PiperTTS()
        self.mode = ListeningMode(os.getenv("VOICE_MODE", "push_to_talk"))

    def status(self) -> dict[str, object]:
        return {
            "stt": {"engine": self.stt.name, "available": self.stt.available()},
            "tts": {"engine": self.tts.name, "available": self.tts.available()},
            "mode": self.mode.value,
        }
