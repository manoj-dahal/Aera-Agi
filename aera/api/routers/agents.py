"""Agent management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...agents.base import Capability, Task
from ...core.errors import ValidationError
from ..deps import get_registry
from ..schemas import AgentActionRequest, AgentTaskRequest, ok

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
async def list_agents(registry=Depends(get_registry)):
    return ok(
        {
            "agents": registry.status(),
            "summary": registry.summary(),
            "capabilities": registry.capability_map(),
        }
    )


@router.get("/status")
async def agents_status(registry=Depends(get_registry)):
    return ok(registry.summary())


@router.get("/history")
async def agent_history(limit: int = 25, registry=Depends(get_registry)):
    return ok({"history": [r.to_public() for r in registry.history(limit)]})


@router.get("/{name}")
async def get_agent(name: str, registry=Depends(get_registry)):
    return ok(registry.get(name).describe())


@router.post("/start")
async def start_agent(payload: AgentActionRequest, registry=Depends(get_registry)):
    agent = await registry.start(payload.agent)
    return ok(agent.describe(), f"Agent '{payload.agent}' started")


@router.post("/stop")
async def stop_agent(payload: AgentActionRequest, registry=Depends(get_registry)):
    agent = await registry.stop(payload.agent)
    return ok(agent.describe(), f"Agent '{payload.agent}' stopped")


@router.post("/restart")
async def restart_agent(payload: AgentActionRequest, registry=Depends(get_registry)):
    agent = await registry.restart(payload.agent)
    return ok(agent.describe(), f"Agent '{payload.agent}' restarted")


@router.post("/task")
async def run_task(payload: AgentTaskRequest, registry=Depends(get_registry)):
    """Dispatch a task to a named agent or the best capability match."""
    try:
        capability = Capability(payload.capability)
    except ValueError as exc:
        raise ValidationError(
            f"unknown capability '{payload.capability}'",
            details={"available": [c.value for c in Capability]},
        ) from exc

    task = Task(
        capability=capability,
        input=payload.input,
        context=payload.context,
        conversation_id=payload.conversation_id,
        project_id=payload.project_id,
        requester="api",
    )
    result = await registry.dispatch(task, agent_name=payload.agent)
    return ok(result.to_public(), "Task complete" if result.success else "Task failed")
