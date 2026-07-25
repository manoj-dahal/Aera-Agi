"""Automation Manager + Workflow Engine (docs/20-AUTOMATION.md).

Documented architecture:

    User → Automation Manager → Workflow Engine
              ├─ Trigger Engine (manual / schedule / event / AI decision)
              ├─ Action Engine
              └─ AI Agents
                        ↓
                  Memory Graph

Documented lifecycle: Trigger → Validation → Load Workflow → Context
Analysis → Agent Selection → Execute Actions → Save Results → Memory Update.

Learning Engine (docs/20): runs, failures, and execution time are tracked
per workflow and stored in the Memory Graph for future optimization.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.automation.actions import ActionEngine
from src.automation.models import (
    ExecutionResult,
    ExecutionStatus,
    ScheduleKind,
    TriggerType,
    Workflow,
    WorkflowCreate,
)
from src.common.schemas import MemoryNodeCreate, NodeType
from src.logging.logger import get_logger

if TYPE_CHECKING:
    from src.agents.manager import AgentManager
    from src.events.bus import Event, EventBus
    from src.memory.graph import MemoryGraph
    from src.services.manager import ServiceManager

log = get_logger("automation")

_SCHEDULE_SECONDS: dict[ScheduleKind, float] = {
    ScheduleKind.HOURLY: 3600,
    ScheduleKind.DAILY: 86_400,
    ScheduleKind.WEEKLY: 604_800,
    ScheduleKind.MONTHLY: 2_592_000,
}


class AutomationManager:
    """Registers workflows, wires triggers, executes, and learns."""

    def __init__(
        self,
        agents: AgentManager,
        memory: MemoryGraph,
        bus: EventBus,
        services: ServiceManager,
    ) -> None:
        self.memory = memory
        self.bus = bus
        self.services = services
        self.actions = ActionEngine(agents, memory, bus)
        self.workflows: dict[int, Workflow] = {}
        self.history: list[ExecutionResult] = []
        self._next_id = 1

    # ── Registration + Trigger Engine ────────────────────

    def register(self, spec: WorkflowCreate) -> Workflow:
        workflow = Workflow(id=self._next_id, **spec.model_dump())
        self._next_id += 1
        self.workflows[workflow.id] = workflow
        self._wire_trigger(workflow)
        log.info("workflow %d '%s' registered (trigger=%s)",
                 workflow.id, workflow.name, workflow.trigger.type.value)
        return workflow

    def _wire_trigger(self, workflow: Workflow) -> None:
        trigger = workflow.trigger

        if trigger.type == TriggerType.EVENT and trigger.topic:
            async def on_event(event: Event, _wf_id: int = workflow.id) -> None:
                wf = self.workflows.get(_wf_id)
                if wf and wf.enabled:
                    await self.execute(_wf_id, TriggerType.EVENT, {"event": event.data})

            self.bus.subscribe(trigger.topic, on_event)

        elif trigger.type == TriggerType.SCHEDULE and trigger.schedule:
            interval = (
                trigger.interval_seconds
                if trigger.schedule == ScheduleKind.INTERVAL
                else _SCHEDULE_SECONDS.get(trigger.schedule)
            )
            if interval:
                async def tick(_wf_id: int = workflow.id) -> None:
                    wf = self.workflows.get(_wf_id)
                    if wf and wf.enabled:
                        await self.execute(_wf_id, TriggerType.SCHEDULE)

                # Workflow Scheduler runs as a documented background service.
                self.services.register(
                    f"workflow-{workflow.id}-scheduler", tick, interval=interval
                )

    def unregister(self, workflow_id: int) -> None:
        if workflow_id not in self.workflows:
            raise KeyError(f"workflow {workflow_id} not found")
        del self.workflows[workflow_id]

    # ── Workflow Engine (documented lifecycle) ───────────

    async def execute(
        self,
        workflow_id: int,
        trigger: TriggerType = TriggerType.MANUAL,
        extra_variables: dict | None = None,
    ) -> ExecutionResult:
        # Validation → Load Workflow
        workflow = self.workflows.get(workflow_id)
        if workflow is None:
            raise KeyError(f"workflow {workflow_id} not found")

        started = datetime.now(timezone.utc)
        t0 = time.perf_counter()
        # Context Analysis: variables = user vars + trigger context
        variables = {**workflow.variables, **(extra_variables or {})}

        # Execute Actions (Agent Selection happens inside AI actions)
        results = []
        status = ExecutionStatus.SUCCESS
        for spec in workflow.actions:
            result = await self.actions.run(spec, variables, workflow.approved)
            results.append(result)
            if result.status in (ExecutionStatus.FAILED, ExecutionStatus.BLOCKED):
                status = result.status
                break  # Error Recovery: stop; retries already happened per-action

        duration_ms = (time.perf_counter() - t0) * 1000

        # Learning Engine: execution time / failure patterns
        workflow.runs += 1
        if status != ExecutionStatus.SUCCESS:
            workflow.failures += 1
        workflow.last_run = started
        workflow.avg_duration_ms = (
            workflow.avg_duration_ms + (duration_ms - workflow.avg_duration_ms) / workflow.runs
        )

        execution = ExecutionResult(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            status=status,
            trigger=trigger,
            results=results,
            variables=variables,
            duration_ms=round(duration_ms, 2),
            started_at=started,
        )
        self.history.append(execution)
        if len(self.history) > 200:
            self.history.pop(0)

        # Save Results → Memory Update (docs: every execution updates the graph)
        self.memory.add_node(
            MemoryNodeCreate(
                type=NodeType.TASK,
                content=(
                    f"workflow '{workflow.name}' {status.value} "
                    f"({trigger.value}, {duration_ms:.0f}ms, run #{workflow.runs})"
                ),
                importance=0.3 if status == ExecutionStatus.SUCCESS else 0.6,
            )
        )
        # Audit log via event bus
        await self.bus.publish(
            "automation.executed",
            {"workflow": workflow.name, "status": status.value, "trigger": trigger.value},
        )
        return execution
