# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""REST API and WebSocket integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aera.api.app import create_app


@pytest.fixture
def client(config):
    with TestClient(create_app(config)) as c:
        yield c


class TestHealthAndSystem:
    def test_health(self, client):
        body = client.get("/health").json()
        assert body["status"] == "healthy" and body["ready"] is True

    def test_status(self, client):
        data = client.get("/api/v1/system/status").json()["data"]
        assert data["ready"] is True and data["agents"]["total"] > 0

    def test_info(self, client):
        data = client.get("/api/v1/system/info").json()["data"]
        assert data["name"] == "AERA" and data["version"]

    def test_settings_exclude_secrets(self, client):
        body = client.get("/api/v1/system/settings").text
        assert "api_key" not in body and "jwt_secret" not in body

    def test_secrets_are_masked(self, client):
        data = client.get("/api/v1/system/secrets").json()["data"]
        assert isinstance(data["secrets"], dict)

    def test_events(self, client):
        data = client.get("/api/v1/system/events").json()["data"]
        assert isinstance(data["events"], list)

    def test_dashboard_served(self, client):
        res = client.get("/")
        assert res.status_code == 200 and "AERA" in res.text

    def test_openapi(self, client):
        schema = client.get("/openapi.json").json()
        assert "/api/v1/chat" in schema["paths"]


class TestEnvelope:
    def test_success_shape(self, client):
        body = client.get("/api/v1/system/status").json()
        assert set(body) >= {"success", "message", "data"} and body["success"] is True

    def test_404_shape(self, client):
        body = client.get("/api/v1/memory/does-not-exist").json()
        assert body["success"] is False and body["code"] == 404

    def test_validation_error(self, client):
        body = client.post("/api/v1/chat", json={}).json()
        assert body["success"] is False and body["code"] == 400

    def test_empty_message_rejected(self, client):
        assert client.post("/api/v1/chat", json={"message": ""}).status_code == 400

    def test_request_id_header(self, client):
        assert client.get("/health").headers.get("X-Request-ID")

    def test_response_time_header(self, client):
        assert client.get("/health").headers.get("X-Response-Time")


class TestChat:
    def test_chat(self, client):
        data = client.post("/api/v1/chat", json={"message": "hello there"}).json()["data"]
        assert data["success"] is True and data["output"]
        assert data["conversation_id"]

    def test_routes_to_specialist(self, client):
        data = client.post(
            "/api/v1/chat", json={"message": "write a python function to sort a list"}
        ).json()["data"]
        assert data["agent"] == "coding"

    def test_conversation_continuity(self, client):
        first = client.post("/api/v1/chat", json={"message": "remember: I use dark mode"}).json()["data"]
        cid = first["conversation_id"]
        second = client.post(
            "/api/v1/chat", json={"message": "what did I say?", "conversation_id": cid}
        ).json()["data"]
        assert second["conversation_id"] == cid
        history = client.get(f"/api/v1/memory/history?conversation_id={cid}").json()["data"]
        assert history["count"] >= 4

    def test_forced_agent(self, client):
        data = client.post(
            "/api/v1/chat", json={"message": "anything", "agent": "reasoning"}
        ).json()["data"]
        assert data["data"]["routed_to"] == "reasoning"

    def test_streaming(self, client):
        with client.stream(
            "POST", "/api/v1/chat", json={"message": "explain caching", "stream": True}
        ) as res:
            assert res.status_code == 200
            body = "".join(res.iter_text())
        assert "data:" in body and '"type": "done"' in body

    def test_generate(self, client):
        data = client.post("/api/v1/models/generate", json={"prompt": "hello"}).json()["data"]
        assert data["content"] and data["provider"]

    def test_list_models(self, client):
        data = client.get("/api/v1/models").json()["data"]
        assert data["count"] >= 1

    def test_provider_health(self, client):
        assert "builtin" in client.get("/api/v1/models/health").json()["data"]


