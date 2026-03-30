
import pytest

from src.analysis.intervention_engine import Intervention, InterventionQuadrant
from src.decision.scenarios import get_scenario
from src.generation.population import GenerationParams, Population, PopulationMetadata
from src.simulation.quadrant_runner import (
    InterventionRunResult,
    QuadrantRunResult,
    run_intervention_quadrant,
)


@pytest.fixture
def mock_population():
    params = GenerationParams(size=10, seed=42, deep_persona_count=0)
    meta = PopulationMetadata(
        generation_timestamp="2024-01-01T00:00:00Z",
        generation_duration_seconds=0.1,
        engine_version="1.0.0"
    )
    return Population(
        id="test_pop",
        generation_params=params,
        tier1_personas=[],
        metadata=meta
    )

@pytest.fixture
def mock_quadrant():
    i1 = Intervention(
        id="i1", name="Int 1", description="Desc 1",
        scope="general", temporality="non_temporal",
        target_cohort_id=None,
        expected_mechanism="Mechanism 1", parameter_modifications={}
    )
    i2 = Intervention(
        id="i2", name="Int 2", description="Desc 2",
        scope="cohort_specific", temporality="temporal",
        target_cohort_id="current_user",
        expected_mechanism="Mechanism 2", parameter_modifications={}
    )
    return InterventionQuadrant(
        problem_id="prob1",
        quadrants={
            "general_non_temporal": [i1],
            "cohort_temporal": [i2],
            "general_temporal": [],
            "cohort_non_temporal": []
        }
    )

def test_run_intervention_quadrant_nutrimix(mock_population, mock_quadrant):
    scenario = get_scenario("nutrimix_2_6")
    # Mocking adoption to be non-zero for baseline
    # (In reality, evaluate_scenario_adoption will run)

    result = run_intervention_quadrant(mock_quadrant, mock_population, scenario)

    assert isinstance(result, QuadrantRunResult)
    assert result.scenario_id == scenario.id
    assert result.baseline_adoption_rate >= 0
    assert len(result.results) == 2

    for res in result.results:
        assert isinstance(res, InterventionRunResult)
        assert 0.0 <= res.adoption_rate <= 1.0
        assert res.population_tested <= 10
        if res.temporality == "temporal" and scenario.mode == "temporal" and res.population_tested > 0:
            assert res.final_active_rate is not None

def test_empty_cohort_handling(mock_population, mock_quadrant):
    scenario = get_scenario("nutrimix_2_6")
    # Force empty population for the cohort-specific intervention
    # by mocking filter_by_cohort
    import unittest.mock as mock
    with mock.patch.object(Population, 'filter_by_cohort') as mocked_filter:
        mocked_filter.return_value = Population(
            id="empty", generation_params=mock_population.generation_params,
            tier1_personas=[], metadata=mock_population.metadata
        )

        result = run_intervention_quadrant(mock_quadrant, mock_population, scenario)

        # Finding the cohort-specific result
        cohort_res = next(r for r in result.results if r.scope == "cohort_specific")
        assert cohort_res.population_tested == 0
        assert cohort_res.adoption_rate == 0.0
        assert cohort_res.adoption_count == 0

def test_run_timing(mock_population, mock_quadrant):
    scenario = get_scenario("nutrimix_2_6")
    result = run_intervention_quadrant(mock_quadrant, mock_population, scenario)
    assert result.duration_seconds > 0

@pytest.mark.parametrize("scenario_id", ["nutrimix_2_6", "nutrimix_7_14", "magnesium_gummies", "protein_mix"])
def test_run_quadrant_all_scenarios(mock_population, mock_quadrant, scenario_id):
    scenario = get_scenario(scenario_id)
    result = run_intervention_quadrant(mock_quadrant, mock_population, scenario)
    assert result.scenario_id == scenario_id
    assert len(result.results) == 2

@pytest.mark.parametrize("pop_size", [1, 2, 5, 10, 20])
def test_run_quadrant_variable_pop_size(mock_quadrant, pop_size):
    from src.generation.population import PopulationGenerator
    gen = PopulationGenerator()
    pop = gen.generate(size=pop_size, seed=42)
    scenario = get_scenario("nutrimix_2_6")
    result = run_intervention_quadrant(mock_quadrant, pop, scenario)
    assert result.population_size == pop_size
    assert len(result.results) == 2
