# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Canonical AERA error hierarchy.

Every error carries an HTTP status code and a stable machine-readable ``code``
so the API layer can translate exceptions into the documented error envelope::

    {"success": false, "code": 404, "error": "Model not found"}
"""

from __future__ import annotations


class AeraError(Exception):
    """Base class for every AERA error."""

    status_code: int = 500
    code: str = "aera_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        payload = {
            "success": False,
            "code": self.status_code,
            "error": self.message,
            "type": self.code,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class ConfigError(AeraError):
    status_code = 500
    code = "config_error"


class ValidationError(AeraError):
    status_code = 400
    code = "validation_error"


class NotFoundError(AeraError):
    status_code = 404
    code = "not_found"


class ConflictError(AeraError):
    status_code = 409
    code = "conflict"


class AuthenticationError(AeraError):
    status_code = 401
    code = "unauthenticated"


class PermissionDeniedError(AeraError):
    status_code = 403
    code = "permission_denied"


class RateLimitError(AeraError):
    status_code = 429
    code = "rate_limited"


class ProviderError(AeraError):
    """Raised when an upstream AI provider fails."""

    status_code = 502
    code = "provider_error"


class ProviderUnavailableError(ProviderError):
    status_code = 503
    code = "provider_unavailable"


class AgentError(AeraError):
    status_code = 500
    code = "agent_error"


class AgentNotFoundError(NotFoundError):
    code = "agent_not_found"


class TaskExecutionError(AgentError):
    code = "task_failed"


class MemoryError_(AeraError):
    status_code = 500
    code = "memory_error"


class WorkflowError(AeraError):
    status_code = 500
    code = "workflow_error"


class SandboxViolation(PermissionDeniedError):
    """Raised when an operation escapes its permitted sandbox root."""

    code = "sandbox_violation"
