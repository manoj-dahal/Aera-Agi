# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Reasoning, planning, research, writing, documentation and translation agents."""

from __future__ import annotations

import json
import re

from .base import Agent, Capability, Task, TaskResult


class ReasoningAgent(Agent):
    """Structured analysis, comparison and explanation."""

    name = "reasoning"
    description = "Performs step-by-step analysis, comparison and explanation."
    capabilities = (Capability.REASONING,)
    priority = 7
    model_task = "reasoning"

    async def handle(self, task: Task) -> TaskResult:
        memory_context = task.context.get("memory_context", "")
        system = (
            "You are AERA's Reasoning Agent. Think carefully and answer with a clear "
            "logical structure: state assumptions, work through the reasoning, then give "
            "a decisive conclusion. Flag genuine uncertainty rather than hiding it."
        )
        if memory_context:
            system += f"\n\nKnown context:\n{memory_context}"

        response = await self.ctx.router.complete(
            task.input, task=self.model_task, system=system, temperature=0.4
        )
        return TaskResult(
            task_id=task.id, agent=self.name, output=response.content,
            model=response.model, provider=response.provider,
        )


class PlanningAgent(Agent):
    """Breaks goals into ordered, dependency-aware steps."""

    name = "planning"
    description = "Decomposes goals into ordered steps with dependencies and estimates."
    capabilities = (Capability.PLANNING,)
    priority = 7
    model_task = "reasoning"

    async def handle(self, task: Task) -> TaskResult:
        memory_context = task.context.get("memory_context", "")
        system = (
            "You are AERA's Planning Agent. Produce an actionable plan as a numbered list. "
            "Each step must have: a short title, what to do, and its dependencies. "
            "Finish with the risks and the definition of done. Be realistic, not generic."
        )
        if memory_context:
            system += f"\n\nProject context:\n{memory_context}"

        response = await self.ctx.router.complete(
            task.input, task=self.model_task, system=system, temperature=0.4
        )
        steps = _parse_steps(response.content)

        # Persist the plan so later turns and the automation engine can pick it up.
        node = await self.ctx.memory.store(
            title=f"Plan: {task.input[:60]}",
            content=response.content,
            node_type="workflow",
            memory_type="procedural",
            tags=["plan", "planning"],
            importance=0.65,
            creator=self.name,
            project_id=task.project_id,
        )
        return TaskResult(
            task_id=task.id, agent=self.name, output=response.content,
            model=response.model, provider=response.provider,
            data={"steps": steps, "step_count": len(steps)},
            memory_ids=[node.id],
        )


class ResearchAgent(Agent):
    """Collects, organises and summarises knowledge."""

    name = "research"
    description = "Gathers and organises technical knowledge, then summarises findings."
    capabilities = (Capability.RESEARCH,)
    priority = 7
    model_task = "research"

    async def handle(self, task: Task) -> TaskResult:
        # Check what the graph already knows before asking a model.
        known = await self.recall(task.input, limit=6, project_id=task.project_id)
        prior = "\n".join(f"- {r.node.title}: {r.node.summary(160)}" for r in known)

        system = (
            "You are AERA's Research Agent. Organise what is known, separate established "
            "fact from inference, and end with a short summary plus open questions. "
            "Never invent citations or URLs."
        )
        if prior:
            system += f"\n\nAlready in memory:\n{prior}"

        response = await self.ctx.router.complete(
            task.input, task=self.model_task, system=system, temperature=0.5
        )
        node = await self.ctx.memory.store(
            title=f"Research: {task.input[:60]}",
            content=response.content,
            node_type="knowledge",
            memory_type="semantic",
            tags=["research"],
            importance=0.6,
            creator=self.name,
            project_id=task.project_id,
            related_to=[r.node.id for r in known[:3]],
        )
        return TaskResult(
            task_id=task.id, agent=self.name, output=response.content,
            model=response.model, provider=response.provider,
            data={"prior_memories": len(known)},
            memory_ids=[node.id],
        )


class WritingAgent(Agent):
    """Long-form and technical writing."""

    name = "writing"
    description = "Produces documentation, reports, summaries and technical prose."
    capabilities = (Capability.WRITING, Capability.DOCUMENTATION)
    priority = 7
    model_task = "default"

    async def handle(self, task: Task) -> TaskResult:
        style = task.context.get("style", "clear technical prose")
        fmt = task.context.get("format", "markdown")
        system = (
            f"You are AERA's Writing Agent. Write in {style}, formatted as {fmt}. "
            "Prefer short paragraphs and concrete detail. No filler, no restating the prompt."
        )
        response = await self.ctx.router.complete(
            task.input, task=self.model_task, system=system, temperature=0.7
        )
        return TaskResult(
            task_id=task.id, agent=self.name, output=response.content,
            model=response.model, provider=response.provider,
            data={"format": fmt, "word_count": len(response.content.split())},
        )


class TranslationAgent(Agent):
    """Translation and localisation."""

    name = "translation"
    description = "Translates text between languages and corrects grammar."
    capabilities = (Capability.TRANSLATION,)
    priority = 7
    model_task = "default"

    _TARGET = re.compile(
        r"\b(?:in|into|to)\s+(spanish|french|german|italian|portuguese|japanese|chinese|"
        r"korean|hindi|nepali|arabic|russian|dutch|swedish|polish|turkish|vietnamese|"
        r"thai|indonesian|english)\b",
        re.I,
    )

    async def handle(self, task: Task) -> TaskResult:
        target = task.context.get("target_language")
        if not target:
            match = self._TARGET.search(task.input)
            target = match.group(1).capitalize() if match else "English"

        system = (
            f"You are AERA's Translation Agent. Translate the user's text into {target}. "
            "Preserve tone, formatting and technical terms. Output only the translation "
            "unless the user explicitly asks for an explanation."
        )
        response = await self.ctx.router.complete(
            task.input, task=self.model_task, system=system, temperature=0.3
        )
        return TaskResult(
            task_id=task.id, agent=self.name, output=response.content,
            model=response.model, provider=response.provider,
            data={"target_language": target},
        )


def _parse_steps(text: str) -> list[dict]:
    """Pull numbered steps out of a plan for structured consumption."""
    steps: list[dict] = []
    for line in text.splitlines():
        match = re.match(r"\s*(\d+)[.)]\s+(.{3,})", line)
        if match:
            steps.append({"index": int(match.group(1)), "text": match.group(2).strip()})
    return steps


def _safe_json(text: str) -> dict | None:
    """Best-effort JSON extraction from a model response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
