"""Cross-scenario regression checks for static simulation validity."""

from __future__ import annotations

from src.constants import DEFAULT_SEED, SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.generation.population import PopulationGenerator
from src.simulation.static import run_static_simulation


def test_all_scenarios_produce_valid_rates() -> None:
    pop = PopulationGenerator().generate(size=30, seed=DEFAULT_SEED)
    for scenario_id in SCENARIO_IDS:
        result = run_static_simulation(pop, get_scenario(scenario_id), seed=DEFAULT_SEED)
        assert 0.0 <= result.adoption_rate <= 1.0
        assert result.population_size == 30
        assert result.adoption_count <= result.population_size
