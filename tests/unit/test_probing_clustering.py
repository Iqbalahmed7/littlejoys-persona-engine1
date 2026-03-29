"""Unit tests for probing response clustering."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.probing.clustering import cluster_responses_mock

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


def _persona_variant(template: Persona, persona_id: str, budget_consciousness: float) -> Persona:
    return template.model_copy(
        update={
            "id": persona_id,
            "daily_routine": template.daily_routine.model_copy(
                update={"budget_consciousness": budget_consciousness}
            ),
        },
        deep=True,
    )


def test_mock_clustering_price_keywords(sample_persona: Persona) -> None:
    """Response mentioning price clusters into price_sensitivity."""

    clusters = cluster_responses_mock(
        [(sample_persona, "The price felt too expensive for our budget this month.")]
    )

    assert clusters[0].theme == "price_sensitivity"


def test_mock_clustering_multiple_themes(sample_persona: Persona) -> None:
    """Multiple distinct responses produce multiple clusters."""

    second = _persona_variant(sample_persona, "persona-2", 0.2)
    clusters = cluster_responses_mock(
        [
            (sample_persona, "The price felt too expensive and not worth it."),
            (second, "Honestly I forgot to reorder because life got hectic."),
        ]
    )

    assert {cluster.theme for cluster in clusters} == {"price_sensitivity", "forgetfulness"}


def test_mock_clustering_empty_responses() -> None:
    """Empty response list returns empty clusters."""

    assert cluster_responses_mock([]) == []


def test_mock_clustering_percentages_sum_to_one(sample_persona: Persona) -> None:
    """Cluster percentages sum to approximately 1.0."""

    second = _persona_variant(sample_persona, "persona-2", 0.3)
    third = _persona_variant(sample_persona, "persona-3", 0.9)
    fourth = _persona_variant(sample_persona, "persona-4", 0.8)
    clusters = cluster_responses_mock(
        [
            (sample_persona, "The price felt too expensive."),
            (second, "The cost looked high for our budget."),
            (third, "I forgot to reorder and things got hectic."),
            (fourth, "I got busy and it slipped my mind."),
        ]
    )

    assert sum(cluster.percentage for cluster in clusters) == pytest.approx(1.0, abs=0.01)


def test_mock_clustering_dominant_attributes_stay_normalized(sample_persona: Persona) -> None:
    """Dominant attribute summaries only include normalized trait values."""

    second = _persona_variant(sample_persona, "persona-2", 0.85)
    clusters = cluster_responses_mock(
        [
            (sample_persona, "The price felt too expensive."),
            (second, "The cost looked high for our budget."),
        ]
    )

    assert clusters
    assert all(0.0 <= value <= 1.0 for value in clusters[0].dominant_attributes.values())
