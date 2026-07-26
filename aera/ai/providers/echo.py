# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Built-in offline provider.

AERA must stay useful with no API keys and no local runtime installed, so this
provider is always present as the final fallback. It performs lightweight
deterministic reasoning over the prompt (and any memory context the Core Agent
injected) instead of pretending to be an LLM.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import AsyncIterator

from ..base import AIProvider, CompletionRequest, CompletionResponse, ModelInfo, Role, Usage

_GREETING = re.compile(r"^\s*(hi|hello|hey|yo|good (morning|evening|afternoon))\b", re.I)
_QUESTION_WORDS = ("what", "why", "how", "when", "where", "who", "which", "can", "does", "is")


class EchoProvider(AIProvider):
    """Deterministic local reasoner used when no real model is configured."""

    name = "builtin"
    is_local = True

    def __init__(self, **options) -> None:
        super().__init__(**options)
        self.model_id = options.get("model", "aera-builtin")

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        started = time.perf_counter()
        await asyncio.sleep(0)  # stay a genuine coroutine / yield control

        system = " ".join(m.content for m in request.messages if m.role == Role.SYSTEM)
        user_messages = [m for m in request.messages if m.role == Role.USER]
        latest = user_messages[-1].content.strip() if user_messages else ""

        content = self._respond(latest, system)
        elapsed = (time.perf_counter() - started) * 1000

        return CompletionResponse(
            content=content,
            model=request.model or self.model_id,
            provider=self.name,
            usage=Usage(
                prompt_tokens=_approx_tokens(request.prompt_text()),
                completion_tokens=_approx_tokens(content),
            ),
            latency_ms=elapsed,
            metadata={"offline": True},
        )

    def _respond(self, prompt: str, system: str) -> str:
        if not prompt:
            return "I did not receive a question. What would you like me to work on?"

        if _GREETING.match(prompt):
            return (
                "Hello. AERA is online and running fully offline on the built-in reasoner. "
                "Configure Ollama or a cloud provider in config/models.yaml to enable a full LLM."
            )

        context_note = ""
        if "Relevant memories:" in system or "Recent conversation:" in system:
            recalled = [
                line.strip("- ").strip()
                for line in system.splitlines()
                if line.strip().startswith("-")
            ]
            if recalled:
                shown = "; ".join(recalled[:3])
                context_note = f"\n\nFrom memory I recalled: {shown}"

        lowered = prompt.lower()
        keywords = _keywords(prompt)
        kw = ", ".join(keywords[:5]) if keywords else "your request"

        if lowered.startswith(_QUESTION_WORDS) or prompt.rstrip().endswith("?"):
            body = (
                f"You asked about {kw}. Running on the built-in offline reasoner I can "
                f"organise what is known and route the task, but I cannot generate a full "
                f"model-quality answer until an LLM provider is connected."
            )
        else:
            body = (
                f"Understood. I have registered the request concerning {kw} and stored it "
                f"in the memory graph so later agents can build on it."
            )
        return body + context_note

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Emit word-by-word so the WebSocket streaming path is exercised offline."""
        response = await self.complete(request)
        for token in response.content.split(" "):
            await asyncio.sleep(0)
            yield token + " "

    async def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id=self.model_id,
                provider=self.name,
                name="AERA Built-in Reasoner",
                context_length=8192,
                local=True,
                status="ready",
            )
        ]

    async def _probe(self) -> bool:
        return True


def _approx_tokens(text: str) -> int:
    """Rough 4-chars-per-token estimate, good enough for usage accounting."""
    return max(1, len(text) // 4)


def _keywords(text: str, limit: int = 8) -> list[str]:
    stop = {
        "the", "a", "an", "and", "or", "but", "for", "with", "that", "this",
        "you", "your", "can", "does", "how", "what", "why", "when", "where",
        "who", "which", "is", "are", "was", "were", "to", "of", "in", "on",
        "do", "did", "me", "my", "i", "it", "its", "please", "should", "would",
    }
    words = re.findall(r"[A-Za-z][A-Za-z0-9_.-]+", text.lower())
    out: list[str] = []
    for w in words:
        if w not in stop and w not in out and len(w) > 2:
            out.append(w)
        if len(out) >= limit:
            break
    return out
