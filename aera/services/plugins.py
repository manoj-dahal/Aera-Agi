# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Plugin runtime (docs/17-PLUGIN-SYSTEM.md).

Discovers plugins on disk, validates their manifests, and gates them behind
explicit user approval. A plugin declares the permissions it wants; nothing is
granted implicitly, and an unapproved plugin cannot be enabled.

Deliberately narrow about execution. Running third-party Python inside the
kernel process gives it everything the kernel has -- the filesystem, the
vault, the network -- and neither Python's ``exec`` sandbox nor an import hook
is a real security boundary. So this loads, validates, gates and tracks
plugins, and refuses to execute code until a genuine isolation mechanism
(subprocess with dropped privileges, or WASM) is in place. ``load_error`` says
so at the point of use rather than pretending.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from ..core.errors import ValidationError
from ..core.logging import get_logger

logger = get_logger("services.plugins")

#: Manifest filenames, in probe order. The spec shows both.
MANIFEST_NAMES = ("manifest.yaml", "manifest.yml", "plugin.json")

#: Permissions a plugin may request (docs/17, "Permissions").
PERMISSIONS = frozenset(
    {
        "workspace", "files", "terminal", "git", "network", "internet",
        "memory", "voice", "hologram", "notifications", "camera",
        "microphone", "clipboard", "local_ai", "cloud_ai",
    }
)

#: Permissions that can read user data or reach the outside world. These
#: require explicit approval even when the plugin is otherwise trusted.
SENSITIVE = frozenset(
    {"terminal", "network", "internet", "camera", "microphone", "files", "clipboard"}
)

#: Plugin categories (docs/17, "Plugin Types").
PLUGIN_TYPES = frozenset(
    {
        "ai", "agent", "voice", "workspace", "gallery", "terminal", "git",
        "automation", "security", "theme", "connector", "device", "cloud",
        "tool",
    }
)

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+")


class PluginState(str, Enum):
    """Lifecycle position (docs/17, "Plugin Lifecycle")."""

    DISCOVERED = "discovered"
    #: Manifest failed validation; the plugin cannot be used.
    INVALID = "invalid"
    #: Valid, but the user has not approved its permissions yet.
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ENABLED = "enabled"
    DISABLED = "disabled"


@dataclass
class PluginManifest:
    """A validated plugin manifest."""

    name: str
    version: str
    author: str = "unknown"
    type: str = "tool"
    description: str = ""
    permissions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    minimum_version: str = "1.0.0"
    entry: str | None = None

    @property
    def sensitive_permissions(self) -> list[str]:
        return sorted(p for p in self.permissions if p in SENSITIVE)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "type": self.type,
            "description": self.description,
            "permissions": self.permissions,
            "sensitive_permissions": self.sensitive_permissions,
            "dependencies": self.dependencies,
            "minimum_version": self.minimum_version,
            "entry": self.entry,
        }


@dataclass
class Plugin:
    """A discovered plugin and its current state."""

    id: str
    path: Path
    manifest: PluginManifest | None = None
    state: PluginState = PluginState.DISCOVERED
    #: Why the manifest was rejected, or why it cannot run.
    error: str | None = None
    granted: list[str] = field(default_factory=list)
    discovered_at: float = field(default_factory=time.time)

    @property
    def name(self) -> str:
        return self.manifest.name if self.manifest else self.path.name

    @property
    def runnable(self) -> bool:
        """Whether the runtime would execute this plugin's code.

        Always False for now: see the module docstring. Kept as a property so
        callers ask the runtime rather than assuming.
        """
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "state": self.state.value,
            "error": self.error,
            "granted": self.granted,
            "runnable": self.runnable,
            "manifest": self.manifest.to_dict() if self.manifest else None,
            "discovered_at": self.discovered_at,
        }


