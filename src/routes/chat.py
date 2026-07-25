"""Chat route — the Core Agent entry point (docs/07-AGENTS.md)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.common.schemas import TaskRequest, TaskResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=TaskResponse)
async def chat(task: TaskRequest, request: Request) -> TaskResponse:
    """Send a message to AERA. The Agent Manager routes it automatically."""
    return await request.app.state.agents.execute(task)
