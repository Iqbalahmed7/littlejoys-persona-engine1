import pytest

from src.analysis.intervention_engine import (
    Intervention,
    InterventionQuadrant,
    SimulationRunConfig,
    generate_intervention_quadrant,
    generate_simulation_configs,
)
from src.decision.scenarios import get_scenario
from src.generation.population import GenerationParams, Population, PopulationMetadata


@pytest.fixture
def mock_decomposition():
    class MockDecomp:
        problem_id = "test_problem_123"
    return MockDecomp()

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

def test_generate_intervention_quadrant(mock_decomposition):
    scenario = get_scenario("nutrimix_2_6")
    quadrant = generate_intervention_quadrant(mock_decomposition, scenario)

    assert isinstance(quadrant, InterventionQuadrant)
    assert quadrant.problem_id == "test_problem_123"

    expected_keys = {"general_temporal", "general_non_temporal", "cohort_temporal", "cohort_non_temporal"}
    assert set(quadrant.quadrants.keys()) == expected_keys

    for _key, interventions in quadrant.quadrants.items():
        assert len(interventions) >= 1
        for i in interventions:
            assert isinstance(i, Intervention)
            if i.scope == "general":
                assert i.target_cohort_id is None
            else:
                assert i.target_cohort_id is not None
            assert i.temporality in ["temporal", "non_temporal"]

def test_generate_simulation_configs(mock_decomposition, mock_population):
    scenario = get_scenario("nutrimix_2_6")
    quadrant = generate_intervention_quadrant(mock_decomposition, scenario)

    configs = generate_simulation_configs(quadrant, scenario, mock_population)

    assert isinstance(configs, list)
    assert len(configs) > 0
    for config in configs:
        assert isinstance(config, SimulationRunConfig)
        assert config.intervention_id != ""
        assert config.scenario_config.id == scenario.id

        # Verify parameter modifications were applied (at least one check)
        # Find an intervention that modifies something
        found_mod = False
        for _, interventions in quadrant.quadrants.items():
            for i in interventions:
                if i.id == config.intervention_id:
                    # Check if the param was changed
                    # This is tricky because apply_scenario_modifications is internal logic
                    # but we can check if it returns a copy
                    assert config.scenario_config is not scenario
                    found_mod = True
                    break
        assert found_mod

def test_intervention_invalid_input():
    class BrokenDecomp:
        pass

    scenario = get_scenario("nutrimix_2_6")
    with pytest.raises(ValueError, match="decomposition must include a non-empty problem_id"):
        generate_intervention_quadrant(BrokenDecomp(), scenario)

def test_population_filter_for_cohort_mapping():
    from src.analysis.intervention_engine import _population_filter_for_cohort
    assert _population_filter_for_cohort(None) is None
    assert _population_filter_for_cohort("lapsed_users") == {"cohort": "lapsed_users", "ever_adopted": True, "is_active": False}
    assert _population_filter_for_cohort("unknown") == {"cohort": "unknown"}

def test_intervention_expected_mechanism(mock_decomposition):
    scenario = get_scenario("nutrimix_2_6")
    quadrant = generate_intervention_quadrant(mock_decomposition, scenario)
    for q_list in quadrant.quadrants.values():
        for i in q_list:
            assert len(i.expected_mechanism) > 10
            assert isinstance(i.parameter_modifications, dict)
