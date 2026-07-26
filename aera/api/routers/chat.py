# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Chat and AI generation endpoints."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ...agents.base import Capability
from ...ai.providers import create_provider
from ...core.errors import NotFoundError, ValidationError
from ..deps import get_kernel_dep, get_router_dep
from ..schemas import AddProviderRequest, ChatRequest, GenerateRequest, ok

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


# --------------------------------------------------------------------------- #
# custom providers
# --------------------------------------------------------------------------- #
@router.get("/models/providers/types")
async def provider_types():
    """Adapter names accepted when adding a provider."""
    from ...ai.providers import PROVIDER_REGISTRY

    return ok(
        {
            "types": sorted(PROVIDER_REGISTRY),
            "custom": "custom",
            "note": (
                "Use 'custom' with a base_url for any OpenAI-compatible server "
                "(vLLM, llama.cpp, LiteLLM, a company gateway)."
            ),
        }
    )


@router.post("/models/providers")
async def add_provider(payload: AddProviderRequest, kernel=Depends(get_kernel_dep)):
    """Register an AI provider at runtime.

    Previously providers could only come from config/models.yaml, which meant
    editing a file and restarting to point AERA at your own model. The
    registration is in-memory: persist it in the config file to survive a
    restart.
    """
    model_router = kernel.router
    if model_router is None:
        raise ValidationError("the AI router is unavailable")

    name = payload.name.strip().lower().replace(" ", "-")
    if not name:
        raise ValidationError("a provider name is required")
    if name == "builtin":
        raise ValidationError("'builtin' is reserved for the offline fallback")
    if model_router.get(name) and not payload.replace:
        raise ValidationError(
            f"provider '{name}' already exists; pass replace=true to overwrite"
        )

    options = dict(payload.options or {})
    options.setdefault("label", name)
    if payload.base_url:
        options["base_url"] = payload.base_url
    if payload.api_key:
        options["api_key"] = payload.api_key
    if payload.model:
        options["model"] = payload.model

    try:
        provider = create_provider(payload.type, **options)
    except KeyError as exc:
        from ...ai.providers import PROVIDER_REGISTRY

        raise ValidationError(
            str(exc), details={"available": sorted(PROVIDER_REGISTRY)}
        ) from exc
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"could not build provider: {exc}") from exc

    # The adapter names itself from `label`; force the requested name so the
    # caller can address it by exactly what they asked for.
    provider.name = name
    if model_router.get(name):
        await model_router.unregister(name)
    model_router.register(provider)

    healthy = await provider.health_check()
    return ok(
        {
            **provider.describe(),
            "healthy": healthy,
            # An unreachable endpoint is registered but flagged, rather than
            # rejected: the server may simply not be running yet.
            "warning": None if healthy else f"{name} did not respond to a health check",
        },
        f"Provider '{name}' registered",
    )


@router.post("/models/providers/{name}/test")
async def test_provider(name: str, kernel=Depends(get_kernel_dep)):
    """Health-check one provider and list the models it exposes."""
    model_router = kernel.router
    if model_router is None:
        raise ValidationError("the AI router is unavailable")

    provider = model_router.get(name)
    if provider is None:
        raise NotFoundError(f"no such provider: {name}")

    healthy = await provider.health_check()
    models: list[str] = []
    error: str | None = None
    if healthy:
        try:
            models = [m.id for m in await provider.list_models()]
        except Exception as exc:  # noqa: BLE001 - report, do not raise
            error = str(exc)

    return ok(
        {"provider": name, "healthy": healthy, "models": models, "error": error},
        f"{name} is reachable" if healthy else f"{name} is not responding",
    )


@router.delete("/models/providers/{name}")
async def remove_provider(name: str, kernel=Depends(get_kernel_dep)):
    model_router = kernel.router
    if model_router is None:
        raise ValidationError("the AI router is unavailable")

    try:
        removed = await model_router.unregister(name)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    if not removed:
        raise NotFoundError(f"no such provider: {name}")
    return ok({"provider": name}, f"Provider '{name}' removed")
