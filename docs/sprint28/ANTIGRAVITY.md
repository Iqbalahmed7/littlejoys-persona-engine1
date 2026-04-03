# Sprint 28 — Brief: ANTIGRAVITY

**Role:** Tests / validation
**Model:** Gemini 3 Flash
**Assignment:** Write the full test suite for Sprint 28 deliverables
**Est. duration:** 3-4 hours
**START:** Only after Cursor + Codex + Goose all signal done

---

## Files to Create

| Action | File |
|---|---|
| CREATE | `tests/conftest.py` (shared fixtures) |
| CREATE | `tests/test_memory.py` |
| CREATE | `tests/test_agent.py` |
| CREATE | `tests/test_constraint_checker.py` |

## Do NOT Touch

Any `src/` file. Read-only for this sprint.

---

## Rules

1. **No real API calls.** All LLM calls must be mocked with `unittest.mock.patch`.
2. Use `pytest`. Add `pytest` and `pytest-mock` to dev requirements if not present.
3. Tests must pass with `pytest tests/` from the project root.
4. Minimum counts: `test_memory.py` ≥ 15 tests, `test_agent.py` ≥ 10 tests, `test_constraint_checker.py` ≥ 20 tests.

---

## File 1: `tests/conftest.py`

```python
import pytest
from src.taxonomy.schema import (
    Persona, DemographicAttributes, PsychologyAttributes,
    HealthAttributes, CulturalAttributes, RelationshipAttributes,
    CareerAttributes, EducationLearningAttributes, LifestyleAttributes,
    DailyRoutineAttributes, ValueAttributes, EmotionalAttributes,
    MediaAttributes, ParentTraits, BudgetProfile, DecisionRights,
)


@pytest.fixture
def minimal_persona():
    """A coherent, minimal persona for testing. Designed to pass all 30 constraint rules."""
    return Persona(
        demographics=DemographicAttributes(
            parent_name="Priya Test",
            parent_age=32,
            parent_gender="female",
            city_tier="Tier2",
            household_income_lpa=8.0,
            household_structure="nuclear",
            num_children=1,
            child_ages=[4],
            child_genders=["female"],
            youngest_child_age=4,
            oldest_child_age=4,
        ),
        psychology=PsychologyAttributes(
            health_anxiety=0.6,
            information_need=0.7,
            social_proof_bias=0.5,
            risk_tolerance=0.4,
            loss_aversion=0.5,
            authority_bias=0.6,
            status_quo_bias=0.4,
            analysis_paralysis_tendency=0.4,
            decision_speed=0.5,
            regret_sensitivity=0.5,
            anchoring_bias=0.5,
            halo_effect_susceptibility=0.5,
            comparison_anxiety=0.5,
            guilt_sensitivity=0.5,
            control_need=0.5,
            mental_bandwidth=0.5,
            decision_fatigue_level=0.5,
            simplicity_preference=0.5,
        ),
        health=HealthAttributes(
            child_health_proactivity=0.6,
            medical_authority_trust=0.6,
        ),
        cultural=CulturalAttributes(
            social_media_active=True,
            mommy_group_membership=False,
        ),
        relationships=RelationshipAttributes(
            elder_advice_weight=0.4,
            pediatrician_influence=0.6,
            influencer_trust=0.4,
            wom_transmitter_tendency=0.5,
        ),
        career=CareerAttributes(
            employment_status="full_time",
            work_hours_per_week=40,
            perceived_time_scarcity=0.5,
            career_ambition=0.5,
        ),
        education_learning=EducationLearningAttributes(
            label_reading_habit=0.5,
        ),
        lifestyle=LifestyleAttributes(),
        daily_routine=DailyRoutineAttributes(
            digital_payment_comfort=0.6,
            budget_consciousness=0.5,
            deal_seeking_intensity=0.5,
            impulse_purchase_tendency=0.3,
            online_vs_offline_preference=0.7,
            milk_supplement_current="none",
        ),
        values=ValueAttributes(
            best_for_my_child_intensity=0.6,
            supplement_necessity_belief=0.5,
            food_first_belief=0.4,
            brand_loyalty_tendency=0.5,
        ),
        emotional=EmotionalAttributes(),
        media=MediaAttributes(
            daily_social_media_hours=1.5,
        ),
        parent_traits=ParentTraits(
            decision_style="analytical",
            trust_anchor="peer",
            risk_appetite="medium",
            primary_value_orientation="features",
            coping_mechanism="research_deep_dive",
            consistency_score=72,
        ),
        budget_profile=BudgetProfile(
            monthly_food_budget_inr=6000,
            discretionary_child_nutrition_budget_inr=1200,
            price_sensitivity="medium",
        ),
        decision_rights=DecisionRights(
            child_nutrition="mother_final",
            grocery_shopping="mother_lead",
            supplements="mother_final",
        ),
    )
```

