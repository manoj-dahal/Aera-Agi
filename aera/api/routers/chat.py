"""Chat and AI generation endpoints."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ...agents.base import Capability
from ..deps import get_kernel_dep, get_router_dep
from ..schemas import ChatRequest, GenerateRequest, ok

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(payload: ChatRequest, kernel=Depends(get_kernel_dep)):
    """Main conversational entry point - runs the full Core Agent pipeline."""
    conversation_id = payload.conversation_id or uuid.uuid4().hex[:12]

    if payload.stream:
        return StreamingResponse(
            _stream_chat(kernel, payload, conversation_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Conversation-ID": conversation_id},
        )

    try:
        capability = Capability(payload.capability)
    except ValueError:
        capability = Capability.CONVERSATION

    result = await kernel.chat(
        payload.message,
        conversation_id=conversation_id,
        project_id=payload.project_id,
        agent=payload.agent,
        capability=capability,
    )
    return ok(
        {**result.to_public(), "conversation_id": conversation_id},
        "Response generated" if result.success else "Request failed",
    )


async def _stream_chat(kernel, payload: ChatRequest, conversation_id: str):
    """Server-sent events carrying incremental tokens."""
    yield _sse({"type": "start", "conversation_id": conversation_id})

    context = ""
    if kernel.memory is not None:
        context = await kernel.memory.build_context(
            payload.message, conversation_id=conversation_id, project_id=payload.project_id
        )

    system = (
        "You are AERA, an AI operating system with persistent memory. "
        "Be direct and technically precise."
    )
    if context:
        system += f"\n\n{context}"

    pieces: list[str] = []
    try:
        async for token in kernel.router.stream(payload.message, system=system):
            pieces.append(token)
            yield _sse({"type": "token", "content": token})
    except Exception as exc:  # noqa: BLE001
        yield _sse({"type": "error", "error": str(exc)})
        return

    full = "".join(pieces)
    if kernel.memory is not None and full:
        await kernel.memory.remember_exchange(
            payload.message, full, conversation_id=conversation_id,
            project_id=payload.project_id,
        )
    yield _sse({"type": "done", "content": full, "conversation_id": conversation_id})


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/ai/chat")
@router.post("/models/generate")
async def generate(payload: GenerateRequest, model_router=Depends(get_router_dep)):
    """Direct model access, bypassing the agent layer."""
    if payload.stream:
        async def gen():
            async for token in model_router.stream(
                payload.prompt, task=payload.task, model=payload.model,
                temperature=payload.temperature, max_tokens=payload.max_tokens,
                system=payload.system,
            ):
                yield _sse({"type": "token", "content": token})
            yield _sse({"type": "done"})

        return StreamingResponse(gen(), media_type="text/event-stream")

    response = await model_router.complete(
        payload.prompt,
        task=payload.task,
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        system=payload.system,
    )
    return ok(response.to_public(), "Generation complete")


@router.get("/models")
@router.get("/ai/models")
async def list_models(model_router=Depends(get_router_dep)):
    """Every model exposed by every healthy provider."""
    models = await model_router.list_models()
    return ok(
        {
            "models": [m.model_dump() for m in models],
            "count": len(models),
            "providers": list(model_router.providers),
        }
    )


@router.get("/models/health")
@router.get("/ai/providers")
async def provider_health(model_router=Depends(get_router_dep)):
    return ok(await model_router.health())
