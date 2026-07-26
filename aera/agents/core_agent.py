# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Core Agent - the master coordinator (``docs/agents/Core-Agent.md``).

Implements the documented pipeline::

    intent detection -> context collection -> memory recall -> task planning
    -> agent selection -> execution -> response generation -> memory update

The Core Agent never performs specialised work itself; it delegates.
"""

from __future__ import annotations

import re
import time
from typing import Any

from ..core.logging import get_logger
from .base import Agent, Capability, Task, TaskResult

logger = get_logger("agent.core")


# Intent detection: ordered rules, first match wins. Kept explicit and
# inspectable rather than model-based so routing works offline and is testable.
_INTENT_RULES: list[tuple[Capability, tuple[str, ...]]] = [
    (Capability.GIT, (r"\bgit\b", r"\bcommit\b", r"\bbranch(es)?\b", r"\bmerge\b",
                      r"\bpull request\b", r"\brepo(sitory)?\b", r"\bdiff\b")),
    (Capability.TERMINAL, (r"\brun (the )?command\b", r"\bterminal\b", r"\bshell\b",
                           r"\bexecute\b", r"\bbash\b")),
    (Capability.CODE_REVIEW, (r"\breview (my|the|this) code\b", r"\bcode review\b")),
    (Capability.DEBUGGING, (r"\bdebug\b", r"\bstack ?trace\b", r"\btraceback\b",
                            r"\bexception\b", r"\bwhy (is|does).*(fail|break|crash)",
                            r"\bfix (this|the|my) (bug|error|issue)\b")),
    (Capability.CODING, (r"\bcode\b", r"\bfunction\b", r"\bclass\b", r"\bimplement\b",
                         r"\brefactor\b", r"\bpython\b", r"\bjavascript\b", r"\btypescript\b",
                         r"\bapi endpoint\b", r"\bwrite a (script|program)\b", r"\bunit tests?\b")),
    (Capability.FILE_ANALYSIS, (r"\bsummari[sz]e (this|the) (file|document|pdf|report)\b",
                                r"\bread (this|the) (file|document)\b",
                                r"\bwhat does (this|the) (file|document) say\b")),
    (Capability.VISION, (r"\bimage\b", r"\bscreenshot\b", r"\bphoto\b",
                         r"\bocr\b", r"\bwhat.s in (this|the) (picture|image)\b")),
    (Capability.DEVICE, (r"\bmy (phone|device|laptop|machine)\b", r"\bbattery\b",
                         r"\bpair (a )?device\b")),
    (Capability.DOCUMENTATION, (r"\bdocument(ation)?\b", r"\bdocstring\b", r"\breadme\b",
                                r"\bchangelog\b")),
    (Capability.WORKSPACE, (r"\bworkspace\b", r"\bproject (structure|tree|files)\b",
                            r"\bindex (the )?(project|folder)\b", r"\bopen folder\b",
                            r"\bwhat files\b")),
    (Capability.RESEARCH, (r"\bresearch\b", r"\bfind out\b", r"\blook up\b",
                           r"\bcompare\b", r"\binvestigate\b")),
    (Capability.PLANNING, (r"\bplan\b", r"\broadmap\b", r"\bbreak (this )?down\b",
                           r"\bsteps to\b", r"\bmilestones?\b", r"\bschedule\b")),
    (Capability.TRANSLATION, (r"\btranslate\b", r"\bin (spanish|french|german|japanese|chinese|hindi|nepali)\b")),
    (Capability.WRITING, (r"\bwrite (a|an|the) (post|article|email|report|summary)\b",
                          r"\bsummar(y|ise|ize)\b", r"\bdraft\b", r"\brephrase\b")),
    (Capability.SECURITY, (r"\bsecurity\b", r"\bvulnerabilit(y|ies)\b", r"\bexploit\b",
                           r"\baudit\b", r"\bpermissions?\b", r"\bencrypt",
                           r"\bharden(ing)?\b", r"\bpenetration test", r"\bthreat model",
                           r"\bsecure (my|the|this)\b", r"\bcve\b")),
    (Capability.PERFORMANCE, (r"\bperformance\b", r"\bslow\b", r"\boptimi[sz]e\b",
                              r"\bmemory usage\b", r"\bcpu\b", r"\bbenchmark\b")),
    (Capability.AUTOMATION, (r"\bautomat(e|ion)\b", r"\bworkflow\b", r"\bmacro\b",
                             r"\bevery (day|hour|week)\b", r"\btrigger\b")),
    (Capability.MEMORY, (r"\bremember\b", r"\brecall\b", r"\bwhat did (i|we)\b",
                         r"\bforget\b", r"\bmemor(y|ies)\b")),
    (Capability.REASONING, (r"\bwhy\b", r"\bexplain\b", r"\banaly[sz]e\b",
                            r"\bcompare\b", r"\bpros and cons\b", r"\btrade-?offs?\b")),
]


class CoreAgent(Agent):
    """Central orchestrator: understands, plans, delegates, and responds."""

    name = "core"
    description = (
        "Master coordinator that detects intent, recalls memory, selects specialised "
        "agents and assembles the final response."
    )
    capabilities = (Capability.CONVERSATION, Capability.REASONING)
    priority = 10
    model_task = "default"

    def __init__(self, context) -> None:
        super().__init__(context)
        self.routed_tasks = 0

    # ------------------------------------------------------------------ #
    # intent detection
    # ------------------------------------------------------------------ #
    def detect_intent(self, text: str) -> tuple[Capability, float]:
        """Classify a request into a capability with a confidence score."""
        lowered = (text or "").lower().strip()
        if not lowered:
            return Capability.CONVERSATION, 0.0

        best: tuple[Capability, int] | None = None
        for capability, patterns in _INTENT_RULES:
            hits = sum(1 for p in patterns if re.search(p, lowered))
            if hits and (best is None or hits > best[1]):
                best = (capability, hits)

        if best is None:
            return Capability.CONVERSATION, 0.3
        capability, hits = best
        return capability, min(1.0, 0.55 + 0.15 * hits)

    # ------------------------------------------------------------------ #
    # main pipeline
    # ------------------------------------------------------------------ #
    async def handle(self, task: Task) -> TaskResult:
        started = time.perf_counter()
        text = task.input.strip()

        # 1. intent detection ------------------------------------------------
        capability, confidence = self.detect_intent(text)
        forced = task.context.get("force_agent")

        # 1b. reasoning engine: complexity, skill match and capability gaps.
        assessment = None
        engine = getattr(self.ctx, "reasoning_engine", None)
        if engine is not None:
            assessment = engine.assess(text)

        # 2-3. context collection + memory recall ----------------------------
        context_block = await self.ctx.memory.build_context(
            text,
            conversation_id=task.conversation_id,
            project_id=task.project_id,
            max_items=6,
        )

        # 4-5. plan + agent selection ---------------------------------------
        registry = self.ctx.registry
        delegate = None
        if registry is not None:
            if forced:
                delegate = registry.try_get(forced)
            elif capability not in self.capabilities:
                delegate = registry.best_for(capability)
                if delegate is self:
                    delegate = None

            # The skill catalogue is more granular than the capability enum, so
            # it can name a better-suited agent when intent detection is vague.
            if delegate is None and assessment and assessment.suggested_agent:
                candidate = registry.try_get(assessment.suggested_agent)
                if candidate is not None and candidate is not self:
                    delegate = candidate

        # 6. execution -------------------------------------------------------
        if delegate is not None:
            self.routed_tasks += 1
            self.log.info("routing '%s' -> %s (%.0f%%)", capability.value, delegate.name, confidence * 100)
            sub = task.with_context(
                memory_context=context_block,
                intent=capability.value,
                confidence=confidence,
                routed_by=self.name,
            )
            sub.capability = capability
            result = await delegate.execute(sub)
            result.data.setdefault("intent", capability.value)
            result.data.setdefault("confidence", round(confidence, 2))
            result.data.setdefault("routed_to", delegate.name)
            if assessment:
                result.data.setdefault("skill", assessment.suggested_skill)
                result.data.setdefault("complexity", assessment.complexity)
        else:
            result = await self._respond_directly(task, context_block, capability, confidence)

        # 7-8. memory update -------------------------------------------------
        if result.success and result.output and task.conversation_id:
            try:
                user_node, assistant_node = await self.ctx.memory.remember_exchange(
                    text,
                    result.output,
                    conversation_id=task.conversation_id,
                    agent=result.agent,
                    project_id=task.project_id,
                )
                result.memory_ids = [user_node.id, assistant_node.id]
            except Exception:  # noqa: BLE001 - memory must never break the reply
                self.log.warning("could not persist conversation memory", exc_info=True)

        # Surface a capability gap rather than letting the reply improvise.
        if assessment and assessment.unavailable_reason and result.success:
            result.data.setdefault("capability_gap", assessment.unavailable_reason)

        result.duration_ms = (time.perf_counter() - started) * 1000
        return result

    async def _respond_directly(
        self, task: Task, context_block: str, capability: Capability, confidence: float
    ) -> TaskResult:
        """Answer conversational requests the Core Agent owns itself."""
        system = self.system_prompt()
        if context_block:
            system = f"{system}\n\n{context_block}"

        response = await self.ctx.router.complete(
            task.input, task="default", system=system, temperature=0.7
        )
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            success=True,
            output=response.content,
            model=response.model,
            provider=response.provider,
            data={
                "intent": capability.value,
                "confidence": round(confidence, 2),
                "routed_to": self.name,
                "memory_context_used": bool(context_block),
            },
        )

    def system_prompt(self) -> str:
        return (
            "You are AERA, an AI operating system with persistent memory across sessions. "
            "You are direct, technically precise and concise. When memory context is "
            "provided, use it naturally instead of asking the user to repeat themselves."
        )

    def describe(self) -> dict[str, Any]:
        data = super().describe()
        data["routed_tasks"] = self.routed_tasks
        return data
