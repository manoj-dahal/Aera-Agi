# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from ..core.errors import AeraError
from ..core.kernel import Kernel


class ServiceUnavailable(AeraError):
    status_code = 503
    code = "service_unavailable"


def get_kernel_dep(request: Request) -> Kernel:
    """Resolve the kernel stored on the FastAPI app state."""
    kernel: Kernel | None = getattr(request.app.state, "kernel", None)
    if kernel is None or not kernel.ready:
        raise ServiceUnavailable("AERA kernel is not ready")
    return kernel


def get_memory(request: Request):
    kernel = get_kernel_dep(request)
    if kernel.memory is None:
        raise ServiceUnavailable("memory subsystem is unavailable")
    return kernel.memory


def get_router_dep(request: Request):
    kernel = get_kernel_dep(request)
    if kernel.router is None:
        raise ServiceUnavailable("AI router is unavailable")
    return kernel.router


def get_registry(request: Request):
    kernel = get_kernel_dep(request)
    if kernel.registry is None:
        raise ServiceUnavailable("agent registry is unavailable")
    return kernel.registry


def get_workspace(request: Request):
    kernel = get_kernel_dep(request)
    if kernel.workspace is None:
        raise ServiceUnavailable("workspace subsystem is unavailable")
    return kernel.workspace


def get_automation(request: Request):
    kernel = get_kernel_dep(request)
    if kernel.automation is None:
        raise ServiceUnavailable("automation engine is unavailable")
    return kernel.automation


def get_voice(request: Request):
    kernel = get_kernel_dep(request)
    if kernel.voice is None:
        raise ServiceUnavailable("voice subsystem is unavailable")
    return kernel.voice


def get_hologram(request: Request):
    kernel = get_kernel_dep(request)
    if kernel.hologram is None:
        raise ServiceUnavailable("hologram subsystem is unavailable")
    return kernel.hologram
