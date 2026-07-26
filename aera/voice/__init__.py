# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

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
