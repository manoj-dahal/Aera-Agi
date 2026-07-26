# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Background engines.

The specification names five engines that run behind the interface:

* **Context Engine**   - tracks what is currently relevant
* **Reasoning Engine** - decides how a request should be approached
* **Planning Engine**  - turns goals into ordered steps
* **Learning Engine**  - observes outcomes and adapts
* **Skill Manager**    - see :mod:`aera.skills.manager`

They are deliberately not agents. Agents answer requests; engines maintain
state and make routing decisions continuously, whether or not anyone is
talking to AERA.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..core.logging import get_logger
from .manager import Availability, SkillManager

if TYPE_CHECKING:  # pragma: no cover
    from ..agents.registry import AgentRegistry
    from ..memory.engine import MemoryEngine

logger = get_logger("skills.engines")


# --------------------------------------------------------------------------- #
# Context Engine
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class ActiveContext:
    """What AERA currently considers relevant."""

    conversation_id: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    open_file: str | None = None
    last_intent: str | None = None
    last_agent: str | None = None
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "open_file": self.open_file,
            "last_intent": self.last_intent,
            "last_agent": self.last_agent,
            "updated_at": self.updated_at,
        }


class ContextEngine:
    """Maintains the active working context and detects switches."""

    def __init__(self, *, memory: MemoryEngine | None = None, bus: Any = None) -> None:
        self.memory = memory
        self.bus = bus
        self.context = ActiveContext()
        self._switches = 0

    async def update(self, **changes: Any) -> ActiveContext:
        """Apply changes, publishing an event when the project changes."""
        previous_project = self.context.project_id

        for key, value in changes.items():
            if value is None or not hasattr(self.context, key):
                continue
            setattr(self.context, key, value)
        self.context.updated_at = time.time()

        if previous_project and self.context.project_id != previous_project:
            self._switches += 1
            logger.info("context switched to project %s", self.context.project_name)
            if self.bus:
                await self.bus.publish(
                    "context.switched",
                    {"from": previous_project, "to": self.context.project_id},
                    source="context",
                )

        if self.memory is not None:
            self.memory.set_working("active_context", self.context.to_dict(), ttl=3600)
        return self.context

    def snapshot(self) -> dict[str, Any]:
        return {**self.context.to_dict(), "switches": self._switches}


# --------------------------------------------------------------------------- #
# Reasoning Engine
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class ReasoningResult:
    """How a request should be approached."""

    complexity: str            # trivial | simple | moderate | complex
    needs_planning: bool
    needs_memory: bool
    suggested_agent: str | None
    suggested_skill: str | None
    unavailable_reason: str | None
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "complexity": self.complexity,
            "needs_planning": self.needs_planning,
            "needs_memory": self.needs_memory,
            "suggested_agent": self.suggested_agent,
            "suggested_skill": self.suggested_skill,
            "unavailable_reason": self.unavailable_reason,
            "rationale": self.rationale,
        }


class ReasoningEngine:
    """Assesses a request before any model is called.

    Deliberately rule-based: routing decisions must work offline, run in
    microseconds, and be inspectable. Calling a model to decide which model to
    call is a loop worth avoiding.
    """

    #: Markers of a request that needs decomposition rather than one answer.
    _MULTI_STEP = (
        " and then ", " after that ", " followed by ", "step by step",
        "first ", "finally ", "migrate", "refactor the entire", "build a",
    )
    _MEMORY_HINTS = (
        "remember", "recall", "last time", "we discussed", "earlier",
        "what did i", "my preference", "as i said",
    )

    def __init__(self, *, skills: SkillManager) -> None:
        self.skills = skills

    def assess(self, text: str) -> ReasoningResult:
        lowered = (text or "").lower().strip()
        words = len(lowered.split())

        multi_step = sum(1 for marker in self._MULTI_STEP if marker in lowered)
        needs_memory = any(hint in lowered for hint in self._MEMORY_HINTS)

        if words <= 3:
            complexity = "trivial"
        elif words <= 20 and multi_step == 0:
            complexity = "simple"
        elif multi_step >= 2 or words > 80:
            complexity = "complex"
        else:
            complexity = "moderate"

        matches = self.skills.match(text, limit=5)
        best = matches[0] if matches else None
        available = next(
            (m for m in matches if m.availability is Availability.AVAILABLE), None
        )

        suggested_agent = available.skill.agent if available else None
        suggested_skill = available.skill.id if available else None

        unavailable_reason = None
        if best and available is None:
            # The strongest match cannot run; say why rather than silently
            # routing somewhere that will improvise.
            unavailable_reason = (
                f"{best.skill.name} is the best match but is unavailable: {best.reason}"
            )

        rationale = (
            f"{complexity} request ({words} words)"
            + (f", matched {best.skill.name}" if best else ", no specific skill matched")
            + (", needs planning" if complexity == "complex" else "")
            + (", memory-dependent" if needs_memory else "")
        )

        return ReasoningResult(
            complexity=complexity,
            needs_planning=complexity == "complex",
            needs_memory=needs_memory or complexity != "trivial",
            suggested_agent=suggested_agent,
            suggested_skill=suggested_skill,
            unavailable_reason=unavailable_reason,
            rationale=rationale,
        )


