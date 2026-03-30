import pytest

from src.analysis.intervention_engine import Intervention, InterventionQuadrant
from src.analysis.quadrant_analysis import (
    QuadrantAnalysis,
    analyze_quadrant_results,
    format_quadrant_table,
)
from src.simulation.quadrant_runner import InterventionRunResult, QuadrantRunResult


@pytest.fixture
def mock_run_result():
    i1_run = InterventionRunResult(
        intervention_id="i1",
        intervention_name="Int 1",
        scope="general",
        temporality="non_temporal",
        target_cohort_id=None,
        adoption_rate=0.4,
        adoption_count=4,
        population_tested=10,
    )
    i2_run = InterventionRunResult(
        intervention_id="i2",
        intervention_name="Int 2",
        scope="cohort_specific",
        temporality="temporal",
        target_cohort_id="current_user",
        adoption_rate=0.6,
        adoption_count=3,
        population_tested=5,
        final_active_rate=0.5,
        total_revenue=500.0,
    )
    return QuadrantRunResult(
        scenario_id="nutrimix_2_6",
        baseline_adoption_rate=0.3,
        baseline_active_rate=0.2,
        baseline_revenue=200.0,
        results=[i1_run, i2_run],
        duration_seconds=5.0,
        population_size=10,
        seed=42,
    )


@pytest.fixture
def mock_quadrant():
    i1 = Intervention(
        id="i1",
        name="Int 1",
        description="Desc 1",
        scope="general",
        temporality="non_temporal",
        target_cohort_id=None,
        expected_mechanism="Mechanism 1",
        parameter_modifications={},
    )
    i2 = Intervention(
        id="i2",
        name="Int 2",
        description="Desc 2",
        scope="cohort_specific",
        temporality="temporal",
        target_cohort_id="current_user",
        expected_mechanism="Mechanism 2",
        parameter_modifications={},
    )
    return InterventionQuadrant(
        problem_id="prob1",
        quadrants={
            "general_non_temporal": [i1],
            "cohort_temporal": [i2],
            "general_temporal": [],
            "cohort_non_temporal": [],
        },
    )


def test_analyze_produces_ranked_list(mock_run_result, mock_quadrant):
    analysis = analyze_quadrant_results(mock_run_result, mock_quadrant)

    assert isinstance(analysis, QuadrantAnalysis)
    assert len(analysis.ranked_interventions) == 2

    # Lift computation:
    # i1: 0.4 - 0.3 = 0.1 lift
    # i2: 0.6 - 0.3 = 0.3 lift
    # Sorting: i2 (rank 1), i1 (rank 2)
    assert analysis.ranked_interventions[0].intervention_id == "i2"
    assert analysis.ranked_interventions[0].rank == 1
    assert analysis.ranked_interventions[1].intervention_id == "i1"
    assert analysis.ranked_interventions[1].rank == 2


def test_top_recommendation(mock_run_result, mock_quadrant):
    analysis = analyze_quadrant_results(mock_run_result, mock_quadrant)
    assert analysis.top_recommendation.rank == 1
    assert analysis.top_recommendation.intervention_id == "i2"


def test_quadrant_summaries_all_four_keys(mock_run_result, mock_quadrant):
    analysis = analyze_quadrant_results(mock_run_result, mock_quadrant)
    expected_keys = {
        "general_temporal",
        "general_non_temporal",
        "cohort_temporal",
        "cohort_non_temporal",
    }
    assert set(analysis.quadrant_summaries.keys()) == expected_keys

    # Check populated bucket
    assert analysis.quadrant_summaries["cohort_temporal"]["count"] == 1
    assert analysis.quadrant_summaries["cohort_temporal"]["best"] == "Int 2"

    # Check empty bucket
    assert analysis.quadrant_summaries["general_temporal"]["count"] == 0
    assert analysis.quadrant_summaries["general_temporal"]["avg_lift"] == 0.0


def test_format_quadrant_table(mock_run_result, mock_quadrant):
    analysis = analyze_quadrant_results(mock_run_result, mock_quadrant)
    table = format_quadrant_table(analysis)

    assert isinstance(table, list)
    assert len(table) == 2

    first_row = table[0]
    expected_cols = {
        "name",
        "scope",
        "temporality",
        "cohort",
        "baseline_adoption",
        "intervention_adoption",
        "lift_pct",
        "rank",
    }
    assert set(first_row.keys()) == expected_cols
    assert first_row["name"] == "Int 2"
    assert first_row["rank"] == 1


@pytest.mark.parametrize(
    "adoption_rate, expected_lift_pct",
    [
        (0.3, 0.0),
        (0.6, 100.0),
        (0.0, -100.0),
        (0.45, 50.0),
        (0.15, -50.0),
        (0.9, 200.0),
        (1.0, 233.33333333333334),
        (0.03, -90.0),
    ],
)
def test_analyze_lift_math(mock_quadrant, adoption_rate, expected_lift_pct):
    i1_run = InterventionRunResult(
        intervention_id="i1",
        intervention_name="Int 1",
        scope="general",
        temporality="non_temporal",
        target_cohort_id=None,
        adoption_rate=adoption_rate,
        adoption_count=int(adoption_rate * 10),
        population_tested=10,
    )
    result = QuadrantRunResult(
        scenario_id="s1",
        baseline_adoption_rate=0.3,
        results=[i1_run],
        duration_seconds=1.0,
        population_size=10,
        seed=42,
    )
    analysis = analyze_quadrant_results(result, mock_quadrant)
    assert pytest.approx(analysis.ranked_interventions[0].adoption_lift_pct) == expected_lift_pct


@pytest.mark.parametrize("baseline_adoption", [0.0, 0.5, 1.0])
def test_analyze_zero_baseline(mock_quadrant, baseline_adoption):
    i1_run = InterventionRunResult(
        intervention_id="i1",
        intervention_name="Int 1",
        scope="general",
        temporality="non_temporal",
        target_cohort_id=None,
        adoption_rate=0.6,
        adoption_count=6,
        population_tested=10,
    )
    result = QuadrantRunResult(
        scenario_id="s1",
        baseline_adoption_rate=baseline_adoption,
        results=[i1_run],
        duration_seconds=1.0,
        population_size=10,
        seed=42,
    )
    analysis = analyze_quadrant_results(result, mock_quadrant)
    if baseline_adoption == 0:
        assert analysis.ranked_interventions[0].adoption_lift_pct == 0.0
    else:
        assert (
            analysis.ranked_interventions[0].adoption_lift_pct
            == ((0.6 - baseline_adoption) / baseline_adoption) * 100
        )
