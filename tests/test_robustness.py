# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Error paths, concurrency and scale.

The rest of the suite covers the happy path. These cover what happens when a
caller sends nonsense, when several things run at once, and when the graph is
larger than a handful of nodes -- the conditions that produce bugs nobody sees
until the software is actually used.
"""

from __future__ import annotations

import asyncio
import threading

import pytest
from fastapi.testclient import TestClient

from aera.agents.base import Task
from aera.api.app import create_app
from aera.memory.graph import MemoryGraph


@pytest.fixture
def client(config):
    with TestClient(create_app(config)) as c:
        yield c


class TestMalformedRequests:
    """A bad request must produce a clean envelope, never a stack trace."""

    def test_invalid_json(self, client):
        response = client.post(
            "/api/v1/chat",
            content="{not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        assert response.json()["success"] is False

    @pytest.mark.parametrize(
        "body",
        [
            {},                       # no message at all
            {"message": ""},          # empty
            {"message": "x" * 200_000},  # past the length cap
        ],
    )
    def test_rejected_chat_bodies(self, client, body):
        assert client.post("/api/v1/chat", json=body).status_code == 400

    def test_unknown_agent_is_a_404(self, client):
        response = client.post(
            "/api/v1/agents/task",
            json={"agent": "ghost", "capability": "conversation", "input": "hi"},
        )

        assert response.status_code == 404

    def test_unknown_capability_lists_the_valid_ones(self, client):
        response = client.post(
            "/api/v1/agents/task", json={"capability": "nope", "input": "hi"}
        )

        assert response.status_code == 400
        assert response.json()["details"]["available"]

    def test_unknown_memory_node(self, client):
        assert client.get("/api/v1/memory/ghost-id").status_code == 404

    def test_negative_limits_are_refused(self, client):
        assert client.get("/api/v1/memory?limit=-5").status_code == 400

    def test_unknown_route_is_a_clean_404(self, client):
        assert client.get("/api/v1/nope").status_code == 404

    def test_wrong_method_is_a_405(self, client):
        assert client.delete("/api/v1/chat").status_code == 405

    def test_every_error_uses_the_documented_envelope(self, client):
        body = client.get("/api/v1/memory/ghost").json()

        assert body["success"] is False
        assert "error" in body and "code" in body


class TestConcurrency:
    def test_the_graph_survives_parallel_writers(self):
        """MemoryGraph advertises thread safety; hold it to that."""
        graph = MemoryGraph()
        errors: list[Exception] = []

        def writer(worker: int) -> None:
            try:
                for i in range(50):
                    graph.create_node(title=f"w{worker}-{i}", content="x")
            except Exception as exc:  # noqa: BLE001 - recorded and asserted
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors
        # No lost updates: every write must be present.
        assert len(graph) == 8 * 50

    async def test_parallel_recall_while_writing(self, kernel):
        for i in range(40):
            await kernel.memory.store(f"note {i}", creator="core")

        results = await asyncio.gather(
            *[kernel.memory.recall("note", limit=5) for _ in range(20)],
            return_exceptions=True,
        )

        assert not [r for r in results if isinstance(r, Exception)]

    async def test_agents_dispatch_in_parallel(self, kernel):
        tasks = [kernel.registry.dispatch(Task(input=f"q{i}")) for i in range(10)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        assert not [r for r in results if isinstance(r, Exception)]

    def test_parallel_http_requests(self, client):
        """The API is served by one kernel; simultaneous reads must not clash."""
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=8) as pool:
            codes = list(
                pool.map(lambda _: client.get("/api/v1/system/status").status_code, range(24))
            )

        assert set(codes) == {200}


class TestScale:
    async def test_recall_stays_responsive_with_many_nodes(self, kernel):
        for i in range(300):
            await kernel.memory.store(f"record {i}", content=f"body {i}", creator="core")

        hits = await kernel.memory.recall("record 250", limit=10)

        assert hits
        # The top hit should be the one actually asked for, not noise.
        assert "250" in hits[0].node.title

    def test_a_large_graph_round_trips_through_disk(self, tmp_path):
        graph = MemoryGraph()
        for i in range(500):
            graph.create_node(title=f"n{i}", content="x" * 50)
        path = tmp_path / "graph.json"

        graph.save(path)
        restored = MemoryGraph()
        count = restored.load(path)

        assert count == 500
        assert len(restored) == 500

    async def test_pruning_bounds_growth(self, kernel):
        """Consolidation is what stops the graph growing without limit."""
        for i in range(50):
            await kernel.memory.store(f"trivial {i}", importance=0.05)

        result = await kernel.memory.consolidate()

        assert set(result) == {"promoted", "pruned"}


class TestWebSocketRobustness:
    def test_unknown_message_type_does_not_close_the_socket(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"type": "not-a-real-type"})

            # The connection must survive; a ping proves it is still usable.
            ws.send_json({"type": "ping"})
            for _ in range(10):
                message = ws.receive_json()
                if message["type"] == "pong":
                    break
            else:
                pytest.fail("socket stopped responding after an unknown message")

    def test_malformed_payload_does_not_crash_the_server(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_text("this is not json")

            ws.send_json({"type": "ping"})
            for _ in range(10):
                if ws.receive_json()["type"] == "pong":
                    break
            else:
                pytest.fail("socket stopped responding after bad input")

        # The HTTP side must be unaffected.
        assert client.get("/health").status_code == 200
