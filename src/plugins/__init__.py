"""Plugin System — sandboxed extensions (docs/17-PLUGIN-SYSTEM.md)."""

from src.plugins.api import PluginAPI, PluginPermissionError
from src.plugins.manager import PluginError, PluginManager
from src.plugins.models import PluginManifest, PluginPermission, PluginState, PluginType

__all__ = [
    "PluginAPI",
    "PluginError",
    "PluginManager",
    "PluginManifest",
    "PluginPermission",
    "PluginPermissionError",
    "PluginState",
    "PluginType",
]
