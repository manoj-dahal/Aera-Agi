"""Plugin sandbox API (docs/17-PLUGIN-SYSTEM.md "Plugin API" + "Security").

Plugins never touch core objects directly — they receive a PluginAPI facade
whose every capability is gated by the permissions the user approved
("Users approve permissions before activation", "Permission Isolation").

Documented APIs exposed (server-side subset): Memory Graph API, Agent API,
Notification API, Event Bus. The rest (Voice/Hologram/Workspace/Gallery/
Git/Terminal) attach here as those subsystems gain public APIs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.common.schemas import MemoryNodeCreate, NodeType, TaskRequest
from src.plugins.models import PluginPermission

if TYPE_CHECKING:
    from src.agents.manager import AgentManager
    from src.events.bus import EventBus
    from src.memory.graph import MemoryGraph


class PluginPermissionError(PermissionError):
    """Raised when a plugin calls an API it was not granted."""


class PluginAPI:
    """Capability-gated facade handed to each running plugin."""

    def __init__(
        self,
        plugin_name: str,
        granted: set[PluginPermission],
        memory: MemoryGraph,
        agents: AgentManager,
        bus: EventBus,
    ) -> None:
        self._plugin = plugin_name
        self._granted = granted
        self._memory = memory
        self._agents = agents
        self._bus = bus
        self._subscriptions: list[tuple[str, Any]] = []

    def _require(self, permission: PluginPermission) -> None:
        if permission not in self._granted:
            raise PluginPermissionError(
                f"plugin '{self._plugin}' lacks permission: {permission.value}"
            )

    # ── Memory Graph API ──────────────────────────────────

    def memory_recall(self, query: str, limit: int = 5) -> list[str]:
        self._require(PluginPermission.MEMORY_GRAPH)
        return [n.content for n in self._memory.recall(query, limit=limit)]

    def memory_store(self, content: str, importance: float = 0.5) -> int:
        self._require(PluginPermission.MEMORY_GRAPH)
        node = self._memory.add_node(
            MemoryNodeCreate(
                type=NodeType.FACT,
                content=f"[plugin:{self._plugin}] {content}",
                importance=importance,
            )
        )
        return node.id

    # ── Agent API ─────────────────────────────────────────

    async def ask_agent(self, message: str, agent: str | None = None) -> str:
        self._require(PluginPermission.LOCAL_AI)
        result = await self._agents.execute(TaskRequest(message=message, agent=agent))
        return result.response

    # ── Notification API ──────────────────────────────────

    async def notify(self, message: str, level: str = "info") -> None:
        self._require(PluginPermission.NOTIFICATIONS)
        await self._bus.publish(
            "notification", {"message": message, "level": level, "source": self._plugin}
        )

    # ── Event System (docs/17: plugins receive events) ───

    def on_event(self, topic_pattern: str, handler: Any) -> None:
        """Subscribe to bus events (memory.*, voice.*, automation.*, ...)."""
        self._bus.subscribe(topic_pattern, handler)
        self._subscriptions.append((topic_pattern, handler))

    async def emit(self, topic: str, data: dict | None = None) -> None:
        """Plugins emit under their own namespace to avoid impersonation."""
        await self._bus.publish(f"plugin.{self._plugin}.{topic}", data or {})

    def _teardown(self) -> None:
        """Unload: detach every subscription (crash/lifecycle isolation)."""
        for pattern, handler in self._subscriptions:
            self._bus.unsubscribe(pattern, handler)
        self._subscriptions.clear()
