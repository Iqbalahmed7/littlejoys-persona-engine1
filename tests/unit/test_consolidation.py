"""Unit tests for exploration result consolidation."""

from __future__ import annotations

import pytest

from src.decision.scenarios import get_scenario
from src.simulation.consolidation import (
    ExplorationConsolidator,
    VariantResult,
    _format_modification,
    _get_nested_value,
)


def _result(
    *,
    variant_id: str,
    adoption_rate: float,
    modifications: dict[str, object],
    is_baseline: bool = False,
    rank: int = 0,
) -> VariantResult:
    return VariantResult(
        variant_id=variant_id,
        variant_name=variant_id,
        adoption_rate=adoption_rate,
        adoption_count=int(adoption_rate * 100),
        population_size=100,
        rejection_distribution={"purchase": 10},
        modifications=modifications,
        is_baseline=is_baseline,
        rank=rank,
    )


def test_get_nested_value_reads_scenario_dot_path() -> None:
    scenario = get_scenario("nutrimix_2_6")
    assert _get_nested_value(scenario, "product.price_inr") == scenario.product.price_inr


def test_format_modification_price_bool_and_ratio() -> None:
    assert _format_modification("product.price_inr", 599.0, 399.0) == "Price Inr: ₹599 -> ₹399"
    assert (
        _format_modification("marketing.school_partnership", False, True)
        == "School Partnership: enabled"
    )
    assert (
        _format_modification("marketing.awareness_budget", 0.45, 0.7)
        == "Awareness Budget: 45% -> 70%"
    )


def test_consolidate_builds_report_with_ranked_extremes() -> None:
    scenario = get_scenario("nutrimix_2_6")
    consolidator = ExplorationConsolidator()
    all_results = [
        _result(
            variant_id="v-best",
            adoption_rate=0.62,
            modifications={"product.price_inr": 399.0},
            rank=1,
        ),
        _result(
            variant_id="v-mid",
            adoption_rate=0.5,
            modifications={"marketing.awareness_budget": 0.7},
            rank=2,
        ),
        _result(
            variant_id="v-base",
            adoption_rate=0.41,
            modifications={},
            is_baseline=True,
            rank=3,
        ),
        _result(
            variant_id="v-worst",
            adoption_rate=0.21,
            modifications={"product.price_inr": 899.0},
            rank=4,
        ),
    ]

    report = consolidator.consolidate(
        base_scenario_id=scenario.id,
        base_scenario=scenario,
        all_results=all_results,
        execution_time=12.5,
        strategy="sweep",
    )

    assert report.total_variants == 4
    assert report.best_result.variant_id == "v-best"
    assert report.worst_result.variant_id == "v-worst"
    assert report.baseline_result.variant_id == "v-base"
    assert report.recommended_modifications == {"product.price_inr": 399.0}
    assert report.median_adoption_rate == pytest.approx(0.455)


def test_compute_sensitivities_sorted_and_filtered() -> None:
    consolidator = ExplorationConsolidator()
    all_results = [
        _result(
            variant_id="v1",
            adoption_rate=0.2,
            modifications={"product.price_inr": 799.0},
        ),
        _result(
            variant_id="v2",
            adoption_rate=0.55,
            modifications={"product.price_inr": 399.0},
        ),
        _result(
            variant_id="v3",
            adoption_rate=0.31,
            modifications={"marketing.awareness_budget": 0.4},
        ),
        _result(
            variant_id="v4",
            adoption_rate=0.33,
            modifications={"marketing.awareness_budget": 0.5},
        ),
    ]

    sensitivities = consolidator._compute_sensitivities(all_results)

    assert len(sensitivities) == 2
    assert sensitivities[0].parameter_path == "product.price_inr"
    assert sensitivities[0].sensitivity_score == pytest.approx(0.35)


def test_generate_missed_insights_threshold_and_explanations() -> None:
    scenario = get_scenario("nutrimix_2_6")
    consolidator = ExplorationConsolidator()
    baseline = _result(
        variant_id="baseline",
        adoption_rate=0.4,
        modifications={},
        is_baseline=True,
    )
    all_results = [
        _result(
            variant_id="v-strong",
            adoption_rate=0.62,
            modifications={
                "product.price_inr": 399.0,
                "marketing.school_partnership": True,
                "marketing.awareness_budget": 0.7,
            },
        ),
        _result(
            variant_id="v-weak",
            adoption_rate=0.44,
            modifications={"marketing.awareness_budget": 0.6},
        ),
        baseline,
    ]

    insights = consolidator._generate_missed_insights(
        baseline=baseline,
        all_results=all_results,
        base_scenario=scenario,
    )

    assert len(insights) == 1
    assert insights[0].variant_id == "v-strong"
    assert insights[0].lift_over_baseline == pytest.approx(0.22)
    assert "Price Inr: ₹599 -> ₹399" in insights[0].key_differences
    assert "School Partnership: enabled" in insights[0].key_differences
    assert "62% adoption (+22% over your scenario)" in insights[0].explanation
