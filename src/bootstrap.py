"""Bootstrap — initialize every AERA subsystem in dependency order.

    Event Bus ──► Memory Graph ──► Model Router ──► Agent Manager
                                                        │
                       Emotion Engine ──► Conversation Engine
                                                        │
                              Speech Service    Service Manager

Per docs/02-SYSTEM-ARCHITECTURE.md and docs/24-BACKGROUND-SERVICES.md
(services are event-driven, self-healing, and registered with the manager).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.agents.manager import AgentManager
from src.ai.router import ModelRouter
from src.auth.service import AuthService
from src.automation.manager import AutomationManager
from src.events.bus import EventBus
from src.hologram.animation import AnimationEngine
from src.logging.logger import get_logger
from src.memory.graph import MemoryGraph
from src.plugins.manager import PluginManager
from src.security.ai_guard import AIGuard
from src.security.audit import AuditLog
from src.security.permissions import PermissionManager
from src.services.manager import ServiceManager
from src.speech.engines import SpeechService
from src.voice.conversation import ConversationEngine
from src.voice.emotion import EmotionEngine
from src.workspace.manager import WorkspaceManager

log = get_logger("bootstrap")


@dataclass
class AeraSystem:
    """Handle to all running AERA subsystems."""

    bus: EventBus
    memory: MemoryGraph
    router: ModelRouter
    agents: AgentManager
    emotions: EmotionEngine
    conversation: ConversationEngine
    speech: SpeechService
    services: ServiceManager
    automation: AutomationManager
    audit: AuditLog
    permissions: PermissionManager
    auth: AuthService
    guard: AIGuard
    plugins: PluginManager
    hologram: AnimationEngine
    workspace: WorkspaceManager
    auth_required: bool

    async def start_services(self) -> None:
        await self.services.start_all()

    async def stop_services(self) -> None:
        await self.services.stop_all()

    def shutdown(self) -> None:
        log.info("shutting down AERA subsystems")
        self.memory.close()


def _register_core_services(system: AeraSystem) -> None:
    """Register the documented core background services (docs/24)."""

    async def memory_service() -> None:
        # Memory Service: storage/recall run inline; this tick handles upkeep.
        stats = system.memory.stats()
        await system.bus.publish("memory.stats", stats.model_dump())

    async def local_llm_monitor() -> None:
        # Local LLM Monitor: detect running models / runtime health check.
        online = await system.router.ollama_available()
        await system.bus.publish("ai.local.status", {"online": online})

    system.services.register("memory-service", memory_service, interval=60.0)
    system.services.register("local-llm-monitor", local_llm_monitor, interval=30.0)


def boot() -> AeraSystem:
    """Initialize and wire together the core subsystems."""
    log.info("booting AERA core")
    import os

    bus = EventBus()
    memory = MemoryGraph()
    router = ModelRouter()
    audit = AuditLog(bus)
    permissions = PermissionManager(audit)
    guard = AIGuard()
    auth = AuthService()
    agents = AgentManager(memory, router, guard)
    emotions = EmotionEngine()
    conversation = ConversationEngine(agents, emotions, bus)
    speech = SpeechService()
    services = ServiceManager(bus)
    automation = AutomationManager(agents, memory, bus, services)
    plugins = PluginManager(memory, agents, bus, audit)
    hologram = AnimationEngine(bus)
    workspace = WorkspaceManager(memory, agents, bus)

    system = AeraSystem(
        bus=bus,
        memory=memory,
        router=router,
        agents=agents,
        emotions=emotions,
        conversation=conversation,
        speech=speech,
        services=services,
        automation=automation,
        audit=audit,
        permissions=permissions,
        auth=auth,
        guard=guard,
        plugins=plugins,
        hologram=hologram,
        workspace=workspace,
        auth_required=os.getenv("AERA_AUTH_REQUIRED", "false").lower() == "true",
    )
    _register_core_services(system)
    log.info(
        "AERA online — %d agents, %d background services registered",
        len(agents.agents),
        len(services.services),
    )
    return system