---

## File 2: `tests/test_memory.py`

```python
"""Tests for MemoryManager and EmbeddingCache."""
import pytest
from unittest.mock import patch
import numpy as np
import copy

from src.agents.memory import MemoryManager, RECENCY_DECAY_FACTOR
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
        for _ in range(5):
            mm.update_brand_memory("littlejoys", {"channel": "purchase", "sentiment": 0.8, "content": "positive"})
        assert minimal_persona.brand_memories["littlejoys"].trust_level > 0.4

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
```

---

## File 3: `tests/test_agent.py`

```python
"""Tests for CognitiveAgent.perceive() and update_memory()."""
import pytest
import json
from unittest.mock import patch, MagicMock
import copy

from src.agents.agent import CognitiveAgent
from src.agents.perception_result import PerceptionResult


@pytest.fixture
def agent(minimal_persona):
    return CognitiveAgent(minimal_persona)


@pytest.fixture
def mock_llm_response():
    return json.dumps({
        "importance": 7,
        "emotional_valence": 0.4,
        "dominant_attributes": ["health_anxiety", "social_proof_bias"],
        "interpretation": "She finds this relevant given her health focus."
    })


class TestCognitiveAgentInit:
    def test_agent_initialises_without_api_calls(self, minimal_persona):
        with patch("anthropic.Anthropic") as mock_anthropic:
            agent = CognitiveAgent(minimal_persona)
            mock_anthropic.assert_not_called()

    def test_agent_has_memory_manager(self, agent):
        from src.agents.memory import MemoryManager
        assert isinstance(agent.memory, MemoryManager)

    def test_agent_client_is_none_at_init(self, agent):
        assert agent._client is None


class TestCognitiveAgentPerceive:
    def test_perceive_returns_perception_result(self, agent, mock_llm_response):
        with patch.object(agent, "_llm_call", return_value=mock_llm_response):
            result = agent.perceive({"type": "ad", "source": "instagram", "content": "LittleJoys ad"})
        assert isinstance(result, PerceptionResult)

    def test_perceive_importance_normalised(self, agent, mock_llm_response):
        with patch.object(agent, "_llm_call", return_value=mock_llm_response):
            result = agent.perceive({"type": "ad", "content": "test", "source": "test"})
        # importance 7 → (7-1)/9 ≈ 0.667
        assert 0.0 <= result.importance <= 1.0
        assert abs(result.importance - 6/9) < 0.01

    def test_perceive_importance_in_unit_interval(self, agent):
        for raw_importance in [1, 5, 10]:
            response = json.dumps({
                "importance": raw_importance,
                "emotional_valence": 0.0,
                "dominant_attributes": [],
                "interpretation": "test"
            })
            with patch.object(agent, "_llm_call", return_value=response):
                result = agent.perceive({"type": "ad", "content": "test", "source": "test"})
            assert 0.0 <= result.importance <= 1.0

    def test_perceive_high_importance_sets_reflection_trigger(self, agent):
        response = json.dumps({"importance": 9, "emotional_valence": 0.7,
                               "dominant_attributes": ["health_anxiety"], "interpretation": "Very relevant."})
        with patch.object(agent, "_llm_call", return_value=response):
            result = agent.perceive({"type": "wom", "content": "critical", "source": "friend"})
        assert result.reflection_trigger_candidate is True

    def test_perceive_low_importance_no_reflection_trigger(self, agent):
        response = json.dumps({"importance": 3, "emotional_valence": 0.0,
                               "dominant_attributes": [], "interpretation": "Not relevant."})
        with patch.object(agent, "_llm_call", return_value=response):
            result = agent.perceive({"type": "ad", "content": "irrelevant", "source": "newspaper"})
        assert result.reflection_trigger_candidate is False

    def test_perceive_writes_to_episodic_memory(self, agent, mock_llm_response):
        initial_count = len(agent.persona.episodic_memory)
        with patch.object(agent, "_llm_call", return_value=mock_llm_response):
            agent.perceive({"type": "ad", "content": "test ad", "source": "instagram"})
        assert len(agent.persona.episodic_memory) == initial_count + 1

    def test_perceive_with_brand_updates_brand_memory(self, agent, mock_llm_response):
        with patch.object(agent, "_llm_call", return_value=mock_llm_response):
            agent.perceive({
                "type": "ad", "content": "LittleJoys new product",
                "source": "instagram", "brand": "littlejoys",
            })
        assert "littlejoys" in agent.persona.brand_memories

    def test_perceive_without_brand_no_brand_memory(self, agent, mock_llm_response):
        with patch.object(agent, "_llm_call", return_value=mock_llm_response):
            agent.perceive({"type": "ad", "content": "generic ad", "source": "instagram"})
        assert len(agent.persona.brand_memories) == 0

    def test_perceive_returns_memory_written_true(self, agent, mock_llm_response):
        with patch.object(agent, "_llm_call", return_value=mock_llm_response):
            result = agent.perceive({"type": "ad", "content": "test", "source": "test"})
        assert result.memory_written is True

    def test_perceive_handles_malformed_json_gracefully(self, agent):
        messy_response = 'Here is the result: {"importance": 5, "emotional_valence": 0.1, "dominant_attributes": [], "interpretation": "ok"} Done!'
        with patch.object(agent, "_llm_call", return_value=messy_response):
            result = agent.perceive({"type": "ad", "content": "test", "source": "test"})
        assert isinstance(result, PerceptionResult)


class TestCognitiveAgentUpdateMemory:
    def test_update_memory_writes_to_episodic_memory(self, agent):
        agent.update_memory({
            "event_type": "decision",
            "content": "Decided to try the product",
            "emotional_valence": 0.2,
            "salience": 0.7,
        })
        assert len(agent.persona.episodic_memory) == 1

    def test_update_memory_no_longer_raises_not_implemented(self, agent):
        try:
            agent.update_memory({"event_type": "stimulus", "content": "test"})
        except NotImplementedError:
            pytest.fail("update_memory still raises NotImplementedError — stub not replaced")


class TestCognitiveAgentDecide:
    def test_decide_raises_not_implemented_before_goose(self, agent):
        """Regression guard: Codex must not have accidentally implemented decide()."""
        with pytest.raises(NotImplementedError):
            agent.decide({"description": "test scenario"})
```

