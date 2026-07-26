# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Automation / workflow engine (``docs/20-AUTOMATION.md``).

Executes declarative workflows made of actions, with conditionals, loops,
variable interpolation and full run history. Triggers can be manual, scheduled
or event-driven via the Event Bus.
"""

from __future__ import annotations

import asyncio
import re
import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..core.errors import ValidationError, WorkflowError
from ..core.events import EventBus, Topics
from ..core.logging import get_logger

logger = get_logger("automation.engine")

_VAR = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    EVENT = "event"
    FILE_CHANGE = "file_change"
    WEBHOOK = "webhook"
    STARTUP = "startup"
    AI_DECISION = "ai_decision"


class ActionType(str, Enum):
    AI_GENERATE = "ai_generate"
    AGENT_TASK = "agent_task"
    MEMORY_STORE = "memory_store"
    MEMORY_SEARCH = "memory_search"
    NOTIFY = "notify"
    PUBLISH_EVENT = "publish_event"
    SET_VARIABLE = "set_variable"
    WAIT = "wait"
    CONDITION = "condition"
    LOOP = "loop"
    LOG = "log"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Action(BaseModel):
    """One step in a workflow."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    type: ActionType
    name: str = ""
    params: dict[str, Any] = Field(default_factory=dict)
    store_as: str | None = None
    continue_on_error: bool = False
    # CONDITION / LOOP children
    then: list[Action] = Field(default_factory=list)
    otherwise: list[Action] = Field(default_factory=list)
    body: list[Action] = Field(default_factory=list)


Action.model_rebuild()


class Trigger(BaseModel):
    type: TriggerType = TriggerType.MANUAL
    #: event topic pattern, cron-ish spec or interval seconds
    value: str | None = None
    interval_seconds: float | None = None


class Workflow(BaseModel):
    """A named, versioned automation."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    description: str = ""
    enabled: bool = True
    triggers: list[Trigger] = Field(default_factory=lambda: [Trigger()])
    actions: list[Action] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    max_iterations: int = 100
    created_at: float = Field(default_factory=time.time)


class StepResult(BaseModel):
    action_id: str
    type: str
    success: bool = True
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class WorkflowRun(BaseModel):
    """A single execution of a workflow."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    workflow_id: str
    workflow_name: str
    status: RunStatus = RunStatus.PENDING
    started_at: float = Field(default_factory=time.time)
    finished_at: float | None = None
    steps: list[StepResult] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

    @property
    def duration_ms(self) -> float:
        end = self.finished_at or time.time()
        return (end - self.started_at) * 1000

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": round(self.duration_ms, 2),
            "steps": [s.model_dump() for s in self.steps],
            "error": self.error,
            "variables": {k: v for k, v in self.variables.items() if not k.startswith("_")},
        }


