"""Action Engine — executes workflow actions (docs/20-AUTOMATION.md).

Security per docs/20: Permission Validation, User Approval for Sensitive
Actions, Audit Logs (via event bus + execution log).
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import httpx

from src.automation.models import (
    SENSITIVE_ACTIONS,
    ActionResult,
    ActionSpec,
    ActionType,
    Condition,
    ExecutionStatus,
)
from src.common.schemas import MemoryNodeCreate, NodeType, TaskRequest
from src.logging.logger import get_logger

if TYPE_CHECKING:
    from src.agents.manager import AgentManager
    from src.events.bus import EventBus
    from src.memory.graph import MemoryGraph

log = get_logger("automation.actions")


def _render(value: Any, variables: dict[str, Any]) -> Any:
    """Template {{var}} placeholders inside string params (Workflow Variables)."""
    if isinstance(value, str):
        for key, val in variables.items():
            value = value.replace("{{" + key + "}}", str(val))
        return value
    if isinstance(value, dict):
        return {k: _render(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [_render(v, variables) for v in value]
    return value


def check_condition(cond: Condition | None, variables: dict[str, Any]) -> bool:
    """Documented conditions: exists, empty, equals, contains, gt, lt."""
    if cond is None:
        return True
    actual = variables.get(cond.variable)
    op = cond.operator
    if op == "exists":
        return actual is not None
    if op == "empty":
        return not actual
    if op == "equals":
        return actual == cond.value
    if op == "contains":
        return cond.value is not None and cond.value in str(actual or "")
    if op == "gt":
        return actual is not None and float(actual) > float(cond.value)
    if op == "lt":
        return actual is not None and float(actual) < float(cond.value)
    raise ValueError(f"unknown condition operator: {op}")


class ActionEngine:
    """Executes individual workflow actions with retry (docs/20 Error Recovery)."""

    def __init__(self, agents: AgentManager, memory: MemoryGraph, bus: EventBus) -> None:
        self.agents = agents
        self.memory = memory
        self.bus = bus

    async def run(
        self, spec: ActionSpec, variables: dict[str, Any], approved: bool
    ) -> ActionResult:
        # Conditional Logic
        if not check_condition(spec.condition, variables):
            return ActionResult(action=spec.type, status=ExecutionStatus.SKIPPED)

        # Permission Validation / User Approval for Sensitive Actions
        if spec.type in SENSITIVE_ACTIONS and not approved:
            log.warning("blocked sensitive action %s (workflow not approved)", spec.type)
            return ActionResult(
                action=spec.type,
                status=ExecutionStatus.BLOCKED,
                error="sensitive action requires an approved workflow",
            )

        params = _render(spec.params, variables)

        # Retry loop (docs/20: Failure → Save State → Retry → ... → Complete)
        attempts = 0
        while True:
            attempts += 1
            try:
                output = await self._dispatch(spec.type, params)
                if spec.save_as:
                    variables[spec.save_as] = output
                return ActionResult(
                    action=spec.type,
                    status=ExecutionStatus.SUCCESS,
                    output=output,
                    attempts=attempts,
                )
            except Exception as exc:  # noqa: BLE001 — recovery is the documented behavior
                if attempts > spec.retries:
                    return ActionResult(
                        action=spec.type,
                        status=ExecutionStatus.FAILED,
                        error=str(exc),
                        attempts=attempts,
                    )
                await asyncio.sleep(min(0.5 * attempts, 5.0))

    async def _dispatch(self, action: ActionType, p: dict[str, Any]) -> Any:
        if action == ActionType.AI_GENERATE:
            result = await self.agents.execute(
                TaskRequest(message=str(p.get("prompt", "")), agent=p.get("agent"))
            )
            return result.response

        if action == ActionType.MEMORY_SEARCH:
            nodes = self.memory.recall(str(p.get("query", "")), limit=int(p.get("limit", 5)))
            return [n.content for n in nodes]

        if action == ActionType.MEMORY_UPDATE:
            node = self.memory.add_node(
                MemoryNodeCreate(
                    type=NodeType(p.get("node_type", "fact")),
                    content=str(p["content"]),
                    importance=float(p.get("importance", 0.5)),
                )
            )
            return node.id

        if action == ActionType.NOTIFY:
            await self.bus.publish(
                "notification", {"message": str(p.get("message", "")), "level": p.get("level", "info")}
            )
            return "sent"

        if action == ActionType.WAIT:
            seconds = min(float(p.get("seconds", 1.0)), 300.0)  # safeguard
            await asyncio.sleep(seconds)
            return f"waited {seconds}s"

        if action == ActionType.CONDITION:
            return True  # evaluated via spec.condition; standalone no-op

        if action == ActionType.EXECUTE_COMMAND:
            proc = await asyncio.create_subprocess_shell(
                str(p["command"]),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            out, _ = await asyncio.wait_for(
                proc.communicate(), timeout=float(p.get("timeout", 60))
            )
            if proc.returncode != 0:
                raise RuntimeError(f"command exited {proc.returncode}: {out.decode()[:500]}")
            return out.decode()[:10_000]

        if action == ActionType.HTTP_REQUEST:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.request(
                    p.get("method", "GET"), str(p["url"]), json=p.get("json")
                )
                return {"status": res.status_code, "body": res.text[:10_000]}

        raise ValueError(f"unsupported action type: {action}")