class TestAgentsApi:
    def test_list(self, client):
        data = client.get("/api/v1/agents").json()["data"]
        assert data["summary"]["total"] > 0 and "coding" in data["capabilities"]["coding"]

    def test_get_one(self, client):
        assert client.get("/api/v1/agents/coding").json()["data"]["name"] == "coding"

    def test_get_missing(self, client):
        assert client.get("/api/v1/agents/ghost").status_code == 404

    def test_stop_start_restart(self, client):
        assert client.post("/api/v1/agents/stop", json={"agent": "coding"}).json()["data"]["status"] == "stopped"
        assert client.post("/api/v1/agents/start", json={"agent": "coding"}).json()["data"]["status"] == "running"
        assert client.post("/api/v1/agents/restart", json={"agent": "coding"}).status_code == 200

    def test_task_dispatch(self, client):
        data = client.post(
            "/api/v1/agents/task",
            json={"capability": "planning", "input": "plan a release"},
        ).json()["data"]
        assert data["success"] and data["agent"] == "planning"

    def test_bad_capability(self, client):
        assert client.post(
            "/api/v1/agents/task", json={"capability": "nonsense", "input": "x"}
        ).status_code == 400

    def test_history(self, client):
        client.post("/api/v1/chat", json={"message": "hi"})
        assert isinstance(client.get("/api/v1/agents/history").json()["data"]["history"], list)


class TestMemoryApi:
    def test_store_and_get(self, client):
        stored = client.post(
            "/api/v1/memory",
            json={"title": "Test memory", "content": "some content", "tags": ["t"]},
        ).json()["data"]
        fetched = client.get(f"/api/v1/memory/{stored['id']}").json()["data"]
        assert fetched["node"]["title"] == "Test memory"

    def test_search(self, client):
        client.post("/api/v1/memory", json={"title": "Kubernetes", "content": "container orchestration"})
        data = client.post("/api/v1/memory/search", json={"query": "containers"}).json()["data"]
        assert data["count"] >= 1

    def test_search_get(self, client):
        client.post("/api/v1/memory", json={"title": "Redis", "content": "cache layer"})
        assert client.get("/api/v1/memory/search?q=cache").json()["data"]["count"] >= 1

    def test_list_and_filter(self, client):
        client.post("/api/v1/memory", json={"title": "Tagged", "content": "x", "tags": ["special"]})
        assert client.get("/api/v1/memory?tag=special").json()["data"]["count"] == 1

    def test_update(self, client):
        node = client.post("/api/v1/memory", json={"title": "Before", "content": "x"}).json()["data"]
        updated = client.patch(
            f"/api/v1/memory/{node['id']}", json={"title": "After", "importance": 0.9}
        ).json()["data"]
        assert updated["title"] == "After" and updated["importance"] == 0.9

    def test_delete(self, client):
        node = client.post("/api/v1/memory", json={"title": "Doomed", "content": "x"}).json()["data"]
        assert client.delete(f"/api/v1/memory/{node['id']}").status_code == 200
        assert client.get(f"/api/v1/memory/{node['id']}").status_code == 404

    def test_connect_and_graph(self, client):
        a = client.post("/api/v1/memory", json={"title": "A", "content": "a"}).json()["data"]
        b = client.post("/api/v1/memory", json={"title": "B", "content": "b"}).json()["data"]
        client.post("/api/v1/memory/connect", json={"source": a["id"], "target": b["id"]})
        graph = client.post(f"/api/v1/memory/graph?node_id={a['id']}").json()["data"]
        assert len(graph["nodes"]) >= 2 and len(graph["edges"]) >= 1

    def test_stats(self, client):
        assert "nodes" in client.get("/api/v1/memory/stats").json()["data"]

    def test_consolidate(self, client):
        data = client.post("/api/v1/memory/consolidate").json()["data"]
        assert "promoted" in data and "pruned" in data

    def test_invalid_importance_rejected(self, client):
        assert client.post(
            "/api/v1/memory", json={"title": "x", "importance": 5.0}
        ).status_code == 400


