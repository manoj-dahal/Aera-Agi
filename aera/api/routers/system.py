# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""System, settings and health endpoints."""

from __future__ import annotations

import platform
import sys
import time

from fastapi import APIRouter, Depends, Query, Request

from ... import __version__
from ..deps import get_kernel_dep
from ..schemas import ok

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
async def system_status(kernel=Depends(get_kernel_dep)):
    return ok(kernel.status())


@router.get("/info")
async def system_info(kernel=Depends(get_kernel_dep)):
    cfg = kernel.config
    return ok(
        {
            "name": cfg.system.name,
            "version": __version__,
            "environment": cfg.system.environment,
            "python": sys.version.split()[0],
            "platform": f"{platform.system()} {platform.release()}",
            "architecture": platform.machine(),
            "debug": cfg.system.debug,
            "language": cfg.system.language,
            "timezone": cfg.system.timezone,
        }
    )


@router.get("/telemetry")
async def telemetry(kernel=Depends(get_kernel_dep)):
    """Live CPU, GPU, RAM, disk, network and temperature readings."""
    return ok(await kernel.telemetry.snapshot_async(force=True))


@router.get("/settings")
async def get_settings(kernel=Depends(get_kernel_dep)):
    """Non-sensitive configuration for the dashboard."""
    cfg = kernel.config
    return ok(
        {
            "settings": cfg.settings.model_dump(),
            "voice": cfg.voice.model_dump(),
            "memory": cfg.memory.model_dump(),
            "agents": cfg.agents.model_dump(),
            "models": {
                "default": cfg.models.default,
                "routing_mode": cfg.models.routing_mode,
                "local": cfg.models.local.model_dump(),
                "providers": sorted((cfg.models.providers or {}).keys()),
            },
            "workspace": cfg.workspace.model_dump(),
        }
    )


@router.get("/events")
async def recent_events(
    pattern: str = Query("*"),
    limit: int = Query(50, ge=1, le=200),
    kernel=Depends(get_kernel_dep),
):
    return ok({"events": [e.to_dict() for e in kernel.bus.history(pattern, limit)]})


@router.get("/secrets")
async def list_secrets(kernel=Depends(get_kernel_dep)):
    """Secret names with masked values - never returns plaintext."""
    if kernel.vault is None:
        return ok({"secrets": {}})
    return ok({"secrets": kernel.vault.masked()})


@router.get("/audit")
async def audit_log(limit: int = Query(50, ge=1, le=500), kernel=Depends(get_kernel_dep)):
    if kernel.audit is None:
        return ok({"entries": []})
    return ok({"entries": kernel.audit.entries(limit)})


# --------------------------------------------------------------------------- #
# unauthenticated health probe (mounted at the app root)
# --------------------------------------------------------------------------- #
health_router = APIRouter(tags=["system"])


@health_router.get("/health")
async def health(request: Request):
    kernel = getattr(request.app.state, "kernel", None)
    ready = bool(kernel and kernel.ready)
    return {
        "success": True,
        "status": "healthy" if ready else "starting",
        "version": __version__,
        "ready": ready,
        "uptime_seconds": round(time.time() - kernel.started_at, 1)
        if kernel and kernel.started_at
        else 0,
    }
