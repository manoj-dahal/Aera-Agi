# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""AI provider and model router tests."""

from __future__ import annotations

import pytest

from aera.ai import CompletionResponse, Message, ModelRouter, Role, create_provider
from aera.ai.base import AIProvider, CompletionRequest, ModelInfo, Usage
from aera.ai.providers.echo import EchoProvider
from aera.core.config import LocalModelSection, ModelsSection
from aera.core.errors import ProviderError, ProviderUnavailableError


class FailingProvider(AIProvider):
    """Always errors - used to exercise failover."""

    name = "failing"
    is_local = False

    async def complete(self, request):
        raise ProviderUnavailableError("always down")

    async def list_models(self):
        return []

    async def _probe(self):
        return True


class CountingProvider(AIProvider):
    """Records how many calls it served."""

    name = "counting"
    is_local = True

    def __init__(self, **options):
        super().__init__(**options)
        self.calls = 0

    async def complete(self, request):
        self.calls += 1
        return CompletionResponse(
            content="counted", model="counting-1", provider=self.name,
            usage=Usage(prompt_tokens=3, completion_tokens=2),
        )

    async def list_models(self):
        return [ModelInfo(id="counting-1", provider=self.name, local=True)]

    async def _probe(self):
        return True


@pytest.fixture
def offline_models():
    return ModelsSection(local=LocalModelSection(enabled=False))


class TestEchoProvider:
    async def test_answers_questions(self):
        provider = EchoProvider()
        response = await provider.complete(
            CompletionRequest(messages=[Message(role=Role.USER, content="what is docker?")])
        )
        assert response.content and response.provider == "builtin"

    async def test_greeting(self):
        provider = EchoProvider()
        response = await provider.complete(
            CompletionRequest(messages=[Message(role=Role.USER, content="hello")])
        )
        assert "AERA" in response.content

    async def test_uses_memory_context(self):
        provider = EchoProvider()
        response = await provider.complete(
            CompletionRequest(
                messages=[
                    Message(role=Role.SYSTEM, content="Relevant memories:\n- Docker: uses compose"),
                    Message(role=Role.USER, content="how do I deploy?"),
                ]
            )
        )
        assert "memory" in response.content.lower()

    async def test_streaming(self):
        provider = EchoProvider()
        tokens = [
            t async for t in provider.stream(
                CompletionRequest(messages=[Message(role=Role.USER, content="explain caching")])
            )
        ]
        assert len(tokens) > 1
        assert "".join(tokens).strip()

    async def test_usage_counted(self):
        provider = EchoProvider()
        response = await provider.complete(
            CompletionRequest(messages=[Message(role=Role.USER, content="a longer question here")])
        )
        assert response.usage.total_tokens > 0

    async def test_always_healthy(self):
        assert await EchoProvider().health_check() is True

    async def test_lists_models(self):
        models = await EchoProvider().list_models()
        assert models and models[0].local is True


class TestProviderRegistry:
    @pytest.mark.parametrize(
        "name", ["builtin", "ollama", "openai", "claude", "gemini", "lmstudio", "openrouter"]
    )
    def test_creates_known_providers(self, name):
        assert create_provider(name) is not None

    def test_unknown_provider_raises(self):
        with pytest.raises(KeyError):
            create_provider("not-a-provider")

    def test_aliases(self):
        assert create_provider("anthropic").name == "claude"
        assert create_provider("google").name == "gemini"

    async def test_cloud_providers_unavailable_without_keys(self):
        assert await create_provider("openai").health_check() is False
        assert await create_provider("claude").health_check() is False
        assert await create_provider("gemini").health_check() is False


class TestModelRouter:
    async def test_builtin_always_present(self, offline_models):
        router = ModelRouter(offline_models)
        assert "builtin" in router.providers
        await router.close()

    async def test_completes_offline(self, offline_models):
        router = ModelRouter(offline_models)
        response = await router.complete("hello there")
        assert response.provider == "builtin" and response.content
        await router.close()

    async def test_fails_over_to_healthy_provider(self, offline_models):
        router = ModelRouter(offline_models)
        counting = CountingProvider()
        router.register(FailingProvider())
        router.register(counting)
        router.config.default = "failing"

        response = await router.complete("test")
        assert response.provider in ("counting", "builtin")
        assert router.stats()["failing"]["failures"] == 1
        await router.close()

    async def test_all_providers_failing_raises(self, offline_models):
        router = ModelRouter(offline_models)
        router._providers.clear()
        router._stats.clear()
        router.register(FailingProvider())
        with pytest.raises(ProviderError):
            await router.complete("test")
        await router.close()

    async def test_local_first_prefers_local(self, offline_models):
        offline_models.routing_mode = "local_first"
        router = ModelRouter(offline_models)
        router.register(CountingProvider())      # local
        router.register(FailingProvider())       # cloud
        order = router._preference_order("default")
        assert order.index("counting") < order.index("failing")
        await router.close()

    async def test_cloud_first_prefers_cloud(self, offline_models):
        offline_models.routing_mode = "cloud_first"
        offline_models.default = "builtin"
        router = ModelRouter(offline_models)
        router.register(CountingProvider())
        router.register(FailingProvider())
        order = router._preference_order("default")
        assert order.index("failing") < order.index("counting")
        await router.close()

    async def test_offline_mode_excludes_cloud(self, offline_models):
        offline_models.routing_mode = "offline"
        router = ModelRouter(offline_models)
        router.register(CountingProvider())
        router.register(FailingProvider())
        order = router._preference_order("default")
        assert "failing" not in order[:-1] or order[-1] == "builtin"
        await router.close()

    async def test_task_specific_routing(self, offline_models):
        offline_models.coding = "counting"
        router = ModelRouter(offline_models)
        router.register(CountingProvider())
        assert router._preference_order("coding")[0] == "counting"
        await router.close()

    async def test_model_prefix_pins_provider(self, offline_models):
        router = ModelRouter(offline_models)
        counting = router.register(CountingProvider())
        selected = await router.select("default", model="counting/some-model")
        assert selected is counting
        await router.close()

    async def test_select_returns_builtin_when_nothing_healthy(self, offline_models):
        router = ModelRouter(offline_models)
        assert (await router.select()).name == "builtin"
        await router.close()

    async def test_streaming(self, offline_models):
        router = ModelRouter(offline_models)
        tokens = [t async for t in router.stream("explain events")]
        assert "".join(tokens).strip()
        await router.close()

    async def test_stats_tracked(self, offline_models):
        router = ModelRouter(offline_models)
        await router.complete("one")
        await router.complete("two")
        assert router.stats()["builtin"]["requests"] == 2
        assert router.stats()["builtin"]["tokens_out"] > 0
        await router.close()

    async def test_health_report(self, offline_models):
        router = ModelRouter(offline_models)
        health = await router.health()
        assert health["builtin"]["healthy"] is True
        await router.close()

    async def test_list_models(self, offline_models):
        router = ModelRouter(offline_models)
        assert await router.list_models()
        await router.close()

    async def test_system_prompt_prepended(self, offline_models):
        router = ModelRouter(offline_models)
        request = router._make_request(
            "user question", model=None, temperature=0.5, max_tokens=None, system="be terse"
        )
        assert request.messages[0].role == Role.SYSTEM
        assert request.messages[0].content == "be terse"
        await router.close()

    async def test_publishes_events(self, offline_models, bus):
        router = ModelRouter(offline_models, bus=bus)
        seen = []
        await bus.subscribe("ai.*", lambda e: seen.append(e.topic))
        await router.complete("hi")
        assert "ai.request" in seen and "ai.completed" in seen
        await router.close()