class TestWorkspaceApi:
    def test_empty_state(self, client):
        assert client.get("/api/v1/workspace").json()["data"]["active"] == {}

    def test_open_and_search(self, client, tmp_path):
        (tmp_path / "main.py").write_text("def hello():\n    return 1\n")
        (tmp_path / "util.py").write_text("class Helper:\n    pass\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")

        opened = client.post(
            "/api/v1/workspace/open", json={"path": str(tmp_path), "index": True}
        ).json()["data"]
        assert opened["files"] == 3 and "python" in opened["kinds"]

        found = client.get("/api/v1/workspace/search?q=hello").json()["data"]
        assert any("main.py" in r["path"] for r in found["results"])

    def test_open_missing_path(self, client):
        assert client.post(
            "/api/v1/workspace/open", json={"path": "/no/such/dir"}
        ).status_code == 404

    def test_read_file(self, client, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        client.post("/api/v1/workspace/open", json={"path": str(tmp_path)})
        assert "x = 1" in client.get("/api/v1/workspace/file?path=a.py").json()["data"]["content"]

    def test_path_traversal_blocked(self, client, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        client.post("/api/v1/workspace/open", json={"path": str(tmp_path)})
        assert client.get("/api/v1/workspace/file?path=../../etc/passwd").status_code == 403

    def test_tree(self, client, tmp_path):
        (tmp_path / "a.py").write_text("x=1")
        client.post("/api/v1/workspace/open", json={"path": str(tmp_path)})
        assert "a.py" in client.get("/api/v1/workspace/tree").json()["data"]["files"]


class TestVoiceAndAvatar:
    def test_voice_status(self, client):
        assert client.get("/api/v1/voice/status").json()["data"]["enabled"] is True

    def test_speak(self, client):
        data = client.post("/api/v1/voice/speak", json={"text": "Great news, it works!"}).json()["data"]
        assert data["duration_ms"] > 0 and data["emotion"] in ("happy", "excited", "neutral")

    def test_speak_empty_rejected(self, client):
        assert client.post("/api/v1/voice/speak", json={"text": ""}).status_code == 400

    def test_listen(self, client):
        data = client.post("/api/v1/voice/listen", json={"text": "AERA open the project"}).json()["data"]
        assert data["text"] == "AERA open the project" and data["wake_word_detected"] is True

    def test_emotion_analysis(self, client):
        data = client.post("/api/v1/voice/emotion", json={"text": "critical security failure"}).json()["data"]
        assert data["emotion"] == "serious"

    def test_avatar_lifecycle(self, client):
        assert client.post("/api/v1/avatar/show").json()["data"]["visible"] is True
        emotion = client.post(
            "/api/v1/avatar/emotion", json={"emotion": "happy", "intensity": 0.9}
        ).json()["data"]
        assert emotion["emotion"] == "happy" and emotion["blendshapes"]
        assert client.post("/api/v1/avatar/gesture", json={"gesture": "wave"}).json()["data"]["gesture"] == "wave"
        assert client.post("/api/v1/avatar/hide").json()["data"]["visible"] is False

    def test_avatar_bad_emotion(self, client):
        assert client.post("/api/v1/avatar/emotion", json={"emotion": "banana"}).status_code == 500


class TestAutomationApi:
    def test_create_and_run(self, client):
        created = client.post(
            "/api/v1/automation/create",
            json={
                "name": "greet",
                "actions": [
                    {"type": "set_variable", "params": {"who": "world"}},
                    {"type": "log", "params": {"message": "hello {{ who }}"}, "store_as": "msg"},
                ],
            },
        ).json()["data"]

        run = client.post(f"/api/v1/automation/run?workflow_id={created['id']}").json()["data"]
        assert run["status"] == "success"
        assert run["variables"]["msg"] == "hello world"

    def test_list(self, client):
        client.post("/api/v1/automation/create", json={"name": "wf", "actions": []})
        assert client.get("/api/v1/automation").json()["data"]["count"] >= 1

    def test_runs_history(self, client):
        created = client.post("/api/v1/automation/create", json={"name": "h", "actions": []}).json()["data"]
        client.post(f"/api/v1/automation/run?workflow_id={created['id']}")
        assert len(client.get("/api/v1/automation/runs").json()["data"]["runs"]) >= 1

    def test_invalid_definition(self, client):
        assert client.post(
            "/api/v1/automation/create",
            json={"name": "bad", "actions": [{"type": "not_a_real_action"}]},
        ).status_code == 400

    def test_missing_workflow(self, client):
        assert client.post("/api/v1/automation/run?workflow_id=ghost").status_code == 400

    def test_disable(self, client):
        created = client.post("/api/v1/automation/create", json={"name": "d", "actions": []}).json()["data"]
        assert client.post(f"/api/v1/automation/stop?workflow_id={created['id']}").json()["data"]["enabled"] is False


class TestWebSocket:
    def test_connect_and_ping(self, client):
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "connected"
            ws.send_json({"type": "ping", "timestamp": 123})
            assert ws.receive_json()["type"] == "pong"

    def test_streaming_chat(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"type": "chat", "content": "hello"})
            types, tokens = [], []
            for _ in range(60):
                msg = ws.receive_json()
                if msg["type"] == "event":
                    continue
                types.append(msg["type"])
                if msg["type"] == "stream.token":
                    tokens.append(msg["content"])
                if msg["type"] == "stream.done":
                    break
            assert "stream.start" in types and "stream.done" in types and tokens

    def test_memory_query(self, client):
        client.post("/api/v1/memory", json={"title": "WSTest", "content": "websocket memory"})
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"type": "memory", "query": "websocket"})
            for _ in range(20):
                msg = ws.receive_json()
                if msg["type"] == "memory.results":
                    assert isinstance(msg["results"], list)
                    return
            pytest.fail("no memory.results received")

    def test_unknown_type(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"type": "nonsense"})
            for _ in range(20):
                msg = ws.receive_json()
                if msg["type"] == "error":
                    return
            pytest.fail("no error received")


