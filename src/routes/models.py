"""Model routes — available local and cloud models (docs/18, 19)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from src.common.schemas import ModelInfo

router = APIRouter(tags=["models"])


@router.get("/models", response_model=list[ModelInfo])
async def list_models(request: Request) -> list[ModelInfo]:
    return await request.app.state.router.list_models()
