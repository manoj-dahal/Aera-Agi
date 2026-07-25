"""WebSocket endpoints — realtime chat and events (docs/api/WebSocket.md)."""

from src.websocket.chat import ws_router

__all__ = ["ws_router"]
