# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""AERA skill system: catalogue, manager and background engines."""

from .engines import (
    ActiveContext,
    ContextEngine,
    LearningEngine,
    PlanningEngine,
    PlanStep,
    ReasoningEngine,
    ReasoningResult,
)
from .manager import (
    Availability,
    Backend,
    BackendStatus,
    SkillManager,
    SkillMatch,
    SkillState,
)
from .registry import (
    SKILLS,
    SKILLS_BY_ID,
    Skill,
    SkillCategory,
    category_counts,
    skills_in,
)

__all__ = [
    "SKILLS",
    "SKILLS_BY_ID",
    "ActiveContext",
    "Availability",
    "Backend",
    "BackendStatus",
    "ContextEngine",
    "LearningEngine",
    "PlanStep",
    "PlanningEngine",
    "ReasoningEngine",
    "ReasoningResult",
    "Skill",
    "SkillCategory",
    "SkillManager",
    "SkillMatch",
    "SkillState",
    "category_counts",
    "skills_in",
]