# --------------------------------------------------------------------------- #
# Planning Engine
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class PlanStep:
    index: int
    description: str
    skill: str | None
    agent: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "description": self.description,
            "skill": self.skill,
            "agent": self.agent,
        }


class PlanningEngine:
    """Turns a goal into an ordered set of skill invocations."""

    def __init__(self, *, skills: SkillManager) -> None:
        self.skills = skills

    def decompose(self, goal: str, *, max_steps: int = 6) -> list[PlanStep]:
        """Split a goal on conjunctions, mapping each clause to a skill."""
        clauses = self._split(goal)
        steps: list[PlanStep] = []

        for i, clause in enumerate(clauses[:max_steps], start=1):
            match = next(
                (m for m in self.skills.match(clause, limit=3)
                 if m.availability is Availability.AVAILABLE),
                None,
            )
            steps.append(
                PlanStep(
                    index=i,
                    description=clause.strip(),
                    skill=match.skill.id if match else None,
                    agent=match.skill.agent if match else None,
                )
            )
        return steps

    @staticmethod
    def _split(goal: str) -> list[str]:
        import re

        parts = re.split(
            r"\s+(?:and then|then|after that|followed by|,\s*then)\s+",
            goal.strip(),
            flags=re.I,
        )
        return [p for p in (part.strip(" .,;") for part in parts) if p]


# --------------------------------------------------------------------------- #
# Learning Engine
# --------------------------------------------------------------------------- #
class LearningEngine:
    """Observes outcomes and turns them into durable knowledge."""

    def __init__(
        self,
        *,
        skills: SkillManager,
        memory: MemoryEngine | None = None,
        registry: AgentRegistry | None = None,
        bus: Any = None,
    ) -> None:
        self.skills = skills
        self.memory = memory
        self.registry = registry
        self.bus = bus
        self._observed = 0

    async def observe(self, *, agent: str, skill_id: str | None, success: bool) -> None:
        """Record one task outcome."""
        self._observed += 1
        if skill_id:
            self.skills.record(skill_id, success=success)
        else:
            self.skills.record_for_agent(agent, success=success)

    def insights(self) -> dict[str, Any]:
        """What has been learned so far."""
        used = [s for s in self.skills.all() if s.invocations > 0]
        used.sort(key=lambda s: -s.invocations)

        struggling = [
            {"skill": s.skill.id, "success_rate": s.success_rate, "failures": s.failures}
            for s in used
            if s.success_rate is not None and s.success_rate < 0.7 and s.invocations >= 3
        ]

        gaps = [
            {"skill": s.skill.id, "name": s.skill.name, "reason": s.reason}
            for s in self.skills.unavailable()
            if s.availability is Availability.NEEDS_BACKEND
        ]

        return {
            "observations": self._observed,
            "skills_used": len(used),
            "most_used": [
                {"skill": s.skill.id, "invocations": s.invocations} for s in used[:5]
            ],
            "struggling": struggling,
            "capability_gaps": gaps[:10],
        }

    async def consolidate(self) -> dict[str, Any]:
        """Persist notable findings into the memory graph."""
        insights = self.insights()
        if self.memory is None or insights["skills_used"] == 0:
            return insights

        top = insights["most_used"][:3]
        if top:
            summary = ", ".join(f"{t['skill']} ({t['invocations']}x)" for t in top)
            await self.memory.store(
                title="Learned usage pattern",
                content=f"Most-used skills: {summary}",
                node_type="knowledge",
                memory_type="procedural",
                tags=["learning", "usage"],
                importance=0.55,
                creator="learning_engine",
            )
        return insights


__all__ = [
    "ActiveContext",
    "ContextEngine",
    "LearningEngine",
    "PlanStep",
    "PlanningEngine",
    "ReasoningEngine",
    "ReasoningResult",
]
