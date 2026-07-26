# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Anthropic Claude provider (``docs/api/Claude.md``)."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import httpx

from ...core.errors import ProviderError, ProviderUnavailableError
from ..base import AIProvider, CompletionRequest, CompletionResponse, ModelInfo, Role, Usage

_KNOWN_MODELS = [
    ("claude-sonnet-4-5", 200000),
    ("claude-opus-4-1", 200000),
    ("claude-3-5-haiku-latest", 200000),
]


class AnthropicProvider(AIProvider):
    """Claude Messages API adapter."""

    name = "claude"
    is_local = False

    def __init__(self, **options) -> None:
        super().__init__(**options)
        self.api_key = options.get("api_key") or ""
        self.base_url = str(options.get("base_url", "https://api.anthropic.com/v1")).rstrip("/")
        self.model_id = options.get("model", "claude-sonnet-4-5")
        self.version = options.get("anthropic_version", "2023-06-01")
        self.timeout = float(options.get("timeout", 120.0))
        self._client: httpx.AsyncClient | None = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": self.version,
                    "content-type": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    def _payload(self, request: CompletionRequest, *, stream: bool) -> dict:
        """Claude takes ``system`` out-of-band and only user/assistant turns inline."""
        system = "\n\n".join(m.content for m in request.messages if m.role == Role.SYSTEM)
        turns = [
            {"role": "assistant" if m.role == Role.ASSISTANT else "user", "content": m.content}
            for m in request.messages
            if m.role in (Role.USER, Role.ASSISTANT)
        ]
        if not turns:
            turns = [{"role": "user", "content": request.prompt_text() or "Hello"}]

        payload: dict = {
            "model": request.model or self.model_id,
            "messages": turns,
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
            "stream": stream,
        }
        if system:
            payload["system"] = system
        if request.stop:
            payload["stop_sequences"] = request.stop
        return payload

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        if not self.api_key:
            raise ProviderUnavailableError("Anthropic API key is not configured")

        started = time.perf_counter()
        try:
            resp = await self._http().post("/messages", json=self._payload(request, stream=False))
            resp.raise_for_status()
            data = resp.json()
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError("cannot reach the Anthropic API") from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"Claude error {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Claude request failed: {exc}") from exc

        text = "".join(
            block.get("text", "") for block in data.get("content", [])
            if block.get("type") == "text"
        )
        usage = data.get("usage") or {}
        return CompletionResponse(
            content=text,
            model=data.get("model", self.model_id),
            provider=self.name,
            finish_reason=data.get("stop_reason") or "stop",
            usage=Usage(
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
            ),
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        if not self.api_key:
            raise ProviderUnavailableError("Anthropic API key is not configured")
        try:
            async with self._http().stream(
                "POST", "/messages", json=self._payload(request, stream=True)
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    body = line[5:].strip()
                    if not body:
                        continue
                    try:
                        event = json.loads(body)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "content_block_delta":
                        token = (event.get("delta") or {}).get("text")
                        if token:
                            yield token
                    elif event.get("type") == "message_stop":
                        break
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError("cannot reach the Anthropic API") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Claude stream failed: {exc}") from exc

    async def list_models(self) -> list[ModelInfo]:
        if not self.api_key:
            return []
        return [
            ModelInfo(id=mid, provider=self.name, name=mid, context_length=ctx)
            for mid, ctx in _KNOWN_MODELS
        ]

    async def _probe(self) -> bool:
        return bool(self.api_key)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
