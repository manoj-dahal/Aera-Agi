"""Audit System (docs/21-SECURITY.md "Audit Logging").

"Every important event is recorded." Documented examples: Login, Logout,
Plugin Installed/Removed, Permission Granted/Denied, AI Provider Changes,
Security Alerts.

Events are kept in a bounded in-memory ring (dashboard "Recent Security
Events") and published to the event bus so background services can react.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.logging.logger import get_logger

if TYPE_CHECKING:
    from src.events.bus import EventBus

log = get_logger("security.audit")


@dataclass
class AuditEntry:
    event: str
    subject: str
    detail: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog:
    def __init__(self, bus: EventBus | None = None, size: int = 500) -> None:
        self.bus = bus
        self._entries: list[AuditEntry] = []
        self._size = size

    def record(self, event: str, *, subject: str = "system", detail: str = "") -> AuditEntry:
        entry = AuditEntry(event=event, subject=subject, detail=detail)
        self._entries.append(entry)
        if len(self._entries) > self._size:
            self._entries.pop(0)
        log.info("audit: %s subject=%s %s", event, subject, detail)
        if self.bus is not None:
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    self.bus.publish(f"security.audit.{event}", {"subject": subject, "detail": detail})
                )
            except RuntimeError:
                pass  # no running loop (sync context) — ring buffer still records
        return entry

    def recent(self, limit: int = 50, event_prefix: str = "") -> list[AuditEntry]:
        matched = [e for e in self._entries if e.event.startswith(event_prefix)]
        return matched[-limit:]
