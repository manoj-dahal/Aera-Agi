# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Memory node / edge domain models (``docs/06-MEMORY-GRAPH.md``)."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MemoryType(str, Enum):
    """The six memory systems described in the spec."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    WORKING = "working"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


class NodeType(str, Enum):
    """Every object the graph can represent."""

    USER = "user"
    CONVERSATION = "conversation"
    MESSAGE = "message"
    PROJECT = "project"
    FOLDER = "folder"
    FILE = "file"
    TASK = "task"
    AGENT = "agent"
    PROMPT = "prompt"
    COMMAND = "command"
    KNOWLEDGE = "knowledge"
    API = "api"
    MODEL = "model"
    APPLICATION = "application"
    DEVICE = "device"
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    WEBSITE = "website"
    WORKFLOW = "workflow"
    DECISION = "decision"
    EVENT = "event"
    PREFERENCE = "preference"


class RelationType(str, Enum):
    """Supported relationship types."""

    PARENT = "parent"
    CHILD = "child"
    RELATED = "related"
    DEPENDS_ON = "depends_on"
    USES = "uses"
    REFERENCES = "references"
    CREATED_BY = "created_by"
    UPDATED_BY = "updated_by"
    CONNECTED_TO = "connected_to"
    SIMILAR_TO = "similar_to"


# Traversing a `parent` edge forward is the same as traversing `child` backward.
INVERSE_RELATIONS: dict[RelationType, RelationType] = {
    RelationType.PARENT: RelationType.CHILD,
    RelationType.CHILD: RelationType.PARENT,
    RelationType.CREATED_BY: RelationType.CREATED_BY,
    RelationType.UPDATED_BY: RelationType.UPDATED_BY,
    RelationType.RELATED: RelationType.RELATED,
    RelationType.SIMILAR_TO: RelationType.SIMILAR_TO,
    RelationType.CONNECTED_TO: RelationType.CONNECTED_TO,
}


class MemoryNode(BaseModel):
    """A single node in the Memory Graph."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str
    content: str = ""
    description: str = ""
    type: NodeType = NodeType.KNOWLEDGE
    memory_type: MemoryType = MemoryType.LONG_TERM
    tags: list[str] = Field(default_factory=list)
    importance: float = 0.5
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    accessed_at: float = Field(default_factory=time.time)
    access_count: int = 0
    creator: str = "system"
    source: str | None = None
    project_id: str | None = None
    conversation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None

    @field_validator("importance")
    @classmethod
    def _clamp_importance(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, v: list[str]) -> list[str]:
        seen, out = set(), []
        for tag in v:
            t = tag.strip().lower()
            if t and t not in seen:
                seen.add(t)
                out.append(t)
        return out

    def touch(self) -> None:
        """Record an access - feeds the recency/frequency ranking factors."""
        self.accessed_at = time.time()
        self.access_count += 1

    def searchable_text(self) -> str:
        return " ".join(
            filter(None, [self.title, self.description, self.content, " ".join(self.tags)])
        )

    def summary(self, width: int = 160) -> str:
        text = self.content or self.description or self.title
        text = " ".join(text.split())
        return text if len(text) <= width else text[: width - 1] + "…"

    def to_public(self) -> dict[str, Any]:
        """Serialise without the (large) embedding vector."""
        data = self.model_dump(exclude={"embedding"})
        data["has_embedding"] = self.embedding is not None
        return data


class MemoryEdge(BaseModel):
    """A directed, weighted relationship between two nodes."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    source: str
    target: str
    relation: RelationType = RelationType.RELATED
    weight: float = 1.0
    created_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("weight")
    @classmethod
    def _clamp_weight(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    def key(self) -> tuple[str, str, str]:
        return (self.source, self.target, self.relation.value)


class RecallResult(BaseModel):
    """A ranked recall hit."""

    node: MemoryNode
    score: float
    reason: str = "match"
    hops: int = 0

    def to_public(self) -> dict[str, Any]:
        return {
            "node": self.node.to_public(),
            "score": round(self.score, 4),
            "reason": self.reason,
            "hops": self.hops,
        }
