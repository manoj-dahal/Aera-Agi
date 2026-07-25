"""Tests for the Event Bus and Background Service Manager (docs/24)."""

import asyncio

import pytest

from src.events.bus import EventBus
from src.services.manager import ServiceManager, ServiceState

# ── Event Bus ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_subscribe() -> None:
    bus = EventBus()
    received = []
    bus.subscribe("memory.*", lambda e: received.append(e.topic))
    await bus.publish("memory.stats", {"nodes": 1})
    await bus.publish("voice.emotion.changed", {})
    assert received == ["memory.stats"]


@pytest.mark.asyncio
async def test_wildcard_and_history() -> None:
    bus = EventBus()
    await bus.publish("a.one")
    await bus.publish("b.two")
    assert len(bus.history("*")) == 2
    assert [e.topic for e in bus.history("a.*")] == ["a.one"]


@pytest.mark.asyncio
async def test_failing_handler_does_not_break_bus() -> None:
    bus = EventBus()
    ok = []

    def bad(_e):
        raise RuntimeError("boom")

    bus.subscribe("*", bad)
    bus.subscribe("*", lambda e: ok.append(e.topic))
    await bus.publish("x")
    assert ok == ["x"]


# ── Service Manager (docs/24: self-healing, lifecycle) ──────


@pytest.mark.asyncio
async def test_service_lifecycle() -> None:
    bus = EventBus()
    manager = ServiceManager(bus)
    ticks = []

    async def tick() -> None:
        ticks.append(1)

    manager.register("test-service", tick, interval=0.01)
    await manager.start("test-service")
    await asyncio.sleep(0.05)
    assert manager.services["test-service"].state == ServiceState.RUNNING
    assert len(ticks) >= 2  # scheduled repeatedly

    await manager.stop("test-service")
    assert manager.services["test-service"].state == ServiceState.STOPPED


@pytest.mark.asyncio
async def test_service_self_healing_then_failed() -> None:
    """Docs/24: restart failed services, up to a limit."""
    manager = ServiceManager(EventBus())

    async def always_fails() -> None:
        raise RuntimeError("crash")

    svc = manager.register("crashy", always_fails, interval=0.005)
    svc.max_restarts = 2
    await manager.start("crashy")
    await asyncio.sleep(0.1)
    assert svc.state == ServiceState.FAILED
    assert svc.restarts == 3  # exceeded max → gave up


def test_services_api(client) -> None:
    res = client.get("/api/services")
    assert res.status_code == 200
    names = {s["name"] for s in res.json()}
    # Documented core services (docs/24): Memory Service, Local LLM Monitor
    assert {"memory-service", "local-llm-monitor"} <= names
    for s in res.json():
        assert s["state"] == "running"


def test_service_restart_api(client) -> None:
    res = client.post("/api/services/memory-service/restart")
    assert res.status_code == 202
    assert res.json()["state"] == "running"
    assert client.post("/api/services/nope/restart").status_code == 404
