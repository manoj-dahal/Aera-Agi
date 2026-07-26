# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Skill catalogue endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...core.errors import NotFoundError
from ..deps import get_kernel_dep
from ..schemas import ok

router = APIRouter(prefix="/skills", tags=["skills"])


def _skills(kernel):
    if kernel.skills is None:
        raise NotFoundError("the skill manager is unavailable")
    return kernel.skills


@router.get("")
async def list_skills(
    category: str | None = None,
    agent: str | None = None,
    available_only: bool = False,
    kernel=Depends(get_kernel_dep),
):
    """The full catalogue, optionally filtered."""
    manager = _skills(kernel)
    if category:
        states = manager.by_category(category)
    elif agent:
        states = manager.by_agent(agent)
    else:
        states = manager.all()

    if available_only:
        states = [s for s in states if s.availability.value == "available"]

    return ok(
        {
            "skills": [s.to_dict() for s in sorted(states, key=lambda x: x.skill.name)],
            "count": len(states),
            "summary": manager.summary(),
        }
    )


@router.get("/summary")
async def skills_summary(kernel=Depends(get_kernel_dep)):
    return ok(_skills(kernel).summary())


@router.get("/backends")
async def backends(kernel=Depends(get_kernel_dep)):
    """Which backends are present and what each unlocks."""
    return ok(_skills(kernel).summary()["backends"])


@router.get("/gaps")
async def capability_gaps(kernel=Depends(get_kernel_dep)):
    """Skills that cannot run, and precisely why."""
    manager = _skills(kernel)
    return ok(
        {
            "gaps": [
                {
                    "id": s.skill.id,
                    "name": s.skill.name,
                    "category": s.skill.category.value,
                    "backend": s.skill.backend.value,
                    "availability": s.availability.value,
                    "reason": s.reason,
                }
                for s in manager.unavailable()
            ]
        }
    )


@router.post("/match")
async def match_skills(
    q: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=25),
    kernel=Depends(get_kernel_dep),
):
    """Rank catalogued skills against a request."""
    matches = _skills(kernel).match(q, limit=limit)
    return ok({"matches": [m.to_dict() for m in matches], "count": len(matches)})


@router.post("/resolve")
async def resolve_skills(kernel=Depends(get_kernel_dep)):
    """Re-probe backends and recompute availability."""
    await _skills(kernel).resolve()
    return ok(_skills(kernel).summary(), "Skills resolved")


@router.get("/insights")
async def learning_insights(kernel=Depends(get_kernel_dep)):
    """What the Learning Engine has observed."""
    if kernel.learning_engine is None:
        raise NotFoundError("the learning engine is unavailable")
    return ok(kernel.learning_engine.insights())


@router.get("/{skill_id}")
async def get_skill(skill_id: str, kernel=Depends(get_kernel_dep)):
    state = _skills(kernel).get(skill_id)
    if state is None:
        raise NotFoundError(f"unknown skill: {skill_id}")
    return ok(state.to_dict())
