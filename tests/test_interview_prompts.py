"""Tests for the 5-layer interview prompt system."""

import pytest

try:
    from src.analysis.interview_prompts import (
        BELIEF_CATEGORIES,
        BELIEF_CONVERTERS,
        assemble_system_prompt,
        build_decision_narrative,
        build_identity_anchor,
        build_scope_guardrails,
    )
except ImportError:
    pytest.skip("Sprint 9 Track A not yet merged", allow_module_level=True)

class TestBeliefConverters:
    """Each belief converter must produce valid text for all score ranges."""

    @pytest.mark.parametrize("score", [0.0, 0.15, 0.25, 0.50, 0.75, 0.90, 1.0])
    def test_budget_consciousness_all_tiers(self, score):
        result = BELIEF_CONVERTERS["budget_consciousness"](score)
        assert isinstance(result, str)
        assert len(result) > 20  # non-trivial text

    @pytest.mark.parametrize("score", [0.0, 0.25, 0.50, 0.75, 1.0])
    def test_health_anxiety_all_tiers(self, score):
        result = BELIEF_CONVERTERS["health_anxiety"](score)
        assert isinstance(result, str)
        assert len(result) > 20

    def test_all_converters_exist_for_categories(self):
        """Every attribute listed in BELIEF_CATEGORIES must have a converter."""
        for category, attrs in BELIEF_CATEGORIES.items():
            for attr in attrs:
                assert attr in BELIEF_CONVERTERS, (
                    f"Missing converter for {attr} in category {category}"
                )

    def test_minimum_converter_count(self):
        """Must have at least 15 converters."""
        assert len(BELIEF_CONVERTERS) >= 15

    def test_converters_produce_different_text_for_extremes(self):
        """High and low scores should produce different belief statements."""
        for attr, converter in BELIEF_CONVERTERS.items():
            high = converter(0.9)
            low = converter(0.1)
            assert high != low, f"Converter for {attr} returns same text for 0.9 and 0.1"

    def test_all_categories_non_empty(self):
        """Each belief category must contain at least one attribute."""
        for category, attrs in BELIEF_CATEGORIES.items():
            assert len(attrs) >= 1, f"Category {category} is empty"


@pytest.fixture
def sample_persona():
    """Create a minimal persona for testing.

    Load from disk if available, otherwise skip.
    """
    from pathlib import Path

    from src.generation.population import Population

    pop_path = Path("data/population")
    if not pop_path.exists():
        pytest.skip("Population data not generated")
    pop = Population.load(pop_path)
    return pop.tier1_personas[0]

@pytest.fixture
def sample_decision_result():
    return {
        "outcome": "reject",
        "need_score": 0.65,
        "awareness_score": 0.22,
        "consideration_score": 0.0,
        "purchase_score": 0.0,
        "rejection_stage": "awareness",
        "rejection_reason": "low_awareness",
    }


class TestIdentityAnchor:
    def test_contains_city_name(self, sample_persona):
        anchor = build_identity_anchor(sample_persona)
        assert sample_persona.demographics.city_name in anchor

    def test_contains_age(self, sample_persona):
        anchor = build_identity_anchor(sample_persona)
        assert str(sample_persona.demographics.parent_age) in anchor

    def test_contains_children_description(self, sample_persona):
        anchor = build_identity_anchor(sample_persona)
        assert "child" in anchor.lower() or "son" in anchor.lower() or "daughter" in anchor.lower()

    def test_contains_employment_description(self, sample_persona):
        anchor = build_identity_anchor(sample_persona)
        assert str(sample_persona.career.employment_status).replace("_", " ") in anchor.lower()

    def test_contains_not_role_playing(self, sample_persona):
        anchor = build_identity_anchor(sample_persona)
        assert "NOT role-playing" in anchor or "NOT an AI" in anchor or "NOT roleplaying" in anchor

    def test_does_not_contain_raw_id(self, sample_persona):
        anchor = build_identity_anchor(sample_persona)
        assert sample_persona.id not in anchor


class _MockProduct:
    name = "NutriMix"
    category = "health_drink"
class _MockScenario:
    product = _MockProduct()

@pytest.fixture
def mock_scenario():
    return _MockScenario()

class TestDecisionNarrative:
    def test_adopter_contains_product_name(self, sample_persona, mock_scenario):
        result = build_decision_narrative(sample_persona, {"outcome": "adopt"}, mock_scenario)
        assert "NutriMix" in result

    def test_adopter_contains_positive_language(self, sample_persona, mock_scenario):
        result = build_decision_narrative(sample_persona, {"outcome": "adopt"}, mock_scenario)
        assert any(word in result.lower() for word in ["buy", "purchased", "use", "adopted", "bought", "try", "repeat"])

    def test_rejector_need_recognition(self, sample_persona, mock_scenario):
        result = build_decision_narrative(sample_persona, {"outcome": "reject", "rejection_stage": "need_recognition"}, mock_scenario)
        assert "need" in result.lower() or "didn't feel" in result.lower()

    def test_rejector_awareness(self, sample_persona, mock_scenario):
        result = build_decision_narrative(sample_persona, {"outcome": "reject", "rejection_stage": "awareness"}, mock_scenario)
        assert "never came across" in result.lower() or "not aware" in result.lower()

    def test_rejector_consideration(self, sample_persona, mock_scenario):
        result = build_decision_narrative(sample_persona, {"outcome": "reject", "rejection_stage": "consideration"}, mock_scenario)
        assert "did not click" in result.lower() or "switching takes" in result.lower() or "considered" in result.lower()

    def test_rejector_purchase(self, sample_persona, mock_scenario):
        result = build_decision_narrative(sample_persona, {"outcome": "reject", "rejection_stage": "purchase"}, mock_scenario)
        assert "price" in result.lower() or "did not pull" in result.lower() or "cart" in result.lower() or "expensive" in result.lower() or "considered" in result.lower()

    def test_narrative_does_not_contain_raw_scores(self, sample_persona, mock_scenario):
        result = build_decision_narrative(sample_persona, {"outcome": "reject", "rejection_stage": "awareness", "awareness_score": 0.45}, mock_scenario)
        assert "0.45" not in result


class TestScopeGuardrails:
    def test_contains_will_answer(self, mock_scenario):
        guardrails = build_scope_guardrails(mock_scenario)
        assert "WILL answer" in guardrails or "will answer" in guardrails.lower() or "answer" in guardrails.lower()

    def test_contains_will_not_answer(self, mock_scenario):
        guardrails = build_scope_guardrails(mock_scenario)
        assert "WILL NOT answer" in guardrails or "will not answer" in guardrails.lower()

    def test_contains_product_name(self, mock_scenario):
        guardrails = build_scope_guardrails(mock_scenario)
        assert "NutriMix" in guardrails


class TestAssembly:
    def test_assemble_returns_non_empty(self, sample_persona, sample_decision_result):
        prompt = assemble_system_prompt(sample_persona, "nutrimix_2_6", sample_decision_result)
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_contains_layer_separators(self, sample_persona, sample_decision_result):
        prompt = assemble_system_prompt(sample_persona, "nutrimix_2_6", sample_decision_result)
        assert "---" in prompt

    def test_contains_text_from_all_layers(self, sample_persona, sample_decision_result):
        prompt = assemble_system_prompt(sample_persona, "nutrimix_2_6", sample_decision_result)
        assert sample_persona.demographics.city_name in prompt  # layer 1
        assert "WILL NOT answer" in prompt or "will not answer" in prompt.lower()  # layer 4
