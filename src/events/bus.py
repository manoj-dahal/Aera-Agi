"""Event Bus — async pub/sub backbone (docs/24-BACKGROUND-SERVICES.md).

"Unlike traditional background processes, AERA's services are event-driven
and AI-aware. Services only activate when needed."

Subsystems publish typed events; subscribers (services, agents, hologram)
react without polling.
"""

from __future__ import annotations

import asyncio
import fnmatch
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.logging.logger import get_logger

log = get_logger("events")

Handler = Callable[["Event"], Awaitable[None] | None]


@dataclass
class Event:
    """A typed event, e.g. topic='voice.emotion.changed'."""

    topic: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    """Async pub/sub with wildcard topics ('memory.*', '*')."""

    def __init__(self, history_size: int = 100) -> None:
        self._subscribers: dict[str, list[Handler]] = {}
        self._history: list[Event] = []
        self._history_size = history_size

    def subscribe(self, pattern: str, handler: Handler) -> None:
        self._subscribers.setdefault(pattern, []).append(handler)

    def unsubscribe(self, pattern: str, handler: Handler) -> None:
        handlers = self._subscribers.get(pattern, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, topic: str, data: dict[str, Any] | None = None) -> Event:
        event = Event(topic=topic, data=data or {})
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history.pop(0)

        for pattern, handlers in self._subscribers.items():
            if fnmatch.fnmatch(topic, pattern):
                for handler in handlers:
                    try:
                        result = handler(event)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception:  # noqa: BLE001 — one bad handler must not break the bus
                        log.exception("event handler failed for topic %s", topic)
        return event

    def history(self, pattern: str = "*", limit: int = 50) -> list[Event]:
        matched = [e for e in self._history if fnmatch.fnmatch(e.topic, pattern)]
        return matched[-limit:]
