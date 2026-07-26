# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""AERA core: configuration, events, logging, errors and the kernel.

``Kernel`` is exported lazily: it imports the agent, memory and AI subsystems,
which in turn import :mod:`aera.core.config`. Deferring that import keeps the
package import graph acyclic.
"""

from typing import TYPE_CHECKING, Any

from .config import AeraConfig, get_config, load_config, reset_config, set_config
from .errors import (
    AeraError,
    AgentNotFoundError,
    ConfigError,
    NotFoundError,
    PermissionDeniedError,
    ProviderError,
    ProviderUnavailableError,
    SandboxViolation,
    ValidationError,
)
from .events import Event, EventBus, Topics
from .logging import get_logger, setup_logging

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .kernel import Kernel, get_kernel, set_kernel

_LAZY = {"Kernel", "get_kernel", "set_kernel"}


def __getattr__(name: str) -> Any:
    """Resolve kernel exports on first access."""
    if name in _LAZY:
        from . import kernel as _kernel

        return getattr(_kernel, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | _LAZY)


__all__ = [
    "AeraConfig",
    "AeraError",
    "AgentNotFoundError",
    "ConfigError",
    "Event",
    "EventBus",
    "Kernel",
    "NotFoundError",
    "PermissionDeniedError",
    "ProviderError",
    "ProviderUnavailableError",
    "SandboxViolation",
    "Topics",
    "ValidationError",
    "get_config",
    "get_kernel",
    "get_logger",
    "load_config",
    "reset_config",
    "set_config",
    "set_kernel",
    "setup_logging",
]
