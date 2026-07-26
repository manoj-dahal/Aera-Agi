"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from aera.agents import AgentContext, build_default_registry
from aera.ai.router import ModelRouter
from aera.core.config import AeraConfig, LocalModelSection, ModelsSection
from aera.core.events import EventBus
from aera.core.kernel import Kernel
from aera.memory.engine import MemoryEngine


@pytest.fixture
def config(tmp_path) -> AeraConfig:
    """An isolated config that never touches the real filesystem state."""
    cfg = AeraConfig()
    cfg.system.storage = str(tmp_path / "storage")
    cfg.system.logs = str(tmp_path / "logs")
    cfg.system.cache = str(tmp_path / "cache")
    cfg.system.temp = str(tmp_path / "temp")
    cfg.security.secret_key_file = str(tmp_path / "storage" / ".secret.key")
    cfg.logging.level = "WARNING"
    cfg.logging.file = None
    # No local runtime in CI: rely on the always-available built-in provider.
    cfg.models = ModelsSection(local=LocalModelSection(enabled=False))
    return cfg


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def memory(config, bus) -> MemoryEngine:
    return MemoryEngine(config.memory, bus=bus)


@pytest.fixture
def router(config, bus) -> ModelRouter:
    return ModelRouter(config.models, bus=bus)


@pytest.fixture
def agent_context(memory, router, bus, config) -> AgentContext:
    return AgentContext(memory=memory, router=router, bus=bus, config=config)


@pytest.fixture
def registry(agent_context, config):
    return build_default_registry(agent_context, config.agents)


@pytest.fixture
async def kernel(config):
    k = Kernel(config)
    await k.start()
    try:
        yield k
    finally:
        await k.stop()


@pytest.fixture
def stt_factory():
    """Build a fake STT backend that records what it was handed.

    The real backends (Whisper and friends) are not bundled, so agent-level
    transcription is covered with a stand-in that satisfies the STTBackend
    contract. Pass an exception to simulate a backend that fails.
    """
    from aera.voice.engine import STTBackend, Transcript

    def make(result):
        class FakeSTT(STTBackend):
            name = "fake-stt"

            def __init__(self) -> None:
                self.received: bytes | None = None
                self.language: str | None = None

            async def transcribe(self, audio: bytes, *, language: str = "en") -> Transcript:
                self.received = audio
                self.language = language
                if isinstance(result, Exception):
                    raise result
                return Transcript(
                    text=result,
                    confidence=0.97,
                    language=language,
                    duration_ms=1200.0,
                )

        return FakeSTT()

    return make
