"""WebSocket gateway (``docs/api/WebSocket.md``).

Provides live two-way messaging: streaming AI tokens, agent events, memory
updates, voice and avatar events, plus ping/pong heartbeats.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...core.logging import get_logger

logger = get_logger("api.ws")

router = APIRouter()


class ConnectionManager:
    """Tracks live sockets so the server can broadcast events."""

    def __init__(self) -> None:
        self.active: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        client_id = uuid.uuid4().hex[:12]
        self.active[client_id] = websocket
        logger.info("websocket connected: %s (%d live)", client_id, len(self.active))
        return client_id

    def disconnect(self, client_id: str) -> None:
        self.active.pop(client_id, None)
        logger.info("websocket disconnected: %s (%d live)", client_id, len(self.active))

    async def send(self, client_id: str, payload: dict) -> None:
        websocket = self.active.get(client_id)
        if websocket is None:
            return
        with contextlib.suppress(Exception):
            await websocket.send_text(json.dumps(payload))

    async def broadcast(self, payload: dict) -> None:
        message = json.dumps(payload)
        for client_id, websocket in list(self.active.items()):
            try:
                await websocket.send_text(message)
            except Exception:  # noqa: BLE001 - drop dead sockets
                self.disconnect(client_id)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    kernel = getattr(websocket.app.state, "kernel", None)
    if kernel is None or not kernel.ready:
        await websocket.close(code=1013, reason="AERA is not ready")
        return

    client_id = await manager.connect(websocket)
    forwarder = asyncio.create_task(_forward_events(kernel, client_id))

    await manager.send(
        client_id,
        {"type": "connected", "client_id": client_id, "version": kernel.config.system.version},
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send(client_id, {"type": "error", "error": "invalid JSON"})
                continue
            await _handle(kernel, client_id, message)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("websocket error for %s", client_id)
    finally:
        forwarder.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await forwarder
        manager.disconnect(client_id)


async def _forward_events(kernel, client_id: str) -> None:
    """Relay selected bus events to this client."""
    patterns = ("agent.*", "memory.*", "ai.completed", "voice.*", "avatar.*",
                "automation.*", "notification.*", "workspace.*")
    async for event in kernel.bus.stream("*"):
        if not any(_match(p, event.topic) for p in patterns):
            continue
        await manager.send(
            client_id,
            {"type": "event", "topic": event.topic, "payload": event.payload,
             "timestamp": event.timestamp},
        )


def _match(pattern: str, topic: str) -> bool:
    import fnmatch

    return fnmatch.fnmatchcase(topic, pattern)


async def _handle(kernel, client_id: str, message: dict) -> None:
    """Dispatch one inbound socket message."""
    kind = str(message.get("type", "")).lower()

    if kind == "ping":
        await manager.send(client_id, {"type": "pong", "timestamp": message.get("timestamp")})
        return

    if kind in ("message", "chat"):
        text = str(message.get("content") or message.get("message") or "").strip()
        if not text:
            await manager.send(client_id, {"type": "error", "error": "empty message"})
            return

        conversation_id = message.get("conversation_id") or client_id
        await manager.send(
            client_id, {"type": "stream.start", "conversation_id": conversation_id}
        )

        context = ""
        if kernel.memory is not None:
            context = await kernel.memory.build_context(text, conversation_id=conversation_id)

        system = "You are AERA, an AI operating system with persistent memory."
        if context:
            system += f"\n\n{context}"

        pieces: list[str] = []
        try:
            async for token in kernel.router.stream(text, system=system):
                pieces.append(token)
                await manager.send(client_id, {"type": "stream.token", "content": token})
        except Exception as exc:  # noqa: BLE001
            await manager.send(client_id, {"type": "error", "error": str(exc)})
            return

        full = "".join(pieces)
        if kernel.memory is not None and full:
            await kernel.memory.remember_exchange(
                text, full, conversation_id=conversation_id
            )
        await manager.send(
            client_id,
            {"type": "stream.done", "content": full, "conversation_id": conversation_id},
        )
        return

    if kind == "agent":
        from ...agents.base import Capability, Task

        task = Task(
            capability=Capability(message.get("capability", "conversation")),
            input=str(message.get("input", "")),
            requester="websocket",
        )
        result = await kernel.registry.dispatch(task, agent_name=message.get("agent"))
        await manager.send(client_id, {"type": "agent.result", "result": result.to_public()})
        return

    if kind == "voice":
        text = str(message.get("text", ""))
        if text and kernel.voice is not None:
            result = await kernel.voice.speak(text)
            await manager.send(client_id, {"type": "voice.result", "result": result.model_dump()})
        return

    if kind == "memory":
        query = str(message.get("query", ""))
        results = await kernel.memory.recall(query, limit=int(message.get("limit", 5)))
        await manager.send(
            client_id,
            {"type": "memory.results", "results": [r.to_public() for r in results]},
        )
        return

    if kind == "status":
        await manager.send(client_id, {"type": "status", "data": kernel.status()})
        return

    await manager.send(client_id, {"type": "error", "error": f"unknown message type '{kind}'"})
