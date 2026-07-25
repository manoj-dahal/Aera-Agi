"""Hologram avatar system — animation, emotion, lip sync (docs/09-HOLOGRAM.md)."""

from src.hologram.animation import AnimationEngine
from src.hologram.lipsync import text_to_visemes
from src.hologram.models import (
    AvatarState,
    EyeState,
    Gesture,
    HologramEmotion,
    HologramFrame,
    MouthShape,
    Viseme,
)

__all__ = [
    "AnimationEngine",
    "AvatarState",
    "EyeState",
    "Gesture",
    "HologramEmotion",
    "HologramFrame",
    "MouthShape",
    "Viseme",
    "text_to_visemes",
]
