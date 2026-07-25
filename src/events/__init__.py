"""Event bus — pub/sub used by background services (docs/24-BACKGROUND-SERVICES.md)."""

from src.events.bus import Event, EventBus

__all__ = ["Event", "EventBus"]
