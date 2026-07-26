# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Ollama local-runtime provider (``docs/18-LOCAL-LLM.md``)."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import httpx

from ...core.errors import ProviderError, ProviderUnavailableError
from ..base import AIProvider, CompletionRequest, CompletionResponse, ModelInfo, Usage


class OllamaProvider(AIProvider):
    """Talks to a local Ollama daemon over its native HTTP API."""

    name = "ollama"
    is_local = True

    def __init__(self, **options) -> None:
        super().__init__(**options)
        self.endpoint = str(options.get("endpoint", "http://localhost:11434")).rstrip("/")
        self.model_id = options.get("model", "llama3")
        self.timeout = float(options.get("timeout", 120.0))
        self._client: httpx.AsyncClient | None = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.endpoint, timeout=self.timeout)
        return self._client

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        payload = {
            "model": request.model or self.model_id,
            "messages": [m.to_wire() for m in request.messages],
            "stream": False,
            "options": self._options(request),
        }
        started = time.perf_counter()
        try:
            resp = await self._http().post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(f"Ollama not reachable at {self.endpoint}") from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"Ollama error {exc.response.status_code}: {exc.response.text[:200]}") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc

        return CompletionResponse(
            content=(data.get("message") or {}).get("content", ""),
            model=data.get("model", payload["model"]),
            provider=self.name,
            finish_reason=data.get("done_reason", "stop"),
            usage=Usage(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
            ),
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        payload = {
            "model": request.model or self.model_id,
            "messages": [m.to_wire() for m in request.messages],
            "stream": True,
            "options": self._options(request),
        }
        try:
            async with self._http().stream("POST", "/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = (chunk.get("message") or {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        except httpx.ConnectError as exc:
            raise ProviderUnavailableError(f"Ollama not reachable at {self.endpoint}") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama stream failed: {exc}") from exc

    def _options(self, request: CompletionRequest) -> dict:
        opts: dict = {"temperature": request.temperature}
        if request.max_tokens:
            opts["num_predict"] = request.max_tokens
        if request.stop:
            opts["stop"] = request.stop
        if self.options.get("context"):
            opts["num_ctx"] = int(self.options["context"])
        return opts

    async def list_models(self) -> list[ModelInfo]:
        try:
            resp = await self._http().get("/api/tags", timeout=10.0)
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError:
            return []

        models: list[ModelInfo] = []
        for entry in payload.get("models", []):
            details = entry.get("details") or {}
            models.append(
                ModelInfo(
                    id=entry.get("name", "unknown"),
                    provider=self.name,
                    name=entry.get("name", "unknown"),
                    context_length=int(self.options.get("context", 8192)),
                    local=True,
                    size=_human_size(entry.get("size")),
                    quantization=details.get("quantization_level"),
                    status="ready",
                )
            )
        return models

    async def embed(self, texts: list[str]) -> list[list[float]]:
        model = self.options.get("embedding_model", "nomic-embed-text")
        out: list[list[float]] = []
        for text in texts:
            try:
                resp = await self._http().post(
                    "/api/embeddings", json={"model": model, "prompt": text}, timeout=60.0
                )
                resp.raise_for_status()
                out.append(resp.json().get("embedding", []))
            except httpx.HTTPError as exc:
                raise ProviderError(f"Ollama embedding failed: {exc}") from exc
        return out

    async def _probe(self) -> bool:
        try:
            resp = await self._http().get("/api/tags", timeout=3.0)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def _human_size(size: int | None) -> str | None:
    if not size:
        return None
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return None
