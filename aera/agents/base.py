"""Agent framework foundations.

Every specialised agent subclasses :class:`Agent`, declares the capabilities it
can serve, and implements :meth:`Agent.handle`. The Core Agent uses those
declarations to route tasks.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from ..core.errors import TaskExecutionError
from ..core.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..ai.router import ModelRouter
    from ..core.events import EventBus
    from ..memory.engine import MemoryEngine


class AgentStatus(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    BUSY = "busy"
    STOPPED = "stopped"
    ERROR = "error"


class Capability(str, Enum):
    """Task kinds an agent can advertise."""

    CONVERSATION = "conversation"
    REASONING = "reasoning"
    PLANNING = "planning"
    CODING = "coding"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    WRITING = "writing"
    RESEARCH = "research"
    TRANSLATION = "translation"
    MEMORY = "memory"
    WORKSPACE = "workspace"
    FILE_ANALYSIS = "file_analysis"
    TERMINAL = "terminal"
    GIT = "git"
    VISION = "vision"
    VOICE = "voice"
    AUTOMATION = "automation"
    SECURITY = "security"
    PERFORMANCE = "performance"
    NOTIFICATION = "notification"
    DEVICE = "device"
    LEARNING = "learning"


class Task(BaseModel):
    """A unit of work handed to an agent."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    capability: Capability = Capability.CONVERSATION
    input: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str | None = None
    project_id: str | None = None
    requester: str = "user"
    created_at: float = Field(default_factory=time.time)
    priority: int = 5  # 1 = highest

    def with_context(self, **extra: Any) -> Task:
        merged = dict(self.context)
        merged.update(extra)
        return self.model_copy(update={"context": merged})


class TaskResult(BaseModel):
    """The outcome of executing a :class:`Task`."""

    task_id: str
    agent: str
    success: bool = True
    output: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0
    model: str | None = None
    provider: str | None = None
    memory_ids: list[str] = Field(default_factory=list)

    def to_public(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent": self.agent,
            "success": self.success,
            "output": self.output,
            "data": self.data,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "model": self.model,
            "provider": self.provider,
        }


class AgentContext:
    """Shared services injected into every agent (spec: shared intelligence)."""

    def __init__(
        self,
        *,
        memory: MemoryEngine,
        router: ModelRouter,
        bus: EventBus,
        config: Any = None,
        registry: Any = None,
        workspace: Any = None,
    ) -> None:
        self.memory = memory
        self.router = router
        self.bus = bus
        self.config = config
        self.registry = registry
        #: set by the kernel once the workspace indexer exists
        self.workspace = workspace


class Agent(ABC):
    """Base class for every AERA agent."""

    name: str = "agent"
    description: str = ""
    capabilities: tuple[Capability, ...] = ()
    #: Higher wins when several agents can serve the same capability.
    priority: int = 5
    #: Router task-kind used when this agent calls an LLM.
    model_task: str = "default"

    def __init__(self, context: AgentContext) -> None:
        self.ctx = context
        self.status = AgentStatus.IDLE
        self.log = get_logger(f"agent.{self.name}")
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_duration_ms = 0.0
        self.last_error: str | None = None
        self.started_at: float | None = None

    # -- lifecycle -------------------------------------------------------- #
    async def start(self) -> None:
        self.status = AgentStatus.STARTING
        await self.on_start()
        self.status = AgentStatus.RUNNING
        self.started_at = time.time()
        self.log.debug("agent started")

    async def stop(self) -> None:
        await self.on_stop()
        self.status = AgentStatus.STOPPED
        self.log.debug("agent stopped")

    async def on_start(self) -> None:  # noqa: B027 - optional hook, not abstract
        """Optional startup hook. Subclasses override it only when needed."""

    async def on_stop(self) -> None:  # noqa: B027 - optional hook, not abstract
        """Optional shutdown hook. Subclasses override it only when needed."""

    # -- execution -------------------------------------------------------- #
    @abstractmethod
    async def handle(self, task: Task) -> TaskResult:
        """Do the work. Subclasses implement this."""

    async def execute(self, task: Task) -> TaskResult:
        """Run a task with timing, status tracking and error capture."""
        if self.status == AgentStatus.STOPPED:
            await self.start()

        self.status = AgentStatus.BUSY
        started = time.perf_counter()
        try:
            result = await self.handle(task)
            result.duration_ms = result.duration_ms or (time.perf_counter() - started) * 1000
            self.tasks_completed += 1
            self.total_duration_ms += result.duration_ms
            return result
        except TaskExecutionError as exc:
            self.tasks_failed += 1
            self.last_error = str(exc)
            return TaskResult(
                task_id=task.id, agent=self.name, success=False, error=str(exc),
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        except Exception as exc:  # noqa: BLE001 - an agent must never crash the platform
            self.tasks_failed += 1
            self.last_error = str(exc)
            self.log.exception("task %s failed", task.id)
            return TaskResult(
                task_id=task.id, agent=self.name, success=False,
                error=f"{type(exc).__name__}: {exc}",
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        finally:
            self.status = AgentStatus.RUNNING

    # -- helpers available to subclasses ---------------------------------- #
    async def think(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ):
        """Call the model router using this agent's configured task kind."""
        return await self.ctx.router.complete(
            prompt,
            task=self.model_task,
            system=system or self.system_prompt(),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def system_prompt(self) -> str:
        return (
            f"You are the {self.name} agent inside AERA, an AI operating system. "
            f"{self.description} Answer precisely and stay within your specialisation."
        )

    async def recall(self, query: str, *, limit: int = 5, project_id: str | None = None):
        return await self.ctx.memory.recall(query, limit=limit, project_id=project_id)

    def can_handle(self, capability: Capability | str) -> bool:
        try:
            cap = Capability(capability)
        except ValueError:
            return False
        return cap in self.capabilities

    # -- introspection ---------------------------------------------------- #
    def describe(self) -> dict[str, Any]:
        avg = self.total_duration_ms / self.tasks_completed if self.tasks_completed else 0.0
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "capabilities": [c.value for c in self.capabilities],
            "priority": self.priority,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "avg_duration_ms": round(avg, 2),
            "last_error": self.last_error,
            "uptime_seconds": round(time.time() - self.started_at, 1) if self.started_at else 0,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} name={self.name} status={self.status.value}>"
