"""Model Router — Local First AI routing (docs/18-LOCAL-LLM.md, docs/19-CLOUD-AI.md).

Routing policy:
1. Ollama (local) if reachable
2. Cloud providers if API keys are configured (OpenAI → Anthropic → Gemini)
3. Echo provider — a deterministic offline fallback so AERA always answers
"""

from __future__ import annotations

import os

import httpx

from shared.schemas import ModelInfo, ModelProvider


class ModelRouter:
    def __init__(self) -> None:
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.default_local_model = os.getenv("LOCAL_MODEL_DEFAULT", "llama3")

    # ── Discovery ─────────────────────────────────────────

    async def ollama_available(self) -> bool:
        if os.getenv("LOCAL_LLM_ENABLED", "true").lower() != "true":
            return False
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.ollama_host}/api/tags")
                return res.status_code == 200
        except httpx.HTTPError:
            return False

    def cloud_provider(self) -> ModelProvider | None:
        if os.getenv("OPENAI_API_KEY"):
            return ModelProvider.OPENAI
        if os.getenv("ANTHROPIC_API_KEY"):
            return ModelProvider.ANTHROPIC
        if os.getenv("GEMINI_API_KEY"):
            return ModelProvider.GEMINI
        return None

    async def list_models(self) -> list[ModelInfo]:
        models: list[ModelInfo] = []
        local_ok = await self.ollama_available()
        models.append(
            ModelInfo(
                provider=ModelProvider.OLLAMA,
                name=self.default_local_model,
                local=True,
                available=local_ok,
            )
        )
        cloud = self.cloud_provider()
        if cloud:
            models.append(
                ModelInfo(provider=cloud, name="default", local=False, available=True)
            )
        models.append(
            ModelInfo(provider=ModelProvider.ECHO, name="echo", local=True, available=True)
        )
        return models

    # ── Completion ────────────────────────────────────────

    async def complete(self, prompt: str, system: str = "") -> tuple[str, str]:
        """Return (response_text, model_label) using the local-first policy."""
        if await self.ollama_available():
            try:
                return await self._ollama_complete(prompt, system)
            except httpx.HTTPError:
                pass  # fall through
        # Cloud SDK calls are added as providers are wired in; for now the
        # echo provider guarantees an offline response.
        return self._echo_complete(prompt), "echo"

    async def _ollama_complete(self, prompt: str, system: str) -> tuple[str, str]:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.default_local_model,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                },
            )
            res.raise_for_status()
            data = res.json()
            return data.get("response", ""), f"ollama/{self.default_local_model}"

    @staticmethod
    def _echo_complete(prompt: str) -> str:
        return (
            "AERA (offline echo mode): I received your message — "
            f"\"{prompt[:200]}\". Connect a local model (Ollama) or add a cloud "
            "API key in .env to enable full reasoning."
        )
