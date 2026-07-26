# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Coding, code-review and debugging agents."""

from __future__ import annotations

import re

from .base import Agent, Capability, Task, TaskResult

SUPPORTED_LANGUAGES = (
    "python", "dart", "javascript", "typescript", "csharp", "cpp", "c",
    "java", "go", "rust", "php", "kotlin", "swift", "ruby", "sql", "bash",
)

_LANG_HINTS = {
    "python": (r"\bpython\b", r"\bdjango\b", r"\bflask\b", r"\bfastapi\b", r"\bpytest\b", r"\.py\b"),
    "dart": (r"\bdart\b", r"\bflutter\b", r"\.dart\b"),
    "typescript": (r"\btypescript\b", r"\bts\b", r"\.tsx?\b", r"\bangular\b"),
    "javascript": (r"\bjavascript\b", r"\bnode(\.js)?\b", r"\breact\b", r"\.jsx?\b"),
    "go": (r"\bgolang\b", r"\bgo\b", r"\.go\b"),
    "rust": (r"\brust\b", r"\bcargo\b", r"\.rs\b"),
    "java": (r"\bjava\b", r"\bspring\b", r"\.java\b"),
    "csharp": (r"\bc#\b", r"\bcsharp\b", r"\bdotnet\b", r"\.cs\b"),
    "cpp": (r"\bc\+\+\b", r"\bcpp\b", r"\.cpp\b", r"\.hpp\b"),
    "swift": (r"\bswift\b", r"\.swift\b"),
    "kotlin": (r"\bkotlin\b", r"\.kt\b"),
    "php": (r"\bphp\b", r"\.php\b"),
    "ruby": (r"\bruby\b", r"\brails\b", r"\.rb\b"),
    "sql": (r"\bsql\b", r"\bselect .* from\b", r"\bpostgres\b"),
    "bash": (r"\bbash\b", r"\bshell script\b", r"\.sh\b"),
}


def detect_language(text: str, default: str = "python") -> str:
    """Best-effort language detection from a free-text request."""
    lowered = text.lower()
    fence = re.search(r"```(\w+)", lowered)
    if fence and fence.group(1) in SUPPORTED_LANGUAGES:
        return fence.group(1)
    scores = {
        lang: sum(1 for p in patterns if re.search(p, lowered))
        for lang, patterns in _LANG_HINTS.items()
    }
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] else default


def extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """Return ``(language, code)`` pairs from fenced markdown blocks."""
    return [
        (lang or "text", code.strip())
        for lang, code in re.findall(r"```(\w*)\n(.*?)```", text, re.DOTALL)
    ]


class CodingAgent(Agent):
    """Generates, explains and refactors code across the supported languages."""

    name = "coding"
    description = (
        "Writes, explains, refactors and tests code in Python, Dart, JavaScript, "
        "TypeScript, Go, Rust, Java, C#, C++, Swift, Kotlin, PHP, Ruby and SQL."
    )
    capabilities = (Capability.CODING, Capability.DOCUMENTATION)
    priority = 8
    model_task = "coding"

    async def handle(self, task: Task) -> TaskResult:
        language = task.context.get("language") or detect_language(task.input)
        memory_context = task.context.get("memory_context", "")

        system = (
            f"You are AERA's Coding Agent, an expert {language} engineer. "
            "Produce correct, idiomatic, production-quality code. "
            "Always wrap code in fenced blocks tagged with the language. "
            "Explain non-obvious decisions briefly after the code, never before it."
        )
        if memory_context:
            system += f"\n\nProject context:\n{memory_context}"

        response = await self.ctx.router.complete(
            task.input, task=self.model_task, system=system, temperature=0.2
        )
        blocks = extract_code_blocks(response.content)

        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=response.content,
            model=response.model,
            provider=response.provider,
            data={
                "language": language,
                "code_blocks": len(blocks),
                "snippets": [{"language": lang, "code": code} for lang, code in blocks[:5]],
            },
        )


class CodeReviewAgent(Agent):
    """Reviews code for correctness, security and maintainability."""

    name = "code_review"
    description = "Reviews code for bugs, security issues, performance and style."
    capabilities = (Capability.CODE_REVIEW,)
    priority = 8
    model_task = "coding"

    async def handle(self, task: Task) -> TaskResult:
        language = task.context.get("language") or detect_language(task.input)
        system = (
            f"You are AERA's Code Review Agent reviewing {language} code. "
            "Report findings grouped as Correctness, Security, Performance, and Style. "
            "Cite the offending lines, rank issues by severity, and suggest a concrete fix "
            "for each. If the code is sound, say so plainly instead of inventing problems."
        )
        response = await self.ctx.router.complete(
            task.input, task=self.model_task, system=system, temperature=0.2
        )
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=response.content,
            model=response.model,
            provider=response.provider,
            data={"language": language},
        )


class DebugAgent(Agent):
    """Diagnoses errors, stack traces and unexpected behaviour."""

    name = "debug"
    description = "Analyses stack traces and failing behaviour, then proposes a fix."
    capabilities = (Capability.DEBUGGING,)
    priority = 8
    model_task = "coding"

    async def handle(self, task: Task) -> TaskResult:
        language = task.context.get("language") or detect_language(task.input)
        memory_context = task.context.get("memory_context", "")

        system = (
            f"You are AERA's Debugging Agent working on {language}. "
            "Work in this order: (1) state the most likely root cause, (2) show the "
            "minimal fix as a code block, (3) list how to verify it, (4) note any "
            "related risks. Be concrete; do not speculate wildly."
        )
        if memory_context:
            system += f"\n\nProject context:\n{memory_context}"

        response = await self.ctx.router.complete(
            task.input, task=self.model_task, system=system, temperature=0.2
        )
        return TaskResult(
            task_id=task.id,
            agent=self.name,
            output=response.content,
            model=response.model,
            provider=response.provider,
            data={
                "language": language,
                "traceback_detected": bool(
                    re.search(r"(Traceback|Exception|Error:|at .+\(.+:\d+\))", task.input)
                ),
            },
        )
