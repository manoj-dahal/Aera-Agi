"""Permission Manager (docs/21-SECURITY.md "Authorization").

"Every operation requires permission." — Zero Trust.

Documented permission examples are modeled as an enum; grants are cached
(docs/21 Performance: "Cached Permissions") and every grant/deny decision
is recorded through the Audit Logger.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from src.logging.logger import get_logger

if TYPE_CHECKING:
    from src.security.audit import AuditLog

log = get_logger("security.permissions")


class Permission(str, Enum):
    """Documented permissions (docs/21 Authorization)."""

    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    DELETE_FILES = "delete_files"
    EXECUTE_TERMINAL = "execute_terminal"
    INTERNET_ACCESS = "internet_access"
    PLUGIN_ACCESS = "plugin_access"
    CAMERA_ACCESS = "camera_access"
    MICROPHONE_ACCESS = "microphone_access"
    DEVICE_ACCESS = "device_access"
    AI_PROVIDER_ACCESS = "ai_provider_access"


#: Default grants for the local owner — local-first, privacy-first:
#: sensors and destructive capabilities start denied until granted.
OWNER_DEFAULTS: set[Permission] = {
    Permission.READ_FILES,
    Permission.WRITE_FILES,
    Permission.INTERNET_ACCESS,
    Permission.AI_PROVIDER_ACCESS,
}


class PermissionManager:
    """Grants, revokes, and checks permissions per subject (user/plugin/agent)."""

    def __init__(self, audit: AuditLog) -> None:
        self.audit = audit
        self._grants: dict[str, set[Permission]] = {"owner": set(OWNER_DEFAULTS)}

    def grant(self, subject: str, permission: Permission) -> None:
        self._grants.setdefault(subject, set()).add(permission)
        self.audit.record("permission.granted", subject=subject, detail=permission.value)

    def revoke(self, subject: str, permission: Permission) -> None:
        self._grants.get(subject, set()).discard(permission)
        self.audit.record("permission.revoked", subject=subject, detail=permission.value)

    def check(self, subject: str, permission: Permission) -> bool:
        allowed = permission in self._grants.get(subject, set())
        if not allowed:
            # Documented audit event: Permission Denied
            self.audit.record("permission.denied", subject=subject, detail=permission.value)
        return allowed

    def require(self, subject: str, permission: Permission) -> None:
        if not self.check(subject, permission):
            raise PermissionError(f"{subject} lacks permission: {permission.value}")

    def grants_for(self, subject: str) -> list[str]:
        return sorted(p.value for p in self._grants.get(subject, set()))
