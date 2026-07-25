"""AERA memory subsystem: graph, embeddings and the unified engine."""

from .embeddings import EmbeddingProvider, HashingEmbedder, cosine_similarity, get_embedder
from .engine import MemoryEngine
from .graph import MemoryGraph
from .models import (
    MemoryEdge,
    MemoryNode,
    MemoryType,
    NodeType,
    RecallResult,
    RelationType,
)

__all__ = [
    "EmbeddingProvider",
    "HashingEmbedder",
    "MemoryEdge",
    "MemoryEngine",
    "MemoryGraph",
    "MemoryNode",
    "MemoryType",
    "NodeType",
    "RecallResult",
    "RelationType",
    "cosine_similarity",
    "get_embedder",
]
