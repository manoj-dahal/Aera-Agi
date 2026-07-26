# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Tap-to-memory workflow.

From the requirements conversation:

    "When the Dashboard's tap-to-speak button is pressed, a tap-to-memory
     workflow runs in the background first. It recalls previous conversation,
     active projects, workspace, shared memory, preferences, context, and then
     enables voice listening."

So tapping does not open the microphone first: it primes context, and only then
hands control to the voice engine. This module performs that priming and returns
a structured summary the UI can display while listening starts.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from ..core.logging import get_logger
from ..memory.models import MemoryType, NodeType

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..memory.engine import MemoryEngine
    from ..workspace.indexer import WorkspaceIndexer

logger = get_logger("agents.tap_memory")


class TapMemoryWorkflow:
    """Primes AERA's context before a voice session begins."""

    #: Ordered stages, matching the conversation.
    STAGES = (
        "previous_conversation",
        "active_projects",
        "workspace",
        "shared_memory",
        "preferences",
        "context",
    )

    def __init__(
        self,
        memory: MemoryEngine,
        *,
        workspace: WorkspaceIndexer | None = None,
        registry: Any = None,
        bus: Any = None,
    ) -> None:
        self.memory = memory
        self.workspace = workspace
        self.registry = registry
        self.bus = bus

    async def run(self, *, conversation_id: str | None = None) -> dict[str, Any]:
        """Execute every stage, returning what was recalled."""
        started = time.perf_counter()
        result: dict[str, Any] = {"stages": {}, "ready": False}

        if self.bus:
            await self.bus.publish("memory.tap.started", {"conversation_id": conversation_id})

        for stage in self.STAGES:
            try:
                result["stages"][stage] = await getattr(self, f"_{stage}")(conversation_id)
            except Exception as exc:  # noqa: BLE001 - a failed stage must not block speech
                logger.warning("tap-to-memory stage '%s' failed: %s", stage, exc)
                result["stages"][stage] = {"error": str(exc)}

        result["ready"] = True
        result["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
        result["summary"] = self._summarise(result["stages"])

        # Park the primed context in working memory so the next turn can use it
        # without repeating the recall.
        self.memory.set_working("tap_context", result["summary"], ttl=600)

        if self.bus:
            await self.bus.publish(
                "memory.tap.completed",
                {"duration_ms": result["duration_ms"], "conversation_id": conversation_id},
            )
        logger.info("tap-to-memory primed in %.0fms", result["duration_ms"])
        return result

    # ------------------------------------------------------------------ #
    # stages
    # ------------------------------------------------------------------ #
    async def _previous_conversation(self, conversation_id: str | None) -> dict[str, Any]:
        if not conversation_id:
            recent = self.memory.recent(limit=4)
        else:
            recent = self.memory.conversation_history(conversation_id, limit=4)
        return {
            "turns": len(recent),
            "items": [{"creator": n.creator, "text": n.summary(120)} for n in recent],
        }

    async def _active_projects(self, _: str | None) -> dict[str, Any]:
        nodes = self.memory.graph.find(node_type=NodeType.PROJECT, limit=5)
        return {
            "count": len(nodes),
            "items": [{"id": n.id, "title": n.title} for n in nodes],
        }

    async def _workspace(self, _: str | None) -> dict[str, Any]:
        if self.workspace is None or self.workspace.active_project is None:
            return {"open": False}
        summary = self.workspace.summary()
        return {
            "open": True,
            "name": summary.get("name"),
            "files": summary.get("files"),
            "languages": list(summary.get("languages", {}))[:5],
        }

    async def _shared_memory(self, _: str | None) -> dict[str, Any]:
        stats = self.memory.stats()
        return {
            "nodes": stats.get("nodes", 0),
            "edges": stats.get("edges", 0),
            "long_term": stats.get("by_memory_type", {}).get("long_term", 0),
        }

    async def _preferences(self, _: str | None) -> dict[str, Any]:
        nodes = self.memory.graph.find(node_type=NodeType.PREFERENCE, limit=8)
        if not nodes:
            # Preferences are often captured as tagged knowledge rather than a
            # dedicated node type.
            nodes = self.memory.graph.find(tag="preference", limit=8)
        return {
            "count": len(nodes),
            "items": [n.summary(90) for n in nodes],
        }

    async def _context(self, conversation_id: str | None) -> dict[str, Any]:
        """Rank what matters right now, biased toward durable memory."""
        results = await self.memory.recall(
            "current work in progress",
            limit=5,
            memory_types=[MemoryType.LONG_TERM, MemoryType.SEMANTIC, MemoryType.PROCEDURAL],
            expand_hops=1,
        )
        return {
            "count": len(results),
            "items": [{"title": r.node.title, "score": round(r.score, 3)} for r in results],
        }

    # ------------------------------------------------------------------ #
    # summary
    # ------------------------------------------------------------------ #
    @staticmethod
    def _summarise(stages: dict[str, Any]) -> str:
        """One-line human-readable summary for the UI."""
        parts: list[str] = []

        conversation = stages.get("previous_conversation", {})
        if conversation.get("turns"):
            parts.append(f"{conversation['turns']} recent turns")

        workspace = stages.get("workspace", {})
        if workspace.get("open"):
            parts.append(f"project {workspace.get('name')}")

        shared = stages.get("shared_memory", {})
        if shared.get("nodes"):
            parts.append(f"{shared['nodes']} memories")

        preferences = stages.get("preferences", {})
        if preferences.get("count"):
            parts.append(f"{preferences['count']} preferences")

        return "Context primed: " + (", ".join(parts) if parts else "no prior context")
