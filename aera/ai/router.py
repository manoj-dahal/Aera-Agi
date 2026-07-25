"""Model Router.

Chooses which provider serves each request based on the configured routing
mode and the task kind, then retries down a fallback chain when a provider is
unhealthy or errors. Also tracks per-provider usage statistics.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from ..core.config import ModelsSection
from ..core.errors import ProviderError, ProviderUnavailableError
from ..core.events import EventBus, Topics
from ..core.logging import get_logger
from .base import AIProvider, CompletionRequest, CompletionResponse, Message, ModelInfo, Role
from .providers import create_provider

logger = get_logger("ai.router")

# Task kinds the router understands; each maps to a config field.
TASK_KINDS = ("default", "reasoning", "coding", "research", "vision")


class ProviderStats:
    """Rolling counters used by the performance monitor and /system/status."""

    __slots__ = ("requests", "failures", "tokens_in", "tokens_out", "total_latency_ms")

    def __init__(self) -> None:
        self.requests = 0
        self.failures = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.total_latency_ms = 0.0

    @property
    def avg_latency_ms(self) -> float:
        ok = self.requests - self.failures
        return self.total_latency_ms / ok if ok > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "failures": self.failures,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


class ModelRouter:
    """Selects providers, executes completions and handles failover."""

    def __init__(self, config: ModelsSection | None = None, *, bus: EventBus | None = None) -> None:
        self.config = config or ModelsSection()
        self.bus = bus
        self._providers: dict[str, AIProvider] = {}
        self._stats: dict[str, ProviderStats] = {}
        self._build_providers()

    # ------------------------------------------------------------------ #
    # setup
    # ------------------------------------------------------------------ #
    def _build_providers(self) -> None:
        """Instantiate every configured provider plus the always-on fallback."""
        cfg = self.config

        if cfg.local.enabled:
            try:
                self.register(
                    create_provider(
                        cfg.local.provider,
                        model=cfg.local.model,
                        endpoint=cfg.local.endpoint,
                        context=cfg.local.context,
                        gpu=cfg.local.gpu,
                    )
                )
            except KeyError as exc:
                logger.warning("skipping local provider: %s", exc)

        for name, options in (cfg.providers or {}).items():
            opts = dict(options or {})
            if not opts.pop("enabled", True):
                continue
            try:
                self.register(create_provider(name, **opts))
            except KeyError as exc:
                logger.warning("skipping provider %s: %s", name, exc)

        # The built-in reasoner guarantees the platform always answers.
        if "builtin" not in self._providers:
            self.register(create_provider("builtin"))

    def register(self, provider: AIProvider) -> AIProvider:
        self._providers[provider.name] = provider
        self._stats.setdefault(provider.name, ProviderStats())
        logger.debug("registered AI provider: %s (local=%s)", provider.name, provider.is_local)
        return provider

    def get(self, name: str) -> AIProvider | None:
        return self._providers.get(name.strip().lower())

    @property
    def providers(self) -> dict[str, AIProvider]:
        return dict(self._providers)

    # ------------------------------------------------------------------ #
    # selection
    # ------------------------------------------------------------------ #
    def _preference_order(self, task: str = "default") -> list[str]:
        """Ordered candidate provider names for a task under the current mode."""
        cfg = self.config
        preferred = getattr(cfg, task if task in TASK_KINDS else "default", cfg.default)

        local = [n for n, p in self._providers.items() if p.is_local and n != "builtin"]
        cloud = [n for n, p in self._providers.items() if not p.is_local]
        mode = cfg.routing_mode

        if mode == "manual":
            order = [preferred]
        elif mode == "offline" or mode == "privacy":
            order = [preferred] if preferred in local else []
            order += local
        elif mode == "local_first":
            order = [preferred] + local + cloud
        elif mode == "cloud_first":
            order = [preferred] + cloud + local
        elif mode == "performance":
            # fastest observed average latency first, among healthy providers
            ranked = sorted(
                (n for n in self._providers if n != "builtin"),
                key=lambda n: self._stats[n].avg_latency_ms or 1e9,
            )
            order = [preferred] + ranked
        else:  # automatic
            order = [preferred] + local + cloud

        # de-duplicate, keep only known providers, always end with the fallback
        seen: set[str] = set()
        result: list[str] = []
        for name in order:
            key = (name or "").strip().lower()
            if key in self._providers and key not in seen:
                seen.add(key)
                result.append(key)
        if "builtin" in self._providers and "builtin" not in seen:
            result.append("builtin")
        return result

    async def select(self, task: str = "default", *, model: str | None = None) -> AIProvider:
        """Return the first healthy provider for a task."""
        if model and "/" in model:
            # "provider/model" pins the provider explicitly
            prefix = model.split("/", 1)[0].lower()
            if prefix in self._providers:
                return self._providers[prefix]

        for name in self._preference_order(task):
            provider = self._providers[name]
            if not provider.enabled:
                continue
            if await provider.health_check():
                return provider
        return self._providers["builtin"]

    # ------------------------------------------------------------------ #
    # execution
    # ------------------------------------------------------------------ #
    async def complete(
        self,
        messages: list[Message] | str,
        *,
        task: str = "default",
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
        system: str | None = None,
    ) -> CompletionResponse:
        """Run a completion with automatic failover down the preference chain."""
        request = self._make_request(
            messages, model=model, temperature=temperature,
            max_tokens=max_tokens, stop=stop, system=system,
        )

        if self.bus:
            await self.bus.publish(
                Topics.AI_REQUEST, {"task": task, "model": model}, source="ai.router"
            )

        errors: list[str] = []
        for name in self._preference_order(task):
            provider = self._providers[name]
            if not provider.enabled:
                continue
            if name != "builtin" and not await provider.health_check():
                errors.append(f"{name}: unhealthy")
                continue

            stats = self._stats[name]
            stats.requests += 1
            started = time.perf_counter()
            try:
                response = await provider.complete(request)
            except (ProviderUnavailableError, ProviderError) as exc:
                stats.failures += 1
                errors.append(f"{name}: {exc}")
                logger.warning("provider %s failed, trying next: %s", name, exc)
                continue
            except Exception as exc:  # noqa: BLE001 - never let one provider break routing
                stats.failures += 1
                errors.append(f"{name}: {exc}")
                logger.exception("unexpected error from provider %s", name)
                continue

            stats.total_latency_ms += (time.perf_counter() - started) * 1000
            stats.tokens_in += response.usage.prompt_tokens
            stats.tokens_out += response.usage.completion_tokens

            if self.bus:
                await self.bus.publish(
                    Topics.AI_COMPLETED,
                    {
                        "provider": response.provider,
                        "model": response.model,
                        "tokens": response.usage.total_tokens,
                        "latency_ms": round(response.latency_ms, 2),
                    },
                    source="ai.router",
                )
            return response

        detail = "; ".join(errors) or "no providers configured"
        if self.bus:
            await self.bus.publish(Topics.AI_FAILED, {"errors": errors}, source="ai.router")
        raise ProviderError(f"all AI providers failed ({detail})")

    async def stream(
        self,
        messages: list[Message] | str,
        *,
        task: str = "default",
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        system: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream tokens from the first provider that accepts the request."""
        request = self._make_request(
            messages, model=model, temperature=temperature,
            max_tokens=max_tokens, system=system, stream=True,
        )

        for name in self._preference_order(task):
            provider = self._providers[name]
            if not provider.enabled:
                continue
            if name != "builtin" and not await provider.health_check():
                continue

            stats = self._stats[name]
            stats.requests += 1
            produced = False
            try:
                async for token in provider.stream(request):
                    produced = True
                    yield token
                if produced:
                    return
            except (ProviderUnavailableError, ProviderError) as exc:
                stats.failures += 1
                logger.warning("stream from %s failed: %s", name, exc)
                if produced:
                    return  # partial output already delivered; do not restart
                continue
        # Nothing streamed: fall back to a single blocking completion.
        response = await self.complete(
            messages, task=task, model=model, temperature=temperature,
            max_tokens=max_tokens, system=system,
        )
        yield response.content

    def _make_request(
        self,
        messages: list[Message] | str,
        *,
        model: str | None,
        temperature: float,
        max_tokens: int | None,
        system: str | None = None,
        stop: list[str] | None = None,
        stream: bool = False,
    ) -> CompletionRequest:
        if isinstance(messages, str):
            msgs = [Message(role=Role.USER, content=messages)]
        else:
            msgs = list(messages)
        if system:
            msgs = [Message(role=Role.SYSTEM, content=system), *msgs]
        # strip a provider prefix such as "ollama/llama3"
        resolved = model.split("/", 1)[1] if model and "/" in model else model
        return CompletionRequest(
            messages=msgs,
            model=resolved,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
            stream=stream,
        )

    # ------------------------------------------------------------------ #
    # introspection
    # ------------------------------------------------------------------ #
    async def list_models(self) -> list[ModelInfo]:
        models: list[ModelInfo] = []
        for provider in self._providers.values():
            if not provider.enabled:
                continue
            try:
                models.extend(await provider.list_models())
            except Exception:  # noqa: BLE001
                logger.debug("could not list models for %s", provider.name)
        return models

    async def health(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, provider in self._providers.items():
            out[name] = {
                **provider.describe(),
                "healthy": await provider.health_check(),
                "stats": self._stats[name].to_dict(),
            }
        return out

    def stats(self) -> dict[str, Any]:
        return {name: s.to_dict() for name, s in self._stats.items()}

    async def close(self) -> None:
        for provider in self._providers.values():
            try:
                await provider.close()
            except Exception:  # noqa: BLE001
                logger.debug("error closing provider %s", provider.name)
