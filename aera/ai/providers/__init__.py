"""Provider registry.

Maps the provider names used in ``config/models.yaml`` to adapter classes.
"""

from __future__ import annotations

from ..base import AIProvider
from .anthropic import AnthropicProvider
from .echo import EchoProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .openai import LMStudioProvider, OpenAIProvider, OpenRouterProvider

PROVIDER_REGISTRY: dict[str, type[AIProvider]] = {
    "builtin": EchoProvider,
    "echo": EchoProvider,
    "local": OllamaProvider,
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "lmstudio": LMStudioProvider,
    "openrouter": OpenRouterProvider,
    "claude": AnthropicProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "google": GeminiProvider,
}


def create_provider(name: str, **options) -> AIProvider:
    """Instantiate a provider adapter by name."""
    key = name.strip().lower()
    cls = PROVIDER_REGISTRY.get(key)
    if cls is None:
        raise KeyError(
            f"unknown AI provider '{name}'. Available: {', '.join(sorted(PROVIDER_REGISTRY))}"
        )
    return cls(**options)


__all__ = [
    "AnthropicProvider",
    "EchoProvider",
    "GeminiProvider",
    "LMStudioProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "OpenRouterProvider",
    "PROVIDER_REGISTRY",
    "create_provider",
]
