"""Secure storage, permissions and audit logging (``docs/21-SECURITY.md``)."""

from __future__ import annotations

import base64
import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from ..core.errors import PermissionDeniedError
from ..core.logging import get_logger

logger = get_logger("security.vault")


class SecretVault:
    """Fernet-encrypted key/value store for API keys and tokens.

    The master key lives in a 0600 file outside the repository. Values are
    encrypted individually so a partial read never exposes the whole vault.
    """

    def __init__(self, key_file: str | Path, store_file: str | Path | None = None) -> None:
        self.key_file = Path(key_file).expanduser()
        self.store_file = (
            Path(store_file).expanduser()
            if store_file
            else self.key_file.with_name("secrets.enc")
        )
        self._fernet = Fernet(self._load_or_create_key())
        self._cache: dict[str, str] = {}
        self._load()

    def _load_or_create_key(self) -> bytes:
        if self.key_file.exists():
            return self.key_file.read_bytes().strip()
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        self.key_file.write_bytes(key)
        try:
            os.chmod(self.key_file, 0o600)
        except OSError:  # pragma: no cover - platform dependent
            logger.warning("could not restrict permissions on %s", self.key_file)
        logger.info("generated a new master key at %s", self.key_file)
        return key

    def _load(self) -> None:
        if not self.store_file.exists():
            return
        try:
            raw = json.loads(self.store_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("could not read the secret store: %s", exc)
            return
        for name, token in raw.items():
            try:
                self._cache[name] = self._fernet.decrypt(token.encode()).decode()
            except InvalidToken:
                logger.error("secret '%s' could not be decrypted with the current key", name)

    def _flush(self) -> None:
        payload = {
            name: self._fernet.encrypt(value.encode()).decode()
            for name, value in self._cache.items()
        }
        self.store_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.store_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.store_file)
        try:
            os.chmod(self.store_file, 0o600)
        except OSError:  # pragma: no cover
            pass

    def set(self, name: str, value: str) -> None:
        self._cache[name] = value
        self._flush()

    def get(self, name: str, default: str | None = None) -> str | None:
        """Look up a secret, falling back to the environment."""
        return self._cache.get(name) or os.environ.get(name.upper()) or default

    def delete(self, name: str) -> None:
        self._cache.pop(name, None)
        self._flush()

    def names(self) -> list[str]:
        return sorted(self._cache)

    def masked(self) -> dict[str, str]:
        """Vault contents with values redacted, safe to return over the API."""
        return {name: _mask(value) for name, value in sorted(self._cache.items())}


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


class Permission:
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    DELETE_FILES = "delete_files"
    EXECUTE_TERMINAL = "execute_terminal"
    INTERNET_ACCESS = "internet_access"
    PLUGIN_ACCESS = "plugin_access"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    DEVICE_ACCESS = "device_access"
    AI_PROVIDER = "ai_provider"
    MEMORY_WRITE = "memory_write"
    ADMIN = "admin"


#: Default grants per role (spec: Authorization roles).
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "administrator": {
        Permission.READ_FILES, Permission.WRITE_FILES, Permission.DELETE_FILES,
        Permission.EXECUTE_TERMINAL, Permission.INTERNET_ACCESS, Permission.PLUGIN_ACCESS,
        Permission.CAMERA, Permission.MICROPHONE, Permission.DEVICE_ACCESS,
        Permission.AI_PROVIDER, Permission.MEMORY_WRITE, Permission.ADMIN,
    },
    "user": {
        Permission.READ_FILES, Permission.WRITE_FILES, Permission.INTERNET_ACCESS,
        Permission.MICROPHONE, Permission.AI_PROVIDER, Permission.MEMORY_WRITE,
    },
    "agent": {
        Permission.READ_FILES, Permission.AI_PROVIDER, Permission.MEMORY_WRITE,
    },
    "plugin": {Permission.READ_FILES},
    "service": {Permission.READ_FILES, Permission.AI_PROVIDER, Permission.MEMORY_WRITE},
    "guest": set(),
}


class PermissionManager:
    """Zero-trust permission checks with per-principal overrides."""

    def __init__(self, *, default_role: str = "user") -> None:
        self.default_role = default_role
        self._roles: dict[str, str] = {}
        self._grants: dict[str, set[str]] = {}
        self._revocations: dict[str, set[str]] = {}

    def assign_role(self, principal: str, role: str) -> None:
        if role not in ROLE_PERMISSIONS:
            raise PermissionDeniedError(f"unknown role: {role}")
        self._roles[principal] = role

    def role_of(self, principal: str) -> str:
        return self._roles.get(principal, self.default_role)

    def grant(self, principal: str, permission: str) -> None:
        self._grants.setdefault(principal, set()).add(permission)
        self._revocations.get(principal, set()).discard(permission)

    def revoke(self, principal: str, permission: str) -> None:
        self._revocations.setdefault(principal, set()).add(permission)
        self._grants.get(principal, set()).discard(permission)

    def permissions_of(self, principal: str) -> set[str]:
        base = set(ROLE_PERMISSIONS.get(self.role_of(principal), set()))
        base |= self._grants.get(principal, set())
        base -= self._revocations.get(principal, set())
        return base

    def check(self, principal: str, permission: str) -> bool:
        perms = self.permissions_of(principal)
        return Permission.ADMIN in perms or permission in perms

    def require(self, principal: str, permission: str) -> None:
        if not self.check(principal, permission):
            raise PermissionDeniedError(
                f"'{principal}' lacks the '{permission}' permission",
                details={"role": self.role_of(principal)},
            )


class AuditLog:
    """Append-only ring buffer of security-relevant events."""

    def __init__(self, *, capacity: int = 1000, file: str | Path | None = None) -> None:
        self._entries: deque[dict[str, Any]] = deque(maxlen=capacity)
        self.file = Path(file).expanduser() if file else None

    def record(
        self,
        action: str,
        *,
        principal: str = "system",
        outcome: str = "allowed",
        details: dict | None = None,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": time.time(),
            "action": action,
            "principal": principal,
            "outcome": outcome,
            "details": details or {},
        }
        self._entries.append(entry)
        if self.file:
            try:
                self.file.parent.mkdir(parents=True, exist_ok=True)
                with self.file.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry) + "\n")
            except OSError:  # pragma: no cover
                logger.warning("could not append to the audit log")
        return entry

    def entries(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(self._entries)[-limit:]


def generate_api_key(prefix: str = "aera") -> str:
    """Create a URL-safe random API key."""
    return f"{prefix}_{base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip('=')}"
