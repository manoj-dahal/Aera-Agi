"""Request/response schemas for the REST API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Envelope(BaseModel):
    """The documented success envelope."""

    success: bool = True
    message: str = "Completed"
    data: Any = None


class ErrorEnvelope(BaseModel):
    success: bool = False
    code: int = 500
    error: str = "Internal Server Error"
    type: str | None = None
    details: dict[str, Any] | None = None


def ok(data: Any = None, message: str = "Completed") -> dict[str, Any]:
    return {"success": True, "message": message, "data": data}


# --------------------------------------------------------------------------- #
# chat / AI
# --------------------------------------------------------------------------- #
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=100_000)
    conversation_id: str | None = None
    project_id: str | None = None
    agent: str | None = Field(default=None, description="Force a specific agent")
    capability: str = "conversation"
    stream: bool = False


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None
    task: str = "default"
    system: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=32000)
    stream: bool = False


# --------------------------------------------------------------------------- #
# agents
# --------------------------------------------------------------------------- #
class AgentTaskRequest(BaseModel):
    agent: str | None = None
    capability: str = "conversation"
    input: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str | None = None
    project_id: str | None = None


class AgentActionRequest(BaseModel):
    agent: str


# --------------------------------------------------------------------------- #
# memory
# --------------------------------------------------------------------------- #
class MemoryStoreRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = ""
    type: str = "knowledge"
    memory_type: str = "long_term"
    tags: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    project_id: str | None = None
    conversation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    related_to: list[str] = Field(default_factory=list)


class MemorySearchRequest(BaseModel):
    query: str = ""
    limit: int = Field(default=10, ge=1, le=100)
    node_types: list[str] | None = None
    memory_types: list[str] | None = None
    tags: list[str] | None = None
    project_id: str | None = None
    expand_hops: int = Field(default=1, ge=0, le=3)


class MemoryConnectRequest(BaseModel):
    source: str
    target: str
    relation: str = "related"
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class MemoryUpdateRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    memory_type: str | None = None


# --------------------------------------------------------------------------- #
# workspace
# --------------------------------------------------------------------------- #
class WorkspaceOpenRequest(BaseModel):
    path: str
    index: bool = True


class WorkspaceSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=20, ge=1, le=200)


# --------------------------------------------------------------------------- #
# voice / hologram
# --------------------------------------------------------------------------- #
class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    emotion: str | None = None
    speed: float | None = Field(default=None, ge=0.25, le=3.0)


class ListenRequest(BaseModel):
    text: str = Field(default="", description="Pre-transcribed text for headless STT")
    language: str | None = None


class AvatarEmotionRequest(BaseModel):
    emotion: str
    intensity: float = Field(default=0.7, ge=0.0, le=1.0)


class AvatarGestureRequest(BaseModel):
    gesture: str


# --------------------------------------------------------------------------- #
# automation
# --------------------------------------------------------------------------- #
class WorkflowCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    enabled: bool = True
    actions: list[dict[str, Any]] = Field(default_factory=list)
    triggers: list[dict[str, Any]] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunRequest(BaseModel):
    variables: dict[str, Any] = Field(default_factory=dict)


class AddProviderRequest(BaseModel):
    """Register an AI provider at runtime.

    ``type`` selects the adapter; ``custom`` covers any OpenAI-compatible
    server, which is most self-hosted options.
    """

    name: str = Field(min_length=1, max_length=64, description="How you will refer to it")
    type: str = Field(default="custom", description="Adapter: custom, openai, ollama, ...")
    base_url: str | None = Field(default=None, description="e.g. http://localhost:8000/v1")
    api_key: str | None = None
    model: str | None = Field(default=None, description="Default model id")
    options: dict[str, Any] | None = Field(default=None, description="Extra adapter options")
    replace: bool = Field(default=False, description="Overwrite an existing provider")
