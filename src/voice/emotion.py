"""Emotion Engine (docs/voice/Emotion-Engine.md, docs/08-VOICE-SYSTEM.md).

Documented pipeline:

    Conversation → Sentiment Analysis → Emotion Selection → Voice Style → Avatar Expression

Documented outputs: Voice Tone, Facial Expression, Speaking Speed, Pitch, Gestures.

The engine analyzes conversation context, user sentiment, confidence levels,
and system events to pick one of the 10 documented emotions. Voice and avatar
always remain synchronized — both consume the same EmotionState.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Emotion(str, Enum):
    """The 10 supported emotions from docs/voice/Emotion-Engine.md."""

    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    CURIOUS = "curious"
    CALM = "calm"
    CONFIDENT = "confident"
    CONCERNED = "concerned"
    THINKING = "thinking"
    FRIENDLY = "friendly"
    SERIOUS = "serious"


@dataclass(frozen=True)
class EmotionState:
    """The synchronized output consumed by both voice (TTS) and avatar."""

    emotion: Emotion
    voice_tone: str  # tone description for the TTS engine
    facial_expression: str  # avatar expression preset
    speaking_speed: float  # 1.0 = normal
    pitch: float  # 1.0 = normal
    gesture: str  # avatar gesture preset


# Voice-style + avatar presets per emotion (docs/voice/Emotion-Engine.md outputs)
_PROFILES: dict[Emotion, EmotionState] = {
    Emotion.NEUTRAL: EmotionState(Emotion.NEUTRAL, "even", "relaxed", 1.0, 1.0, "idle"),
    Emotion.HAPPY: EmotionState(Emotion.HAPPY, "warm", "smile", 1.05, 1.08, "open-hands"),
    Emotion.EXCITED: EmotionState(Emotion.EXCITED, "bright", "wide-smile", 1.15, 1.12, "energetic"),
    Emotion.CURIOUS: EmotionState(Emotion.CURIOUS, "inquisitive", "raised-brow", 1.0, 1.05, "head-tilt"),
    Emotion.CALM: EmotionState(Emotion.CALM, "soft", "gentle", 0.92, 0.96, "still"),
    Emotion.CONFIDENT: EmotionState(Emotion.CONFIDENT, "assured", "steady-gaze", 1.0, 0.98, "upright"),
    Emotion.CONCERNED: EmotionState(Emotion.CONCERNED, "gentle", "furrowed", 0.9, 0.95, "lean-in"),
    Emotion.THINKING: EmotionState(Emotion.THINKING, "measured", "look-up", 0.88, 0.97, "chin-touch"),
    Emotion.FRIENDLY: EmotionState(Emotion.FRIENDLY, "welcoming", "soft-smile", 1.0, 1.03, "nod"),
    Emotion.SERIOUS: EmotionState(Emotion.SERIOUS, "firm", "focused", 0.95, 0.94, "still"),
}

# Lightweight keyword sentiment cues; replaced by model-based analysis later.
_CUES: list[tuple[Emotion, tuple[str, ...]]] = [
    (Emotion.CONCERNED, ("error", "problem", "fail", "worried", "broken", "crash", "wrong", "sad")),
    (Emotion.EXCITED, ("amazing", "awesome", "great news", "wow", "excellent", "love it", "!")),
    (Emotion.HAPPY, ("thanks", "thank you", "great", "nice", "perfect", "happy")),
    (Emotion.CURIOUS, ("why", "how", "what if", "curious", "wonder", "?")),
    (Emotion.THINKING, ("analyze", "think", "consider", "complex", "plan", "reason")),
    (Emotion.SERIOUS, ("security", "urgent", "critical", "warning", "important", "deadline")),
    (Emotion.CALM, ("relax", "slow", "calm", "gently", "no rush")),
    (Emotion.FRIENDLY, ("hello", "hi ", "hey", "good morning", "good evening", "welcome")),
]


class EmotionEngine:
    """Selects the emotional tone of every AI response."""

    def __init__(self) -> None:
        self._current: EmotionState = _PROFILES[Emotion.NEUTRAL]

    @property
    def current(self) -> EmotionState:
        return self._current

    def analyze(self, user_message: str, ai_response: str = "") -> EmotionState:
        """Sentiment Analysis → Emotion Selection (docs pipeline)."""
        text = f"{user_message} {ai_response}".lower()
        best, best_score = Emotion.NEUTRAL, 0
        for emotion, cues in _CUES:
            score = sum(1 for cue in cues if cue in text)
            if score > best_score:
                best, best_score = emotion, score
        self._current = _PROFILES[best]
        return self._current

    def set(self, emotion: Emotion) -> EmotionState:
        """Explicit emotion override (e.g. system events)."""
        self._current = _PROFILES[emotion]
        return self._current