---

## File 4: `tests/test_constraint_checker.py`

```python
"""Tests for ConstraintChecker — all 30 rules."""
import pytest
import copy

from src.agents.constraint_checker import ConstraintChecker, ConstraintViolation


@pytest.fixture
def checker():
    return ConstraintChecker()


class TestConstraintCheckerSetup:
    def test_checker_has_exactly_30_rules(self, checker):
        assert len(checker._rules) == 30

    def test_coherent_persona_has_no_hard_violations(self, checker, minimal_persona):
        hard_violations = checker.check_hard_only(minimal_persona)
        assert len(hard_violations) == 0

    def test_check_returns_list(self, checker, minimal_persona):
        assert isinstance(checker.check(minimal_persona), list)

    def test_check_hard_only_filters_soft(self, checker, minimal_persona):
        violations = checker.check_hard_only(minimal_persona)
        assert all(v.severity == "hard" for v in violations)

    def test_all_rules_have_valid_severity(self, checker):
        for rule in checker._rules:
            assert rule.severity in ("hard", "soft")

    def test_all_rule_ids_unique(self, checker):
        ids = [r.rule_id for r in checker._rules]
        assert len(ids) == len(set(ids))


class TestKnownViolations:
    """Rules 1-4 must catch the 4 violations documented in population_meta.json."""

    def test_r001_low_income_high_aspiration(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.demographics.household_income_lpa = 2.5
        p.values.best_for_my_child_intensity = 0.8
        rule_ids = [v.rule_id for v in checker.check(p)]
        assert "CAT1-R001" in rule_ids

    def test_r002_tier3_high_digital(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.demographics.city_tier = "Tier3"
        p.daily_routine.digital_payment_comfort = 0.9
        rule_ids = [v.rule_id for v in checker.check(p)]
        assert "CAT1-R002" in rule_ids

    def test_r003_low_anxiety_high_supplement(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.psychology.health_anxiety = 0.1
        p.values.supplement_necessity_belief = 0.9
        rule_ids = [v.rule_id for v in checker.check(p)]
        assert "CAT1-R003" in rule_ids

    def test_r004_homemaker_high_time_scarcity(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.career.employment_status = "homemaker"
        p.career.perceived_time_scarcity = 0.85
        rule_ids = [v.rule_id for v in checker.check(p)]
        assert "CAT1-R004" in rule_ids


class TestHardViolations:
    def test_r005_parent_child_age_gap_too_small(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.demographics.parent_age = 20
        p.demographics.oldest_child_age = 5
        assert any(v.rule_id == "CAT1-R005" for v in checker.check_hard_only(p))

    def test_r009_full_time_zero_hours(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.career.employment_status = "full_time"
        p.career.work_hours_per_week = 0
        assert any(v.rule_id == "CAT2-R009" for v in checker.check_hard_only(p))

    def test_r011_discretionary_over_50pct_food_budget(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.budget_profile.monthly_food_budget_inr = 5000
        p.budget_profile.discretionary_child_nutrition_budget_inr = 3000
        assert any(v.rule_id == "CAT2-R011" for v in checker.check_hard_only(p))

    def test_r014_high_risk_high_loss_aversion(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.psychology.risk_tolerance = 0.85
        p.psychology.loss_aversion = 0.85
        assert any(v.rule_id == "CAT3-R014" for v in checker.check_hard_only(p))

    def test_r016_vegan_dairy_supplement(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.cultural.dietary_culture = "vegan"
        p.daily_routine.milk_supplement_current = "horlicks"
        assert any(v.rule_id == "CAT3-R016" for v in checker.check_hard_only(p))

    def test_r017_paralysis_plus_fast_decision(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.psychology.analysis_paralysis_tendency = 0.9
        p.psychology.decision_speed = 0.9
        assert any(v.rule_id == "CAT3-R017" for v in checker.check_hard_only(p))

    def test_r019_no_children_supplement(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.demographics.num_children = 0
        p.daily_routine.milk_supplement_current = "pediasure"
        assert any(v.rule_id == "CAT4-R019" for v in checker.check_hard_only(p))

    def test_r020_extreme_impulse_and_paralysis(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.daily_routine.impulse_purchase_tendency = 0.9
        p.psychology.analysis_paralysis_tendency = 0.9
        assert any(v.rule_id == "CAT4-R020" for v in checker.check_hard_only(p))

    def test_r021_offline_preference_quick_commerce(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.daily_routine.online_vs_offline_preference = 0.1
        p.daily_routine.primary_shopping_platform = "quick_commerce"
        assert any(v.rule_id == "CAT4-R021" for v in checker.check_hard_only(p))

    def test_r024_no_social_media_high_influencer_trust(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.media.daily_social_media_hours = 0.0
        p.relationships.influencer_trust = 0.9
        assert any(v.rule_id == "CAT4-R024" for v in checker.check_hard_only(p))

    def test_r025_doctor_gated_no_doctor_visits(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.decision_rights.supplements = "doctor_gated"
        p.health.pediatrician_visit_frequency = "rarely"
        assert any(v.rule_id == "CAT5-R025" for v in checker.check_hard_only(p))

    def test_r027_supplement_and_food_first_both_extreme(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.values.supplement_necessity_belief = 0.9
        p.values.food_first_belief = 0.9
        assert any(v.rule_id == "CAT5-R027" for v in checker.check_hard_only(p))

    def test_r030_single_parent_joint_rights(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.demographics.household_structure = "single-parent"
        p.decision_rights.child_nutrition = "joint"
        assert any(v.rule_id == "CAT5-R030" for v in checker.check_hard_only(p))


class TestViolationStructure:
    def test_violation_has_all_required_fields(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.demographics.household_income_lpa = 2.0
        p.values.best_for_my_child_intensity = 0.85
        violations = checker.check(p)
        v = next(v for v in violations if v.rule_id == "CAT1-R001")
        assert hasattr(v, "rule_id")
        assert hasattr(v, "message")
        assert hasattr(v, "severity")
        assert hasattr(v, "attribute_a")
        assert hasattr(v, "attribute_b")
        assert hasattr(v, "values")
        assert isinstance(v.message, str) and len(v.message) > 0

    def test_violation_severity_is_valid_enum(self, checker, minimal_persona):
        p = copy.deepcopy(minimal_persona)
        p.demographics.household_income_lpa = 2.0
        p.values.best_for_my_child_intensity = 0.85
        violations = checker.check(p)
        for v in violations:
            assert v.severity in ("hard", "soft")

    def test_no_false_positive_at_threshold_boundary(self, checker, minimal_persona):
        """Exactly at threshold = no violation."""
        p = copy.deepcopy(minimal_persona)
        p.demographics.household_income_lpa = 3.0   # not < 3.0
        p.values.best_for_my_child_intensity = 0.7  # not > 0.7
        rule_ids = [v.rule_id for v in checker.check(p)]
        assert "CAT1-R001" not in rule_ids

    def test_multiple_violations_returned(self, checker, minimal_persona):
        """A badly constructed persona can have multiple violations simultaneously."""
        p = copy.deepcopy(minimal_persona)
        p.psychology.risk_tolerance = 0.9
        p.psychology.loss_aversion = 0.9          # CAT3-R014
        p.psychology.analysis_paralysis_tendency = 0.95
        p.psychology.decision_speed = 0.95        # CAT3-R017
        violations = checker.check_hard_only(p)
        rule_ids = [v.rule_id for v in violations]
        assert "CAT3-R014" in rule_ids
        assert "CAT3-R017" in rule_ids
```

---

## Acceptance Criteria

- [ ] `pytest tests/` exits 0 from project root
- [ ] No real API calls — all LLM calls mocked
- [ ] `test_memory.py`: ≥ 15 tests, all pass
- [ ] `test_agent.py`: ≥ 10 tests, all pass
- [ ] `test_constraint_checker.py`: ≥ 20 tests, all pass
- [ ] All 4 known violations (R001-R004) have dedicated tests
- [ ] At least 8 hard rules tested explicitly
- [ ] `test_decide_raises_not_implemented_before_goose` passes (confirms Codex didn't over-implement)
- [ ] `conftest.py` `minimal_persona` is shared across all 3 test files via pytest fixture discovery
- [ ] Boundary value test present (`test_no_false_positive_at_threshold_boundary`)
