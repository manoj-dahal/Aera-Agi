# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""REST and WebSocket routers."""

from . import (
    agents,
    automation,
    avatars,
    chat,
    docker,
    memory,
    plugins,
    skills,
    system,
    uploads,
    voice,
    websocket,
    workspace,
)

__all__ = [
    "agents", "automation", "avatars", "chat", "docker", "memory", "skills", "system",
    "plugins", "uploads", "voice",
    "websocket", "workspace",
]