def parse_manifest(data: dict[str, Any]) -> PluginManifest:
    """Validate a manifest, raising with the specific problem.

    Every rejection names the field, because "invalid manifest" tells a plugin
    author nothing about what to fix.
    """
    if not isinstance(data, dict):
        raise ValidationError("manifest must be a mapping")

    name = str(data.get("name", "")).strip()
    if not name:
        raise ValidationError("manifest is missing 'name'")
    if not _NAME.match(name):
        raise ValidationError(
            f"invalid plugin name {name!r}: letters, digits, spaces, dot, dash "
            "and underscore only, up to 64 characters"
        )

    version = str(data.get("version", "")).strip()
    if not version:
        raise ValidationError("manifest is missing 'version'")
    if not _SEMVER.match(version):
        raise ValidationError(f"version {version!r} is not semantic (expected e.g. 1.0.0)")

    plugin_type = str(data.get("type", "tool")).strip().lower()
    if plugin_type not in PLUGIN_TYPES:
        raise ValidationError(
            f"unknown plugin type {plugin_type!r}",
            details={"supported": sorted(PLUGIN_TYPES)},
        )

    raw_permissions = data.get("permissions") or []
    if not isinstance(raw_permissions, list):
        raise ValidationError("'permissions' must be a list")
    permissions = [str(p).strip().lower() for p in raw_permissions if str(p).strip()]
    unknown = sorted(set(permissions) - PERMISSIONS)
    if unknown:
        raise ValidationError(
            f"unknown permission(s): {', '.join(unknown)}",
            details={"supported": sorted(PERMISSIONS)},
        )

    dependencies = data.get("dependencies") or []
    if not isinstance(dependencies, list):
        raise ValidationError("'dependencies' must be a list")

    return PluginManifest(
        name=name,
        version=version,
        author=str(data.get("author", "unknown")).strip() or "unknown",
        type=plugin_type,
        description=str(data.get("description", "")).strip(),
        # Deduplicate while preserving the author's ordering.
        permissions=list(dict.fromkeys(permissions)),
        dependencies=[str(d).strip() for d in dependencies if str(d).strip()],
        minimum_version=str(data.get("minimumVersion") or data.get("minimum_version") or "1.0.0"),
        entry=str(data["entry"]).strip() if data.get("entry") else None,
    )


def read_manifest(directory: Path) -> dict[str, Any]:
    """Load the first manifest found in a plugin directory."""
    for filename in MANIFEST_NAMES:
        candidate = directory / filename
        if not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValidationError(f"could not read {filename}: {exc}") from exc
        try:
            if candidate.suffix == ".json":
                return json.loads(text)
            return yaml.safe_load(text) or {}
        except (json.JSONDecodeError, yaml.YAMLError) as exc:
            raise ValidationError(f"{filename} is malformed: {exc}") from exc

    raise ValidationError(
        f"no manifest in {directory.name} (expected one of {', '.join(MANIFEST_NAMES)})"
    )


