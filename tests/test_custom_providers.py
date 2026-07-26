# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Voice Reasoning Assistant

"""Runtime AI provider registration.

Providers could previously only come from config/models.yaml, so pointing
AERA at your own model server meant editing a file and restarting. These
cover the runtime path, exercised against a real HTTP server rather than a
mock, so the adapter's request and response handling is genuinely tested.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

from aera.ai.providers import PROVIDER_REGISTRY, create_provider
from aera.api.app import create_app

REPLY = "Reply from the user's own model."


class _FakeModelServer(BaseHTTPRequestHandler):
    """A minimal OpenAI-compatible endpoint."""

    def log_message(self, *args):  # noqa: A003 - silence the default logger
        pass

    def _send(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        if "models" in self.path:
            self._send({"data": [{"id": "my-llama-3"}, {"id": "my-mistral"}]})
        else:
            self._send({"ok": True})

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self._send(
            {
                "id": "cmpl-1",
                "model": "my-llama-3",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": REPLY},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
            }
        )


@pytest.fixture
def model_server():
    """A live OpenAI-compatible server on a free port."""
    server = HTTPServer(("127.0.0.1", 0), _FakeModelServer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


@pytest.fixture
def client(config):
    with TestClient(create_app(config)) as c:
        yield c


class TestCustomAdapter:
    def test_custom_is_registered_as_a_type(self):
        assert "custom" in PROVIDER_REGISTRY

    def test_keeps_the_user_supplied_name(self):
        """Several custom providers can coexist, so each needs its own name."""
        provider = create_provider("custom", label="My vLLM", base_url="http://x/v1")

        assert provider.name == "my-vllm"

    def test_detects_a_local_endpoint(self):
        """A localhost model must not be treated as a cloud fallback."""
        local = create_provider("custom", label="a", base_url="http://localhost:8000/v1")
        cloud = create_provider("custom", label="b", base_url="https://ai.corp.com/v1")

        assert local.is_local is True
        assert cloud.is_local is False

    def test_unknown_type_lists_the_alternatives(self):
        with pytest.raises(KeyError, match="unknown AI provider"):
            create_provider("definitely-not-real")


class TestProviderApi:
    def test_lists_available_types(self, client):
        data = client.get("/api/v1/models/providers/types").json()["data"]

        assert "custom" in data["types"]
        assert "openai" in data["types"]

    def test_add_test_and_generate(self, client, model_server):
        """The whole point: register your own model and get text out of it."""
        added = client.post(
            "/api/v1/models/providers",
            json={
                "name": "my-server",
                "type": "custom",
                "base_url": model_server,
                "model": "my-llama-3",
                "api_key": "none",
            },
        )
        assert added.status_code == 200
        assert added.json()["data"]["healthy"] is True

        probe = client.post("/api/v1/models/providers/my-server/test").json()["data"]
        assert probe["models"] == ["my-llama-3", "my-mistral"]

        generated = client.post(
            "/api/v1/models/generate",
            json={"prompt": "hello", "model": "my-server:my-llama-3"},
        ).json()["data"]
        assert generated["provider"] == "my-server"
        assert generated["content"] == REPLY

    def test_appears_in_the_model_list(self, client, model_server):
        client.post(
            "/api/v1/models/providers",
            json={"name": "my-server", "type": "custom", "base_url": model_server},
        )

        assert "my-server" in client.get("/api/v1/models").json()["data"]["providers"]

    def test_unreachable_endpoints_are_registered_but_flagged(self, client):
        """The server may simply not be running yet; do not refuse outright."""
        response = client.post(
            "/api/v1/models/providers",
            json={
                "name": "not-up",
                "type": "custom",
                "base_url": "http://127.0.0.1:9/v1",
            },
        )

        data = response.json()["data"]
        assert response.status_code == 200
        assert data["healthy"] is False
        assert data["warning"]

    def test_duplicate_names_are_refused(self, client, model_server):
        body = {"name": "dupe", "type": "custom", "base_url": model_server}
        client.post("/api/v1/models/providers", json=body)

        response = client.post("/api/v1/models/providers", json=body)

        assert response.status_code == 400
        assert "already exists" in response.json()["error"]

    def test_replace_overwrites(self, client, model_server):
        body = {"name": "dupe", "type": "custom", "base_url": model_server}
        client.post("/api/v1/models/providers", json=body)

        response = client.post(
            "/api/v1/models/providers", json={**body, "replace": True}
        )

        assert response.status_code == 200

    def test_builtin_is_protected(self, client):
        """The offline fallback must always exist or a failure has nowhere to land."""
        response = client.post(
            "/api/v1/models/providers", json={"name": "builtin", "type": "custom"}
        )

        assert response.status_code == 400
        assert "reserved" in response.json()["error"]

    def test_builtin_cannot_be_removed(self, client):
        response = client.delete("/api/v1/models/providers/builtin")

        assert response.status_code == 400
        assert "cannot be removed" in response.json()["error"]

    def test_unknown_type_is_rejected_with_options(self, client):
        response = client.post(
            "/api/v1/models/providers", json={"name": "x", "type": "nope"}
        )

        assert response.status_code == 400
        assert "available" in response.json()["details"]

    def test_remove(self, client, model_server):
        client.post(
            "/api/v1/models/providers",
            json={"name": "temp", "type": "custom", "base_url": model_server},
        )

        assert client.delete("/api/v1/models/providers/temp").status_code == 200
        # Gone means gone: a later probe must 404, not silently succeed.
        assert client.post("/api/v1/models/providers/temp/test").status_code == 404

    def test_removing_something_absent_is_a_404(self, client):
        assert client.delete("/api/v1/models/providers/ghost").status_code == 404

    def test_testing_something_absent_is_a_404(self, client):
        assert client.post("/api/v1/models/providers/ghost/test").status_code == 404
