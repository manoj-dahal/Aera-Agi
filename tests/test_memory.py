# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Memory graph, embeddings and engine tests."""

from __future__ import annotations

import pytest

from aera.core.errors import NotFoundError, ValidationError
from aera.memory import MemoryGraph, MemoryNode, MemoryType, NodeType, RelationType
from aera.memory.embeddings import HashingEmbedder, cosine_similarity, keyword_overlap


class TestEmbeddings:
    def test_deterministic(self):
        e = HashingEmbedder(128)
        assert e.embed("hello world") == e.embed("hello world")

    def test_normalised(self):
        vec = HashingEmbedder(64).embed("docker deployment pipeline")
        assert abs(sum(v * v for v in vec) ** 0.5 - 1.0) < 1e-6

    def test_empty_text(self):
        assert HashingEmbedder(32).embed("") == [0.0] * 32

    def test_similar_text_scores_higher(self):
        e = HashingEmbedder(256)
        base = e.embed("python fastapi backend server")
        near = e.embed("python fastapi backend service")
        far = e.embed("watercolour landscape painting")
        assert cosine_similarity(base, near) > cosine_similarity(base, far)

    def test_cosine_handles_none(self):
        assert cosine_similarity(None, [1.0]) == 0.0
        assert cosine_similarity([], []) == 0.0

    def test_keyword_overlap(self):
        assert keyword_overlap("docker compose", "docker compose file") == 1.0
        assert keyword_overlap("docker", "unrelated text") == 0.0

    def test_rejects_tiny_dimensions(self):
        with pytest.raises(ValueError):
            HashingEmbedder(4)


