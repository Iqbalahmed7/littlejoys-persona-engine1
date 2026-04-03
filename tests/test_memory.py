"""Tests for MemoryManager and EmbeddingCache."""
import pytest
from unittest.mock import patch
import numpy as np
import copy

from src.agents.memory import MemoryManager
from src.agents.embedding_cache import EmbeddingCache
from src.taxonomy.schema import MemoryEntry


class TestEmbeddingCache:
    def test_embed_returns_numpy_array(self):
        cache = EmbeddingCache()
        vec = cache.embed("test sentence")
        assert isinstance(vec, np.ndarray)

    def test_embed_same_text_returns_same_vector(self):
        cache = EmbeddingCache()
        v1 = cache.embed("hello world")
        v2 = cache.embed("hello world")
        np.testing.assert_array_equal(v1, v2)

    def test_embed_different_texts_returns_different_vectors(self):
        cache = EmbeddingCache()
        v1 = cache.embed("hello world")
        v2 = cache.embed("completely different content")
        assert not np.array_equal(v1, v2)

    def test_cosine_similarity_same_vector_returns_one(self):
        cache = EmbeddingCache()
        v = cache.embed("test")
        sim = cache.cosine_similarity(v, v)
        assert abs(sim - 1.0) < 1e-5

    def test_cosine_similarity_zero_vector_returns_zero(self):
        cache = EmbeddingCache()
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 0.0, 0.0])
        sim = cache.cosine_similarity(v1, v2)
        assert sim == 0.0

    def test_lru_eviction_does_not_crash(self):
        cache = EmbeddingCache()
        cache.MAX_CACHE_SIZE = 10
        for i in range(25):
            cache.embed(f"unique text number {i} with extra words")
        assert len(cache._cache) <= 10

    def test_backend_name_is_string(self):
        cache = EmbeddingCache()
        assert isinstance(cache.backend_name, str)
        assert cache.backend_name in ("sentence-transformers", "tfidf-fallback")


