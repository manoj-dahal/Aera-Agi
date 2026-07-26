# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Memory Engine - the façade every agent uses to read and write memory.

Wraps the raw :class:`MemoryGraph` with the higher-level behaviour from the
spec: a bounded short-term buffer, conversation threading, working-memory
scratchpads, context assembly for prompts, and background maintenance.
"""

from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from typing import Any

from ..core.config import MemorySection
from ..core.events import EventBus, Topics
from ..core.logging import get_logger
from .embeddings import get_embedder
from .graph import MemoryGraph
from .models import MemoryNode, MemoryType, NodeType, RecallResult, RelationType

logger = get_logger("memory.engine")


class MemoryEngine:
    """Unified memory API shared by all agents."""

    def __init__(
        self,
        config: MemorySection | None = None,
        *,
        bus: EventBus | None = None,
        storage_path: str | Path | None = None,
    ) -> None:
        self.config = config or MemorySection()
        self.bus = bus
        self.graph = MemoryGraph(
            embedder=get_embedder(256),
            storage_path=storage_path,
        )
        # Rolling window of the freshest utterances, cheap to read every turn.
        self._short_term: deque[str] = deque(maxlen=self.config.short_term_capacity)
        self._working: dict[str, dict[str, Any]] = {}
        self._conversations: dict[str, str] = {}  # conversation id -> root node id

    # ------------------------------------------------------------------ #
    # storing
    # ------------------------------------------------------------------ #
    async def store(
        self,
        title: str,
        content: str = "",
        *,
        node_type: NodeType | str = NodeType.KNOWLEDGE,
        memory_type: MemoryType | str = MemoryType.LONG_TERM,
        tags: list[str] | None = None,
        importance: float = 0.5,
        creator: str = "system",
        project_id: str | None = None,
        conversation_id: str | None = None,
        metadata: dict | None = None,
        related_to: list[str] | None = None,
    ) -> MemoryNode:
        """Create a memory node and link it into the graph."""
        if not self.config.enabled:
            raise RuntimeError("memory subsystem is disabled")

        node = self.graph.create_node(
            title=title,
            content=content,
            type=NodeType(node_type),
            memory_type=MemoryType(memory_type),
            tags=tags or [],
            importance=importance,
            creator=creator,
            project_id=project_id,
            conversation_id=conversation_id,
            metadata=metadata or {},
        )

        if node.memory_type == MemoryType.SHORT_TERM:
            self._short_term.append(node.id)

        for other in related_to or []:
            if self.graph.has_node(other):
                self.graph.connect(node.id, other, RelationType.RELATED)

        if conversation_id:
            self._attach_to_conversation(node, conversation_id)

        if self.bus:
            await self.bus.publish(
                Topics.MEMORY_STORED,
                {"id": node.id, "title": node.title, "type": node.type.value},
                source="memory",
            )
        return node

    def _attach_to_conversation(self, node: MemoryNode, conversation_id: str) -> None:
        """Ensure a conversation root exists and chain the message under it."""
        root_id = self._conversations.get(conversation_id)
        if root_id is None or not self.graph.has_node(root_id):
            root = self.graph.create_node(
                title=f"Conversation {conversation_id[:8]}",
                type=NodeType.CONVERSATION,
                memory_type=MemoryType.EPISODIC,
                conversation_id=conversation_id,
                importance=0.4,
            )
            root_id = root.id
            self._conversations[conversation_id] = root_id
        if node.id != root_id:
            self.graph.connect(root_id, node.id, RelationType.PARENT)

    async def remember_exchange(
        self,
        user_message: str,
        assistant_message: str,
        *,
        conversation_id: str,
        agent: str = "core",
        project_id: str | None = None,
        importance: float = 0.45,
    ) -> tuple[MemoryNode, MemoryNode]:
        """Persist one user/assistant turn as two linked episodic nodes."""
        user_node = await self.store(
            title=_headline(user_message),
            content=user_message,
            node_type=NodeType.MESSAGE,
            memory_type=MemoryType.EPISODIC,
            importance=importance,
            creator="user",
            conversation_id=conversation_id,
            project_id=project_id,
            tags=["conversation", "user"],
        )
        assistant_node = await self.store(
            title=_headline(assistant_message),
            content=assistant_message,
            node_type=NodeType.MESSAGE,
            memory_type=MemoryType.EPISODIC,
            importance=importance,
            creator=agent,
            conversation_id=conversation_id,
            project_id=project_id,
            tags=["conversation", "assistant", agent],
        )
        self.graph.connect(user_node.id, assistant_node.id, RelationType.RELATED, weight=1.0)
        return user_node, assistant_node

    # ------------------------------------------------------------------ #
    # recall
    # ------------------------------------------------------------------ #
    async def recall(
        self,
        query: str,
        *,
        limit: int | None = None,
        node_types: list[NodeType | str] | None = None,
        memory_types: list[MemoryType | str] | None = None,
        tags: list[str] | None = None,
        project_id: str | None = None,
        expand_hops: int = 1,
    ) -> list[RecallResult]:
        """Hybrid recall with graph expansion."""
        if not self.config.enabled:
            return []
        results = self.graph.search(
            query,
            limit=limit or self.config.recall_limit,
            node_types=node_types,
            memory_types=memory_types,
            tags=tags,
            project_id=project_id,
            min_score=self.config.importance_threshold * 0.2,
            expand_hops=expand_hops,
        )
        if self.bus and results:
            await self.bus.publish(
                Topics.MEMORY_RECALLED,
                {"query": query, "hits": len(results)},
                source="memory",
            )
        return results

    async def build_context(
        self,
        query: str,
        *,
        conversation_id: str | None = None,
        project_id: str | None = None,
        max_items: int = 8,
        max_chars: int = 4000,
    ) -> str:
        """Assemble a compact prompt context block from relevant memories."""
        chunks: list[str] = []
        budget = max_chars

        if conversation_id:
            recent = self.conversation_history(conversation_id, limit=4)
            if recent:
                chunks.append("Recent conversation:")
                for node in recent:
                    line = f"- [{node.creator}] {node.summary(200)}"
                    if len(line) <= budget:
                        chunks.append(line)
                        budget -= len(line)

        results = await self.recall(
            query, limit=max_items, project_id=project_id, expand_hops=1
        )
        relevant = [r for r in results if not r.node.conversation_id or r.node.conversation_id != conversation_id]
        if relevant:
            chunks.append("\nRelevant memories:")
            for result in relevant[:max_items]:
                line = f"- ({result.node.type.value}) {result.node.title}: {result.node.summary(200)}"
                if len(line) <= budget:
                    chunks.append(line)
                    budget -= len(line)

        return "\n".join(chunks).strip()

    def conversation_history(self, conversation_id: str, *, limit: int = 20) -> list[MemoryNode]:
        """Messages of a conversation in chronological order."""
        root_id = self._conversations.get(conversation_id)
        if root_id and self.graph.has_node(root_id):
            nodes = self.graph.neighbors(root_id, relation=RelationType.PARENT, direction="out")
        else:
            nodes = [
                n for n in self.graph.find(node_type=NodeType.MESSAGE, limit=500)
                if n.conversation_id == conversation_id
            ]
        nodes.sort(key=lambda n: n.created_at)
        return nodes[-limit:]

    def recent(self, limit: int = 10) -> list[MemoryNode]:
        """Most recently written short-term memories."""
        ids = list(self._short_term)[-limit:]
        return [self.graph.get_node(i) for i in ids if self.graph.has_node(i)]

    # ------------------------------------------------------------------ #
    # working memory
    # ------------------------------------------------------------------ #
    def set_working(self, key: str, value: Any, *, ttl: float | None = None) -> None:
        """Store a transient scratchpad value for in-flight reasoning."""
        self._working[key] = {
            "value": value,
            "expires_at": time.time() + ttl if ttl else None,
            "updated_at": time.time(),
        }

    def get_working(self, key: str, default: Any = None) -> Any:
        entry = self._working.get(key)
        if entry is None:
            return default
        if entry["expires_at"] and time.time() > entry["expires_at"]:
            self._working.pop(key, None)
            return default
        return entry["value"]

    def clear_working(self, key: str | None = None) -> None:
        if key is None:
            self._working.clear()
        else:
            self._working.pop(key, None)

    def working_snapshot(self) -> dict[str, Any]:
        now = time.time()
        return {
            k: v["value"]
            for k, v in self._working.items()
            if not v["expires_at"] or v["expires_at"] > now
        }

    # ------------------------------------------------------------------ #
    # maintenance
    # ------------------------------------------------------------------ #
    async def update(self, node_id: str, **changes: Any) -> MemoryNode:
        node = self.graph.update_node(node_id, **changes)
        if self.bus:
            await self.bus.publish(Topics.MEMORY_UPDATED, {"id": node_id}, source="memory")
        return node

    async def remove(self, node_id: str) -> None:
        self.graph.remove_node(node_id)
        if self.bus:
            await self.bus.publish(Topics.MEMORY_REMOVED, {"id": node_id}, source="memory")

    async def consolidate(self) -> dict[str, int]:
        """Promote valuable short-term memories, then prune the rest.

        This is the Compression/Learning Engine step run by the scheduler.
        """
        promoted = 0
        for node_id in list(self._short_term):
            if not self.graph.has_node(node_id):
                continue
            node = self.graph.get_node(node_id)
            if node.importance >= 0.7 or node.access_count >= 3:
                self.graph.promote(node_id, MemoryType.LONG_TERM)
                promoted += 1

        pruned = 0
        if self.config.auto_cleanup:
            pruned = self.graph.prune(
                older_than=self.config.short_term_ttl_seconds,
                max_importance=self.config.importance_threshold,
                memory_type=MemoryType.SHORT_TERM,
            )
        self._short_term = deque(
            (i for i in self._short_term if self.graph.has_node(i)),
            maxlen=self.config.short_term_capacity,
        )
        if promoted or pruned:
            logger.info("memory consolidation: promoted=%d pruned=%d", promoted, pruned)
        return {"promoted": promoted, "pruned": pruned}

    def save(self, path: str | Path | None = None) -> Path | None:
        try:
            return self.graph.save(path)
        except Exception as exc:  # noqa: BLE001 - persistence must never crash the app
            logger.error("failed to save memory graph: %s", exc)
            return None

    def stats(self) -> dict[str, Any]:
        data = self.graph.stats()
        data.update(
            {
                "short_term_buffer": len(self._short_term),
                "working_keys": len(self.working_snapshot()),
                "conversations": len(self._conversations),
                "enabled": self.config.enabled,
            }
        )
        return data


def _headline(text: str, width: int = 70) -> str:
    """First meaningful line of a message, used as a node title."""
    flat = " ".join(text.split())
    if not flat:
        return "(empty)"
    return flat if len(flat) <= width else flat[: width - 1] + "…"
