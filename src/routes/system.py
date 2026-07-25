"""System routes — health and status (docs/26-API.md)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request

from src import __version__

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe used by Docker healthchecks and the dashboard."""
    return {
        "status": "ok",
        "version": __version__,
        "env": os.getenv("AERA_ENV", "development"),
    }


@router.get("/system/info")
async def system_info(request: Request) -> dict[str, object]:
    """System information for the dashboard status panel."""
    local_ai = await request.app.state.router.ollama_available()
    return {
        "name": "AERA",
        "version": __version__,
        "modules": {
            "memory_graph": "active",
            "agents": "active",
            "model_router": "active",
            "local_ai": "online" if local_ai else "offline",
            "voice": "planned",
            "hologram": "planned",
            "automation": "planned",
        },
    }
