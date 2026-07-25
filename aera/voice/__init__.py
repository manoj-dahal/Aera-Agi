"""Voice subsystem: STT, TTS, emotion and conversation control."""

from .engine import (
    Emotion,
    NullSTT,
    NullTTS,
    SpeechRequest,
    SpeechResult,
    STTBackend,
    Transcript,
    TTSBackend,
    VoiceEngine,
    VoiceState,
    detect_emotion,
    generate_visemes,
)

__all__ = [
    "Emotion",
    "NullSTT",
    "NullTTS",
    "STTBackend",
    "SpeechRequest",
    "SpeechResult",
    "TTSBackend",
    "Transcript",
    "VoiceEngine",
    "VoiceState",
    "detect_emotion",
    "generate_visemes",
]
