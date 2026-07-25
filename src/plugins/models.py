"""Plugin System models (docs/17-PLUGIN-SYSTEM.md).

Documented manifest fields: name, version, author, type, permissions,
dependencies, minimumVersion.
Documented states: Installed, Enabled, Disabled, Updating, Loading, Error,
Uninstalled.
Documented permissions: Workspace, Files, Terminal, Git, Network, Internet,
Memory Graph, Voice, Hologram, Notifications, Camera, Microphone,
Clipboard, Local AI, Cloud AI.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PluginType(str, Enum):
    """Documented plugin categories (subset most relevant server-side)."""

    AI = "ai"
    AGENT = "agent"
    VOICE = "voice"
    WORKSPACE = "workspace"
    GALLERY = "gallery"
    TERMINAL = "terminal"
    GIT = "git"
    AUTOMATION = "automation"
    SECURITY = "security"
    UI_THEME = "ui-theme"
    API_CONNECTOR = "api-connector"
    DEVICE = "device"
    CLOUD_PROVIDER = "cloud-provider"
    CUSTOM_TOOL = "custom-tool"


class PluginPermission(str, Enum):
    """The 15 documented plugin permissions."""

    WORKSPACE = "workspace"
    FILES = "files"
    TERMINAL = "terminal"
    GIT = "git"
    NETWORK = "network"
    INTERNET = "internet"
    MEMORY_GRAPH = "memory_graph"
    VOICE = "voice"
    HOLOGRAM = "hologram"
    NOTIFICATIONS = "notifications"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    CLIPBOARD = "clipboard"
    LOCAL_AI = "local_ai"
    CLOUD_AI = "cloud_ai"


class PluginState(str, Enum):
    """The 7 documented plugin states."""

    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    UPDATING = "updating"
    LOADING = "loading"
    ERROR = "error"
    UNINSTALLED = "uninstalled"


class PluginManifest(BaseModel):
    """manifest.yaml, per the documented example."""

    name: str = Field(min_length=1, max_length=100)
    version: str = "1.0.0"
    author: str = "unknown"
    type: PluginType = PluginType.CUSTOM_TOOL
    description: str = ""
    permissions: list[PluginPermission] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    minimumVersion: str = "1.0.0"  # noqa: N815 — documented field name
    entry: str = "src/main.py"  # python entry inside the plugin directory


class PluginInfo(BaseModel):
    """Plugin Manager display fields (docs/17: name, version, author,
    status, permissions, dependencies)."""

    name: str
    version: str
    author: str
    type: PluginType
    description: str
    state: PluginState
    permissions: list[PluginPermission]
    approved_permissions: list[PluginPermission]
    dependencies: list[str]
    error: str | None = None
