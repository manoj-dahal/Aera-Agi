"""Tests for the Agent Manager routing and chat pipeline (docs/07-AGENTS.md)."""

from services.agents.manager import AgentManager
from services.ai.router import ModelRouter
from services.memory.graph import MemoryGraph


def make_manager() -> AgentManager:
    return AgentManager(MemoryGraph(db_path=":memory:"), ModelRouter())


# ── Routing ──────────────────────────────────────────────────


def test_routes_to_coding_agent() -> None:
    m = make_manager()
    assert m.route("fix this bug in my function").name == "coding"


def test_routes_to_planning_agent() -> None:
    m = make_manager()
    assert m.route("make a plan and roadmap for the release").name == "planning"


def test_defaults_to_core_agent() -> None:
    m = make_manager()
    assert m.route("hello there!").name == "core"


# ── API ──────────────────────────────────────────────────────


def test_list_agents(client) -> None:
    res = client.get("/api/agents")
    assert res.status_code == 200
    names = {a["name"] for a in res.json()}
    assert {"core", "coding", "research", "writing", "planning", "memory"} <= names


def test_chat_offline_echo(client) -> None:
    """With no local/cloud AI, the echo provider must still answer."""
    res = client.post("/api/chat", json={"message": "remember that I like tea"})
    assert res.status_code == 200
    body = res.json()
    assert body["agent"] == "memory"
    assert body["model"] == "echo"
    assert body["response"]


def test_chat_stores_conversation_in_memory(client) -> None:
    client.post("/api/chat", json={"message": "my favourite editor is vim"})
    res = client.get("/api/memory/recall", params={"q": "favourite editor vim"})
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_chat_explicit_agent(client) -> None:
    res = client.post("/api/chat", json={"message": "hi", "agent": "writing"})
    assert res.status_code == 200
    assert res.json()["agent"] == "writing"


def test_models_endpoint(client) -> None:
    res = client.get("/api/models")
    assert res.status_code == 200
    providers = {m["provider"] for m in res.json()}
    assert "echo" in providers


def test_websocket_chat(client) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.send_text("hello aera")
        data = ws.receive_json()
        assert data["agent"] == "core"
        assert data["response"]
