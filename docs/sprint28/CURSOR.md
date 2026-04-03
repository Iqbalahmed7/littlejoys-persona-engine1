# Sprint 28 — Brief: CURSOR

**Role:** Architecture lead / complex implementation
**Model:** Auto
**Assignment:** Implement `MemoryManager` — the in-memory episodic store with recency decay,
importance indexing, and embedding-based retrieval scoring
**Est. duration:** 4-6 hours

---

## Files to Create / Modify

| Action | File |
|---|---|
| MODIFY (replace stubs) | `src/agents/memory.py` |
| CREATE | `src/agents/embedding_cache.py` |

## Do NOT Touch

- `src/taxonomy/schema.py` — read-only
- `src/generation/tier2_generator.py` — read-only
- `src/agents/agent.py` — owned by Codex
- Any existing test files

---

## Context

`memory.py` currently has three `NotImplementedError` stubs:
- `add_episodic(self, event: dict) -> None`
- `update_semantic(self, key: str, value: object) -> None`
- `update_brand_memory(self, brand: str, touchpoint: dict) -> None`

`MemoryEntry` is already defined in `src/taxonomy/schema.py`:

```python
class MemoryEntry(BaseModel):
    timestamp: str          # ISO-8601 string
    event_type: str         # "stimulus" | "decision" | "reflection" | "purchase"
    content: str            # free-text description
    emotional_valence: SignedUnitInterval   # -1.0 to 1.0
    salience: UnitInterval                  # 0.0 to 1.0
```

The `Persona` model (also in `schema.py`) has:
```python
episodic_memory: list[MemoryEntry] = Field(default_factory=list)
brand_memories: dict[str, BrandMemory] = Field(default_factory=dict)
purchase_history: list[PurchaseEvent] = Field(default_factory=list)
temporal_state: TemporalState = Field(default_factory=TemporalState)
```

---

## File 1: `src/agents/embedding_cache.py`

```python
"""
Lightweight sentence embedding cache.
Uses sentence-transformers (all-MiniLM-L6-v2) with an LRU cache keyed on content hash.
Falls back to TF-IDF bag-of-words if sentence-transformers is not installed.
"""
import hashlib
import numpy as np
from typing import Protocol

class EmbeddingBackend(Protocol):
    def encode(self, texts: list[str]) -> np.ndarray: ...

class EmbeddingCache:
    MAX_CACHE_SIZE = 2000  # entries

    def __init__(self):
        self._cache: dict[str, np.ndarray] = {}
        self._backend: EmbeddingBackend | None = None
        self._backend_name: str = "none"
        self._init_backend()

    def _init_backend(self) -> None:
        """Try sentence-transformers, fall back to TF-IDF stub."""
        try:
            from sentence_transformers import SentenceTransformer
            self._backend = SentenceTransformer("all-MiniLM-L6-v2")
            self._backend_name = "sentence-transformers"
        except ImportError:
            self._backend = None
            self._backend_name = "tfidf-fallback"

    def embed(self, text: str) -> np.ndarray:
        """Return embedding vector for text, using cache."""
        key = hashlib.md5(text.encode()).hexdigest()
        if key not in self._cache:
            if len(self._cache) >= self.MAX_CACHE_SIZE:
                # Evict oldest 10%
                evict_keys = list(self._cache.keys())[:self.MAX_CACHE_SIZE // 10]
                for k in evict_keys:
                    del self._cache[k]
            self._cache[key] = self._compute(text)
        return self._cache[key]

    def _compute(self, text: str) -> np.ndarray:
        if self._backend is not None:
            return self._backend.encode([text])[0]
        return self._tfidf_fallback(text)

    def _tfidf_fallback(self, text: str) -> np.ndarray:
        """64-dim deterministic hash vector. Not semantically meaningful but consistent."""
        vec = np.zeros(64, dtype=np.float32)
        words = text.lower().split()
        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            vec[h % 64] += 1.0 / (i + 1)  # position-weighted
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Returns cosine similarity in [0, 1]."""
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    @property
    def backend_name(self) -> str:
        return self._backend_name
```

