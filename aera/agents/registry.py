# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Agent registry and scheduler.

Owns agent lifecycle, capability lookup and bounded-concurrency execution.
"""

from __future__ import annotations

import asyncio
from typing import Any

from ..core.errors import AgentNotFoundError
from ..core.events import EventBus, Topics
from ..core.logging import get_logger
from .base import Agent, AgentContext, Capability, Task, TaskResult

logger = get_logger("agents.registry")


class AgentRegistry:
    """Discovers, starts, stops and dispatches to agents."""

    def __init__(self, context: AgentContext, *, max_concurrency: int = 8) -> None:
        self.ctx = context
        self._agents: dict[str, Agent] = {}
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._history: list[TaskResult] = []
        self._max_history = 200
        context.registry = self

    # ------------------------------------------------------------------ #
    # registration
    # ------------------------------------------------------------------ #
    def register(self, agent: Agent) -> Agent:
        if agent.name in self._agents:
            logger.debug("replacing already-registered agent %s", agent.name)
        self._agents[agent.name] = agent
        logger.debug("registered agent %s", agent.name)
        return agent

    def register_class(self, agent_cls: type[Agent]) -> Agent:
        return self.register(agent_cls(self.ctx))

    def unregister(self, name: str) -> None:
        self._agents.pop(name, None)

    def get(self, name: str) -> Agent:
        agent = self._agents.get(name)
        if agent is None:
            raise AgentNotFoundError(f"agent not found: {name}")
        return agent

    def try_get(self, name: str) -> Agent | None:
        return self._agents.get(name)

    @property
    def agents(self) -> dict[str, Agent]:
        return dict(self._agents)

    def names(self) -> list[str]:
        return sorted(self._agents)

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._agents

    # ------------------------------------------------------------------ #
    # capability routing
    # ------------------------------------------------------------------ #
    def find_by_capability(self, capability: Capability | str) -> list[Agent]:
        """Agents that can serve a capability, strongest first."""
        try:
            cap = Capability(capability)
        except ValueError:
            return []
        matches = [a for a in self._agents.values() if cap in a.capabilities]
        matches.sort(key=lambda a: (-a.priority, a.tasks_failed, a.name))
        return matches

    def best_for(self, capability: Capability | str) -> Agent | None:
        matches = self.find_by_capability(capability)
        return matches[0] if matches else None

    def capability_map(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for agent in self._agents.values():
            for cap in agent.capabilities:
                out.setdefault(cap.value, []).append(agent.name)
        return {k: sorted(v) for k, v in sorted(out.items())}

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    async def start_all(self) -> None:
        await asyncio.gather(*(self.start(name) for name in list(self._agents)))

    async def stop_all(self) -> None:
        await asyncio.gather(
            *(self.stop(name) for name in list(self._agents)), return_exceptions=True
        )

    async def start(self, name: str) -> Agent:
        agent = self.get(name)
        await agent.start()
        await self._publish(Topics.AGENT_STARTED, {"agent": name})
        return agent

    async def stop(self, name: str) -> Agent:
        agent = self.get(name)
        await agent.stop()
        await self._publish(Topics.AGENT_STOPPED, {"agent": name})
        return agent

    async def restart(self, name: str) -> Agent:
        await self.stop(name)
        return await self.start(name)

    # ------------------------------------------------------------------ #
    # dispatch
    # ------------------------------------------------------------------ #
    async def dispatch(self, task: Task, *, agent_name: str | None = None) -> TaskResult:
        """Route a task to an explicit agent or the best capability match."""
        agent = self.get(agent_name) if agent_name else self.best_for(task.capability)
        if agent is None:
            raise AgentNotFoundError(
                f"no agent registered for capability '{task.capability.value}'"
            )

        await self._publish(
            Topics.AGENT_TASK_STARTED,
            {"agent": agent.name, "task_id": task.id, "capability": task.capability.value},
        )

        async with self._semaphore:
            result = await agent.execute(task)

        self._remember(result)
        topic = Topics.AGENT_TASK_COMPLETED if result.success else Topics.AGENT_TASK_FAILED
        await self._publish(
            topic,
            {
                "agent": agent.name,
                "task_id": task.id,
                "success": result.success,
                "duration_ms": round(result.duration_ms, 2),
                "error": result.error,
            },
        )
        return result

    async def dispatch_many(self, tasks: list[Task]) -> list[TaskResult]:
        """Execute tasks concurrently (bounded by the registry semaphore)."""
        return list(await asyncio.gather(*(self.dispatch(t) for t in tasks)))

    def _remember(self, result: TaskResult) -> None:
        self._history.append(result)
        if len(self._history) > self._max_history:
            del self._history[: len(self._history) - self._max_history]

    def history(self, limit: int = 50) -> list[TaskResult]:
        return self._history[-limit:]

    # ------------------------------------------------------------------ #
    # reporting
    # ------------------------------------------------------------------ #
    def status(self) -> list[dict[str, Any]]:
        return [a.describe() for a in sorted(self._agents.values(), key=lambda x: x.name)]

    def summary(self) -> dict[str, Any]:
        return {
            "total": len(self._agents),
            "running": sum(1 for a in self._agents.values() if a.status.value == "running"),
            "tasks_completed": sum(a.tasks_completed for a in self._agents.values()),
            "tasks_failed": sum(a.tasks_failed for a in self._agents.values()),
            "capabilities": len(self.capability_map()),
        }

    async def _publish(self, topic: str, payload: dict) -> None:
        bus: EventBus | None = self.ctx.bus
        if bus is not None:
            await bus.publish(topic, payload, source="agents")
