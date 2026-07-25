"""Tests for the Plugin System (docs/17-PLUGIN-SYSTEM.md).

Covers: manifest validation, the documented lifecycle (install → validate →
permission check → load → initialize → running → unload → remove),
permission isolation, crash isolation, hot reload, and the event system.
"""

from pathlib import Path

import pytest

from src.events.bus import EventBus
from src.plugins.api import PluginAPI, PluginPermissionError
from src.plugins.manager import PluginError, PluginManager
from src.plugins.models import PluginPermission, PluginState
from src.security.audit import AuditLog

# ── Fixtures ─────────────────────────────────────────────────

GOOD_MANIFEST = """\
name: Test Plugin
version: 1.0.0
author: tester
type: custom-tool
permissions:
  - memory_graph
  - notifications
entry: src/main.py
"""

GOOD_ENTRY = """\
enabled = []

async def setup(api):
    enabled.append("yes")
    api.memory_store("test plugin loaded")

async def teardown(api):
    enabled.clear()
"""


def make_plugin(tmp_path: Path, manifest: str = GOOD_MANIFEST, entry: str = GOOD_ENTRY) -> Path:
    directory = tmp_path / "test-plugin"
    (directory / "src").mkdir(parents=True)
    (directory / "manifest.yaml").write_text(manifest)
    (directory / "src" / "main.py").write_text(entry)
    return directory


def make_manager(tmp_path: Path):
    from src.agents.manager import AgentManager
    from src.ai.router import ModelRouter
    from src.memory.graph import MemoryGraph

    memory = MemoryGraph(db_path=":memory:")
    bus = EventBus()
    return PluginManager(
        memory, AgentManager(memory, ModelRouter()), bus, AuditLog(), tmp_path
    ), memory, bus


# ── Validation ───────────────────────────────────────────────


def test_install_valid_plugin(tmp_path) -> None:
    manager, *_ = make_manager(tmp_path)
    plugin = manager.install(make_plugin(tmp_path))
    assert plugin.manifest.name == "Test Plugin"
    assert plugin.state == PluginState.INSTALLED


def test_invalid_manifest_rejected(tmp_path) -> None:
    manager, *_ = make_manager(tmp_path)
    with pytest.raises(PluginError, match="invalid manifest"):
        manager.install(make_plugin(tmp_path, manifest="name: [broken"))


def test_missing_entry_rejected(tmp_path) -> None:
    manager, *_ = make_manager(tmp_path)
    directory = make_plugin(tmp_path)
    (directory / "src" / "main.py").unlink()
    with pytest.raises(PluginError, match="entry file missing"):
        manager.install(directory)


def test_minimum_version_enforced(tmp_path) -> None:
    manager, *_ = make_manager(tmp_path)
    manifest = GOOD_MANIFEST.replace("version: 1.0.0", "version: 1.0.0\nminimumVersion: 99.0.0")
    with pytest.raises(PluginError, match="requires AERA"):
        manager.install(make_plugin(tmp_path, manifest=manifest))


# ── Lifecycle (docs/17) ─────────────────────────────────────


@pytest.mark.asyncio
async def test_full_lifecycle(tmp_path) -> None:
    manager, memory, _ = make_manager(tmp_path)
    manager.install(make_plugin(tmp_path))

    # Permission Check: enabling without approval fails
    with pytest.raises(PluginError, match="permissions not approved"):
        await manager.enable("Test Plugin")

    # Users approve permissions before activation
    manager.approve_permissions("Test Plugin")
    plugin = await manager.enable("Test Plugin")
    assert plugin.state == PluginState.ENABLED
    assert plugin.module.enabled == ["yes"]
    # setup() used the Memory Graph API
    assert memory.recall("test plugin loaded")

    # Unload
    plugin = await manager.disable("Test Plugin")
    assert plugin.state == PluginState.DISABLED
    # Remove
    await manager.remove("Test Plugin")
    assert manager.plugins == {}


@pytest.mark.asyncio
async def test_crash_isolation(tmp_path) -> None:
    """Docs/17: 'A faulty plugin cannot directly compromise the AERA Core.'"""
    manager, *_ = make_manager(tmp_path)
    manager.install(make_plugin(tmp_path, entry="def setup(api):\n    raise RuntimeError('boom')\n"))
    manager.approve_permissions("Test Plugin")
    plugin = await manager.enable("Test Plugin")  # must NOT raise
    assert plugin.state == PluginState.ERROR
    assert "boom" in plugin.error


