# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""AI orchestration: providers, routing and prompt plumbing."""

from .base import (
    AIProvider,
    CompletionRequest,
    CompletionResponse,
    Message,
    ModelInfo,
    Role,
    Usage,
)
from .providers import PROVIDER_REGISTRY, create_provider
from .router import ModelRouter

__all__ = [
    "AIProvider",
    "CompletionRequest",
    "CompletionResponse",
    "Message",
    "ModelInfo",
    "ModelRouter",
    "PROVIDER_REGISTRY",
    "Role",
    "Usage",
    "create_provider",
]
