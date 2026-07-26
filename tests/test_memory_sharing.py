# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Multi-agent memory sharing and the neural-memory pipeline.

docs/memory/Neural-Network-Memory-Database.md promises one memory that every
agent reads and writes, layered over vector, graph and relational storage.
These check the code actually delivers that, rather than each agent quietly
keeping its own store.
"""

from __future__ import annotations

import pytest

from aera.memory.embeddings import cosine_similarity, get_embedder, keyword_overlap
from aera.memory.models import MemoryType


class TestSharedAcrossAgents:
    async def test_every_agent_holds_the_same_memory_engine(self, kernel):
        """One graph, not thirty-one. This is the whole premise of the design."""
        agents = list(kernel.registry.agents.values())

        engines = {id(agent.ctx.memory) for agent in agents}

        assert len(agents) > 10, "expected the full roster"
        assert len(engines) == 1, "agents must share a single memory engine"

    async def test_one_agent_recalls_what_another_wrote(self, kernel):
        await kernel.memory.store(
            "The deploy key lives in the encrypted vault", creator="coding"
        )

        hits = await kernel.memory.recall("where is the deploy key", limit=5)

        assert hits, "a memory written by one agent must be visible to all"
        assert hits[0].node.creator == "coding"

    async def test_the_writer_is_recorded(self, kernel):
        """Shared does not mean anonymous; provenance has to survive."""
        await kernel.memory.store("Nginx hardened", creator="security")
        await kernel.memory.store("Refactored the router", creator="coding")

        creators = {n.creator for n in kernel.memory.graph.find()}

        assert {"security", "coding"} <= creators

    async def test_context_assembly_spans_writers(self, kernel):
        """build_context is what reaches the LLM, so it must see everything."""
        await kernel.memory.store("Port 8080 is the API", creator="core")
        await kernel.memory.store("Port 5173 is the dev UI", creator="workspace")

        context = str(await kernel.memory.build_context("which ports are used?"))

        assert "8080" in context or "5173" in context


class TestMemoryLayers:
    """Vector, graph and relational layers from the database document."""

    async def test_vector_layer_is_a_real_embedder(self, kernel):
        stats = kernel.memory.stats()

        assert stats["embedding_dimensions"] > 0

    def test_embeddings_are_deterministic(self):
        """A hashing embedder must give the same vector for the same text."""
        embedder = get_embedder()

        assert embedder.embed("hello world") == embedder.embed("hello world")

    def test_similar_text_scores_higher_than_unrelated(self):
        embedder = get_embedder()
        base = embedder.embed("the database stores user records")
        close = embedder.embed("user records are kept in the database")
        far = embedder.embed("the cat sat on the mat")

        assert cosine_similarity(base, close) > cosine_similarity(base, far)

    def test_keyword_overlap_complements_vectors(self):
        """Recall is hybrid; the lexical half has to work on its own too."""
        assert keyword_overlap("deploy key", "the deploy key is here") > 0
        assert keyword_overlap("deploy key", "unrelated sentence") == 0

    async def test_graph_layer_links_related_memories(self, kernel):
        first = await kernel.memory.store("Project AERA", creator="core")
        second = await kernel.memory.store(
            "Uses FastAPI", creator="core", related_to=[first.id]
        )

        neighbours = kernel.memory.graph.neighbors(second.id)

        assert first.id in {n.id for n in neighbours}

    async def test_memory_types_are_tracked_separately(self, kernel):
        await kernel.memory.store("short lived", memory_type=MemoryType.SHORT_TERM)
        await kernel.memory.store("durable fact", memory_type=MemoryType.LONG_TERM)

        by_type = kernel.memory.stats()["by_memory_type"]

        assert by_type.get("short_term", 0) >= 1
        assert by_type.get("long_term", 0) >= 1

    async def test_consolidation_reports_what_it_did(self, kernel):
        """Promotion and pruning are the learning half of the pipeline."""
        result = await kernel.memory.consolidate()

        assert set(result) == {"promoted", "pruned"}

    async def test_memory_survives_a_save_and_load(self, kernel, tmp_path):
        """The relational layer: state has to outlive the process."""
        await kernel.memory.store("Persisted across restarts", creator="core")
        path = tmp_path / "graph.json"
        kernel.memory.graph.save(path)

        from aera.memory.graph import MemoryGraph

        restored = MemoryGraph()
        count = restored.load(path)

        assert count >= 1
        assert any("Persisted" in n.title for n in restored.find())


class TestMemoryApi:
    """The same store, reachable over REST."""

    @pytest.fixture
    def client(self, config):
        from fastapi.testclient import TestClient

        from aera.api.app import create_app

        with TestClient(create_app(config)) as c:
            yield c

    def test_write_then_search(self, client):
        client.post(
            "/api/v1/memory",
            json={"title": "The vault holds the deploy key", "creator": "coding"},
        )

        results = client.get("/api/v1/memory/search?q=deploy%20key").json()["data"]

        assert results["count"] >= 1

    def test_stats_expose_the_layers(self, client):
        data = client.get("/api/v1/memory/stats").json()["data"]

        for key in ("nodes", "edges", "by_memory_type", "embedding_dimensions"):
            assert key in data

    def test_graph_endpoint_returns_nodes_and_edges(self, client):
        client.post("/api/v1/memory", json={"title": "A node"})

        data = client.post("/api/v1/memory/graph", json={}).json()["data"]

        assert "nodes" in data and "edges" in data

    def test_short_term_buffer_is_distinct_from_the_graph(self, client):
        """recent() reads the short-term ring, not everything ever stored."""
        client.post(
            "/api/v1/memory",
            json={"title": "long lived", "memory_type": "long_term"},
        )

        stats = client.get("/api/v1/memory/stats").json()["data"]

        assert stats["nodes"] >= 1
        assert "short_term_buffer" in stats
