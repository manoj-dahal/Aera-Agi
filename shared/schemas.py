"""Shared Pydantic schemas used across AERA services.

These mirror the Memory Graph and Agent specs:
- docs/06-MEMORY-GRAPH.md
- docs/07-AGENTS.md
- docs/26-API.md
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Memory Graph ──────────────────────────────────────────────


class NodeType(str, Enum):
    FACT = "fact"
    PROJECT = "project"
    FILE = "file"
    AGENT = "agent"
    TASK = "task"
    CONVERSATION = "conversation"
    PREFERENCE = "preference"


class EdgeRelation(str, Enum):
    RELATES_TO = "relates_to"
    BELONGS_TO = "belongs_to"
    CREATED_BY = "created_by"
    DEPENDS_ON = "depends_on"


class MemoryNodeCreate(BaseModel):
    type: NodeType
    content: str = Field(min_length=1, max_length=10_000)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryNode(MemoryNodeCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class MemoryEdgeCreate(BaseModel):
    source_id: int
    target_id: int
    relation: EdgeRelation = EdgeRelation.RELATES_TO
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class MemoryEdge(MemoryEdgeCreate):
    id: int


class MemoryGraphStats(BaseModel):
    nodes: int
    edges: int
    by_type: dict[str, int]


# ── Agents ────────────────────────────────────────────────────


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DISABLED = "disabled"


class AgentInfo(BaseModel):
    name: str
    description: str
    capabilities: list[str]
    status: AgentStatus = AgentStatus.IDLE
    priority: str = "normal"


class TaskRequest(BaseModel):
    message: str = Field(min_length=1, max_length=50_000)
    agent: str | None = None  # explicit agent, else the Core Agent routes
    conversation_id: int | None = None


class TaskResponse(BaseModel):
    agent: str
    response: str
    model: str
    memory_nodes_used: int = 0


# ── AI Router ─────────────────────────────────────────────────


class ModelProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    ECHO = "echo"  # offline fallback for development


class ModelInfo(BaseModel):
    provider: ModelProvider
    name: str
    local: bool
    available: bool