class TestMemoryGraph:
    def test_add_and_get(self):
        g = MemoryGraph()
        node = g.create_node(title="Test", content="content here")
        assert g.get_node(node.id).title == "Test"
        assert node.embedding is not None
        assert len(g) == 1

    def test_duplicate_id_rejected(self):
        g = MemoryGraph()
        node = g.create_node(title="A")
        with pytest.raises(ValidationError):
            g.add_node(MemoryNode(id=node.id, title="B"))

    def test_missing_node_raises(self):
        with pytest.raises(NotFoundError):
            MemoryGraph().get_node("nope")

    def test_update_refreshes_embedding(self):
        g = MemoryGraph()
        node = g.create_node(title="Original", content="first")
        before = list(node.embedding)
        g.update_node(node.id, content="a totally different subject entirely")
        assert g.get_node(node.id).embedding != before

    def test_update_rejects_unknown_field(self):
        g = MemoryGraph()
        node = g.create_node(title="A")
        with pytest.raises(ValidationError):
            g.update_node(node.id, not_a_field=1)

    def test_remove_cleans_edges(self):
        g = MemoryGraph()
        a, b = g.create_node(title="A"), g.create_node(title="B")
        g.connect(a.id, b.id)
        g.remove_node(a.id)
        assert not g.has_node(a.id)
        assert g.edges_of(b.id) == []

    def test_connect_deduplicates(self):
        g = MemoryGraph()
        a, b = g.create_node(title="A"), g.create_node(title="B")
        e1 = g.connect(a.id, b.id, RelationType.RELATED)
        e2 = g.connect(a.id, b.id, RelationType.RELATED)
        assert e1.id == e2.id
        assert len(g.edges_of(a.id)) == 1

    def test_no_self_loops(self):
        g = MemoryGraph()
        a = g.create_node(title="A")
        with pytest.raises(ValidationError):
            g.connect(a.id, a.id)

    def test_connect_requires_existing_nodes(self):
        g = MemoryGraph()
        a = g.create_node(title="A")
        with pytest.raises(NotFoundError):
            g.connect(a.id, "ghost")

    def test_disconnect(self):
        g = MemoryGraph()
        a, b = g.create_node(title="A"), g.create_node(title="B")
        g.connect(a.id, b.id)
        assert g.disconnect(a.id, b.id) == 1
        assert g.edges_of(a.id) == []

    def test_neighbors_respect_inverse_relations(self):
        g = MemoryGraph()
        parent, child = g.create_node(title="P"), g.create_node(title="C")
        g.connect(parent.id, child.id, RelationType.PARENT)
        assert [n.id for n in g.neighbors(parent.id, relation=RelationType.PARENT)] == [child.id]
        assert [n.id for n in g.neighbors(child.id, relation=RelationType.CHILD)] == [parent.id]

    def test_traverse_depth(self):
        g = MemoryGraph()
        a, b, c = (g.create_node(title=t) for t in "ABC")
        g.connect(a.id, b.id)
        g.connect(b.id, c.id)
        one = {n.id for n, _ in g.traverse(a.id, max_hops=1)}
        two = {n.id for n, _ in g.traverse(a.id, max_hops=2)}
        assert one == {b.id}
        assert two == {b.id, c.id}

    def test_path_between(self):
        g = MemoryGraph()
        a, b, c = (g.create_node(title=t) for t in "ABC")
        g.connect(a.id, b.id)
        g.connect(b.id, c.id)
        assert g.path_between(a.id, c.id) == [a.id, b.id, c.id]
        d = g.create_node(title="D")
        assert g.path_between(a.id, d.id) is None

    def test_search_ranks_relevant_first(self):
        g = MemoryGraph()
        g.create_node(title="Docker deployment", content="containers compose kubernetes")
        g.create_node(title="Cooking pasta", content="boil water add salt")
        results = g.search("how do I deploy containers")
        assert results[0].node.title == "Docker deployment"

    def test_search_filters_by_type_and_tag(self):
        g = MemoryGraph()
        g.create_node(title="F", type=NodeType.FILE, tags=["src"])
        g.create_node(title="P", type=NodeType.PROJECT, tags=["src"])
        assert len(g.search("", node_types=[NodeType.FILE])) == 1
        assert len(g.search("", tags=["src"])) == 2
        assert len(g.search("", tags=["missing"])) == 0

    def test_search_expands_over_graph(self):
        g = MemoryGraph()
        hit = g.create_node(title="Docker deployment", content="containers")
        linked = g.create_node(title="Unrelated wording", content="zzz")
        g.connect(hit.id, linked.id)
        ids = {r.node.id for r in g.search("docker containers", expand_hops=1, limit=10)}
        assert linked.id in ids

    def test_search_touch_increments_access(self):
        g = MemoryGraph()
        node = g.create_node(title="Docker")
        g.search("docker")
        assert g.get_node(node.id).access_count >= 1

    def test_prune_removes_stale_low_value(self):
        g = MemoryGraph()
        old = g.create_node(title="Old", memory_type=MemoryType.SHORT_TERM, importance=0.1)
        g.update_node(old.id, updated_at=0.0)
        keep = g.create_node(title="Keep", memory_type=MemoryType.SHORT_TERM, importance=0.9)
        g.update_node(keep.id, updated_at=0.0)
        assert g.prune(older_than=10, max_importance=0.3) == 1
        assert g.has_node(keep.id)

    def test_persistence_round_trip(self, tmp_path):
        path = tmp_path / "graph.json"
        g = MemoryGraph(storage_path=path)
        a = g.create_node(title="Persisted", content="stays", tags=["x"])
        b = g.create_node(title="Other")
        g.connect(a.id, b.id)
        g.save()

        restored = MemoryGraph(storage_path=path)
        assert len(restored) == 2
        assert restored.get_node(a.id).title == "Persisted"
        assert len(restored.edges_of(a.id)) == 1

    def test_save_requires_path(self):
        with pytest.raises(ValidationError):
            MemoryGraph().save()

    def test_load_tolerates_corrupt_file(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        assert MemoryGraph(storage_path=path).load(path) == 0

    def test_importance_and_tags_normalised(self):
        node = MemoryNode(title="T", importance=5.0, tags=["  Alpha ", "alpha", "Beta"])
        assert node.importance == 1.0
        assert node.tags == ["alpha", "beta"]

    def test_stats(self):
        g = MemoryGraph()
        g.create_node(title="A", type=NodeType.FILE)
        assert g.stats()["nodes"] == 1
        assert g.stats()["by_type"]["file"] == 1


class TestMemoryEngine:
    async def test_store_and_recall(self, memory):
        await memory.store("Postgres migration", "move from sqlite to postgres", tags=["db"])
        results = await memory.recall("database migration")
        assert results and "Postgres" in results[0].node.title

    async def test_remember_exchange_links_turns(self, memory):
        user, assistant = await memory.remember_exchange(
            "hello there", "hi, how can I help?", conversation_id="c1"
        )
        assert user.conversation_id == "c1"
        history = memory.conversation_history("c1")
        assert len(history) == 2

    async def test_build_context_includes_memories(self, memory):
        await memory.store("Deploy runbook", "run docker compose up to deploy", tags=["ops"])
        context = await memory.build_context("how do I deploy")
        assert "Deploy runbook" in context

    async def test_build_context_is_bounded(self, memory):
        for i in range(30):
            await memory.store(f"Note {i}", "x" * 400, tags=["bulk"])
        assert len(await memory.build_context("note", max_chars=800)) <= 1400

    async def test_working_memory_ttl(self, memory):
        memory.set_working("k", "v")
        assert memory.get_working("k") == "v"
        memory.set_working("expired", "v", ttl=-1)
        assert memory.get_working("expired") is None

    async def test_consolidate_promotes_important(self, memory):
        node = await memory.store(
            "Critical", "important", memory_type=MemoryType.SHORT_TERM, importance=0.9
        )
        stats = await memory.consolidate()
        assert stats["promoted"] == 1
        assert memory.graph.get_node(node.id).memory_type == MemoryType.LONG_TERM

    async def test_events_published(self, memory, bus):
        seen = []
        await bus.subscribe("memory.*", lambda e: seen.append(e.topic))
        await memory.store("Event test", "content")
        assert "memory.stored" in seen

    async def test_remove(self, memory):
        node = await memory.store("Temp", "x")
        await memory.remove(node.id)
        assert not memory.graph.has_node(node.id)
