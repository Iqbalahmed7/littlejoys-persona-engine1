"""Unit tests for probing tree data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.probing.models import (
    AttributeSplit,
    Hypothesis,
    InterviewResponse,
    Probe,
    ProbeResult,
    ProbeType,
    ProblemStatement,
    ResponseCluster,
    TreeSynthesis,
)


def test_problem_statement_creation() -> None:
    """ProblemStatement with all required fields."""

    problem = ProblemStatement(
        id="repeat_purchase_low",
        title="Why is repeat purchase low despite high NPS?",
        scenario_id="nutrimix_2_6",
        context="Repeat purchase is softer than expected.",
        success_metric="repeat_rate",
    )

    assert problem.id == "repeat_purchase_low"
    assert problem.target_population_filter == {}


def test_hypothesis_enabled_by_default() -> None:
    """New hypothesis is enabled."""

    hypothesis = Hypothesis(
        id="h1",
        problem_id="repeat_purchase_low",
        title="Price memory fades",
        rationale="Families compare more rationally on the second purchase.",
        indicator_attributes=["budget_consciousness"],
    )

    assert hypothesis.enabled is True
    assert hypothesis.order == 0


def test_probe_types_enum() -> None:
    """All 3 probe types exist."""

    assert {member.value for member in ProbeType} == {"interview", "simulation", "attribute"}


def test_probe_result_with_clusters() -> None:
    """ProbeResult accepts interview cluster data."""

    result = ProbeResult(
        probe_id="probe-1",
        confidence=0.72,
        evidence_summary="Price concerns dominated the sample.",
        sample_size=30,
        population_size=120,
        clustering_method="keyword",
        interview_responses=[
            InterviewResponse(
                persona_id="p1",
                persona_name="Mumbai Parent",
                outcome="reject",
                content="The price felt steep the second time.",
            )
        ],
        response_clusters=[
            ResponseCluster(
                theme="price_sensitivity",
                description="Concerns about price or value for money",
                persona_count=18,
                percentage=0.6,
                representative_quotes=["The price felt steep the second time."],
                dominant_attributes={"budget_consciousness": 0.84},
            )
        ],
    )
    probe = Probe(
        id="probe-1",
        hypothesis_id="h1",
        probe_type=ProbeType.INTERVIEW,
        result=result,
    )

    assert probe.result is not None
    assert probe.result.response_clusters[0].theme == "price_sensitivity"


def test_probe_result_with_splits() -> None:
    """ProbeResult accepts attribute split data."""

    result = ProbeResult(
        probe_id="probe-2",
        confidence=0.64,
        evidence_summary="Price sensitivity differs strongly by outcome.",
        sample_size=120,
        attribute_splits=[
            AttributeSplit(
                attribute="budget_consciousness",
                adopter_mean=0.31,
                rejector_mean=0.82,
                effect_size=-0.88,
                significant=True,
            )
        ],
    )

    assert result.attribute_splits[0].significant is True
    assert result.attribute_splits[0].attribute == "budget_consciousness"


def test_tree_synthesis_creation() -> None:
    """TreeSynthesis with full data."""

    synthesis = TreeSynthesis(
        problem_id="repeat_purchase_low",
        hypotheses_tested=4,
        hypotheses_confirmed=2,
        dominant_hypothesis="h3_no_reengagement",
        confidence_ranking=[("h3_no_reengagement", 0.82), ("h1_price_reeval", 0.71)],
        synthesis_narrative="Re-engagement is the strongest driver, with price as a secondary factor.",
        recommended_actions=["Add reorder reminders.", "Test value messaging."],
        overall_confidence=0.82,
        disabled_hypotheses=["h2_taste_fatigue"],
        confidence_impact_of_disabled=0.04,
        total_cost_estimate=0.44,
    )

    assert synthesis.dominant_hypothesis == "h3_no_reengagement"
    assert synthesis.disabled_hypotheses == ["h2_taste_fatigue"]


def test_extra_fields_forbidden() -> None:
    """Models reject unknown fields."""

    with pytest.raises(ValidationError):
        ProblemStatement(
            id="repeat_purchase_low",
            title="Why is repeat purchase low despite high NPS?",
            scenario_id="nutrimix_2_6",
            context="Repeat purchase is softer than expected.",
            success_metric="repeat_rate",
            unexpected="boom",
        )
