# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Security subsystem: secrets, permissions and auditing."""

from .vault import (
    ROLE_PERMISSIONS,
    AuditLog,
    Permission,
    PermissionManager,
    SecretVault,
    generate_api_key,
)

__all__ = [
    "ROLE_PERMISSIONS",
    "AuditLog",
    "Permission",
    "PermissionManager",
    "SecretVault",
    "generate_api_key",
]
