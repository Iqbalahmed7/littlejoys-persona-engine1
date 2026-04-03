"""
Memory management for cognitive agents.

Handles episodic memory formation, semantic memory consolidation,
and brand memory updates during simulation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.agents.embedding_cache import EmbeddingCache
from src.taxonomy.schema import BrandMemory, MemoryEntry, PurchaseEvent

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona

class MemoryManager:
    """
    Manages a persona's memory stores.

    Design notes:
    - Episodic memory is the source of truth for event narratives.
    - Semantic memory is maintained in both structured dict form and mirrored episodic entries.
    - Retrieval combines recency, importance, and embedding relevance.
    """

    MAX_ENTRIES = 1000
    RECENCY_DECAY_FACTOR = 0.995  # 0.5% decay per simulated hour

    _EMBEDDING_CACHE = EmbeddingCache()

    def __init__(self, persona: "Persona") -> None:
        self.persona = persona
        self._embed = self._EMBEDDING_CACHE
        self._importance_index: dict[str, float] | None = None

    def add_episodic(self, event: dict) -> None:
        """Record a new episodic memory from an experience."""
        entry = MemoryEntry(
            timestamp=str(event.get("timestamp") or datetime.now(timezone.utc).isoformat()),
            event_type=str(event.get("event_type", "stimulus")),
            content=str(event.get("content", "")),
            emotional_valence=float(event.get("emotional_valence", 0.0)),
            salience=float(event.get("salience", self._estimate_base_salience(event))),
        )
        self.persona.episodic_memory.append(entry)
        self._importance_index = None

        if len(self.persona.episodic_memory) > self.MAX_ENTRIES:
            self.persona.episodic_memory.sort(key=lambda m: m.salience, reverse=True)
            del self.persona.episodic_memory[self.MAX_ENTRIES :]

    def update_semantic(self, key: str, value: object) -> None:
        """Update a semantic memory (general knowledge/belief)."""
        content = f"{key}: {value}"

        # Keep direct semantic lookup updated for downstream components.
        self.persona.semantic_memory[key] = value

        # Replace semantic mirrors in episodic memory to avoid duplicates for this key.
        self.persona.episodic_memory = [
            m
            for m in self.persona.episodic_memory
            if not (m.event_type == "semantic" and m.content.startswith(f"{key}:"))
        ]
        self.persona.episodic_memory.append(
            MemoryEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="semantic",
                content=content,
                emotional_valence=0.0,
                salience=0.7,
            )
        )
        self._importance_index = None

    def update_brand_memory(self, brand: str, touchpoint: dict) -> None:
        """Update accumulated brand impressions after an interaction."""
        if brand not in self.persona.brand_memories:
            self.persona.brand_memories[brand] = BrandMemory(
                brand_name=brand,
                first_exposure=datetime.now(timezone.utc).isoformat(),
                exposure_channel=str(touchpoint.get("channel", "unknown")),
            )

        bm = self.persona.brand_memories[brand]
        sentiment = float(touchpoint.get("sentiment", 0.0))
        trust_delta = float(touchpoint.get("trust_delta", 0.0))
        sentiment_norm = (sentiment + 1.0) / 2.0

        # EMA update: newer touchpoints carry 30% of signal.
        bm.trust_level = round(0.7 * bm.trust_level + 0.3 * sentiment_norm + trust_delta, 4)
        bm.trust_level = max(0.0, min(1.0, bm.trust_level))

        channel = str(touchpoint.get("channel", "unknown"))
        content = str(touchpoint.get("content", ""))

        if channel == "wom":
            bm.word_of_mouth_received.append(content)

        # Preserve purchase-specific state when purchase touchpoints are provided.
        if channel == "purchase":
            bm.purchase_count += 1
            bm.last_purchase_date = datetime.now(timezone.utc).isoformat()
            satisfaction = float(touchpoint.get("satisfaction", sentiment_norm))
            bm.satisfaction_history.append(max(0.0, min(1.0, satisfaction)))
            self.persona.purchase_history.append(
                PurchaseEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    product=str(touchpoint.get("product", brand)),
                    price_paid=float(touchpoint.get("price_paid", 0.0)),
                    channel=channel,
                    trigger=str(touchpoint.get("trigger", "brand_touchpoint")),
                    outcome=str(touchpoint.get("outcome", "purchased")),
                    satisfaction=max(0.0, min(1.0, satisfaction)),
                )
            )

        self.add_episodic(
            {
                "event_type": "brand_touchpoint",
                "content": f"[{brand}] via {channel}: {content}",
                "emotional_valence": sentiment * 0.5,
                "salience": min(1.0, abs(trust_delta) * 2 + 0.3),
            }
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        simulation_tick: int = 0,
        alpha: float = 0.35,
        beta: float = 0.35,
        gamma: float = 0.30,
    ) -> list[MemoryEntry]:
        """Retrieve top-K memories weighted by recency, importance, and relevance."""
        if not self.persona.episodic_memory:
            return []

        if top_k <= 0:
            return []

        query_vec = self._embed.embed(query)
        scored: list[tuple[float, MemoryEntry]] = []

        for i, mem in enumerate(self.persona.episodic_memory):
            estimated_tick = i
            tick_delta = max(0, simulation_tick - estimated_tick)
            recency = self.RECENCY_DECAY_FACTOR**tick_delta

            importance = min(mem.salience * (1.0 + abs(mem.emotional_valence)), 1.0)
            relevance = self._embed.cosine_similarity(query_vec, self._embed.embed(mem.content))

            score = alpha * recency + beta * importance + gamma * relevance
            scored.append((score, mem))

        scored.sort(key=lambda pair: pair[0], reverse=True)
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
        return float(defaults.get(str(event.get("event_type", "stimulus")), 0.50))