class PluginRegistry:
    """Discovers and tracks plugins.

    State lives in memory and in an approvals file, so a restart re-discovers
    from disk rather than trusting a cached list that may be stale.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._plugins: dict[str, Plugin] = {}
        self._approvals_file = self.root / ".approvals.json"

    # ------------------------------------------------------------------ #
    # discovery
    # ------------------------------------------------------------------ #
    def scan(self) -> list[Plugin]:
        """Find every plugin directory and validate its manifest."""
        self.root.mkdir(parents=True, exist_ok=True)
        approvals = self._load_approvals()
        self._plugins.clear()

        for directory in sorted(self.root.iterdir()):
            if not directory.is_dir() or directory.name.startswith("."):
                continue

            plugin_id = directory.name
            plugin = Plugin(id=plugin_id, path=directory)

            try:
                plugin.manifest = parse_manifest(read_manifest(directory))
            except ValidationError as exc:
                # A broken plugin is listed with its reason rather than hidden,
                # so the author can see what to fix.
                plugin.state = PluginState.INVALID
                plugin.error = str(exc)
                self._plugins[plugin_id] = plugin
                logger.warning("plugin %s is invalid: %s", plugin_id, exc)
                continue

            record = approvals.get(plugin_id)
            if record and record.get("granted") is not None:
                plugin.granted = list(record["granted"])
                plugin.state = (
                    PluginState.ENABLED if record.get("enabled") else PluginState.APPROVED
                )
            elif plugin.manifest.permissions:
                plugin.state = PluginState.PENDING_APPROVAL
            else:
                # Nothing requested, nothing to approve.
                plugin.state = PluginState.APPROVED

            self._plugins[plugin_id] = plugin

        logger.info("plugins: %d discovered in %s", len(self._plugins), self.root)
        return self.all()

    def all(self) -> list[Plugin]:
        return sorted(self._plugins.values(), key=lambda p: p.name.lower())

    def get(self, plugin_id: str) -> Plugin:
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise ValidationError(f"no such plugin: {plugin_id}")
        return plugin

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    def approve(self, plugin_id: str, permissions: list[str] | None = None) -> Plugin:
        """Grant a plugin the permissions the user agreed to.

        Granting a permission the manifest never requested is refused: it
        would mean the approval dialog showed one thing and stored another.
        """
        plugin = self.get(plugin_id)
        if plugin.manifest is None:
            raise ValidationError(f"{plugin_id} has no valid manifest to approve")

        requested = set(plugin.manifest.permissions)
        granted = set(permissions) if permissions is not None else requested

        extra = sorted(granted - requested)
        if extra:
            raise ValidationError(
                f"cannot grant permission(s) the plugin did not request: {', '.join(extra)}"
            )

        plugin.granted = sorted(granted)
        plugin.state = PluginState.APPROVED
        self._save_approvals()
        logger.info("plugin %s approved with %s", plugin_id, plugin.granted or "no permissions")
        return plugin

    def enable(self, plugin_id: str) -> Plugin:
        plugin = self.get(plugin_id)
        if plugin.state is PluginState.INVALID:
            raise ValidationError(f"{plugin_id} cannot be enabled: {plugin.error}")
        if plugin.state is PluginState.PENDING_APPROVAL:
            raise ValidationError(
                f"{plugin_id} requests {', '.join(plugin.manifest.permissions)} "
                "and must be approved first"
            )
        plugin.state = PluginState.ENABLED
        self._save_approvals()
        return plugin

    def disable(self, plugin_id: str) -> Plugin:
        plugin = self.get(plugin_id)
        plugin.state = PluginState.DISABLED
        self._save_approvals()
        return plugin

    def revoke(self, plugin_id: str) -> Plugin:
        """Withdraw approval, returning the plugin to pending."""
        plugin = self.get(plugin_id)
        plugin.granted = []
        plugin.state = (
            PluginState.PENDING_APPROVAL
            if plugin.manifest and plugin.manifest.permissions
            else PluginState.DISCOVERED
        )
        self._save_approvals()
        return plugin

    def has_permission(self, plugin_id: str, permission: str) -> bool:
        """Whether a plugin may use a capability right now.

        Enabled *and* granted: a disabled plugin keeps its grants but must not
        act on them.
        """
        plugin = self._plugins.get(plugin_id)
        if plugin is None or plugin.state is not PluginState.ENABLED:
            return False
        return permission.strip().lower() in plugin.granted

    def load_error(self, plugin_id: str) -> str:
        """Why a plugin's code will not be executed.

        Stated at the point of use so the limitation is visible rather than
        discovered when nothing happens.
        """
        plugin = self.get(plugin_id)
        if plugin.state is PluginState.INVALID:
            return plugin.error or "invalid manifest"
        return (
            "AERA validates and gates plugins but does not execute plugin code yet. "
            "Running third-party Python in the kernel process would give it the "
            "filesystem, the vault and the network, and Python has no real sandbox. "
            "Isolated execution is the remaining work."
        )

    # ------------------------------------------------------------------ #
    # persistence
    # ------------------------------------------------------------------ #
    def _load_approvals(self) -> dict[str, dict[str, Any]]:
        if not self._approvals_file.is_file():
            return {}
        try:
            return json.loads(self._approvals_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            # A corrupt approvals file must not silently re-grant permissions.
            logger.warning("could not read plugin approvals (%s); treating as none", exc)
            return {}

    def _save_approvals(self) -> None:
        payload = {
            plugin.id: {
                "granted": plugin.granted,
                "enabled": plugin.state is PluginState.ENABLED,
            }
            for plugin in self._plugins.values()
            if plugin.granted or plugin.state is PluginState.ENABLED
        }
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self._approvals_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:  # pragma: no cover - disk failure
            logger.error("could not persist plugin approvals: %s", exc)

    def stats(self) -> dict[str, Any]:
        by_state: dict[str, int] = {}
        for plugin in self._plugins.values():
            by_state[plugin.state.value] = by_state.get(plugin.state.value, 0) + 1
        return {
            "count": len(self._plugins),
            "by_state": by_state,
            "execution_supported": False,
            "supported_types": sorted(PLUGIN_TYPES),
            "supported_permissions": sorted(PERMISSIONS),
        }
