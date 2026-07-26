# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Provider abstraction shared by every AI backend."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ImageContent(BaseModel):
    """An image attached to a message.

    Held provider-neutral -- base64 plus a media type -- because the three
    wire formats disagree about everything else. OpenAI wants a data URL
    under ``image_url``, Anthropic wants ``source.data`` with the media type
    beside it, and Gemini wants ``inline_data.data`` with the key spelled
    ``mime_type``. Storing any one of those shapes here would make the other
    two a translation of a translation.
    """

    data: str
    media_type: str = "image/jpeg"
    #: Kept for token estimation and for reporting what was actually sent.
    width: int = 0
    height: int = 0

    @property
    def data_url(self) -> str:
        return f"data:{self.media_type};base64,{self.data}"


class Message(BaseModel):
    role: Role = Role.USER
    content: str
    name: str | None = None
    #: Images travel with the message that refers to them.
    images: list[ImageContent] = Field(default_factory=list)

    @property
    def has_images(self) -> bool:
        return bool(self.images)

    def to_wire(self) -> dict[str, Any]:
        """OpenAI-shaped, which most providers copy.

        A message without images keeps the plain string form: the content
        list is only valid on endpoints that accept multimodal input, and
        sending it unconditionally breaks older deployments that accept a
        string and nothing else.
        """
        data: dict[str, Any] = {"role": self.role.value}
        if self.images:
            parts: list[dict[str, Any]] = []
            if self.content:
                parts.append({"type": "text", "text": self.content})
            parts.extend(
                {"type": "image_url", "image_url": {"url": image.data_url}}
                for image in self.images
            )
            data["content"] = parts
        else:
            data["content"] = self.content
        if self.name:
            data["name"] = self.name
        return data


class CompletionRequest(BaseModel):
    """A normalised chat-completion request."""

    messages: list[Message]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False
    stop: list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def prompt_text(self) -> str:
        return "\n".join(f"{m.role.value}: {m.content}" for m in self.messages)


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class CompletionResponse(BaseModel):
    """A normalised chat-completion response."""

    content: str
    model: str
    provider: str
    finish_reason: str = "stop"
    usage: Usage = Field(default_factory=Usage)
    latency_ms: float = 0.0
    created_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "finish_reason": self.finish_reason,
            "usage": self.usage.model_dump() | {"total_tokens": self.usage.total_tokens},
            "latency_ms": round(self.latency_ms, 2),
        }


class ModelInfo(BaseModel):
    """Metadata for a model exposed by a provider."""

    id: str
    provider: str
    name: str = ""
    context_length: int = 8192
    supports_streaming: bool = True
    supports_vision: bool = False
    local: bool = False
    size: str | None = None
    quantization: str | None = None
    status: str = "available"


class AIProvider(ABC):
    """Interface every AI backend implements."""

    name: str = "base"
    is_local: bool = False

    def __init__(self, **options: Any) -> None:
        self.options = options
        self.enabled: bool = bool(options.get("enabled", True))
        self._healthy: bool | None = None
        self._last_check: float = 0.0

    # -- required ---------------------------------------------------------- #
    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        ...

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        ...

    # -- optional ---------------------------------------------------------- #
    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Default streaming: yield the completed text in one chunk."""
        response = await self.complete(request)
        yield response.content

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(f"{self.name} does not provide embeddings")

    async def health_check(self, *, ttl: float = 30.0) -> bool:
        """Cached availability probe."""
        now = time.time()
        if self._healthy is not None and (now - self._last_check) < ttl:
            return self._healthy
        try:
            self._healthy = await self._probe()
        except Exception:  # noqa: BLE001 - an unreachable provider is simply unhealthy
            self._healthy = False
        self._last_check = now
        return self._healthy

    async def _probe(self) -> bool:
        return self.enabled

    async def close(self) -> None:  # noqa: B027 - optional hook, not abstract
        """Release network resources. Only HTTP-backed providers need this."""

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "local": self.is_local,
            "enabled": self.enabled,
            "healthy": self._healthy,
        }
