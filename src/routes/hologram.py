"""Hologram routes (docs/09-HOLOGRAM.md).

The renderer (dashboard) polls /state or subscribes to hologram.frame
events; /speak/{text} previews the lip-sync viseme timeline.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.hologram.models import AvatarState, HologramFrame, Viseme

router = APIRouter(prefix="/hologram", tags=["hologram"])


class LipsyncRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


class LipsyncResponse(BaseModel):
    visemes: list[Viseme]
    total_ms: int


@router.get("/state", response_model=HologramFrame)
async def hologram_state(request: Request) -> HologramFrame:
    """Current avatar frame for the renderer."""
    return request.app.state.system.hologram.frame()


@router.post("/state/{state}", response_model=HologramFrame)
async def set_state(state: str, request: Request) -> HologramFrame:
    """Manual state override (renderer/dev tooling)."""
    try:
        avatar_state = AvatarState(state)
    except ValueError:
        valid = ", ".join(s.value for s in AvatarState)
        raise HTTPException(status_code=422, detail=f"unknown state; valid: {valid}") from None
    return await request.app.state.system.hologram.set_state(avatar_state)


@router.post("/lipsync", response_model=LipsyncResponse)
async def lipsync(body: LipsyncRequest, request: Request) -> LipsyncResponse:
    """Viseme timeline for a piece of text (docs/hologram/Lip-Sync.md)."""
    visemes = request.app.state.system.hologram.lipsync(body.text)
    return LipsyncResponse(
        visemes=visemes, total_ms=sum(v.duration_ms for v in visemes)
    )


@router.get("/gesture")
async def suggest_gesture(request: Request, text: str = "") -> dict[str, str | None]:
    """Automatic gesture selection for a given text context."""
    gesture = request.app.state.system.hologram.select_gesture(text)
    return {"gesture": gesture.value if gesture else None}