class TestAuthAndRateLimit:
    def test_auth_blocks_without_key(self, config):
        config.api.auth_enabled = True
        config.api.api_keys = ["secret-key"]
        with TestClient(create_app(config)) as c:
            assert c.get("/health").status_code == 200          # public
            assert c.get("/api/v1/system/status").status_code == 401

    def test_auth_allows_valid_key(self, config):
        config.api.auth_enabled = True
        config.api.api_keys = ["secret-key"]
        with TestClient(create_app(config)) as c:
            res = c.get("/api/v1/system/status", headers={"Authorization": "Bearer secret-key"})
            assert res.status_code == 200

    def test_auth_accepts_api_key_header(self, config):
        config.api.auth_enabled = True
        config.api.api_keys = ["secret-key"]
        with TestClient(create_app(config)) as c:
            assert c.get("/api/v1/system/status", headers={"X-API-Key": "secret-key"}).status_code == 200

    def test_rate_limit(self, config):
        config.api.rate_limit_per_minute = 3
        with TestClient(create_app(config)) as c:
            codes = [c.get("/api/v1/system/status").status_code for _ in range(5)]
            assert 429 in codes
            assert codes.count(200) == 3


class TestDockerApi:
    """Docker is absent in CI, which is the case that matters most here:
    the connector must say so rather than pretend the host has no containers.
    """

    def test_status_succeeds_without_a_daemon(self, client):
        # The page calls this first to decide what to render, so an absent
        # daemon has to be a 200 with a reason, not an error.
        data = client.get("/api/v1/docker/status").json()["data"]
        assert data["available"] is False
        assert data["reason"], "an unavailable daemon must explain why"

    def test_status_reports_the_control_gate(self, client):
        data = client.get("/api/v1/docker/status").json()["data"]
        assert data["control_enabled"] is False, "control must default to off"

    @pytest.mark.parametrize(
        "path",
        ["/api/v1/docker/containers", "/api/v1/docker/images", "/api/v1/docker/info"],
    )
    def test_reads_fail_cleanly_without_a_daemon(self, client, path):
        response = client.get(path)
        assert response.status_code == 503
        body = response.json()
        assert body["success"] is False
        assert body["type"] == "docker_unavailable"

    def test_control_is_refused_before_the_daemon_is_even_reached(self, client):
        """Permission is checked first, so the answer is 403 rather than 503."""
        response = client.post("/api/v1/docker/containers/anything/stop")
        assert response.status_code == 403
        assert response.json()["type"] == "docker_control_denied"

    def test_the_kernel_exposes_a_docker_client(self, client):
        from aera.services.docker import DockerClient

        kernel = client.app.state.kernel
        assert isinstance(kernel.docker, DockerClient)
        assert kernel.docker.allow_control is False


class TestDocumentedSurface:
    """The README quotes an operation count; it had already drifted once."""

    def test_readme_operation_count_is_accurate(self):
        import re
        from pathlib import Path

        from aera.api.app import create_app

        schema = create_app().openapi()
        actual = sum(
            1
            for item in schema["paths"].values()
            for method in item
            if method in ("get", "post", "put", "patch", "delete")
        )

        readme = (Path(__file__).resolve().parent.parent / "README.md").read_text()
        claimed = {int(n) for n in re.findall(r"(\d+) REST operations", readme)}
        claimed |= {int(n) for n in re.findall(r"REST API \((\d+) operations\)", readme)}

        assert claimed, "the README no longer states an operation count"
        assert claimed == {actual}, (
            f"README claims {sorted(claimed)} REST operations but the app exposes {actual}"
        )
