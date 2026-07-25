"""The Memory Graph.

An in-memory, index-backed property graph with JSON persistence. Provides node
CRUD, relationship management, BFS traversal and the hybrid (vector + keyword +
ranking-factor) recall described in ``docs/06-MEMORY-GRAPH.md``.
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ..core.errors import NotFoundError, ValidationError
from ..core.logging import get_logger
from .embeddings import EmbeddingProvider, cosine_similarity, get_embedder, keyword_overlap
from .models import (
    INVERSE_RELATIONS,
    MemoryEdge,
    MemoryNode,
    MemoryType,
    NodeType,
    RecallResult,
    RelationType,
)

logger = get_logger("memory.graph")

# Relative contribution of each ranking factor (spec: "Memory Ranking").
_W_SEMANTIC = 0.45
_W_KEYWORD = 0.25
_W_IMPORTANCE = 0.15
_W_RECENCY = 0.10
_W_FREQUENCY = 0.05

_RECENCY_HALFLIFE = 7 * 24 * 3600.0  # a week-old memory scores half on recency


class MemoryGraph:
    """Thread-safe knowledge graph shared by every agent."""

    def __init__(
        self,
        *,
        embedder: EmbeddingProvider | None = None,
        storage_path: str | Path | None = None,
        auto_embed: bool = True,
    ) -> None:
        self._nodes: dict[str, MemoryNode] = {}
        self._edges: dict[str, MemoryEdge] = {}
        self._out: dict[str, set[str]] = defaultdict(set)  # node id -> edge ids
        self._in: dict[str, set[str]] = defaultdict(set)
        self._by_type: dict[NodeType, set[str]] = defaultdict(set)
        self._by_memory_type: dict[MemoryType, set[str]] = defaultdict(set)
        self._by_tag: dict[str, set[str]] = defaultdict(set)
        self._by_project: dict[str, set[str]] = defaultdict(set)
        self._edge_keys: set[tuple[str, str, str]] = set()

        self._embedder = embedder or get_embedder()
        self._auto_embed = auto_embed
        self._storage_path = Path(storage_path).expanduser() if storage_path else None
        self._lock = threading.RLock()

        if self._storage_path and self._storage_path.exists():
            self.load()

    # ------------------------------------------------------------------ #
    # node CRUD
    # ------------------------------------------------------------------ #
    def add_node(self, node: MemoryNode) -> MemoryNode:
        """Insert a node, computing its embedding when needed."""
        with self._lock:
            if node.id in self._nodes:
                raise ValidationError(f"node {node.id} already exists")
            if self._auto_embed and node.embedding is None:
                node.embedding = self._embedder.embed(node.searchable_text())
            self._nodes[node.id] = node
            self._index(node)
            return node

    def create_node(self, **kwargs: Any) -> MemoryNode:
        """Convenience constructor + insert."""
        return self.add_node(MemoryNode(**kwargs))

    def get_node(self, node_id: str, *, touch: bool = False) -> MemoryNode:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                raise NotFoundError(f"memory node not found: {node_id}")
            if touch:
                node.touch()
            return node

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def update_node(self, node_id: str, **changes: Any) -> MemoryNode:
        """Patch fields on a node and refresh its indexes/embedding."""
        with self._lock:
            node = self.get_node(node_id)
            self._deindex(node)

            text_changed = False
            for key, value in changes.items():
                if key in ("id", "created_at"):
                    continue
                if not hasattr(node, key):
                    raise ValidationError(f"unknown memory field: {key}")
                setattr(node, key, value)
                if key in ("title", "description", "content", "tags"):
                    text_changed = True

            # An explicit updated_at wins, so imports and restores can preserve
            # original timestamps; otherwise the edit bumps the clock.
            if "updated_at" not in changes:
                node.updated_at = time.time()
            if text_changed and self._auto_embed:
                node.embedding = self._embedder.embed(node.searchable_text())
            self._index(node)
            return node

    def remove_node(self, node_id: str) -> None:
        """Delete a node together with all of its edges."""
        with self._lock:
            node = self.get_node(node_id)
            for edge_id in list(self._out[node_id] | self._in[node_id]):
                self._drop_edge(edge_id)
            self._deindex(node)
            self._nodes.pop(node_id, None)
            self._out.pop(node_id, None)
            self._in.pop(node_id, None)

    # ------------------------------------------------------------------ #
    # edges
    # ------------------------------------------------------------------ #
    def connect(
        self,
        source: str,
        target: str,
        relation: RelationType | str = RelationType.RELATED,
        *,
        weight: float = 1.0,
        metadata: dict | None = None,
    ) -> MemoryEdge:
        """Create a relationship, de-duplicating identical triples."""
        with self._lock:
            if source not in self._nodes:
                raise NotFoundError(f"source node not found: {source}")
            if target not in self._nodes:
                raise NotFoundError(f"target node not found: {target}")
            if source == target:
                raise ValidationError("cannot connect a node to itself")

            rel = RelationType(relation)
            key = (source, target, rel.value)
            if key in self._edge_keys:
                for edge_id in self._out[source]:
                    edge = self._edges[edge_id]
                    if edge.key() == key:
                        edge.weight = max(edge.weight, weight)
                        return edge

            edge = MemoryEdge(
                source=source, target=target, relation=rel,
                weight=weight, metadata=metadata or {},
            )
            self._edges[edge.id] = edge
            self._out[source].add(edge.id)
            self._in[target].add(edge.id)
            self._edge_keys.add(key)
            return edge

    def disconnect(self, source: str, target: str, relation: RelationType | str | None = None) -> int:
        """Remove matching edges; returns how many were removed."""
        with self._lock:
            rel = RelationType(relation) if relation is not None else None
            victims = [
                eid for eid in list(self._out.get(source, set()))
                if self._edges[eid].target == target
                and (rel is None or self._edges[eid].relation == rel)
            ]
            for eid in victims:
                self._drop_edge(eid)
            return len(victims)

    def edges_of(self, node_id: str, *, direction: str = "both") -> list[MemoryEdge]:
        with self._lock:
            ids: set[str] = set()
            if direction in ("out", "both"):
                ids |= self._out.get(node_id, set())
            if direction in ("in", "both"):
                ids |= self._in.get(node_id, set())
            return [self._edges[i] for i in ids]

    def neighbors(
        self,
        node_id: str,
        *,
        relation: RelationType | str | None = None,
        direction: str = "both",
    ) -> list[MemoryNode]:
        """Directly connected nodes, honouring relation inverses."""
        rel = RelationType(relation) if relation is not None else None
        out: list[MemoryNode] = []
        seen: set[str] = set()
        for edge in self.edges_of(node_id, direction=direction):
            if edge.source == node_id:
                if rel is not None and edge.relation != rel:
                    continue
                other = edge.target
            else:
                if rel is not None and INVERSE_RELATIONS.get(edge.relation, edge.relation) != rel:
                    continue
                other = edge.source
            if other not in seen and other in self._nodes:
                seen.add(other)
                out.append(self._nodes[other])
        return out

    def traverse(
        self,
        start: str,
        *,
        max_hops: int = 2,
        relation: RelationType | str | None = None,
        limit: int = 50,
    ) -> list[tuple[MemoryNode, int]]:
        """Breadth-first walk returning ``(node, hop_count)`` excluding the start."""
        if start not in self._nodes:
            raise NotFoundError(f"memory node not found: {start}")
        visited = {start}
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        results: list[tuple[MemoryNode, int]] = []

        while queue and len(results) < limit:
            current, hops = queue.popleft()
            if hops >= max_hops:
                continue
            for neighbor in self.neighbors(current, relation=relation):
                if neighbor.id in visited:
                    continue
                visited.add(neighbor.id)
                results.append((neighbor, hops + 1))
                queue.append((neighbor.id, hops + 1))
                if len(results) >= limit:
                    break
        return results

    def path_between(self, source: str, target: str, *, max_hops: int = 6) -> list[str] | None:
        """Shortest node-id path via BFS, or ``None`` if unreachable."""
        if source not in self._nodes or target not in self._nodes:
            return None
        if source == target:
            return [source]
        prev: dict[str, str] = {source: source}
        queue: deque[tuple[str, int]] = deque([(source, 0)])
        while queue:
            current, depth = queue.popleft()
            if depth >= max_hops:
                continue
            for neighbor in self.neighbors(current):
                if neighbor.id in prev:
                    continue
                prev[neighbor.id] = current
                if neighbor.id == target:
                    path = [target]
                    while path[-1] != source:
                        path.append(prev[path[-1]])
                    return list(reversed(path))
                queue.append((neighbor.id, depth + 1))
        return None

    # ------------------------------------------------------------------ #
    # search & recall
    # ------------------------------------------------------------------ #
    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        node_types: Iterable[NodeType | str] | None = None,
        memory_types: Iterable[MemoryType | str] | None = None,
        tags: Iterable[str] | None = None,
        project_id: str | None = None,
        min_score: float = 0.0,
        expand_hops: int = 0,
    ) -> list[RecallResult]:
        """Hybrid recall: semantic + keyword, re-ranked by importance/recency/frequency."""
        with self._lock:
            candidates = self._candidate_ids(node_types, memory_types, tags, project_id)
            if not candidates:
                return []

            query_vec = self._embedder.embed(query) if query.strip() else None
            now = time.time()
            scored: list[RecallResult] = []

            for node_id in candidates:
                node = self._nodes[node_id]
                semantic = cosine_similarity(query_vec, node.embedding) if query_vec else 0.0
                # cosine lives in [-1, 1]; fold to [0, 1] so weights stay meaningful
                semantic = (semantic + 1.0) / 2.0 if query_vec else 0.0
                lexical = keyword_overlap(query, node.searchable_text()) if query.strip() else 0.0

                age = max(0.0, now - node.updated_at)
                recency = 0.5 ** (age / _RECENCY_HALFLIFE)
                frequency = min(1.0, node.access_count / 20.0)

                score = (
                    _W_SEMANTIC * semantic
                    + _W_KEYWORD * lexical
                    + _W_IMPORTANCE * node.importance
                    + _W_RECENCY * recency
                    + _W_FREQUENCY * frequency
                )
                if not query.strip():
                    # Browsing rather than searching: rank on the intrinsic factors.
                    score = _W_IMPORTANCE * node.importance + _W_RECENCY * recency

                if score >= min_score:
                    reason = "semantic" if semantic >= lexical else "keyword"
                    scored.append(RecallResult(node=node, score=score, reason=reason))

            scored.sort(key=lambda r: r.score, reverse=True)
            top = scored[:limit]

            if expand_hops > 0 and top:
                top = self._expand(top, expand_hops, limit)

            for result in top:
                result.node.touch()
            return top

    def _expand(self, seeds: list[RecallResult], hops: int, limit: int) -> list[RecallResult]:
        """Pull in graph neighbours of the strongest hits (relationship traversal)."""
        seen = {r.node.id for r in seeds}
        expanded = list(seeds)
        for seed in seeds[: max(1, limit // 2)]:
            for node, hop in self.traverse(seed.node.id, max_hops=hops, limit=limit):
                if node.id in seen:
                    continue
                seen.add(node.id)
                expanded.append(
                    RecallResult(
                        node=node,
                        score=seed.score * (0.5**hop),
                        reason="graph",
                        hops=hop,
                    )
                )
        expanded.sort(key=lambda r: r.score, reverse=True)
        return expanded[:limit]

    def _candidate_ids(
        self,
        node_types: Iterable[NodeType | str] | None,
        memory_types: Iterable[MemoryType | str] | None,
        tags: Iterable[str] | None,
        project_id: str | None,
    ) -> set[str]:
        """Intersect the secondary indexes to shrink the scan set."""
        pools: list[set[str]] = []
        if node_types:
            pool: set[str] = set()
            for t in node_types:
                pool |= self._by_type.get(NodeType(t), set())
            pools.append(pool)
        if memory_types:
            pool = set()
            for t in memory_types:
                pool |= self._by_memory_type.get(MemoryType(t), set())
            pools.append(pool)
        if tags:
            for tag in tags:
                pools.append(set(self._by_tag.get(tag.strip().lower(), set())))
        if project_id:
            pools.append(set(self._by_project.get(project_id, set())))

        if not pools:
            return set(self._nodes)
        result = pools[0]
        for pool in pools[1:]:
            result &= pool
        return result

    def find(
        self,
        *,
        node_type: NodeType | str | None = None,
        memory_type: MemoryType | str | None = None,
        tag: str | None = None,
        project_id: str | None = None,
        limit: int = 100,
    ) -> list[MemoryNode]:
        """Non-scored structured lookup, newest first."""
        with self._lock:
            ids = self._candidate_ids(
                [node_type] if node_type else None,
                [memory_type] if memory_type else None,
                [tag] if tag else None,
                project_id,
            )
            nodes = [self._nodes[i] for i in ids]
            nodes.sort(key=lambda n: n.updated_at, reverse=True)
            return nodes[:limit]

    # ------------------------------------------------------------------ #
    # maintenance
    # ------------------------------------------------------------------ #
    def prune(self, *, older_than: float, max_importance: float = 0.3,
              memory_type: MemoryType | str = MemoryType.SHORT_TERM) -> int:
        """Drop stale, low-value memories (Compression Engine)."""
        with self._lock:
            cutoff = time.time() - older_than
            mtype = MemoryType(memory_type)
            victims = [
                n.id for n in self._nodes.values()
                if n.memory_type == mtype and n.updated_at < cutoff and n.importance <= max_importance
            ]
            for node_id in victims:
                self.remove_node(node_id)
            if victims:
                logger.info("pruned %d %s memories", len(victims), mtype.value)
            return len(victims)

    def promote(self, node_id: str, memory_type: MemoryType | str = MemoryType.LONG_TERM) -> MemoryNode:
        """Move a memory into a longer-lived store (e.g. short -> long term)."""
        return self.update_node(node_id, memory_type=MemoryType(memory_type))

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "nodes": len(self._nodes),
                "edges": len(self._edges),
                "by_type": {t.value: len(ids) for t, ids in self._by_type.items() if ids},
                "by_memory_type": {
                    t.value: len(ids) for t, ids in self._by_memory_type.items() if ids
                },
                "tags": len(self._by_tag),
                "projects": len([p for p, ids in self._by_project.items() if ids]),
                "embedding_dimensions": self._embedder.dimensions,
            }

    # ------------------------------------------------------------------ #
    # persistence
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "version": 1,
                "saved_at": time.time(),
                "nodes": [n.model_dump() for n in self._nodes.values()],
                "edges": [e.model_dump() for e in self._edges.values()],
            }

    def save(self, path: str | Path | None = None) -> Path:
        """Atomically persist the graph to JSON."""
        target = Path(path).expanduser() if path else self._storage_path
        if target is None:
            raise ValidationError("no storage path configured for the memory graph")
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict()), encoding="utf-8")
        tmp.replace(target)
        logger.debug("memory graph saved to %s", target)
        return target

    def load(self, path: str | Path | None = None) -> int:
        """Replace in-memory state with the contents of a snapshot."""
        target = Path(path).expanduser() if path else self._storage_path
        if target is None or not target.exists():
            return 0
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("could not load memory graph from %s: %s", target, exc)
            return 0

        with self._lock:
            self.clear()
            for raw in data.get("nodes", []):
                try:
                    node = MemoryNode(**raw)
                except Exception:  # noqa: BLE001 - skip corrupt records, keep the rest
                    logger.warning("skipping malformed memory node")
                    continue
                self._nodes[node.id] = node
                self._index(node)
            for raw in data.get("edges", []):
                try:
                    edge = MemoryEdge(**raw)
                except Exception:  # noqa: BLE001
                    continue
                if edge.source in self._nodes and edge.target in self._nodes:
                    self._edges[edge.id] = edge
                    self._out[edge.source].add(edge.id)
                    self._in[edge.target].add(edge.id)
                    self._edge_keys.add(edge.key())
        logger.info("memory graph loaded: %d nodes, %d edges", len(self._nodes), len(self._edges))
        return len(self._nodes)

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
            self._edges.clear()
            self._out.clear()
            self._in.clear()
            self._by_type.clear()
            self._by_memory_type.clear()
            self._by_tag.clear()
            self._by_project.clear()
            self._edge_keys.clear()

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #
    def _index(self, node: MemoryNode) -> None:
        self._by_type[node.type].add(node.id)
        self._by_memory_type[node.memory_type].add(node.id)
        for tag in node.tags:
            self._by_tag[tag].add(node.id)
        if node.project_id:
            self._by_project[node.project_id].add(node.id)

    def _deindex(self, node: MemoryNode) -> None:
        self._by_type[node.type].discard(node.id)
        self._by_memory_type[node.memory_type].discard(node.id)
        for tag in node.tags:
            self._by_tag[tag].discard(node.id)
        if node.project_id:
            self._by_project[node.project_id].discard(node.id)

    def _drop_edge(self, edge_id: str) -> None:
        edge = self._edges.pop(edge_id, None)
        if edge is None:
            return
        self._out[edge.source].discard(edge_id)
        self._in[edge.target].discard(edge_id)
        self._edge_keys.discard(edge.key())

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, node_id: object) -> bool:
        return isinstance(node_id, str) and node_id in self._nodes
