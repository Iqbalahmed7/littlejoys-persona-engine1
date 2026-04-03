"""
Lightweight sentence embedding cache.
Uses sentence-transformers (all-MiniLM-L6-v2) with an LRU-like cache keyed on content hash.
Falls back to a deterministic hash-vector approximation when sentence-transformers is unavailable.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from typing import Protocol

import numpy as np


class EmbeddingBackend(Protocol):
    def encode(self, texts: list[str]) -> np.ndarray: ...


class EmbeddingCache:
    MAX_CACHE_SIZE = 2000

    def __init__(self) -> None:
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._backend: EmbeddingBackend | None = None
        self._backend_name: str = "none"
        self._init_backend()

    def _init_backend(self) -> None:
        """Try sentence-transformers, otherwise use deterministic fallback vectors."""
        try:
            from sentence_transformers import SentenceTransformer

            self._backend = SentenceTransformer("all-MiniLM-L6-v2")
            self._backend_name = "sentence-transformers"
        except ImportError:
            self._backend = None
            self._backend_name = "tfidf-fallback"

    def embed(self, text: str) -> np.ndarray:
        """Return an embedding for text using a bounded in-memory cache."""
        key = hashlib.md5(text.encode("utf-8")).hexdigest()
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        if len(self._cache) >= self.MAX_CACHE_SIZE:
            evict_count = max(1, self.MAX_CACHE_SIZE // 10)
            for _ in range(evict_count):
                self._cache.popitem(last=False)

        vector = self._compute(text)
        self._cache[key] = vector
        return vector

    def _compute(self, text: str) -> np.ndarray:
        if self._backend is not None:
            return self._backend.encode([text])[0]
        return self._tfidf_fallback(text)

    def _tfidf_fallback(self, text: str) -> np.ndarray:
        """64-d deterministic vector. Stable, but not semantically rich."""
        vec = np.zeros(64, dtype=np.float32)
        words = text.lower().split()
        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            vec[h % 64] += 1.0 / (i + 1)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Return cosine similarity in [0.0, 1.0]."""
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0.0:
            return 0.0
        return float(np.dot(a, b) / denom)

    @property
    def backend_name(self) -> str:
        return self._backend_name
