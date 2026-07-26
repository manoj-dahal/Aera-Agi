# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Google Gemini provider (``docs/api/Gemini.md``)."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import httpx

from ...core.errors import ProviderError, ProviderUnavailableError
from ..base import AIProvider, CompletionRequest, CompletionResponse, ModelInfo, Role, Usage


class GeminiProvider(AIProvider):
    """Generative Language API adapter."""

    name = "gemini"
    is_local = False

    def __init__(self, **options) -> None:
        super().__init__(**options)
        self.api_key = options.get("api_key") or ""
        self.base_url = str(
            options.get("base_url", "https://generativelanguage.googleapis.com/v1beta")
        ).rstrip("/")
        self.model_id = options.get("model", "gemini-2.5-pro")
        self.timeout = float(options.get("timeout", 120.0))
        self._client: httpx.AsyncClient | None = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self._client

    def _payload(self, request: CompletionRequest) -> dict:
        """Gemini uses ``contents`` with ``user``/``model`` roles + systemInstruction."""
        system = "\n\n".join(m.content for m in request.messages if m.role == Role.SYSTEM)
        contents = [
            {
                "role": "model" if m.role == Role.ASSISTANT else "user",
                "parts": [{"text": m.content}],
            }
            for m in request.messages
            if m.role in (Role.USER, Role.ASSISTANT)
        ]
        if not contents:
            contents = [{"role": "user", "parts": [{"text": request.prompt_text() or "Hello"}]}]

        payload: dict = {
            "contents": contents,
            "generationConfig": {"temperature": request.temperature},
        }
        if request.max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = request.max_tokens
        if request.stop:
            payload["generationConfig"]["stopSequences"] = request.stop
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        return payload

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        if not self.api_key:
            raise ProviderUnavailableError("Gemini API key is not configured")

        model = request.model or self.model_id
        started = time.perf_counter()
        try:
            resp = await self._http().post(
                f"/models/{model}:generateContent",
                params={"key": self.api_key},
                json=self._payload(request),
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError("cannot reach the Gemini API") from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"Gemini error {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Gemini request failed: {exc}") from exc

        candidates = data.get("candidates") or [{}]
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        usage = data.get("usageMetadata") or {}

        return CompletionResponse(
            content=text,
            model=model,
            provider=self.name,
            finish_reason=(candidates[0].get("finishReason") or "stop").lower(),
            usage=Usage(
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
            ),
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        if not self.api_key:
            raise ProviderUnavailableError("Gemini API key is not configured")
        model = request.model or self.model_id
        try:
            async with self._http().stream(
                "POST",
                f"/models/{model}:streamGenerateContent",
                params={"key": self.api_key, "alt": "sse"},
                json=self._payload(request),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    body = line[5:].strip()
                    if not body:
                        continue
                    try:
                        chunk = json.loads(body)
                    except json.JSONDecodeError:
                        continue
                    for cand in chunk.get("candidates", []):
                        for part in (cand.get("content") or {}).get("parts", []):
                            token = part.get("text")
                            if token:
                                yield token
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError("cannot reach the Gemini API") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Gemini stream failed: {exc}") from exc

    async def list_models(self) -> list[ModelInfo]:
        if not self.api_key:
            return []
        try:
            resp = await self._http().get("/models", params={"key": self.api_key}, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError:
            return []
        out: list[ModelInfo] = []
        for m in data.get("models", []):
            mid = str(m.get("name", "")).removeprefix("models/")
            if not mid:
                continue
            out.append(
                ModelInfo(
                    id=mid,
                    provider=self.name,
                    name=m.get("displayName", mid),
                    context_length=m.get("inputTokenLimit", 32768),
                    supports_vision=True,
                )
            )
        return out

    async def _probe(self) -> bool:
        return bool(self.api_key)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
