# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Hologram subsystem: avatar state, emotion and lip-sync."""

from .avatar import (
    EMOTION_BLENDSHAPES,
    AvatarEmotion,
    AvatarState,
    Gesture,
    HologramController,
)
from .loader import AvatarKind, AvatarLibrary, AvatarModel, AvatarVariant

__all__ = [
    "EMOTION_BLENDSHAPES",
    "AvatarKind",
    "AvatarLibrary",
    "AvatarModel",
    "AvatarVariant",
    "AvatarEmotion",
    "AvatarState",
    "Gesture",
    "HologramController",
]