class AutomationEngine:
    """Registers, triggers and executes workflows."""

    def __init__(self, *, router=None, memory=None, registry=None, bus: EventBus | None = None) -> None:
        self.router = router
        self.memory = memory
        self.registry = registry
        self.bus = bus
        self.workflows: dict[str, Workflow] = {}
        self.runs: list[WorkflowRun] = []
        self._max_runs = 100
        self._scheduled: dict[str, asyncio.Task] = {}
        self._event_subs: list[Any] = []

    # ------------------------------------------------------------------ #
    # registration
    # ------------------------------------------------------------------ #
    def register(self, workflow: Workflow) -> Workflow:
        self.workflows[workflow.id] = workflow
        logger.info("workflow registered: %s (%s)", workflow.name, workflow.id)
        return workflow

    def create(self, **kwargs: Any) -> Workflow:
        return self.register(Workflow(**kwargs))

    def get(self, workflow_id: str) -> Workflow:
        wf = self.workflows.get(workflow_id)
        if wf is None:
            # allow lookup by name for convenience
            for candidate in self.workflows.values():
                if candidate.name == workflow_id:
                    return candidate
            raise ValidationError(f"workflow not found: {workflow_id}")
        return wf

    def remove(self, workflow_id: str) -> None:
        self.workflows.pop(workflow_id, None)
        task = self._scheduled.pop(workflow_id, None)
        if task:
            task.cancel()

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "enabled": w.enabled,
                "actions": len(w.actions),
                "triggers": [t.type.value for t in w.triggers],
            }
            for w in self.workflows.values()
        ]

    # ------------------------------------------------------------------ #
    # execution
    # ------------------------------------------------------------------ #
    async def run(self, workflow_id: str, *, variables: dict | None = None) -> WorkflowRun:
        """Execute a workflow start to finish."""
        workflow = self.get(workflow_id)
        if not workflow.enabled:
            raise WorkflowError(f"workflow '{workflow.name}' is disabled")

        run = WorkflowRun(workflow_id=workflow.id, workflow_name=workflow.name)
        run.variables = {**workflow.variables, **(variables or {})}
        run.status = RunStatus.RUNNING
        self._remember(run)

        if self.bus:
            await self.bus.publish(
                Topics.AUTOMATION_STARTED,
                {"workflow": workflow.name, "run_id": run.id},
                source="automation",
            )

        try:
            await self._execute(workflow.actions, run, workflow)
            run.status = RunStatus.SUCCESS
        except WorkflowError as exc:
            run.status = RunStatus.FAILED
            run.error = str(exc)
            logger.warning("workflow %s failed: %s", workflow.name, exc)
        except Exception as exc:  # noqa: BLE001
            run.status = RunStatus.FAILED
            run.error = f"{type(exc).__name__}: {exc}"
            logger.exception("workflow %s crashed", workflow.name)
        finally:
            run.finished_at = time.time()

        if self.bus:
            topic = (
                Topics.AUTOMATION_COMPLETED
                if run.status == RunStatus.SUCCESS
                else Topics.AUTOMATION_FAILED
            )
            await self.bus.publish(
                topic,
                {"workflow": workflow.name, "run_id": run.id, "status": run.status.value},
                source="automation",
            )
        return run

    async def _execute(self, actions: list[Action], run: WorkflowRun, workflow: Workflow) -> None:
        for action in actions:
            started = time.perf_counter()
            try:
                output = await self._execute_one(action, run, workflow)
                step = StepResult(
                    action_id=action.id, type=action.type.value, success=True, output=output,
                    duration_ms=(time.perf_counter() - started) * 1000,
                )
                if action.store_as:
                    run.variables[action.store_as] = output
            except Exception as exc:  # noqa: BLE001
                step = StepResult(
                    action_id=action.id, type=action.type.value, success=False,
                    error=f"{type(exc).__name__}: {exc}",
                    duration_ms=(time.perf_counter() - started) * 1000,
                )
                run.steps.append(step)
                if action.continue_on_error:
                    continue
                raise WorkflowError(
                    f"action '{action.name or action.type.value}' failed: {exc}"
                ) from exc
            run.steps.append(step)

    async def _execute_one(self, action: Action, run: WorkflowRun, workflow: Workflow) -> Any:
        params = self._resolve(action.params, run.variables)
        kind = action.type

        if kind == ActionType.LOG:
            message = str(params.get("message", ""))
            logger.info("[workflow %s] %s", workflow.name, message)
            return message

        if kind == ActionType.SET_VARIABLE:
            for key, value in params.items():
                run.variables[key] = value
            return params

        if kind == ActionType.WAIT:
            seconds = min(float(params.get("seconds", 1)), 60.0)
            await asyncio.sleep(seconds)
            return {"waited": seconds}

        if kind == ActionType.NOTIFY:
            payload = {
                "title": params.get("title", "AERA"),
                "message": params.get("message", ""),
                "level": params.get("level", "info"),
            }
            if self.bus:
                await self.bus.publish(Topics.NOTIFICATION, payload, source="automation")
            return payload

        if kind == ActionType.PUBLISH_EVENT:
            topic = params.get("topic")
            if not topic:
                raise WorkflowError("publish_event requires a 'topic'")
            if self.bus:
                await self.bus.publish(topic, params.get("payload", {}), source="automation")
            return {"topic": topic}

        if kind == ActionType.AI_GENERATE:
            if self.router is None:
                raise WorkflowError("no model router available")
            response = await self.router.complete(
                str(params.get("prompt", "")),
                task=params.get("task", "default"),
                system=params.get("system"),
                temperature=float(params.get("temperature", 0.7)),
            )
            return response.content

        if kind == ActionType.AGENT_TASK:
            if self.registry is None:
                raise WorkflowError("no agent registry available")
            from ..agents.base import Capability, Task  # local import avoids a cycle

            capability = params.get("capability", "conversation")
            task = Task(
                capability=Capability(capability),
                input=str(params.get("input", "")),
                context=params.get("context", {}),
                requester="automation",
            )
            result = await self.registry.dispatch(task, agent_name=params.get("agent"))
            if not result.success:
                raise WorkflowError(result.error or "agent task failed")
            return result.output

        if kind == ActionType.MEMORY_STORE:
            if self.memory is None:
                raise WorkflowError("no memory engine available")
            node = await self.memory.store(
                title=str(params.get("title", "Automation result")),
                content=str(params.get("content", "")),
                tags=params.get("tags", ["automation"]),
                importance=float(params.get("importance", 0.5)),
                creator="automation",
            )
            return node.id

        if kind == ActionType.MEMORY_SEARCH:
            if self.memory is None:
                raise WorkflowError("no memory engine available")
            results = await self.memory.recall(
                str(params.get("query", "")), limit=int(params.get("limit", 5))
            )
            return [{"id": r.node.id, "title": r.node.title, "score": r.score} for r in results]

        if kind == ActionType.CONDITION:
            if self._evaluate(params, run.variables):
                await self._execute(action.then, run, workflow)
                return {"branch": "then"}
            await self._execute(action.otherwise, run, workflow)
            return {"branch": "else"}

        if kind == ActionType.LOOP:
            return await self._loop(action, params, run, workflow)

        raise WorkflowError(f"unsupported action type: {kind}")

    async def _loop(self, action: Action, params: dict, run: WorkflowRun, workflow: Workflow) -> dict:
        """``for_each`` over a list, or ``times`` repetitions - both bounded."""
        iterations = 0
        limit = min(int(params.get("times", 0) or workflow.max_iterations), workflow.max_iterations)

        items = params.get("for_each")
        if isinstance(items, list):
            for item in items[: workflow.max_iterations]:
                run.variables["item"] = item
                run.variables["index"] = iterations
                await self._execute(action.body, run, workflow)
                iterations += 1
        else:
            while iterations < limit:
                run.variables["index"] = iterations
                await self._execute(action.body, run, workflow)
                iterations += 1
        return {"iterations": iterations}

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _resolve(self, value: Any, variables: dict) -> Any:
        """Interpolate ``{{ var }}`` placeholders recursively."""
        if isinstance(value, str):
            def replace(match: re.Match) -> str:
                key = match.group(1)
                cursor: Any = variables
                for part in key.split("."):
                    if isinstance(cursor, dict) and part in cursor:
                        cursor = cursor[part]
                    else:
                        return match.group(0)
                return str(cursor)

            return _VAR.sub(replace, value)
        if isinstance(value, dict):
            return {k: self._resolve(v, variables) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve(v, variables) for v in value]
        return value

    def _evaluate(self, params: dict, variables: dict) -> bool:
        """Evaluate a structured condition - no eval(), no code execution."""
        left = params.get("left")
        right = params.get("right")
        op = str(params.get("operator", "equals")).lower()

        if op in ("equals", "eq", "=="):
            return left == right
        if op in ("not_equals", "ne", "!="):
            return left != right
        if op in ("contains", "in"):
            try:
                return right in left  # type: ignore[operator]
            except TypeError:
                return False
        if op in ("greater_than", "gt", ">"):
            return _num(left) > _num(right)
        if op in ("less_than", "lt", "<"):
            return _num(left) < _num(right)
        if op == "exists":
            return left is not None and left != ""
        if op == "empty":
            return left is None or left == "" or left == [] or left == {}
        if op == "truthy":
            return bool(left)
        raise WorkflowError(f"unsupported condition operator: {op}")

    def _remember(self, run: WorkflowRun) -> None:
        self.runs.append(run)
        if len(self.runs) > self._max_runs:
            del self.runs[: len(self.runs) - self._max_runs]

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_public() for r in self.runs[-limit:]]

    # ------------------------------------------------------------------ #
    # triggers
    # ------------------------------------------------------------------ #
    async def install_triggers(self) -> None:
        """Wire event and schedule triggers for every enabled workflow."""
        for workflow in self.workflows.values():
            if not workflow.enabled:
                continue
            for trigger in workflow.triggers:
                if trigger.type == TriggerType.EVENT and trigger.value and self.bus:
                    await self._subscribe_event(workflow.id, trigger.value)
                elif trigger.type == TriggerType.SCHEDULE and trigger.interval_seconds:
                    self._schedule(workflow.id, trigger.interval_seconds)
                elif trigger.type == TriggerType.STARTUP:
                    asyncio.create_task(self.run(workflow.id))

    async def _subscribe_event(self, workflow_id: str, pattern: str) -> None:
        async def handler(event) -> None:
            await self.run(workflow_id, variables={"event": event.payload, "topic": event.topic})

        sub = await self.bus.subscribe(pattern, handler)
        self._event_subs.append(sub)

    def _schedule(self, workflow_id: str, interval: float) -> None:
        async def loop() -> None:
            while True:
                await asyncio.sleep(max(1.0, interval))
                try:
                    await self.run(workflow_id)
                except Exception:  # noqa: BLE001
                    logger.exception("scheduled workflow %s failed", workflow_id)

        self._scheduled[workflow_id] = asyncio.create_task(loop())

    async def shutdown(self) -> None:
        for task in self._scheduled.values():
            task.cancel()
        self._scheduled.clear()
        for sub in self._event_subs:
            await sub.unsubscribe()
        self._event_subs.clear()


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