---

## File 2: `src/agents/memory.py` — Full Replacement

Replace all three stubs. Complete implementation:

```python
from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from src.taxonomy.schema import MemoryEntry, BrandMemory, PurchaseEvent
from src.agents.embedding_cache import EmbeddingCache

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona

# Module-level embedding cache — shared across all MemoryManager instances
_EMBEDDING_CACHE = EmbeddingCache()

# Recency decay constant: 0.5% decay per simulated hour
RECENCY_DECAY_FACTOR = 0.995

class MemoryManager:
    """
    Manages a persona's episodic memory store.

    Design notes:
      - episodic_memory lives on the Persona object itself (source of truth)
      - MemoryManager is a stateless operator: it reads/writes persona.episodic_memory
      - Recency scores are computed relative to 'simulation_tick' (int hours since sim start)
      - Importance index (dict keyed by content hash) is rebuilt lazily, not persisted
    """

    def __init__(self, persona: Persona):
        self.persona = persona
        self._embed = _EMBEDDING_CACHE
        self._importance_index: dict[str, float] | None = None

    def add_episodic(self, event: dict) -> None:
        """
        Append a new MemoryEntry to persona.episodic_memory.

        Args:
            event: dict with keys:
                event_type (str)    — "stimulus" | "decision" | "reflection" | "purchase"
                content    (str)    — human-readable description of what happened
                emotional_valence   (float, -1 to 1, optional, default 0.0)
                salience   (float, 0 to 1, optional, default derived from importance)
                simulation_tick     (int, optional) — hours since sim start

        Side effects:
            - Appends MemoryEntry to persona.episodic_memory
            - Invalidates _importance_index cache
            - Caps episodic_memory at 1000 entries (evict lowest salience)
        """
        entry = MemoryEntry(
            timestamp=event.get("timestamp", datetime.now(timezone.utc).isoformat()),
            event_type=event.get("event_type", "stimulus"),
            content=event["content"],
            emotional_valence=float(event.get("emotional_valence", 0.0)),
            salience=float(event.get("salience", self._estimate_base_salience(event))),
        )
        self.persona.episodic_memory.append(entry)
        self._importance_index = None  # invalidate cache

        # Memory cap: evict lowest-salience if over 1000
        MAX_ENTRIES = 1000
        if len(self.persona.episodic_memory) > MAX_ENTRIES:
            self.persona.episodic_memory.sort(key=lambda m: m.salience, reverse=True)
            self.persona.episodic_memory = self.persona.episodic_memory[:MAX_ENTRIES]

    def update_semantic(self, key: str, value: object) -> None:
        """
        Update a named semantic fact about the persona's world model.

        Semantic memory is stored as a structured MemoryEntry with
        event_type="semantic" and content=f"{key}: {value}".
        If an entry with the same key already exists, it is replaced.

        Args:
            key:   semantic key, e.g. "brand_trust:littlejoys"
            value: any JSON-serialisable value
        """
        content = f"{key}: {value}"
        # Remove existing entry with same key prefix
        self.persona.episodic_memory = [
            m for m in self.persona.episodic_memory
            if not (m.event_type == "semantic" and m.content.startswith(f"{key}:"))
        ]
        entry = MemoryEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="semantic",
            content=content,
            emotional_valence=0.0,
            salience=0.7,
        )
        self.persona.episodic_memory.append(entry)
        self._importance_index = None

    def update_brand_memory(self, brand: str, touchpoint: dict) -> None:
        """
        Update accumulated brand impressions on persona.brand_memories.

        Args:
            brand:      brand name key (e.g. "littlejoys", "horlicks")
            touchpoint: dict with keys:
                channel      (str)   — "ad" | "purchase" | "wom" | "review" | "in_store"
                sentiment    (float) — -1.0 to 1.0
                content      (str)   — description of the touchpoint
                trust_delta  (float, optional) — direct trust adjustment (-0.2 to +0.2)

        Side effects:
            - Creates BrandMemory if brand not in persona.brand_memories
            - Updates trust_level using exponential moving average (alpha=0.3)
            - Appends to word_of_mouth_received if channel="wom"
            - Also appends an episodic memory entry for the touchpoint
        """
        if brand not in self.persona.brand_memories:
            self.persona.brand_memories[brand] = BrandMemory(
                brand_name=brand,
                first_exposure=datetime.now(timezone.utc).isoformat(),
                exposure_channel=touchpoint.get("channel", "unknown"),
            )

        bm = self.persona.brand_memories[brand]

        # Trust update: EMA alpha=0.3 (new signal weighted 30%)
        sentiment = float(touchpoint.get("sentiment", 0.0))
        trust_delta = float(touchpoint.get("trust_delta", 0.0))
        sentiment_norm = (sentiment + 1.0) / 2.0
        bm.trust_level = round(
            0.7 * bm.trust_level + 0.3 * sentiment_norm + trust_delta, 4
        )
        bm.trust_level = max(0.0, min(1.0, bm.trust_level))

        channel = touchpoint.get("channel", "unknown")
        content = touchpoint.get("content", "")

        if channel == "wom":
            bm.word_of_mouth_received.append(content)

        self.add_episodic({
            "event_type": "brand_touchpoint",
            "content": f"[{brand}] via {channel}: {content}",
            "emotional_valence": sentiment * 0.5,
            "salience": abs(trust_delta) * 2 + 0.3,
        })

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        simulation_tick: int = 0,
        alpha: float = 0.35,   # recency weight
        beta: float = 0.35,    # importance weight
        gamma: float = 0.30,   # relevance weight
    ) -> list[MemoryEntry]:
        """
        Retrieve top-K memories most relevant to a query.

        Score = alpha*recency(t) + beta*importance(m) + gamma*relevance(m, query)

        recency(t)    = RECENCY_DECAY_FACTOR ^ (simulation_tick - entry_tick)
        importance(m) = m.salience * (1 + |m.emotional_valence|)  [capped at 1.0]
        relevance     = cosine_similarity(embed(query), embed(m.content))

        Args:
            query:           description of the current scenario/stimulus
            top_k:           number of entries to return (default 10)
            simulation_tick: current simulated time (hours since sim start)
            alpha/beta/gamma: retrieval weights (must sum to 1.0)
        """
        if not self.persona.episodic_memory:
            return []

        query_vec = self._embed.embed(query)
        scored = []

        for i, mem in enumerate(self.persona.episodic_memory):
            estimated_tick = i
            tick_delta = max(0, simulation_tick - estimated_tick)
            recency = RECENCY_DECAY_FACTOR ** tick_delta

            importance = mem.salience * (1.0 + abs(mem.emotional_valence))
            importance = min(importance, 1.0)

            mem_vec = self._embed.embed(mem.content)
            relevance = self._embed.cosine_similarity(query_vec, mem_vec)

            score = alpha * recency + beta * importance + gamma * relevance
            scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:top_k]]

    def _estimate_base_salience(self, event: dict) -> float:
        defaults = {
            "purchase": 0.85,
            "decision": 0.75,
            "reflection": 0.70,
            "brand_touchpoint": 0.55,
            "stimulus": 0.50,
            "semantic": 0.65,
        }
        return defaults.get(event.get("event_type", "stimulus"), 0.50)
```

---

## Acceptance Criteria

- [ ] All three `NotImplementedError` stubs replaced
- [ ] `add_episodic` correctly appends `MemoryEntry` to `persona.episodic_memory`
- [ ] Memory cap enforced at 1000 entries, lowest salience evicted
- [ ] `update_semantic` replaces existing entry with same key — no duplicates
- [ ] `update_brand_memory` creates `BrandMemory` on first call for a brand
- [ ] `retrieve` returns `top_k` entries sorted by descending score
- [ ] `EmbeddingCache` initialises without crashing if `sentence-transformers` not installed
- [ ] `python -c "from src.agents.memory import MemoryManager"` exits 0
- [ ] All existing imports in `memory.py` preserved
