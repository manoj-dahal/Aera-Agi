"""AERA kernel.

Owns the documented startup sequence::

    load config -> validate -> load agents -> initialise services
    -> load memory -> start API -> ready

and the reverse on shutdown. Everything the API layer needs hangs off this
single object.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ..agents import (
    AgentContext,
    AgentRegistry,
    Capability,
    Task,
    TaskResult,
    build_default_registry,
)
from ..agents.tap_memory import TapMemoryWorkflow
from ..ai.router import ModelRouter
from ..automation.engine import AutomationEngine
from ..hologram.avatar import HologramController
from ..hologram.loader import AvatarLibrary
from ..memory.engine import MemoryEngine
from ..security.vault import AuditLog, PermissionManager, SecretVault
from ..services.docker import DockerClient
from ..services.plugins import PluginRegistry
from ..services.telemetry import TelemetryService
from ..services.uploads import UploadStore
from ..skills.engines import ContextEngine, LearningEngine, PlanningEngine, ReasoningEngine
from ..skills.manager import SkillManager
from ..voice.engine import VoiceEngine
from ..workspace.indexer import WorkspaceIndexer
from .config import AeraConfig, get_config
from .events import EventBus, Topics
from .logging import get_logger, setup_logging

logger = get_logger("kernel")


class Kernel:
    """The running AERA system."""

    def __init__(self, config: AeraConfig | None = None) -> None:
        self.config = config or get_config()
        self.started_at: float | None = None
        self.ready = False

        self.bus = EventBus()
        self.memory: MemoryEngine | None = None
        self.router: ModelRouter | None = None
        self.registry: AgentRegistry | None = None
        self.workspace: WorkspaceIndexer | None = None
        self.automation: AutomationEngine | None = None
        self.voice: VoiceEngine | None = None
        self.hologram: HologramController | None = None
        self.avatars: AvatarLibrary | None = None
        self.vault: SecretVault | None = None
        self.tap_memory: TapMemoryWorkflow | None = None
        self.telemetry = TelemetryService()
        self.docker = DockerClient(
            allow_control=self.config.security.allow_docker_control
        )
        self.uploads = UploadStore(self.config.storage_dir / "uploads")
        self.plugins = PluginRegistry(self.config.storage_dir / "plugins")
        # Background engines (docs: Agent Manager, Skill Manager, Reasoning,
        # Planning, Learning and Context Engines).
        self.skills: SkillManager | None = None
        self.context_engine: ContextEngine | None = None
        self.reasoning_engine: ReasoningEngine | None = None
        self.planning_engine: PlanningEngine | None = None
        self.learning_engine: LearningEngine | None = None
        self.permissions = PermissionManager()
        self.audit: AuditLog | None = None

        self._background: list[asyncio.Task] = []

    # ------------------------------------------------------------------ #
    # startup
    # ------------------------------------------------------------------ #
    async def start(self) -> Kernel:
        """Bring the whole platform up."""
        cfg = self.config
        setup_logging(
            cfg.logging.level, json_format=cfg.logging.json_format, file=cfg.logging.file
        )
        cfg.ensure_dirs()
        logger.info("starting %s v%s (%s)", cfg.system.name, cfg.system.version, cfg.system.environment)
        await self.bus.publish(Topics.SYSTEM_STARTED, {"version": cfg.system.version})

        # -- security -----------------------------------------------------
        self.vault = SecretVault(cfg.security.secret_key_file)
        self.audit = AuditLog(file=cfg.logs_dir / "audit.log" if cfg.security.audit_log else None)

        # -- memory -------------------------------------------------------
        self.memory = MemoryEngine(
            cfg.memory, bus=self.bus, storage_path=cfg.storage_dir / "memory-graph.json"
        )
        logger.info("memory graph ready (%d nodes)", len(self.memory.graph))

        # -- AI router ----------------------------------------------------
        self.router = ModelRouter(self._models_with_secrets(), bus=self.bus)
        logger.info("AI providers: %s", ", ".join(self.router.providers))

        # -- agents -------------------------------------------------------
        context = AgentContext(
            memory=self.memory, router=self.router, bus=self.bus, config=cfg
        )
        self.registry = build_default_registry(context, cfg.agents)
        await self.registry.start_all()
        logger.info("agents online: %d", len(self.registry))

        # -- workspace ----------------------------------------------------
        self.workspace = WorkspaceIndexer(cfg.workspace, memory=self.memory, bus=self.bus)
        context.workspace = self.workspace  # agents reach it through the shared context

        # -- skill system and background engines ----------------------------
        self.skills = SkillManager(
            registry=self.registry, router=self.router, config=cfg, bus=self.bus
        )
        # The voice engine is created below; expose it so backend probing can
        # see which STT/TTS implementations are actually installed.
        await self.skills.resolve()

        self.context_engine = ContextEngine(memory=self.memory, bus=self.bus)
        self.reasoning_engine = ReasoningEngine(skills=self.skills)
        self.planning_engine = PlanningEngine(skills=self.skills)
        self.learning_engine = LearningEngine(
            skills=self.skills, memory=self.memory, registry=self.registry, bus=self.bus
        )
        context.skills = self.skills
        context.reasoning_engine = self.reasoning_engine
        context.planning_engine = self.planning_engine

        # Feed task outcomes back into the Learning Engine.
        await self.bus.subscribe("agent.task.*", self._observe_task)

        logger.info(
            "skills: %d/%d available",
            len(self.skills.available()),
            len(self.skills.all()),
        )

        # -- tap-to-memory --------------------------------------------------
        # Runs before voice listening starts, priming context.
        self.tap_memory = TapMemoryWorkflow(
            self.memory, workspace=self.workspace, registry=self.registry, bus=self.bus
        )

        # -- automation ---------------------------------------------------
        self.automation = AutomationEngine(
            router=self.router, memory=self.memory, registry=self.registry, bus=self.bus
        )

        # -- voice + hologram ---------------------------------------------
        self.voice = VoiceEngine(cfg.voice, bus=self.bus)

        # User-supplied avatar models. AERA ships none of its own; drop a GLB
        # or OBJ into this directory and it is discovered on scan.
        self.avatars = AvatarLibrary(cfg.storage_dir / "avatars")
        discovered = self.avatars.scan()
        if discovered:
            logger.info("avatar models available: %d", len(discovered))

        # Files the user handed over previously; the index lives in memory, so
        # it has to be rebuilt from disk on every start.
        restored = self.uploads.scan()
        if restored:
            logger.info("uploaded files available: %d", len(restored))

        found = self.plugins.scan()
        if found:
            logger.info("plugins discovered: %d", len(found))
        self.hologram = HologramController(bus=self.bus, enabled=cfg.settings.hologram)
        await self.bus.subscribe(
            Topics.AVATAR_EMOTION,
            lambda event: self.hologram.sync_with_voice(event.payload)
            if event.source == "voice"
            else None,
        )

        # -- background services -------------------------------------------
        self._start_background()

        self.started_at = time.time()
        self.ready = True
        await self.bus.publish(Topics.SYSTEM_READY, self.status())
        logger.info("AERA is ready")
        return self

    async def _observe_task(self, event) -> None:
        """Learning Engine hook: record how each dispatched task turned out."""
        if self.learning_engine is None or not event.topic.endswith(("completed", "failed")):
            return
        payload = event.payload or {}
        await self.learning_engine.observe(
            agent=str(payload.get("agent", "")),
            skill_id=payload.get("skill"),
            success=bool(payload.get("success", event.topic.endswith("completed"))),
        )

    def _models_with_secrets(self):
        """Inject vault/environment API keys into the provider config."""
        models = self.config.models.model_copy(deep=True)
        env_names = {
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        for name, options in (models.providers or {}).items():
            if options.get("api_key"):
                continue
            key = None
            if self.vault is not None:
                key = self.vault.get(f"{name}_api_key") or self.vault.get(env_names.get(name, ""))
            if key:
                options["api_key"] = key
        return models

    def _start_background(self) -> None:
        """Launch the always-on maintenance loops."""
        self._background.append(asyncio.create_task(self._memory_maintenance()))
        self._background.append(asyncio.create_task(self._health_monitor()))

    async def _memory_maintenance(self) -> None:
        """Consolidate and persist memory on a fixed cadence."""
        interval = 300.0
        while True:
            try:
                await asyncio.sleep(interval)
                if self.memory is None:
                    continue
                await self.memory.consolidate()
                self.memory.save()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.exception("memory maintenance cycle failed")

    async def _health_monitor(self) -> None:
        """Refresh provider health so routing decisions stay current."""
        while True:
            try:
                await asyncio.sleep(60.0)
                if self.router is not None:
                    await self.router.health()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.exception("health monitor cycle failed")

    # ------------------------------------------------------------------ #
    # main entry point for requests
    # ------------------------------------------------------------------ #
    async def chat(
        self,
        message: str,
        *,
        conversation_id: str | None = None,
        project_id: str | None = None,
        agent: str | None = None,
        capability: Capability | str = Capability.CONVERSATION,
    ) -> TaskResult:
        """Send a message through the Core Agent pipeline."""
        if self.registry is None:
            raise RuntimeError("kernel is not started")
        task = Task(
            capability=Capability(capability),
            input=message,
            conversation_id=conversation_id,
            project_id=project_id,
        )
        if agent:
            task.context["force_agent"] = agent
        return await self.registry.dispatch(task, agent_name="core")

    async def prime_context(self, *, conversation_id: str | None = None) -> dict[str, Any]:
        """Run the tap-to-memory workflow (see TapMemoryWorkflow)."""
        if self.tap_memory is None:
            raise RuntimeError("kernel is not started")
        return await self.tap_memory.run(conversation_id=conversation_id)

    # ------------------------------------------------------------------ #
    # shutdown
    # ------------------------------------------------------------------ #
    async def stop(self) -> None:
        """Tear everything down in reverse order, persisting state."""
        logger.info("shutting AERA down")
        await self.bus.publish(Topics.SYSTEM_STOPPING, {})
        self.ready = False

        for task in self._background:
            task.cancel()
        if self._background:
            await asyncio.gather(*self._background, return_exceptions=True)
        self._background.clear()

        if self.automation is not None:
            await self.automation.shutdown()
        if self.registry is not None:
            await self.registry.stop_all()
        if self.memory is not None:
            self.memory.save()
        if self.router is not None:
            await self.router.close()
        logger.info("AERA stopped")

    # ------------------------------------------------------------------ #
    # reporting
    # ------------------------------------------------------------------ #
    def status(self) -> dict[str, Any]:
        uptime = time.time() - self.started_at if self.started_at else 0.0
        return {
            "name": self.config.system.name,
            "version": self.config.system.version,
            "environment": self.config.system.environment,
            "ready": self.ready,
            "uptime_seconds": round(uptime, 1),
            "agents": self.registry.summary() if self.registry else {},
            "memory": self.memory.stats() if self.memory else {},
            "providers": list(self.router.providers) if self.router else [],
            "workspace": self.workspace.summary() if self.workspace else {},
            "voice": self.voice.status() if self.voice else {},
            "hologram": self.hologram.status() if self.hologram else {},
            "avatars": self.avatars.summary() if self.avatars else {},
            "events_published": self.bus.published_count,
            "telemetry": self.telemetry.snapshot(),
            "skills": self.skills.summary() if self.skills else {},
            "context": self.context_engine.snapshot() if self.context_engine else {},
        }


_kernel: Kernel | None = None


def get_kernel() -> Kernel:
    """Return the process-wide kernel (created on first access)."""
    global _kernel
    if _kernel is None:
        _kernel = Kernel()
    return _kernel


def set_kernel(kernel: Kernel | None) -> None:
    global _kernel
    _kernel = kernel
