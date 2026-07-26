# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Image analysis endpoints.

Split from the agent so a caller that only wants measurements does not pay
for model dispatch, and so the two failure modes stay distinguishable: an
unreadable file is a 4xx, an absent vision model is a successful response
that says no model answered.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core.errors import ValidationError
from ..deps import get_kernel_dep, get_registry
from ..schemas import ok

router = APIRouter(prefix="/vision", tags=["vision"])


@router.get("/status")
async def vision_status(kernel=Depends(get_kernel_dep)):
    """What image understanding can do right now.

    Reports the two layers separately, because they fail independently:
    local analysis needs Pillow, model description needs a provider.
    """
    from ...services import vision

    provider = None
    for name, candidate in kernel.router.providers.items():
        if not candidate.enabled or not await candidate.health_check():
            continue
        try:
            models = await candidate.list_models()
        except Exception:  # noqa: BLE001
            continue
        if any(m.supports_vision for m in models):
            provider = name
            break

    local = vision.pillow_available()
    return ok(
        {
            "local_analysis": local,
            "local_remedy": None if local else 'pip install -e ".[vision]"',
            "model_description": provider is not None,
            "provider": provider,
            "supported_formats": sorted(vision.SUPPORTED_FORMATS),
            "max_image_mb": vision.MAX_IMAGE_BYTES // 1_048_576,
            "max_edge_px": vision.MAX_EDGE_PX,
            # Said plainly: measurement is not recognition.
            "local_identifies_objects": False,
        }
    )


@router.post("/analyse")
async def analyse_image(payload: dict):
    """Measure an image. Offline, no model, no network."""
    from ...services import vision

    path = (payload or {}).get("path")
    if not path:
        raise ValidationError("a 'path' is required")

    analysis = vision.analyse(path)
    return ok(analysis.to_dict(), analysis.describe())


@router.post("/describe")
async def describe_image(payload: dict, registry=Depends(get_registry)):
    """Analyse an image and, when a vision model is connected, describe it."""
    from ...agents.base import Capability, Task

    path = (payload or {}).get("path")
    if not path:
        raise ValidationError("a 'path' is required")

    question = (payload or {}).get("question") or "Describe this image."
    task = Task(
        capability=Capability.VISION,
        input=question,
        context={"path": path},
        requester="api",
    )
    result = await registry.dispatch(task, agent_name="vision")
    return ok(result.to_public(), result.output[:120] if result.output else "")


@router.post("/estimate")
async def estimate_cost(payload: dict):
    """How large an image becomes on the wire, and roughly what it costs.

    Worth knowing before sending a batch: providers tile images and charge
    per tile, so a folder of photographs is not free.
    """
    from ...services import vision

    path = (payload or {}).get("path")
    if not path:
        raise ValidationError("a 'path' is required")

    prepared = vision.prepare(path)
    return ok(
        {
            **prepared.to_dict(),
            "estimated_tokens": vision.estimate_tokens(prepared),
            "note": (
                "Tokens are the common 512-pixel-tile approximation. Exact "
                "arithmetic differs per provider."
            ),
        }
    )
