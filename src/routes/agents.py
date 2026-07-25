"""Agent routes (docs/07-AGENTS.md)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.common.schemas import AgentInfo

router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=list[AgentInfo])
async def list_agents(request: Request) -> list[AgentInfo]:
    return request.app.state.agents.list_agents()
