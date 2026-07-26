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
