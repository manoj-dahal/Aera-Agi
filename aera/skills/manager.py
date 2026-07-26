# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Skill Manager.

Resolves which catalogued skills can actually run right now, matches free-text
requests onto them, and records execution outcomes so the Learning Engine can
see which skills succeed.

The central idea: AERA should know what it cannot do. Availability is probed
against the live system - installed libraries, connected models, configuration
flags - and reported honestly, so the router never hands work to a skill whose
backend is missing.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..core.logging import get_logger
from ..memory.embeddings import tokenize
from .registry import (
    SKILLS,
    SKILLS_BY_ID,
    Availability,
    Backend,
    Skill,
    SkillCategory,
    category_counts,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..agents.registry import AgentRegistry
    from ..ai.router import ModelRouter

logger = get_logger("skills.manager")


@dataclass(slots=True)
class SkillState:
    """Runtime state for one skill."""

    skill: Skill
    availability: Availability
    #: Why it is unavailable, in words the user can act on.
    reason: str | None = None
    invocations: int = 0
    failures: int = 0
    last_used: float | None = None

    @property
    def success_rate(self) -> float | None:
        if self.invocations == 0:
            return None
        return round((self.invocations - self.failures) / self.invocations, 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.skill.to_dict(),
            "availability": self.availability.value,
            "reason": self.reason,
            "invocations": self.invocations,
            "failures": self.failures,
            "success_rate": self.success_rate,
            "last_used": self.last_used,
        }


@dataclass(slots=True)
class BackendStatus:
    """What each backend can currently do."""

    available: bool
    detail: str = ""


@dataclass(slots=True)
class SkillMatch:
    """A skill matched against a request."""

    skill: Skill
    score: float
    availability: Availability
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.skill.id,
            "name": self.skill.name,
            "agent": self.skill.agent,
            "category": self.skill.category.value,
            "score": round(self.score, 3),
            "availability": self.availability.value,
            "reason": self.reason,
        }


