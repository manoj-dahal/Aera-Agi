"""Background Service Manager (docs/24-BACKGROUND-SERVICES.md).

Implements the documented Service Manager responsibilities:
- Starting services        - Monitoring health
- Stopping services        - Restarting failed services (self-healing)
- Scheduling execution

and the documented lifecycle:
    Load Configuration → Initialize → Health Check → Running → Monitoring → Shutdown
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from src.events.bus import EventBus
from src.logging.logger import get_logger

log = get_logger("services")


class ServiceState(str, Enum):
    REGISTERED = "registered"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class BackgroundService:
    """A periodic, event-aware background service."""

    name: str
    tick: Callable[[], Awaitable[None]]
    interval: float = 30.0  # seconds between ticks
    state: ServiceState = ServiceState.REGISTERED
    restarts: int = 0
    max_restarts: int = 3
    last_run: datetime | None = None
    _task: asyncio.Task | None = field(default=None, repr=False)


class ServiceManager:
    """Starts, monitors, restarts, and stops AERA background services."""

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.services: dict[str, BackgroundService] = {}

    def register(
        self,
        name: str,
        tick: Callable[[], Awaitable[None]],
        interval: float = 30.0,
    ) -> BackgroundService:
        service = BackgroundService(name=name, tick=tick, interval=interval)
        self.services[name] = service
        return service

    async def start_all(self) -> None:
        for service in self.services.values():
            await self.start(service.name)

    async def start(self, name: str) -> None:
        service = self.services[name]
        if service.state == ServiceState.RUNNING:
            return
        service.state = ServiceState.RUNNING
        service._task = asyncio.create_task(self._run(service))
        log.info("service %s started (interval=%ss)", name, service.interval)
        await self.bus.publish("service.started", {"name": name})

    async def stop(self, name: str) -> None:
        service = self.services[name]
        if service._task:
            service._task.cancel()
            service._task = None
        service.state = ServiceState.STOPPED
        await self.bus.publish("service.stopped", {"name": name})

    async def stop_all(self) -> None:
        for name in list(self.services):
            await self.stop(name)

    async def _run(self, service: BackgroundService) -> None:
        """Tick loop with self-healing restart on failure."""
        while True:
            try:
                await service.tick()
                service.last_run = datetime.now(timezone.utc)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 — self-healing per docs/24
                service.restarts += 1
                log.exception(
                    "service %s failed (restart %d/%d)",
                    service.name,
                    service.restarts,
                    service.max_restarts,
                )
                await self.bus.publish(
                    "service.failed", {"name": service.name, "restarts": service.restarts}
                )
                if service.restarts > service.max_restarts:
                    service.state = ServiceState.FAILED
                    return
            await asyncio.sleep(service.interval)

    def health(self) -> list[dict[str, object]]:
        """Health snapshot for /api/system endpoints."""
        return [
            {
                "name": s.name,
                "state": s.state.value,
                "interval": s.interval,
                "restarts": s.restarts,
                "last_run": s.last_run.isoformat() if s.last_run else None,
            }
            for s in self.services.values()
        ]
