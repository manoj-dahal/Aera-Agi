# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Internal asynchronous Event Bus.

Per the architecture spec, no module talks to another directly: every
cross-module signal travels over the bus. Subscribers may use exact topic
names or ``prefix.*`` wildcards.

    bus = EventBus()
    await bus.subscribe("agent.*", handler)
    await bus.publish("agent.started", {"agent": "core"})
"""

from __future__ import annotations

import asyncio
import contextlib
import fnmatch
import logging
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("aera.events")

Handler = Callable[["Event"], Awaitable[None] | None]


@dataclass(slots=True)
class Event:
    """A single message on the bus."""

    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source": self.source,
        }


class Subscription:
    """Handle returned by :meth:`EventBus.subscribe`; used to unsubscribe."""

    __slots__ = ("id", "pattern", "handler", "_bus")

    def __init__(self, bus: EventBus, pattern: str, handler: Handler) -> None:
        self.id = uuid.uuid4().hex
        self.pattern = pattern
        self.handler = handler
        self._bus = bus

    async def unsubscribe(self) -> None:
        await self._bus.unsubscribe(self)


class EventBus:
    """Lightweight in-process publish/subscribe bus with a replay buffer."""

    def __init__(self, *, history: int = 256) -> None:
        self._subs: list[Subscription] = []
        self._lock = asyncio.Lock()
        self._history: deque[Event] = deque(maxlen=history)
        self._published = 0

    # ------------------------------------------------------------------ #
    # subscription management
    # ------------------------------------------------------------------ #
    async def subscribe(self, pattern: str, handler: Handler) -> Subscription:
        sub = Subscription(self, pattern, handler)
        async with self._lock:
            self._subs.append(sub)
        return sub

    async def unsubscribe(self, sub: Subscription) -> None:
        async with self._lock:
            self._subs = [s for s in self._subs if s.id != sub.id]

    def subscriber_count(self, topic: str | None = None) -> int:
        if topic is None:
            return len(self._subs)
        return sum(1 for s in self._subs if self._matches(s.pattern, topic))

    # ------------------------------------------------------------------ #
    # publishing
    # ------------------------------------------------------------------ #
    async def publish(
        self,
        topic: str,
        payload: dict[str, Any] | None = None,
        *,
        source: str | None = None,
    ) -> Event:
        """Publish an event and await every matching handler.

        A failing handler is logged and skipped; it never breaks the publisher
        or the other subscribers.
        """
        event = Event(topic=topic, payload=payload or {}, source=source)
        self._history.append(event)
        self._published += 1

        async with self._lock:
            targets = [s for s in self._subs if self._matches(s.pattern, topic)]

        for sub in targets:
            try:
                result = sub.handler(event)
                if asyncio.iscoroutine(result) or isinstance(result, Awaitable):
                    await result
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - a bad subscriber must not kill the bus
                logger.exception("event handler failed for topic %s", topic)
        return event

    def emit(self, topic: str, payload: dict[str, Any] | None = None, *, source: str | None = None):
        """Fire-and-forget publish usable from sync code inside a loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None
        return loop.create_task(self.publish(topic, payload, source=source))

    # ------------------------------------------------------------------ #
    # streaming / introspection
    # ------------------------------------------------------------------ #
    async def stream(self, pattern: str = "*", *, queue_size: int = 128):
        """Async-iterate events matching ``pattern`` (used by the WebSocket API)."""
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=queue_size)

        async def _enqueue(event: Event) -> None:
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(event)

        sub = await self.subscribe(pattern, _enqueue)
        try:
            while True:
                yield await queue.get()
        finally:
            await self.unsubscribe(sub)

    def history(self, pattern: str = "*", limit: int = 50) -> list[Event]:
        items = [e for e in self._history if self._matches(pattern, e.topic)]
        return items[-limit:]

    @property
    def published_count(self) -> int:
        return self._published

    @staticmethod
    def _matches(pattern: str, topic: str) -> bool:
        if pattern in ("*", topic):
            return True
        return fnmatch.fnmatchcase(topic, pattern)


# Canonical topic names published across the platform.
class Topics:
    SYSTEM_STARTED = "system.started"
    SYSTEM_READY = "system.ready"
    SYSTEM_STOPPING = "system.stopping"

    AGENT_REGISTERED = "agent.registered"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_TASK_STARTED = "agent.task.started"
    AGENT_TASK_COMPLETED = "agent.task.completed"
    AGENT_TASK_FAILED = "agent.task.failed"

    MEMORY_STORED = "memory.stored"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_REMOVED = "memory.removed"
    MEMORY_RECALLED = "memory.recalled"

    AI_REQUEST = "ai.request"
    AI_COMPLETED = "ai.completed"
    AI_STREAM_TOKEN = "ai.stream.token"
    AI_FAILED = "ai.failed"

    WORKSPACE_OPENED = "workspace.opened"
    WORKSPACE_INDEXED = "workspace.indexed"

    VOICE_LISTENING = "voice.listening"
    VOICE_SPOKE = "voice.spoke"

    AVATAR_EMOTION = "avatar.emotion"
    AVATAR_GESTURE = "avatar.gesture"

    AUTOMATION_STARTED = "automation.started"
    AUTOMATION_COMPLETED = "automation.completed"
    AUTOMATION_FAILED = "automation.failed"

    PLUGIN_INSTALLED = "plugin.installed"
    DEVICE_CONNECTED = "device.connected"
    NOTIFICATION = "notification.created"
    SECURITY_ALERT = "security.alert"
