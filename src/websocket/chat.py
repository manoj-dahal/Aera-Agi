"""WebSocket chat endpoint (docs/api/WebSocket.md)."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.common.schemas import TaskRequest

ws_router = APIRouter()


@ws_router.websocket("/ws")
async def websocket_chat(ws: WebSocket) -> None:
    """Bidirectional chat channel: send text, receive TaskResponse JSON."""
    await ws.accept()
    try:
        while True:
            message = await ws.receive_text()
            result = await ws.app.state.agents.execute(TaskRequest(message=message))
            await ws.send_json(result.model_dump())
    except WebSocketDisconnect:
        pass
