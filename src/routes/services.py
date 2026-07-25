"""Service routes — background service health (docs/24-BACKGROUND-SERVICES.md)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/services", tags=["services"])


@router.get("")
async def list_services(request: Request) -> list[dict[str, object]]:
    """Health snapshot of every registered background service."""
    return request.app.state.system.services.health()


@router.post("/{name}/restart", status_code=202)
async def restart_service(name: str, request: Request) -> dict[str, str]:
    manager = request.app.state.system.services
    if name not in manager.services:
        raise HTTPException(status_code=404, detail="service not found")
    await manager.stop(name)
    manager.services[name].restarts = 0
    await manager.start(name)
    return {"name": name, "state": manager.services[name].state.value}


@router.get("/events")
async def recent_events(request: Request, pattern: str = "*", limit: int = 50) -> list[dict]:
    """Recent events from the event bus (docs/24 — event-driven services)."""
    events = request.app.state.system.bus.history(pattern, limit=min(limit, 100))
    return [
        {"topic": e.topic, "data": e.data, "timestamp": e.timestamp.isoformat()}
        for e in events
    ]
