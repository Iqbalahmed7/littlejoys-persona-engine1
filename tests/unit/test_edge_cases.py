"""Unit tests for boundary and edge conditions in simulation engines."""

from __future__ import annotations

from src.decision.scenarios import get_scenario
from src.generation.population import GenerationParams, Population, PopulationMetadata
from src.simulation.event_engine import run_event_simulation
from src.simulation.static import run_static_simulation


def _mock_pop(personas: list) -> Population:
    """Create a mock population with minimal valid metadata."""
    return Population.model_construct(
        id="mock-pop",
        generation_params=GenerationParams.model_construct(size=len(personas), seed=42),
        tier1_personas=personas,
        tier2_personas=[],
        metadata=PopulationMetadata.model_construct(
            generation_timestamp="2026-03-30T00:00:00Z",
            generation_duration_seconds=0.1,
            engine_version="0.1.0"
        )
    )


def test_simulation_with_empty_population():
    """Empty population should return valid but empty results, never crash."""
    pop = _mock_pop([])
    scenario = get_scenario("nutrimix_2_6")

    # Static
    result_static = run_static_simulation(pop, scenario)
    assert result_static.population_size == 0
    assert result_static.adoption_count == 0
    assert result_static.adoption_rate == 0.0

    # Event
    result_event = run_event_simulation(pop, scenario, duration_days=30)
    assert result_event.population_size == 0
    assert result_event.final_active_count == 0


def test_simulation_with_single_persona(sample_persona):
    """Full pipeline should work for a single persona population."""
    pop = _mock_pop([sample_persona])
    scenario = get_scenario("nutrimix_2_6")

    # Static
    result_static = run_static_simulation(pop, scenario)
    assert result_static.population_size == 1
    assert result_static.adoption_count in (0, 1)

    # Event
    result_event = run_event_simulation(pop, scenario, duration_days=30)
    assert result_event.population_size == 1


def test_zero_adoption_scenario(sample_persona):
    """Scenario where trial_rate is 0.0 should not cause divide-by-zero or crash."""
    pop = _mock_pop([sample_persona])
    scenario = get_scenario("nutrimix_2_6")

    # Force rejection by setting extreme thresholds
    scenario.product.price_inr = 1_000_000.0

    result = run_static_simulation(pop, scenario)
    assert result.adoption_rate == 0.0
    assert result.adoption_count == 0

    assert result.rejection_distribution is not None
    assert result.population_size == 1
