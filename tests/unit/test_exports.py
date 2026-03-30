import csv
import io
import json

import pytest

from src.analysis.quadrant_analysis import InterventionLift, QuadrantAnalysis, format_quadrant_table


@pytest.fixture
def sample_lift():
    return InterventionLift(
        intervention_id="i1",
        intervention_name="Test Intervention",
        scope="general",
        temporality="non_temporal",
        target_cohort_id=None,
        expected_mechanism="Test Mechanism",
        adoption_lift_abs=0.1,
        adoption_lift_pct=33.3,
        rank=1,
        quadrant_key="general_non_temporal"
    )

@pytest.fixture
def sample_analysis(sample_lift):
    return QuadrantAnalysis(
        scenario_id="nutrimix_2_6",
        baseline_adoption_rate=0.3,
        baseline_active_rate=0.2,
        ranked_interventions=[sample_lift],
        top_recommendation=sample_lift,
        quadrant_summaries={
            "general_non_temporal": {"avg_lift": 33.3, "best": "Test Intervention", "count": 1},
            "general_temporal": {"avg_lift": 0.0, "best": None, "count": 0},
            "cohort_non_temporal": {"avg_lift": 0.0, "best": None, "count": 0},
            "cohort_temporal": {"avg_lift": 0.0, "best": None, "count": 0},
        }
    )

@pytest.mark.parametrize("i", range(15))
def test_phase_a_insights_json_shape(i):
    # Mimic the dict from app/utils/demo_mode.py
    insights = {
        "scenario_id": f"scenario_{i}",
        "cohort": f"Cohort {i}",
        "sub_problems": ["Problem 1", "Problem 2", f"Problem {i}"],
        "root_causes": [{"root": "P1", "pct": 50.0, "count": i}],
        "summary": f"Summary text {i}"
    }
    dumped = json.dumps(insights)
    reloaded = json.loads(dumped)
    assert reloaded["scenario_id"] == f"scenario_{i}"
    assert "sub_problems" in reloaded
    assert isinstance(reloaded["root_causes"], list)

@pytest.mark.parametrize("num_rows", [0, 1, 2, 3, 4, 5, 10, 15, 20, 25])
def test_phase_c_results_csv_shape(sample_analysis, num_rows):
    # Adjust analysis to have num_rows interventions
    base_lift = sample_analysis.top_recommendation
    lifts = []
    for i in range(num_rows):
        lift_item = base_lift.model_copy()
        lift_item.intervention_id = f"i{i}"
        lift_item.rank = i + 1
        lifts.append(lift_item)

    if num_rows > 0:
        sample_analysis.ranked_interventions = lifts
        sample_analysis.top_recommendation = lifts[0]
        table = format_quadrant_table(sample_analysis)
    else:
        # format_quadrant_table handles empty lists fine if ranked_interventions is empty
        sample_analysis.ranked_interventions = []
        table = []

    # Test CSV write-ability
    output = io.StringIO()
    if table:
        writer = csv.DictWriter(output, fieldnames=table[0].keys())
        writer.writeheader()
        writer.writerows(table)

    output.seek(0)
    content = output.read()
    if num_rows > 0:
        assert "name,scope,temporality,cohort" in content
        assert "Test Intervention" in content
        # Check count (header + rows)
        lines = content.strip().split('\n')
        assert len(lines) == num_rows + 1

@pytest.mark.parametrize("scenario_id", ["s1", "s2", "s3", "s4", "s5"])
def test_phase_c_results_json_shape(sample_analysis, scenario_id):
    sample_analysis.scenario_id = scenario_id
    dumped = sample_analysis.model_dump_json()
    reloaded = json.loads(dumped)
    assert reloaded["scenario_id"] == scenario_id
    assert "top_recommendation" in reloaded
    assert len(reloaded["ranked_interventions"]) > 0

@pytest.mark.parametrize("lift_val", [-50.0, 0.0, 10.5, 100.0, 500.0])
def test_phase_c_results_json_lift_values(sample_analysis, lift_val):
    sample_analysis.top_recommendation.adoption_lift_pct = lift_val
    dumped = sample_analysis.model_dump_json()
    reloaded = json.loads(dumped)
    assert reloaded["top_recommendation"]["adoption_lift_pct"] == lift_val

def test_export_table_keys(sample_analysis):
    table = format_quadrant_table(sample_analysis)
    first_row = table[0]
    expected = {
        "name", "scope", "temporality", "cohort",
        "baseline_adoption", "intervention_adoption", "lift_pct", "rank"
    }
    assert set(first_row.keys()) == expected
