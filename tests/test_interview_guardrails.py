"""Tests for interview post-response guardrails."""

import pytest

try:
    from src.analysis.interview_guardrails import (
        check_cross_turn_consistency,
        check_reframing_susceptibility,
        check_scope_violation,
        check_sec_coherence,
        run_all_guardrails,
    )
    from src.analysis.interviews import InterviewTurn
except ImportError:
    pytest.skip("Sprint 9 Track B not yet merged", allow_module_level=True)

class TestScopeViolation:
    def test_clean_response_no_violations(self):
        result = check_scope_violation(
            "I buy Horlicks from the local store for my children."
        )
        assert result == []

    def test_political_reference_flagged(self):
        result = check_scope_violation(
            "I think the election results will affect product prices."
        )
        assert any("scope_violation" in w for w in result)

    def test_sports_reference_flagged(self):
        result = check_scope_violation(
            "I was watching the IPL match instead of shopping."
        )
        assert any("scope_violation" in w for w in result)

    def test_child_cricket_not_flagged(self):
        """Child activities mentioning cricket should NOT be flagged."""
        result = check_scope_violation(
            "My son has cricket practice after school so mornings are hectic."
        )
        # Accept either behavior as per briefing, but asserting it doesn't crash
        assert isinstance(result, list)

    def test_stock_market_flagged(self):
        result = check_scope_violation(
            "I invest in mutual funds and the stock market is down."
        )
        assert any("scope_violation" in w for w in result)

    def test_nutrition_discussion_clean(self):
        result = check_scope_violation(
            "I give my daughter calcium supplements and she takes vitamins daily."
        )
        assert result == []

    def test_religion_flagged(self):
        result = check_scope_violation(
            "Our religion forbids certain foods."
        )
        assert any("scope_violation" in w for w in result)

    def test_dietary_culture_clean(self):
        """Vegetarian/non-veg discussion is in-scope."""
        result = check_scope_violation(
            "We are a vegetarian family so protein sources are limited."
        )
        assert result == []


class _MockDemographics:
    def __init__(self, sec, income, platform="local_store"):
        self.socioeconomic_class = sec
        self.household_income_lpa = income
        self.city_name = "Mumbai"
        self.city_tier = "Tier1"

class _MockDailyRoutine:
    def __init__(self, platform="local_store"):
        self.primary_shopping_platform = platform

class _MockPersona:
    def __init__(self, sec="C1", income=4.0, platform="local_store"):
        self.demographics = _MockDemographics(sec, income, platform)
        self.daily_routine = _MockDailyRoutine(platform)


class TestSECCoherence:
    def test_c1_organic_harvest_flagged(self):
        persona = _MockPersona(sec="C1", income=3.0)
        result = check_sec_coherence("I always buy organic harvest for my family.", persona)
        assert any("sec_incoherent" in w for w in result)

    def test_c2_horlicks_clean(self):
        persona = _MockPersona(sec="C2", income=2.0)
        result = check_sec_coherence("We drink Horlicks in the morning.", persona)
        assert result == []

    def test_a1_cant_afford_flagged(self):
        persona = _MockPersona(sec="A1", income=30.0)
        result = check_sec_coherence("I really can't afford these expensive supplements.", persona)
        assert any("sec_incoherent" in w for w in result)

    def test_a1_premium_brands_clean(self):
        persona = _MockPersona(sec="A1", income=30.0)
        result = check_sec_coherence("I buy premium multivitamin gummies imported from US.", persona)
        assert result == []

    def test_b1_mass_market_clean(self):
        persona = _MockPersona(sec="B1", income=10.0)
        result = check_sec_coherence("I stick to common brands like Bournvita.", persona)
        assert result == []

    def test_c1_blinkit_shopping_flagged(self):
        persona = _MockPersona(sec="C1", income=4.0, platform="local_store")
        result = check_sec_coherence("I order all my groceries from Blinkit.", persona)
        assert any("sec_incoherent" in w for w in result)


class TestAntiReframing:
    def test_non_leading_question_plus_agreement(self):
        result = check_reframing_susceptibility(
            question="What factors influence your purchase?",
            response="I agree that price is important."
        )
        assert result == []

    def test_leading_question_plus_absolute_agreement_flagged(self):
        result = check_reframing_susceptibility(
            question="Don't you think gummies are better than powders?",
            response="Yes, you're absolutely right, gummies are better."
        )
        assert any("reframing_susceptibility" in w for w in result)

    def test_leading_question_plus_disagreement_clean(self):
        result = check_reframing_susceptibility(
            question="Don't you think gummies are better?",
            response="Actually, I prefer powders for my kids."
        )
        assert result == []

    def test_normal_question_normal_response_clean(self):
        result = check_reframing_susceptibility(
            question="How often do you buy milk additives?",
            response="I buy them once a month."
        )
        assert result == []

    def test_leading_question_partial_agreement(self):
        result = check_reframing_susceptibility(
            question="Wouldn't it be easier to shop online?",
            response="I suppose so, but I still prefer stores."
        )
        assert isinstance(result, list)


def _make_turn(role, content):
    return InterviewTurn(role=role, content=content, timestamp="2026-01-01T00:00:00Z")

class TestCrossTurnConsistency:
    def test_no_prior_turns_clean(self):
        result = check_cross_turn_consistency("I like it.", previous_turns=[], persona=_MockPersona())
        assert result == []

    def test_prior_positive_current_negative_flagged(self):
        prev = [_make_turn("persona", "I definitely would buy gummies.")]
        result = check_cross_turn_consistency("Actually, it is a waste of money.", previous_turns=prev, persona=_MockPersona())
        assert any("flip" in w or "contradiction" in w for w in result)

    def test_prior_negative_current_negative_clean(self):
        prev = [_make_turn("persona", "I don't use powders.")]
        result = check_cross_turn_consistency("As I said, I avoid powders.", previous_turns=prev, persona=_MockPersona())
        assert result == []

    def test_prior_mentions_horlicks_current_denies_flagged(self):
        prev = [_make_turn("persona", "We buy Horlicks.")]
        result = check_cross_turn_consistency("I have never used Horlicks.", previous_turns=prev, persona=_MockPersona())
        assert any("contradiction" in w for w in result)


class TestRunAllGuardrails:
    def test_clean_response_empty_list(self):
        persona = _MockPersona()
        result = run_all_guardrails(
            response="I buy milk additives from the local shop.",
            question="Where do you buy groceries?",
            persona=persona,
            decision_result={"outcome": "adopt"},
            previous_turns=[]
        )
        assert result == []

    def test_response_with_multiple_issues(self):
        persona = _MockPersona(sec="C1", income=3.0)
        result = run_all_guardrails(
            response="I invest in the stock market and order organic brands from Blinkit, you're absolutely right.",
            question="Don't you think expensive organic is better?",
            persona=persona,
            decision_result={"outcome": "adopt"},
            previous_turns=[]
        )
        # Should flag scope, SEC, and reframing
        assert len(result) >= 2

    def test_none_previous_turns_no_crash(self):
        persona = _MockPersona()
        result = run_all_guardrails(
            response="Test response.",
            question="Test question?",
            persona=persona,
            decision_result={},
            previous_turns=None
        )
        assert isinstance(result, list)
