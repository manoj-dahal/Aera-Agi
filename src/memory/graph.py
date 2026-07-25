"""Memory Graph engine — persistent knowledge graph shared by all agents.

Implements the core of docs/06-MEMORY-GRAPH.md on SQLite:
- nodes (facts, projects, files, agents, tasks, conversations, preferences)
- weighted edges between nodes
- keyword recall with importance-based ranking

Vector-based semantic recall (ChromaDB) plugs in later behind the same API.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

from src.common.schemas import (
    EdgeRelation,
    MemoryEdge,
    MemoryEdgeCreate,
    MemoryGraphStats,
    MemoryNode,
    MemoryNodeCreate,
)

_SCHEMA = Path(__file__).resolve().parents[2] / "database" / "schema.sql"


class MemoryGraph:
    """Thread-safe SQLite-backed memory graph."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.getenv("AERA_MEMORY_DB", "data/aera.db")
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA.read_text())
        self._conn.commit()

    # ── Nodes ─────────────────────────────────────────────

    def add_node(self, node: MemoryNodeCreate) -> MemoryNode:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO memory_nodes (type, content, importance) VALUES (?, ?, ?)",
                (node.type.value, node.content, node.importance),
            )
            self._conn.commit()
            return self.get_node(int(cur.lastrowid))  # type: ignore[arg-type]

    def get_node(self, node_id: int) -> MemoryNode:
        row = self._conn.execute(
            "SELECT * FROM memory_nodes WHERE id = ?", (node_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"memory node {node_id} not found")
        return MemoryNode(**dict(row))

    def delete_node(self, node_id: int) -> None:
        with self._lock:
            cur = self._conn.execute("DELETE FROM memory_nodes WHERE id = ?", (node_id,))
            self._conn.commit()
        if cur.rowcount == 0:
            raise KeyError(f"memory node {node_id} not found")

    # ── Edges ─────────────────────────────────────────────

    def add_edge(self, edge: MemoryEdgeCreate) -> MemoryEdge:
        # validate endpoints exist
        self.get_node(edge.source_id)
        self.get_node(edge.target_id)
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO memory_edges (source_id, target_id, relation, weight)"
                " VALUES (?, ?, ?, ?)",
                (edge.source_id, edge.target_id, edge.relation.value, edge.weight),
            )
            self._conn.commit()
            return MemoryEdge(id=int(cur.lastrowid), **edge.model_dump())

    def neighbors(self, node_id: int) -> list[MemoryNode]:
        rows = self._conn.execute(
            """
            SELECT n.* FROM memory_nodes n
            JOIN memory_edges e
              ON (e.target_id = n.id AND e.source_id = ?)
              OR (e.source_id = n.id AND e.target_id = ?)
            ORDER BY n.importance DESC
            """,
            (node_id, node_id),
        ).fetchall()
        return [MemoryNode(**dict(r)) for r in rows]

    # ── Recall ────────────────────────────────────────────

    def recall(self, query: str, limit: int = 10) -> list[MemoryNode]:
        """Keyword recall ranked by term matches and importance."""
        terms = [t.strip().lower() for t in query.split() if t.strip()]
        if not terms:
            return []
        clauses = " + ".join(
            "(CASE WHEN lower(content) LIKE ? THEN 1 ELSE 0 END)" for _ in terms
        )
        params: list[object] = [f"%{t}%" for t in terms]
        rows = self._conn.execute(
            f"""
            SELECT *, ({clauses}) AS hits FROM memory_nodes
            WHERE hits > 0
            ORDER BY hits DESC, importance DESC, updated_at DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [MemoryNode(**{k: r[k] for k in r.keys() if k != "hits"}) for r in rows]

    # ── Stats ─────────────────────────────────────────────

    def stats(self) -> MemoryGraphStats:
        nodes = self._conn.execute("SELECT COUNT(*) FROM memory_nodes").fetchone()[0]
        edges = self._conn.execute("SELECT COUNT(*) FROM memory_edges").fetchone()[0]
        by_type = dict(
            self._conn.execute(
                "SELECT type, COUNT(*) FROM memory_nodes GROUP BY type"
            ).fetchall()
        )
        return MemoryGraphStats(nodes=nodes, edges=edges, by_type=by_type)

    def remember_conversation(self, user_msg: str, ai_msg: str) -> None:
        """Convenience: store an exchange and link the two nodes."""
        from src.common.schemas import NodeType

        u = self.add_node(
            MemoryNodeCreate(type=NodeType.CONVERSATION, content=f"user: {user_msg}")
        )
        a = self.add_node(
            MemoryNodeCreate(type=NodeType.CONVERSATION, content=f"aera: {ai_msg}")
        )
        self.add_edge(
            MemoryEdgeCreate(source_id=u.id, target_id=a.id, relation=EdgeRelation.RELATES_TO)
        )

    def close(self) -> None:
        self._conn.close()
