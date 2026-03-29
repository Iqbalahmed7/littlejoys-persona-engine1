"""Unit tests for probing confidence computations."""

from __future__ import annotations

import pytest

from src.probing.confidence import (
    classify_hypothesis,
    compute_attribute_confidence,
    compute_hypothesis_confidence,
    compute_interview_confidence,
    compute_simulation_confidence,
)
from src.probing.models import AttributeSplit, ResponseCluster


def _cluster(percentage: float, **dominant_attributes: float) -> ResponseCluster:
    return ResponseCluster(
        theme="theme",
        description="Theme description",
        persona_count=max(1, int(percentage * 100)),
        percentage=percentage,
        representative_quotes=["quote"],
        dominant_attributes=dominant_attributes,
    )


def test_interview_confidence_single_dominant_cluster() -> None:
    """High confidence when one cluster dominates."""

    confidence = compute_interview_confidence(
        [
            _cluster(0.8, budget_consciousness=0.82, deal_seeking_intensity=0.78),
            _cluster(0.2, ad_receptivity=0.55),
        ]
    )

    assert confidence > 0.8


def test_interview_confidence_no_clusters() -> None:
    """Zero confidence when no clusters."""

    assert compute_interview_confidence([]) == 0.0


def test_interview_confidence_even_split() -> None:
    """Lower confidence when clusters are evenly split."""

    even_confidence = compute_interview_confidence(
        [
            _cluster(0.5, budget_consciousness=0.75, deal_seeking_intensity=0.7),
            _cluster(0.5, ad_receptivity=0.7, subscription_comfort=0.68),
        ]
    )
    dominant_confidence = compute_interview_confidence(
        [
            _cluster(0.8, budget_consciousness=0.75, deal_seeking_intensity=0.7),
            _cluster(0.2, ad_receptivity=0.7, subscription_comfort=0.68),
        ]
    )

    assert even_confidence < dominant_confidence


def test_simulation_confidence_large_lift() -> None:
    """High confidence with large lift and sufficient sample."""

    assert compute_simulation_confidence(0.2, 0.6, 150) == 1.0


def test_simulation_confidence_zero_lift() -> None:
    """Zero confidence when no lift."""

    assert compute_simulation_confidence(0.4, 0.4, 200) == 0.0


def test_attribute_confidence_all_significant() -> None:
    """High confidence when all splits significant."""

    confidence = compute_attribute_confidence(
        [
            AttributeSplit(
                attribute="budget_consciousness",
                adopter_mean=0.2,
                rejector_mean=0.8,
                effect_size=-0.9,
                significant=True,
            ),
            AttributeSplit(
                attribute="health_spend_priority",
                adopter_mean=0.8,
                rejector_mean=0.3,
                effect_size=0.7,
                significant=True,
            ),
        ]
    )

    assert confidence > 0.8


def test_attribute_confidence_none_significant() -> None:
    """Low confidence when no splits significant."""

    confidence = compute_attribute_confidence(
        [
            AttributeSplit(
                attribute="budget_consciousness",
                adopter_mean=0.48,
                rejector_mean=0.5,
                effect_size=-0.05,
                significant=False,
            )
        ]
    )

    assert confidence == 0.0


def test_attribute_confidence_empty_splits() -> None:
    """Empty split lists produce zero confidence."""

    assert compute_attribute_confidence([]) == 0.0


def test_hypothesis_confidence_consistent_probes() -> None:
    """High consistency bonus when probes agree."""

    final_confidence, consistency = compute_hypothesis_confidence([0.68, 0.7, 0.72])

    assert final_confidence > 0.72
    assert consistency > 0.99


def test_hypothesis_confidence_inconsistent_probes() -> None:
    """Low consistency when probes disagree."""

    final_confidence, consistency = compute_hypothesis_confidence([0.9, 0.1, 0.5])

    assert final_confidence < 0.6
    assert consistency < 0.75


@pytest.mark.parametrize(
    ("confidence", "expected"),
    [
        (0.7, "confirmed"),
        (0.5, "partially_confirmed"),
        (0.3, "inconclusive"),
        (0.29, "rejected"),
    ],
)
def test_classify_hypothesis_thresholds(confidence: float, expected: str) -> None:
    """Correct status for each confidence range."""

    assert classify_hypothesis(confidence) == expected
