"""Unit tests for quadrant-level intervention analysis."""

from __future__ import annotations

from typing import Literal

import pytest

from src.analysis.intervention_engine import Intervention, InterventionQuadrant
from src.analysis.quadrant_analysis import (
    QuadrantAnalysis,
    analyze_quadrant_results,
    format_quadrant_table,
)
from src.simulation.quadrant_runner import InterventionRunResult, QuadrantRunResult


def _intervention(
    *,
    intervention_id: str,
    name: str,
    scope: Literal["general", "cohort_specific"],
    temporality: Literal["temporal", "non_temporal"],
    target_cohort_id: str | None = None,
    mechanism: str = "Improves repeat purchase behavior.",
) -> Intervention:
    return Intervention(
        id=intervention_id,
        name=name,
        description=f"{name} description",
        scope=scope,
        temporality=temporality,
        target_cohort_id=target_cohort_id,
        parameter_modifications={"marketing.awareness_budget": 0.6},
        expected_mechanism=mechanism,
    )


def _quadrant() -> InterventionQuadrant:
    return InterventionQuadrant(
        problem_id="repeat_purchase_problem",
        quadrants={
            "general_temporal": [
                _intervention(
                    intervention_id="a",
                    name="A Program",
                    scope="general",
                    temporality="temporal",
                ),
                _intervention(
                    intervention_id="b",
                    name="B Program",
                    scope="general",
                    temporality="temporal",
                ),
            ],
            "general_non_temporal": [
                _intervention(
                    intervention_id="c",
                    name="C Offer",
                    scope="general",
                    temporality="non_temporal",
                ),
            ],
            "cohort_temporal": [
                _intervention(
                    intervention_id="d",
                    name="D Nudge",
                    scope="cohort_specific",
                    temporality="temporal",
                    target_cohort_id="lapsed_user",
                ),
            ],
            "cohort_non_temporal": [],
        },
    )


def _run_result() -> QuadrantRunResult:
    return QuadrantRunResult(
        scenario_id="nutrimix_2_6",
        baseline_adoption_rate=0.20,
        baseline_active_rate=0.40,
        baseline_revenue=1000.0,
        results=[
            InterventionRunResult(
                intervention_id="a",
                intervention_name="A Program",
                scope="general",
                temporality="temporal",
                target_cohort_id=None,
                adoption_rate=0.30,
                adoption_count=30,
                population_tested=100,
                final_active_rate=0.55,
                total_revenue=1300.0,
                monthly_snapshots=[],
                rejection_distribution={},
            ),
            InterventionRunResult(
                intervention_id="b",
                intervention_name="B Program",
                scope="general",
                temporality="temporal",
                target_cohort_id=None,
                adoption_rate=0.30,
                adoption_count=30,
                population_tested=100,
                final_active_rate=0.50,
                total_revenue=1100.0,
                monthly_snapshots=[],
                rejection_distribution={},
            ),
            InterventionRunResult(
                intervention_id="c",
                intervention_name="C Offer",
                scope="general",
                temporality="non_temporal",
                target_cohort_id=None,
                adoption_rate=0.24,
                adoption_count=24,
                population_tested=100,
                final_active_rate=None,
                total_revenue=None,
                monthly_snapshots=None,
                rejection_distribution={},
            ),
        ],
        duration_seconds=0.01,
        population_size=100,
        seed=42,
    )


def test_analyze_quadrant_results_ranks_by_lift_then_revenue() -> None:
    analysis = analyze_quadrant_results(_run_result(), _quadrant())

    assert isinstance(analysis, QuadrantAnalysis)
    assert analysis.top_recommendation.intervention_id == "a"
    assert analysis.ranked_interventions[0].rank == 1
    assert analysis.ranked_interventions[1].rank == 2

    top = analysis.ranked_interventions[0]
    assert top.adoption_lift_abs == pytest.approx(0.10)
    assert top.adoption_lift_pct == pytest.approx(50.0)
    assert top.active_rate_lift_abs == pytest.approx(0.15)
    assert top.revenue_lift == pytest.approx(300.0)
    assert top.expected_mechanism == "Improves repeat purchase behavior."
    assert top.quadrant_key == "general_temporal"


def test_analyze_quadrant_results_non_temporal_has_no_temporal_lift() -> None:
    analysis = analyze_quadrant_results(_run_result(), _quadrant())
    non_temporal = next(
        row for row in analysis.ranked_interventions if row.intervention_id == "c"
    )

    assert non_temporal.active_rate_lift_abs is None
    assert non_temporal.active_rate_lift_pct is None
    assert non_temporal.revenue_lift is None
    assert non_temporal.quadrant_key == "general_non_temporal"


def test_analyze_quadrant_results_builds_all_quadrant_summaries() -> None:
    analysis = analyze_quadrant_results(_run_result(), _quadrant())

    assert set(analysis.quadrant_summaries) == {
        "general_temporal",
        "general_non_temporal",
        "cohort_temporal",
        "cohort_non_temporal",
    }
    assert analysis.quadrant_summaries["general_temporal"]["count"] == 2
    assert analysis.quadrant_summaries["general_temporal"]["best"] == "A Program"
    assert analysis.quadrant_summaries["cohort_temporal"]["count"] == 0


def test_analyze_quadrant_results_raises_when_empty() -> None:
    empty = QuadrantRunResult(
        scenario_id="nutrimix_2_6",
        baseline_adoption_rate=0.2,
        baseline_active_rate=None,
        baseline_revenue=None,
        results=[],
        duration_seconds=0.0,
        population_size=100,
        seed=42,
    )

    with pytest.raises(ValueError, match="does not include any intervention runs"):
        analyze_quadrant_results(empty, _quadrant())


def test_format_quadrant_table_returns_dataframe_ready_rows() -> None:
    analysis = analyze_quadrant_results(_run_result(), _quadrant())
    rows = format_quadrant_table(analysis)

    assert len(rows) == 3
    assert set(rows[0]) == {
        "name",
        "scope",
        "temporality",
        "cohort",
        "baseline_adoption",
        "intervention_adoption",
        "lift_pct",
        "rank",
    }
    assert rows[0]["baseline_adoption"] == pytest.approx(0.20)
    assert rows[0]["intervention_adoption"] == pytest.approx(0.30)
