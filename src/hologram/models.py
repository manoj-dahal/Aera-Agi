"""Hologram avatar model (docs/09-HOLOGRAM.md).

Documented avatar states: Idle, Listening, Thinking, Speaking, Processing,
Offline — each with its documented animation set.

Documented hologram emotions (14): Neutral, Happy, Excited, Calm, Friendly,
Curious, Thinking, Focused, Confident, Serious, Surprised, Laughing,
Playful, Empathetic.

Documented eye states (docs/hologram/Eye-Tracking.md): Looking at User,
Looking Away, Reading, Thinking, Searching, Idle.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AvatarState(str, Enum):
    """The six documented avatar states."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    PROCESSING = "processing"
    OFFLINE = "offline"


class HologramEmotion(str, Enum):
    """The 14 documented hologram emotions (docs/09 Emotion System)."""

    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    CALM = "calm"
    FRIENDLY = "friendly"
    CURIOUS = "curious"
    THINKING = "thinking"
    FOCUSED = "focused"
    CONFIDENT = "confident"
    SERIOUS = "serious"
    SURPRISED = "surprised"
    LAUGHING = "laughing"
    PLAYFUL = "playful"
    EMPATHETIC = "empathetic"


class EyeState(str, Enum):
    """Documented eye tracking states."""

    LOOKING_AT_USER = "looking_at_user"
    LOOKING_AWAY = "looking_away"
    READING = "reading"
    THINKING = "thinking"
    SEARCHING = "searching"
    IDLE = "idle"


class Gesture(str, Enum):
    """The 10 documented gestures (docs/hologram/Gesture-System.md)."""

    WAVE = "wave"
    POINT = "point"
    NOD = "nod"
    SHAKE_HEAD = "shake_head"
    HAND_RAISE = "hand_raise"
    OPEN_HANDS = "open_hands"
    CLAP = "clap"
    EXPLAIN = "explain"
    CELEBRATE = "celebrate"
    THINKING_POSE = "thinking_pose"


class MouthShape(str, Enum):
    """The 9 documented mouth shapes (docs/hologram/Lip-Sync.md)."""

    A = "A"
    E = "E"
    I = "I"  # noqa: E741 — documented shape name
    O = "O"  # noqa: E741
    U = "U"
    CLOSED = "closed"
    SMILE = "smile"
    WIDE = "wide"
    RELAXED = "relaxed"


#: Documented per-state animation sets (docs/09 "Avatar States").
STATE_ANIMATIONS: dict[AvatarState, list[str]] = {
    AvatarState.IDLE: [
        "breathing", "blinking", "small-head-movement", "eye-movement", "idle-posture",
    ],
    AvatarState.LISTENING: [
        "eye-contact", "head-tilt", "listening-posture", "subtle-breathing",
        "focused-expression",
    ],
    AvatarState.THINKING: [
        "looking-upward", "thinking-expression", "slow-blinking", "soft-glow",
        "gentle-floating",
    ],
    AvatarState.SPEAKING: [
        "lip-sync", "facial-expressions", "hand-gestures", "eye-contact",
        "natural-body-movement",
    ],
    AvatarState.PROCESSING: [
        "soft-pulse", "floating-particles", "energy-ring", "status-indicator",
    ],
    AvatarState.OFFLINE: ["dim-hologram", "slow-pulse", "neutral-expression"],
}

#: Eye state per avatar state (docs/hologram/Eye-Tracking.md).
STATE_EYES: dict[AvatarState, EyeState] = {
    AvatarState.IDLE: EyeState.IDLE,
    AvatarState.LISTENING: EyeState.LOOKING_AT_USER,
    AvatarState.THINKING: EyeState.THINKING,
    AvatarState.SPEAKING: EyeState.LOOKING_AT_USER,
    AvatarState.PROCESSING: EyeState.SEARCHING,
    AvatarState.OFFLINE: EyeState.IDLE,
}


class Viseme(BaseModel):
    """One lip-sync frame: mouth shape + duration."""

    shape: MouthShape
    duration_ms: int = Field(gt=0)


class HologramFrame(BaseModel):
    """Full avatar snapshot consumed by the renderer (frontend)."""

    state: AvatarState
    animations: list[str]
    emotion: HologramEmotion
    eye_state: EyeState
    gesture: Gesture | None = None
    glow_intensity: float = Field(default=0.5, ge=0.0, le=1.0)
