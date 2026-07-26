# MADE By Manoj Dahal
# Copyright (c) 2026 Manoj Dahal. All rights reserved.
# Contact: info@manoj-dahal.com.np
# AERA — Artificial Enhanced Reasoning Assistant

"""Embedding provider.

Ships a deterministic, dependency-free hashing embedder so semantic search
works offline out of the box (the "local first" requirement). A real model can
be swapped in behind the same interface without touching callers.
"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

_TOKEN_RE = re.compile(r"[a-z0-9_]+")

_STOPWORDS = frozenset(
    """a an and are as at be by for from has have how in is it its of on or
    that the this to was were what when where which who will with you your
    i me my we our they them he she do does did not no yes if then than""".split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens with stopwords removed."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


class EmbeddingProvider(ABC):
    """Interface every embedder implements."""

    dimensions: int

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class HashingEmbedder(EmbeddingProvider):
    """Deterministic hashed bag-of-ngrams embedding, L2-normalised.

    Uses unigrams plus bigrams so short phrases keep some word-order signal.
    Identical text always yields an identical vector, which makes tests exact.
    """

    def __init__(self, dimensions: int = 256) -> None:
        if dimensions < 8:
            raise ValueError("dimensions must be >= 8")
        self.dimensions = dimensions

    def _bucket(self, token: str) -> tuple[int, float]:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        index = value % self.dimensions
        sign = 1.0 if (value >> 63) & 1 else -1.0
        return index, sign

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            idx, sign = self._bucket(token)
            vector[idx] += sign
        # bigrams: the offset slice is intentionally one shorter, so the
        # shortest-sequence behaviour of zip() is exactly what we want here
        for a, b in zip(tokens, tokens[1:], strict=False):
            idx, sign = self._bucket(f"{a}_{b}")
            vector[idx] += sign * 0.5

        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            return vector
        return [v / norm for v in vector]


def cosine_similarity(a: list[float] | None, b: list[float] | None) -> float:
    """Cosine similarity, tolerant of ``None`` and length mismatch."""
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = na = nb = 0.0
    for i in range(n):
        x, y = a[i], b[i]
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / math.sqrt(na * nb)


def keyword_overlap(query: str, text: str) -> float:
    """Jaccard-style lexical overlap used to complement vector search."""
    q = set(tokenize(query))
    if not q:
        return 0.0
    t = set(tokenize(text))
    if not t:
        return 0.0
    return len(q & t) / len(q)


_default: EmbeddingProvider | None = None


def get_embedder(dimensions: int = 256) -> EmbeddingProvider:
    global _default
    if _default is None or _default.dimensions != dimensions:
        _default = HashingEmbedder(dimensions)
    return _default
