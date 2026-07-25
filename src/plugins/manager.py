"""Plugin Manager (docs/17-PLUGIN-SYSTEM.md).

Documented lifecycle:

    Install → Validate → Permission Check → Load → Initialize → Running
            → Unload → Remove

Documented security: sandboxed execution, permission isolation, crash
isolation — "A faulty plugin cannot directly compromise the AERA Core."

Plugins live in plugins/<dir>/ with a manifest.yaml and a Python entry
module exposing:

    def setup(api) -> None | Awaitable[None]      # required
    def teardown(api) -> None | Awaitable[None]   # optional

Hot Reload (documented objective): reload() re-reads manifest + code
without restarting AERA.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from src.plugins.api import PluginAPI
from src.plugins.models import (
    PluginInfo,
    PluginManifest,
    PluginPermission,
    PluginState,
)

if TYPE_CHECKING:
    from src.agents.manager import AgentManager
    from src.events.bus import EventBus
    from src.memory.graph import MemoryGraph
    from src.security.audit import AuditLog

from src.logging.logger import get_logger

log = get_logger("plugins")

CORE_VERSION = "1.0.0"


class PluginError(Exception):
    """Validation or lifecycle failure."""


@dataclass
class LoadedPlugin:
    directory: Path
    manifest: PluginManifest
    state: PluginState = PluginState.INSTALLED
    approved: set[PluginPermission] = field(default_factory=set)
    module: Any = None
    api: PluginAPI | None = None
    error: str | None = None

    def info(self) -> PluginInfo:
        return PluginInfo(
            name=self.manifest.name,
            version=self.manifest.version,
            author=self.manifest.author,
            type=self.manifest.type,
            description=self.manifest.description,
            state=self.state,
            permissions=self.manifest.permissions,
            approved_permissions=sorted(self.approved, key=lambda p: p.value),
            dependencies=self.manifest.dependencies,
            error=self.error,
        )


def _version_tuple(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


class PluginManager:
    """Installs, validates, loads, runs, reloads, and removes plugins."""

    def __init__(
        self,
        memory: MemoryGraph,
        agents: AgentManager,
        bus: EventBus,
        audit: AuditLog,
        plugins_dir: str | Path = "plugins",
    ) -> None:
        self.memory = memory
        self.agents = agents
        self.bus = bus
        self.audit = audit
        self.plugins_dir = Path(plugins_dir)
        self.plugins: dict[str, LoadedPlugin] = {}

    # ── Install → Validate ───────────────────────────────

    def discover(self) -> list[str]:
        """Scan plugins/ for directories containing manifest.yaml."""
        found = []
        if not self.plugins_dir.exists():
            return found
        for directory in sorted(self.plugins_dir.iterdir()):
            if (directory / "manifest.yaml").exists():
                try:
                    self.install(directory)
                    found.append(directory.name)
                except PluginError as exc:
                    log.warning("skipping plugin %s: %s", directory.name, exc)
        return found

    def install(self, directory: str | Path) -> LoadedPlugin:
        """Install from a local folder (documented installation source)."""
        directory = Path(directory)
        manifest = self._validate(directory)
        plugin = LoadedPlugin(directory=directory, manifest=manifest)
        self.plugins[manifest.name] = plugin
        self.audit.record("plugin.installed", subject=manifest.name,
                          detail=f"v{manifest.version}")
        return plugin

    def _validate(self, directory: Path) -> PluginManifest:
        """Validate: manifest exists, parses, version + dependency checks."""
        manifest_file = directory / "manifest.yaml"
        if not manifest_file.exists():
            raise PluginError("manifest.yaml not found")
        try:
            data = yaml.safe_load(manifest_file.read_text()) or {}
            manifest = PluginManifest(**data)
        except Exception as exc:  # noqa: BLE001 — surface as validation error
            raise PluginError(f"invalid manifest: {exc}") from None
        if _version_tuple(manifest.minimumVersion) > _version_tuple(CORE_VERSION):
            raise PluginError(
                f"requires AERA >= {manifest.minimumVersion} (core is {CORE_VERSION})"
            )
        if not (directory / manifest.entry).exists():
            raise PluginError(f"entry file missing: {manifest.entry}")
        return manifest

    # ── Permission Check (user approval before activation) ──

    def approve_permissions(
        self, name: str, permissions: list[PluginPermission] | None = None
    ) -> LoadedPlugin:
        plugin = self._get(name)
        requested = set(plugin.manifest.permissions)
        granting = requested if permissions is None else (set(permissions) & requested)
        plugin.approved = granting
        for perm in granting:
            self.audit.record("permission.granted",
                              subject=f"plugin:{name}", detail=perm.value)
        return plugin

    # ── Load → Initialize → Running ──────────────────────

    async def enable(self, name: str) -> LoadedPlugin:
        plugin = self._get(name)
        missing = set(plugin.manifest.permissions) - plugin.approved
        if missing:
            raise PluginError(
                "permissions not approved: " + ", ".join(sorted(p.value for p in missing))
            )
        plugin.state = PluginState.LOADING
        try:
            plugin.module = self._load_module(plugin)
            plugin.api = PluginAPI(
                plugin.manifest.name, plugin.approved, self.memory, self.agents, self.bus
            )
            setup = getattr(plugin.module, "setup", None)
            if setup is None:
                raise PluginError("plugin entry must define setup(api)")
            result = setup(plugin.api)
            if asyncio.iscoroutine(result):
                await result
            plugin.state = PluginState.ENABLED
            plugin.error = None
            self.audit.record("plugin.enabled", subject=name)
            await self.bus.publish("plugin.installed", {"name": name})  # documented event
        except Exception as exc:  # noqa: BLE001 — crash isolation (docs/17)
            plugin.state = PluginState.ERROR
            plugin.error = str(exc)
            if plugin.api:
                plugin.api._teardown()
            log.exception("plugin %s failed to enable", name)
        return plugin

    def _load_module(self, plugin: LoadedPlugin) -> Any:
        entry = plugin.directory / plugin.manifest.entry
        module_name = f"aera_plugin_{plugin.manifest.name.lower().replace(' ', '_')}"
        # Hot reload: drop any previously imported module first.
        sys.modules.pop(module_name, None)
        spec = importlib.util.spec_from_file_location(module_name, entry)
        if spec is None or spec.loader is None:
            raise PluginError(f"cannot load entry: {entry}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    # ── Unload → Remove ──────────────────────────────────

    async def disable(self, name: str) -> LoadedPlugin:
        plugin = self._get(name)
        await self._unload(plugin)
        plugin.state = PluginState.DISABLED
        self.audit.record("plugin.disabled", subject=name)
        return plugin

    async def reload(self, name: str) -> LoadedPlugin:
        """Hot Reload: unload, re-validate manifest, re-enable."""
        plugin = self._get(name)
        was_enabled = plugin.state == PluginState.ENABLED
        await self._unload(plugin)
        plugin.manifest = self._validate(plugin.directory)
        plugin.state = PluginState.INSTALLED
        if was_enabled:
            return await self.enable(name)
        return plugin

    async def remove(self, name: str) -> None:
        plugin = self._get(name)
        await self._unload(plugin)
        plugin.state = PluginState.UNINSTALLED
        del self.plugins[name]
        self.audit.record("plugin.removed", subject=name)  # documented audit event

    async def _unload(self, plugin: LoadedPlugin) -> None:
        if plugin.module is not None and plugin.api is not None:
            teardown = getattr(plugin.module, "teardown", None)
            if teardown is not None:
                try:
                    result = teardown(plugin.api)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:  # noqa: BLE001 — crash isolation
                    log.exception("plugin %s teardown failed", plugin.manifest.name)
            plugin.api._teardown()
        plugin.module = None
        plugin.api = None

    # ── Queries ──────────────────────────────────────────

    def _get(self, name: str) -> LoadedPlugin:
        plugin = self.plugins.get(name)
        if plugin is None:
            raise KeyError(f"plugin '{name}' not found")
        return plugin

    def list(self) -> list[PluginInfo]:
        return [p.info() for p in self.plugins.values()]
