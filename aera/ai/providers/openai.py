"""OpenAI-compatible provider.

Also drives LM Studio, vLLM, OpenRouter and any other server exposing the
``/v1/chat/completions`` contract - only ``base_url`` changes.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import httpx

from ...core.errors import ProviderError, ProviderUnavailableError
from ..base import AIProvider, CompletionRequest, CompletionResponse, ModelInfo, Usage


class OpenAIProvider(AIProvider):
    name = "openai"
    is_local = False

    def __init__(self, **options) -> None:
        super().__init__(**options)
        self.api_key = options.get("api_key") or ""
        self.base_url = str(options.get("base_url", "https://api.openai.com/v1")).rstrip("/")
        self.model_id = options.get("model", "gpt-4o-mini")
        self.timeout = float(options.get("timeout", 120.0))
        self.organization = options.get("organization")
        self._client: httpx.AsyncClient | None = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            if self.organization:
                headers["OpenAI-Organization"] = self.organization
            self._client = httpx.AsyncClient(
                base_url=self.base_url, headers=headers, timeout=self.timeout
            )
        return self._client

    def _payload(self, request: CompletionRequest, *, stream: bool) -> dict:
        payload: dict = {
            "model": request.model or self.model_id,
            "messages": [m.to_wire() for m in request.messages],
            "temperature": request.temperature,
            "stream": stream,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.stop:
            payload["stop"] = request.stop
        return payload

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        if not self.api_key and "api.openai.com" in self.base_url:
            raise ProviderUnavailableError("OpenAI API key is not configured")

        started = time.perf_counter()
        try:
            resp = await self._http().post(
                "/chat/completions", json=self._payload(request, stream=False)
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(f"cannot reach {self.base_url}") from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"OpenAI error {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"OpenAI request failed: {exc}") from exc

        choice = (data.get("choices") or [{}])[0]
        usage = data.get("usage") or {}
        return CompletionResponse(
            content=(choice.get("message") or {}).get("content", ""),
            model=data.get("model", self.model_id),
            provider=self.name,
            finish_reason=choice.get("finish_reason", "stop"),
            usage=Usage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            ),
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        try:
            async with self._http().stream(
                "POST", "/chat/completions", json=self._payload(request, stream=True)
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    body = line[5:].strip()
                    if body in ("", "[DONE]"):
                        if body == "[DONE]":
                            break
                        continue
                    try:
                        chunk = json.loads(body)
                    except json.JSONDecodeError:
                        continue
                    delta = ((chunk.get("choices") or [{}])[0].get("delta") or {})
                    token = delta.get("content")
                    if token:
                        yield token
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(f"cannot reach {self.base_url}") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"OpenAI stream failed: {exc}") from exc

    async def list_models(self) -> list[ModelInfo]:
        try:
            resp = await self._http().get("/models", timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError:
            return []
        return [
            ModelInfo(
                id=m.get("id", "unknown"),
                provider=self.name,
                name=m.get("id", "unknown"),
                context_length=int(self.options.get("context", 128000)),
                local=self.is_local,
            )
            for m in data.get("data", [])
        ]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        model = self.options.get("embedding_model", "text-embedding-3-small")
        try:
            resp = await self._http().post(
                "/embeddings", json={"model": model, "input": texts}, timeout=60.0
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"embedding request failed: {exc}") from exc
        return [item["embedding"] for item in resp.json().get("data", [])]

    async def _probe(self) -> bool:
        if not self.api_key and "api.openai.com" in self.base_url:
            return False
        try:
            resp = await self._http().get("/models", timeout=5.0)
            return resp.status_code < 500
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


class LMStudioProvider(OpenAIProvider):
    """LM Studio's local OpenAI-compatible server."""

    name = "lmstudio"
    is_local = True

    def __init__(self, **options) -> None:
        options.setdefault("base_url", "http://localhost:1234/v1")
        options.setdefault("api_key", "lm-studio")
        super().__init__(**options)


class OpenRouterProvider(OpenAIProvider):
    """OpenRouter multi-model gateway."""

    name = "openrouter"
    is_local = False

    def __init__(self, **options) -> None:
        options.setdefault("base_url", "https://openrouter.ai/api/v1")
        options.setdefault("model", "openai/gpt-4o-mini")
        super().__init__(**options)