class SkillManager:
    """Owns the skill catalogue and its live availability."""

    def __init__(
        self,
        *,
        registry: AgentRegistry | None = None,
        router: ModelRouter | None = None,
        config: Any = None,
        bus: Any = None,
    ) -> None:
        self.registry = registry
        self.router = router
        self.config = config
        self.bus = bus
        self._states: dict[str, SkillState] = {
            s.id: SkillState(skill=s, availability=Availability.PLANNED) for s in SKILLS
        }
        self._backends: dict[Backend, BackendStatus] = {}
        self._resolved_at: float = 0.0

    # ------------------------------------------------------------------ #
    # backend probing
    # ------------------------------------------------------------------ #
    async def probe_backends(self) -> dict[Backend, BackendStatus]:
        """Detect which backends are present. Cheap and safe to repeat."""
        status: dict[Backend, BackendStatus] = {
            Backend.NONE: BackendStatus(True, "built in"),
        }

        # -- language models ------------------------------------------------
        if self.router is not None:
            providers = self.router.providers
            healthy = [n for n, p in providers.items() if p.enabled]
            status[Backend.LLM] = BackendStatus(
                bool(healthy), f"{len(healthy)} provider(s)"
            )
            status[Backend.VISION_MODEL] = BackendStatus(
                False, "no vision-capable provider connected"
            )
            for name, provider in providers.items():
                if not provider.enabled:
                    continue
                try:
                    models = await provider.list_models()
                except Exception:  # noqa: BLE001
                    continue
                if any(m.supports_vision for m in models):
                    status[Backend.VISION_MODEL] = BackendStatus(True, name)
                    break
        else:
            status[Backend.LLM] = BackendStatus(False, "no model router")
            status[Backend.VISION_MODEL] = BackendStatus(False, "no model router")

        # Image generation needs a dedicated model; none is wired up.
        status[Backend.IMAGE_MODEL] = BackendStatus(
            False, "no image-generation model configured"
        )

        # -- libraries ------------------------------------------------------
        status[Backend.OCR_ENGINE] = BackendStatus(
            _module_available("pytesseract") and bool(shutil.which("tesseract")),
            "tesseract + pytesseract",
        )
        status[Backend.DOC_PARSER] = BackendStatus(
            _module_available("pypdf") or _module_available("docx"),
            "pypdf / python-docx",
        )
        status[Backend.VIDEO_TOOLS] = BackendStatus(
            bool(shutil.which("ffmpeg")), "ffmpeg"
        )

        # -- speech ---------------------------------------------------------
        stt = "null"
        tts = "null"
        voice_engine = getattr(self.config, "_voice_engine", None) if self.config else None
        if voice_engine is not None:
            stt = getattr(getattr(voice_engine, "stt", None), "name", "null")
            tts = getattr(getattr(voice_engine, "tts", None), "name", "null")
        status[Backend.STT_ENGINE] = BackendStatus(stt != "null", f"backend: {stt}")
        status[Backend.TTS_ENGINE] = BackendStatus(tts != "null", f"backend: {tts}")

        # -- external tools -------------------------------------------------
        status[Backend.GIT] = BackendStatus(bool(shutil.which("git")), "git binary")
        status[Backend.DOCKER] = BackendStatus(bool(shutil.which("docker")), "docker CLI")
        status[Backend.KUBERNETES] = BackendStatus(
            bool(shutil.which("kubectl")), "kubectl"
        )

        # -- policy-gated ---------------------------------------------------
        security = getattr(self.config, "security", None)
        agents_cfg = getattr(self.config, "agents", None)

        terminal_ok = bool(
            getattr(security, "allow_terminal", False)
            and getattr(agents_cfg, "terminal", False)
        )
        status[Backend.TERMINAL] = BackendStatus(
            terminal_ok,
            "enabled" if terminal_ok else "disabled by policy (security.allow_terminal)",
        )

        network_ok = bool(getattr(security, "allow_network", False))
        status[Backend.NETWORK] = BackendStatus(
            network_ok,
            "enabled" if network_ok else "disabled by policy (security.allow_network)",
        )

        status[Backend.DEVICE_LINK] = BackendStatus(False, "no paired device")

        self._backends = status
        return status

    # ------------------------------------------------------------------ #
    # resolution
    # ------------------------------------------------------------------ #
    async def resolve(self) -> dict[str, SkillState]:
        """Recompute every skill's availability."""
        backends = await self.probe_backends()
        agent_names = set(self.registry.names()) if self.registry else set()

        for state in self._states.values():
            skill = state.skill
            backend = backends.get(skill.backend, BackendStatus(False, "unknown backend"))

            if skill.agent not in agent_names:
                state.availability = Availability.DISABLED
                state.reason = f"the {skill.agent} agent is not enabled"
            elif not backend.available:
                state.availability = Availability.NEEDS_BACKEND
                state.reason = backend.detail or f"{skill.backend.value} unavailable"
            else:
                state.availability = Availability.AVAILABLE
                state.reason = None

        self._resolved_at = time.time()
        if self.bus:
            await self.bus.publish(
                "skills.resolved",
                {"available": len(self.available()), "total": len(self._states)},
                source="skills",
            )
        logger.info(
            "skills resolved: %d/%d available", len(self.available()), len(self._states)
        )
        return self._states

    # ------------------------------------------------------------------ #
    # querying
    # ------------------------------------------------------------------ #
    def all(self) -> list[SkillState]:
        return list(self._states.values())

    def get(self, skill_id: str) -> SkillState | None:
        return self._states.get(skill_id)

    def available(self) -> list[SkillState]:
        return [s for s in self._states.values() if s.availability is Availability.AVAILABLE]

    def unavailable(self) -> list[SkillState]:
        return [s for s in self._states.values() if s.availability is not Availability.AVAILABLE]

    def background_skills(self) -> list[SkillState]:
        return [s for s in self._states.values() if s.skill.background]

    def by_category(self, category: SkillCategory | str) -> list[SkillState]:
        value = SkillCategory(category)
        return [s for s in self._states.values() if s.skill.category is value]

    def by_agent(self, agent: str) -> list[SkillState]:
        return [s for s in self._states.values() if s.skill.agent == agent]

    # ------------------------------------------------------------------ #
    # matching
    # ------------------------------------------------------------------ #
    def match(self, text: str, *, limit: int = 5, available_only: bool = False) -> list[SkillMatch]:
        """Rank catalogued skills against a free-text request.

        Keyword phrases score highest because they are hand-picked; name and
        description overlap fill in the rest.
        """
        lowered = (text or "").lower().strip()
        if not lowered:
            return []
        tokens = set(tokenize(lowered))

        matches: list[SkillMatch] = []
        for state in self._states.values():
            skill = state.skill
            score = 0.0

            for phrase in skill.keywords:
                if phrase in lowered:
                    # Multi-word phrases are far more specific than single words.
                    score += 3.0 + 1.5 * phrase.count(" ")

            name_tokens = set(tokenize(skill.name))
            score += 1.2 * len(tokens & name_tokens)
            score += 0.4 * len(tokens & set(tokenize(skill.description)))

            if score <= 0:
                continue
            if available_only and state.availability is not Availability.AVAILABLE:
                continue

            matches.append(
                SkillMatch(
                    skill=skill,
                    score=score,
                    availability=state.availability,
                    reason=state.reason,
                )
            )

        matches.sort(key=lambda m: (-m.score, m.skill.id))
        return matches[:limit]

    def best_agent_for(self, text: str) -> tuple[str, SkillMatch] | None:
        """Which agent the strongest available skill match points to."""
        for match in self.match(text, limit=8):
            if match.availability is Availability.AVAILABLE:
                return match.skill.agent, match
        return None

    # ------------------------------------------------------------------ #
    # outcome tracking
    # ------------------------------------------------------------------ #
    def record(self, skill_id: str, *, success: bool) -> None:
        """Record an execution outcome (feeds the Learning Engine)."""
        state = self._states.get(skill_id)
        if state is None:
            return
        state.invocations += 1
        if not success:
            state.failures += 1
        state.last_used = time.time()

    def record_for_agent(self, agent: str, *, success: bool) -> None:
        """Attribute an agent's outcome to its most-used skill."""
        owned = self.by_agent(agent)
        if not owned:
            return
        target = max(owned, key=lambda s: s.invocations)
        self.record(target.skill.id, success=success)

    # ------------------------------------------------------------------ #
    # reporting
    # ------------------------------------------------------------------ #
    def summary(self) -> dict[str, Any]:
        by_availability: dict[str, int] = {}
        for state in self._states.values():
            key = state.availability.value
            by_availability[key] = by_availability.get(key, 0) + 1

        return {
            "total": len(self._states),
            "available": len(self.available()),
            "background": len(self.background_skills()),
            "categories": len(category_counts()),
            "by_availability": by_availability,
            "by_category": category_counts(),
            "resolved_at": self._resolved_at,
            "backends": {
                backend.value: {"available": s.available, "detail": s.detail}
                for backend, s in self._backends.items()
            },
        }

    def catalogue(self, *, include_unavailable: bool = True) -> list[dict[str, Any]]:
        states = self.all() if include_unavailable else self.available()
        return [s.to_dict() for s in sorted(states, key=lambda s: (s.skill.category.value, s.skill.name))]


def _module_available(name: str) -> bool:
    """True when a module can be imported without importing it fully."""
    import importlib.util

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


__all__ = [
    "Availability",
    "Backend",
    "BackendStatus",
    "Skill",
    "SkillCategory",
    "SkillManager",
    "SkillMatch",
    "SkillState",
    "SKILLS",
    "SKILLS_BY_ID",
]