class TestMemoryManagerAddEpisodic:
    def test_add_episodic_creates_memory_entry(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm.add_episodic({
            "event_type": "stimulus",
            "content": "Saw LittleJoys ad on Instagram",
            "emotional_valence": 0.3,
            "salience": 0.6,
        })
        assert len(minimal_persona.episodic_memory) == 1
        entry = minimal_persona.episodic_memory[0]
        assert isinstance(entry, MemoryEntry)
        assert entry.content == "Saw LittleJoys ad on Instagram"
        assert entry.emotional_valence == pytest.approx(0.3)
        assert entry.salience == pytest.approx(0.6)

    def test_add_episodic_defaults_salience_for_purchase(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm.add_episodic({"event_type": "purchase", "content": "Bought LittleJoys"})
        assert minimal_persona.episodic_memory[0].salience >= 0.8

    def test_add_episodic_defaults_salience_for_stimulus(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm.add_episodic({"event_type": "stimulus", "content": "Saw an ad"})
        assert minimal_persona.episodic_memory[0].salience == pytest.approx(0.5)

    def test_add_episodic_memory_cap_at_1000(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        for i in range(1050):
            mm.add_episodic({"event_type": "stimulus", "content": f"Event {i}", "salience": float(i) / 1050})
        assert len(minimal_persona.episodic_memory) <= 1000

    def test_add_episodic_keeps_highest_salience_after_cap(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        for i in range(999):
            mm.add_episodic({"event_type": "stimulus", "content": f"Low event {i}", "salience": 0.1})
        mm.add_episodic({"event_type": "purchase", "content": "IMPORTANT PURCHASE EVENT", "salience": 0.99})
        mm.add_episodic({"event_type": "stimulus", "content": "Trigger eviction", "salience": 0.1})
        contents = [m.content for m in minimal_persona.episodic_memory]
        assert "IMPORTANT PURCHASE EVENT" in contents

    def test_add_episodic_multiple_entries_accumulate(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        for i in range(5):
            mm.add_episodic({"event_type": "stimulus", "content": f"Event {i}"})
        assert len(minimal_persona.episodic_memory) == 5

    def test_add_episodic_invalidates_importance_index(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm._importance_index = {"fake": 1.0}
        mm.add_episodic({"event_type": "stimulus", "content": "New event"})
        assert mm._importance_index is None


class TestMemoryManagerUpdateSemantic:
    def test_update_semantic_creates_entry(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm.update_semantic("brand_trust:littlejoys", 0.7)
        assert any(
            m.event_type == "semantic" and "brand_trust:littlejoys" in m.content
            for m in minimal_persona.episodic_memory
        )

    def test_update_semantic_replaces_existing_key(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm.update_semantic("brand_trust:littlejoys", 0.5)
        mm.update_semantic("brand_trust:littlejoys", 0.8)
        semantic_entries = [
            m for m in minimal_persona.episodic_memory
            if m.event_type == "semantic" and "brand_trust:littlejoys" in m.content
        ]
        assert len(semantic_entries) == 1
        assert "0.8" in semantic_entries[0].content

    def test_update_semantic_different_keys_coexist(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm.update_semantic("brand_trust:littlejoys", 0.7)
        mm.update_semantic("brand_trust:horlicks", 0.3)
        semantic_entries = [m for m in minimal_persona.episodic_memory if m.event_type == "semantic"]
        assert len(semantic_entries) == 2

    def test_update_semantic_high_base_salience(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm.update_semantic("category_belief:supplements", "necessary")
        entry = next(m for m in minimal_persona.episodic_memory if m.event_type == "semantic")
        assert entry.salience >= 0.6


class TestMemoryManagerUpdateBrand:
    def test_update_brand_creates_brand_memory(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm.update_brand_memory("littlejoys", {"channel": "ad", "sentiment": 0.6, "content": "Instagram ad"})
        assert "littlejoys" in minimal_persona.brand_memories

    def test_update_brand_trust_increases_with_positive_sentiment(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        # Directly initialize if brand_memories dict is empty or not yet populated. Trust default 0.4.
        mm.update_brand_memory("littlejoys", {"channel": "ad", "sentiment": 0.0, "content": "init"})
        initial_trust = minimal_persona.brand_memories["littlejoys"].trust_level
        for _ in range(5):
            mm.update_brand_memory("littlejoys", {"channel": "purchase", "sentiment": 0.9, "content": "positive"})
        assert minimal_persona.brand_memories["littlejoys"].trust_level > initial_trust

    def test_update_brand_wom_appended(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm.update_brand_memory("littlejoys", {
            "channel": "wom", "sentiment": 0.5, "content": "Friend recommended it"
        })
        assert len(minimal_persona.brand_memories["littlejoys"].word_of_mouth_received) == 1

    def test_update_brand_also_writes_episodic_memory(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm.update_brand_memory("testbrand", {"channel": "ad", "sentiment": 0.3, "content": "tv ad"})
        assert any("testbrand" in m.content for m in minimal_persona.episodic_memory)

    def test_update_brand_trust_stays_in_unit_interval(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        for _ in range(20):
            mm.update_brand_memory("littlejoys", {"channel": "purchase", "sentiment": 1.0, "content": "great"})
        trust = minimal_persona.brand_memories["littlejoys"].trust_level
        assert 0.0 <= trust <= 1.0


class TestMemoryManagerRetrieve:
    def test_retrieve_returns_top_k(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        for i in range(20):
            mm.add_episodic({"event_type": "stimulus", "content": f"Event about nutrition {i}"})
        results = mm.retrieve("nutrition supplement for child", top_k=5)
        assert len(results) == 5

    def test_retrieve_empty_memory_returns_empty(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        results = mm.retrieve("anything", top_k=10)
        assert results == []

    def test_retrieve_returns_memory_entry_objects(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm.add_episodic({"event_type": "stimulus", "content": "Saw LittleJoys ad"})
        results = mm.retrieve("LittleJoys", top_k=1)
        assert len(results) == 1
        assert isinstance(results[0], MemoryEntry)

    def test_retrieve_fewer_than_k_returns_all(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        mm.add_episodic({"event_type": "stimulus", "content": "Only entry"})
        results = mm.retrieve("query", top_k=10)
        assert len(results) == 1

    def test_retrieve_high_salience_memory_in_top_results(self, minimal_persona):
        mm = MemoryManager(minimal_persona)
        for i in range(15):
            mm.add_episodic({"event_type": "stimulus", "content": "irrelevant noise event", "salience": 0.1})
        mm.add_episodic({
            "event_type": "purchase",
            "content": "Bought LittleJoys chocolate flavour. Child loved it.",
            "salience": 0.9,
        })
        results = mm.retrieve("LittleJoys chocolate purchase", top_k=5)
        contents = [m.content for m in results]
        assert any("LittleJoys" in c for c in contents)
