"""Tests for the Memory Graph engine and API (docs/06-MEMORY-GRAPH.md)."""

from services.memory.graph import MemoryGraph
from shared.schemas import EdgeRelation, MemoryEdgeCreate, MemoryNodeCreate, NodeType

# ── Engine-level tests ───────────────────────────────────────


def make_graph() -> MemoryGraph:
    return MemoryGraph(db_path=":memory:")


def test_add_and_get_node() -> None:
    g = make_graph()
    node = g.add_node(
        MemoryNodeCreate(type=NodeType.FACT, content="User prefers dark mode", importance=0.8)
    )
    assert node.id > 0
    fetched = g.get_node(node.id)
    assert fetched.content == "User prefers dark mode"
    assert fetched.importance == 0.8


def test_edges_and_neighbors() -> None:
    g = make_graph()
    a = g.add_node(MemoryNodeCreate(type=NodeType.PROJECT, content="AERA project"))
    b = g.add_node(MemoryNodeCreate(type=NodeType.TASK, content="Build memory graph"))
    g.add_edge(
        MemoryEdgeCreate(source_id=b.id, target_id=a.id, relation=EdgeRelation.BELONGS_TO)
    )
    neighbors = g.neighbors(a.id)
    assert [n.id for n in neighbors] == [b.id]


def test_recall_ranks_by_matches() -> None:
    g = make_graph()
    g.add_node(MemoryNodeCreate(type=NodeType.FACT, content="Python is the backend language"))
    g.add_node(
        MemoryNodeCreate(
            type=NodeType.FACT, content="Python backend uses FastAPI", importance=0.9
        )
    )
    g.add_node(MemoryNodeCreate(type=NodeType.FACT, content="Frontend uses TypeScript"))
    results = g.recall("python backend")
    assert len(results) == 2
    assert results[0].content == "Python backend uses FastAPI"  # 2 hits beats 1


def test_delete_node_cascades() -> None:
    g = make_graph()
    a = g.add_node(MemoryNodeCreate(type=NodeType.FACT, content="a"))
    b = g.add_node(MemoryNodeCreate(type=NodeType.FACT, content="b"))
    g.add_edge(MemoryEdgeCreate(source_id=a.id, target_id=b.id))
    g.delete_node(a.id)
    assert g.stats().edges == 0


def test_stats() -> None:
    g = make_graph()
    g.add_node(MemoryNodeCreate(type=NodeType.FACT, content="x"))
    g.add_node(MemoryNodeCreate(type=NodeType.TASK, content="y"))
    s = g.stats()
    assert s.nodes == 2
    assert s.by_type == {"fact": 1, "task": 1}


# ── API-level tests ──────────────────────────────────────────


def test_memory_api_crud(client) -> None:
    res = client.post(
        "/api/memory/nodes", json={"type": "fact", "content": "API test fact"}
    )
    assert res.status_code == 201
    node_id = res.json()["id"]

    res = client.get(f"/api/memory/nodes/{node_id}")
    assert res.status_code == 200

    res = client.get("/api/memory/recall", params={"q": "API test"})
    assert res.status_code == 200
    assert len(res.json()) == 1

    res = client.delete(f"/api/memory/nodes/{node_id}")
    assert res.status_code == 204

    res = client.get(f"/api/memory/nodes/{node_id}")
    assert res.status_code == 404


def test_memory_api_edge_validation(client) -> None:
    res = client.post("/api/memory/edges", json={"source_id": 999, "target_id": 998})
    assert res.status_code == 404