@pytest.mark.asyncio
async def test_hot_reload_picks_up_changes(tmp_path) -> None:
    manager, memory, _ = make_manager(tmp_path)
    directory = make_plugin(tmp_path)
    manager.install(directory)
    manager.approve_permissions("Test Plugin")
    await manager.enable("Test Plugin")

    # Change the plugin source on disk, then hot-reload
    (directory / "src" / "main.py").write_text(
        GOOD_ENTRY.replace("test plugin loaded", "reloaded version active")
    )
    plugin = await manager.reload("Test Plugin")
    assert plugin.state == PluginState.ENABLED
    assert memory.recall("reloaded version active")


# ── Permission isolation ─────────────────────────────────────


@pytest.mark.asyncio
async def test_plugin_api_permission_isolation(tmp_path) -> None:
    """API calls without the matching approved permission must fail."""
    from src.agents.manager import AgentManager
    from src.ai.router import ModelRouter
    from src.memory.graph import MemoryGraph

    memory = MemoryGraph(db_path=":memory:")
    api = PluginAPI(
        "isolated",
        {PluginPermission.NOTIFICATIONS},  # no memory_graph!
        memory,
        AgentManager(memory, ModelRouter()),
        EventBus(),
    )
    with pytest.raises(PluginPermissionError, match="memory_graph"):
        api.memory_store("should fail")
    with pytest.raises(PluginPermissionError, match="local_ai"):
        await api.ask_agent("hi")


def test_partial_approval_limits_grants(tmp_path) -> None:
    manager, *_ = make_manager(tmp_path)
    manager.install(make_plugin(tmp_path))
    plugin = manager.approve_permissions(
        "Test Plugin", [PluginPermission.NOTIFICATIONS]
    )
    assert plugin.approved == {PluginPermission.NOTIFICATIONS}
    # Cannot approve permissions the manifest never requested
    plugin = manager.approve_permissions("Test Plugin", [PluginPermission.CAMERA])
    assert plugin.approved == set()


# ── Event system ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_plugin_receives_events_and_unsubscribes_on_disable(tmp_path) -> None:
    manager, memory, bus = make_manager(tmp_path)
    entry = """\
async def setup(api):
    async def handler(event):
        api.memory_store("saw event " + event.topic)
    api.on_event("workspace.*", handler)
"""
    manager.install(make_plugin(tmp_path, entry=entry))
    manager.approve_permissions("Test Plugin")
    await manager.enable("Test Plugin")

    await bus.publish("workspace.project.opened", {})
    assert memory.recall("saw event workspace.project.opened")

    # After disable, subscriptions are torn down (lifecycle isolation)
    await manager.disable("Test Plugin")
    before = len(memory.recall("saw event", limit=50))
    await bus.publish("workspace.file.saved", {})
    after = len(memory.recall("saw event", limit=50))
    assert after == before  # no new event notes recorded after disable


# ── API + bundled example plugin ─────────────────────────────


def test_plugins_api_discover_and_lifecycle(client) -> None:
    """The bundled memory-notes plugin works through the REST API."""
    res = client.post("/api/plugins/discover")
    assert res.status_code == 200
    assert "memory-notes" in res.json()["installed"]

    plugins = client.get("/api/plugins").json()
    names = {p["name"] for p in plugins}
    assert "Memory Notes" in names

    # Approve + enable
    client.post("/api/plugins/Memory Notes/approve", json={})
    res = client.post("/api/plugins/Memory Notes/enable")
    assert res.status_code == 200
    assert res.json()["state"] == "enabled"

    # The example plugin noted its own activation into memory
    recall = client.get("/api/memory/recall", params={"q": "memory-notes plugin enabled"}).json()
    assert len(recall) >= 1

    # Documented integration: it records automation runs
    wf = client.post(
        "/api/automation/workflows",
        json={
            "name": "plugin-observed",
            "actions": [{"type": "notify", "params": {"message": "hi"}}],
        },
    ).json()
    client.post(f"/api/automation/workflows/{wf['id']}/run")
    recall = client.get("/api/memory/recall", params={"q": "noted automation run plugin-observed"}).json()
    assert len(recall) >= 1

    assert client.post("/api/plugins/Memory Notes/disable").json()["state"] == "disabled"


def test_plugins_api_404(client) -> None:
    assert client.get("/api/plugins/nope").status_code == 404
    assert client.post("/api/plugins/nope/enable").status_code == 404
