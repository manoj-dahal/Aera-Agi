"""Hologram avatar state machine (``docs/09-HOLOGRAM.md``).

Server-side state for the 3D avatar: visibility, emotion, gestures, idle
animation and lip-sync timing. The renderer (web or Flutter) subscribes to the
emitted events and draws the result.
"""

from __future__ import annotations

import random
import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..core.events import EventBus, Topics
from ..core.logging import get_logger

logger = get_logger("hologram.avatar")


class Gesture(str, Enum):
    IDLE = "idle"
    NOD = "nod"
    SHAKE = "shake"
    WAVE = "wave"
    POINT = "point"
    THINK = "think"
    SHRUG = "shrug"
    LEAN_IN = "lean_in"
    TILT = "tilt"


class AvatarEmotion(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    CALM = "calm"
    CONCERNED = "concerned"
    SAD = "sad"
    SERIOUS = "serious"
    CONFIDENT = "confident"
    CURIOUS = "curious"
    THINKING = "thinking"


#: Emotions map onto blend-shape weights the renderer applies.
EMOTION_BLENDSHAPES: dict[AvatarEmotion, dict[str, float]] = {
    AvatarEmotion.NEUTRAL: {"brow": 0.0, "smile": 0.05, "eye_open": 0.85},
    AvatarEmotion.HAPPY: {"brow": 0.25, "smile": 0.75, "eye_open": 0.9},
    AvatarEmotion.EXCITED: {"brow": 0.5, "smile": 0.9, "eye_open": 1.0},
    AvatarEmotion.CALM: {"brow": -0.1, "smile": 0.2, "eye_open": 0.7},
    AvatarEmotion.CONCERNED: {"brow": -0.4, "smile": -0.1, "eye_open": 0.9},
    AvatarEmotion.SAD: {"brow": -0.55, "smile": -0.35, "eye_open": 0.6},
    AvatarEmotion.SERIOUS: {"brow": -0.3, "smile": 0.0, "eye_open": 0.95},
    AvatarEmotion.CONFIDENT: {"brow": 0.15, "smile": 0.4, "eye_open": 0.9},
    AvatarEmotion.CURIOUS: {"brow": 0.35, "smile": 0.2, "eye_open": 1.0},
    AvatarEmotion.THINKING: {"brow": 0.1, "smile": 0.0, "eye_open": 0.55},
}


class AvatarState(BaseModel):
    visible: bool = True
    emotion: AvatarEmotion = AvatarEmotion.NEUTRAL
    intensity: float = 0.5
    gesture: Gesture = Gesture.IDLE
    speaking: bool = False
    gaze: tuple[float, float] = (0.0, 0.0)
    blendshapes: dict[str, float] = Field(default_factory=dict)
    updated_at: float = Field(default_factory=time.time)

    def to_public(self) -> dict[str, Any]:
        return {
            "visible": self.visible,
            "emotion": self.emotion.value,
            "intensity": round(self.intensity, 2),
            "gesture": self.gesture.value,
            "speaking": self.speaking,
            "gaze": {"x": round(self.gaze[0], 3), "y": round(self.gaze[1], 3)},
            "blendshapes": {k: round(v, 3) for k, v in self.blendshapes.items()},
            "updated_at": self.updated_at,
        }


class HologramController:
    """Drives avatar state and broadcasts changes over the event bus."""

    def __init__(self, *, bus: EventBus | None = None, enabled: bool = True) -> None:
        self.bus = bus
        self.enabled = enabled
        self.state = AvatarState(blendshapes=dict(EMOTION_BLENDSHAPES[AvatarEmotion.NEUTRAL]))
        self._lipsync: list[dict[str, Any]] = []

    async def show(self) -> AvatarState:
        self.state.visible = True
        return await self._commit("avatar.shown")

    async def hide(self) -> AvatarState:
        self.state.visible = False
        return await self._commit("avatar.hidden")

    async def set_emotion(
        self, emotion: AvatarEmotion | str, *, intensity: float = 0.7
    ) -> AvatarState:
        """Blend the avatar toward an emotional pose."""
        value = AvatarEmotion(emotion)
        self.state.emotion = value
        self.state.intensity = max(0.0, min(1.0, intensity))
        base = EMOTION_BLENDSHAPES[value]
        # Scale expressive channels by intensity; keep eyes readable.
        self.state.blendshapes = {
            key: (weight * self.state.intensity if key != "eye_open" else weight)
            for key, weight in base.items()
        }
        return await self._commit(Topics.AVATAR_EMOTION)

    async def play_gesture(self, gesture: Gesture | str) -> AvatarState:
        self.state.gesture = Gesture(gesture)
        return await self._commit(Topics.AVATAR_GESTURE)

    async def start_speaking(self, visemes: list[dict[str, Any]] | None = None) -> AvatarState:
        self.state.speaking = True
        self._lipsync = visemes or []
        return await self._commit("avatar.speaking")

    async def stop_speaking(self) -> AvatarState:
        self.state.speaking = False
        self._lipsync = []
        return await self._commit("avatar.silent")

    async def look_at(self, x: float, y: float) -> AvatarState:
        """Aim the gaze; coordinates are clamped to [-1, 1]."""
        self.state.gaze = (max(-1.0, min(1.0, x)), max(-1.0, min(1.0, y)))
        return await self._commit("avatar.gaze")

    def idle_frame(self) -> dict[str, Any]:
        """Subtle breathing/blink motion so the avatar never looks frozen."""
        t = time.time()
        return {
            "breath": round(0.5 + 0.5 * random.uniform(0.95, 1.05) * _sin(t / 4), 3),
            "blink": random.random() < 0.02,
            "sway": round(_sin(t / 7) * 0.02, 4),
        }

    def lipsync_at(self, elapsed_ms: float) -> str:
        """Viseme shape for a point in the current utterance."""
        shape = "neutral"
        for frame in self._lipsync:
            if frame["t"] <= elapsed_ms:
                shape = frame["shape"]
            else:
                break
        return shape

    async def sync_with_voice(self, payload: dict[str, Any]) -> None:
        """Event handler bound to ``avatar.emotion`` events from the voice engine."""
        if not self.enabled:
            return
        emotion = payload.get("emotion", "neutral")
        try:
            await self.set_emotion(emotion, intensity=float(payload.get("intensity", 0.7)))
        except ValueError:
            await self.set_emotion(AvatarEmotion.NEUTRAL)
        if payload.get("visemes"):
            await self.start_speaking(payload["visemes"])

    async def _commit(self, topic: str) -> AvatarState:
        self.state.updated_at = time.time()
        if self.bus and self.enabled:
            await self.bus.publish(topic, self.state.to_public(), source="hologram")
        return self.state

    def status(self) -> dict[str, Any]:
        return {"enabled": self.enabled, **self.state.to_public()}


def _sin(x: float) -> float:
    import math

    return math.sin(x)
