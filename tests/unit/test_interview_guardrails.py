"""Unit tests for interview post-response guardrails."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.analysis.interview_guardrails import (
    check_cross_turn_consistency,
    check_reframing_susceptibility,
    check_scope_violation,
    check_sec_coherence,
    run_all_guardrails,
)
from src.analysis.interviews import InterviewTurn

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


def test_scope_violation_flags_out_of_scope_topics() -> None:
    response = "Honestly I follow the stock market and parliament updates every night."
    warnings = check_scope_violation(response)
    assert "scope_violation:stock market" in warnings
    assert "scope_violation:parliament" in warnings


def test_scope_violation_skips_child_cricket_context() -> None:
    response = "My son has cricket practice, so mornings are rushed and breakfast gets delayed."
    warnings = check_scope_violation(response)
    assert "scope_violation:cricket" not in warnings


def test_scope_violation_uses_word_boundaries() -> None:
    response = "I contemplate buying later once salaries are credited."
    warnings = check_scope_violation(response)
    assert warnings == []


def test_sec_coherence_flags_low_income_premium_reference(sample_persona: Persona) -> None:
    persona = sample_persona.model_copy(
        update={
            "demographics": sample_persona.demographics.model_copy(
                update={"socioeconomic_class": "C1", "household_income_lpa": 6.5}
            )
        },
        deep=True,
    )
    warnings = check_sec_coherence(
        "We usually buy curated imported options from Organic Harvest.", persona
    )
    assert "sec_incoherent_premium_reference" in warnings


def test_sec_coherence_flags_a1_affordability_claim(sample_persona: Persona) -> None:
    persona = sample_persona.model_copy(
        update={
            "demographics": sample_persona.demographics.model_copy(
                update={"socioeconomic_class": "A1", "household_income_lpa": 30.0}
            )
        },
        deep=True,
    )
    warnings = check_sec_coherence("We can't afford this at all this month.", persona)
    assert "sec_incoherent_affordability_claim" in warnings


def test_reframing_susceptibility_detects_loaded_question_agreement() -> None:
    question = "Don't you think every good parent should buy this immediately?"
    response = "You're absolutely right, yes exactly."
    warnings = check_reframing_susceptibility(response, question)
    assert warnings == ["reframing_susceptibility_high"]


def test_cross_turn_consistency_detects_sentiment_flip(sample_persona: Persona) -> None:
    previous_turns = [
        InterviewTurn(
            role="persona",
            content="I would not buy this, it feels like a waste of money for us.",
            timestamp="2026-03-29T00:00:00Z",
        )
    ]
    warnings = check_cross_turn_consistency(
        "Now I love it and would buy this every month.",
        previous_turns,
        sample_persona,
    )
    assert "sentiment_flip_detected" in warnings


def test_cross_turn_consistency_detects_brand_contradiction(sample_persona: Persona) -> None:
    previous_turns = [
        InterviewTurn(
            role="persona",
            content="I use Horlicks every day for my child.",
            timestamp="2026-03-29T00:00:00Z",
        )
    ]
    warnings = check_cross_turn_consistency(
        "I have never used horlicks and don't use it at all.",
        previous_turns,
        sample_persona,
    )
    assert "brand_reference_contradiction" in warnings


def test_run_all_guardrails_aggregates_checks(sample_persona: Persona) -> None:
    persona = sample_persona.model_copy(
        update={
            "demographics": sample_persona.demographics.model_copy(
                update={"socioeconomic_class": "C2", "household_income_lpa": 5.0}
            )
        },
        deep=True,
    )
    previous_turns = [
        InterviewTurn(
            role="persona",
            content="I would not buy this and we don't use Horlicks.",
            timestamp="2026-03-29T00:00:00Z",
        )
    ]
    response = (
        "You're absolutely right, yes exactly. We buy imported curated products and I use Horlicks "
        "now. Also I track the stock market."
    )
    warnings = run_all_guardrails(
        response=response,
        question="Don't you think this is obviously better?",
        persona=persona,
        decision_result={"outcome": "reject"},
        previous_turns=previous_turns,
    )
    assert "reframing_susceptibility_high" in warnings
    assert "sec_incoherent_premium_reference" in warnings
    assert "scope_violation:stock market" in warnings
    assert "brand_reference_contradiction" in warnings
