"""Integration test: full exploration pipeline."""

from pathlib import Path

import pytest

try:
    from src.decision.scenarios import get_scenario
    from src.simulation.batch import BatchSimulationRunner
    from src.simulation.consolidation import ExplorationConsolidator
    from src.simulation.explorer import VariantStrategy, generate_variants
    from src.simulation.static import run_static_simulation
except ImportError:
    pytest.skip("Sprint 10 modules not merged", allow_module_level=True)


@pytest.fixture
def population():
    pop_path = Path("data/population")
    if not pop_path.exists():
        pytest.skip("Population data not generated")
    from src.generation.population import Population
    return Population.load(pop_path)


class TestFullPipeline:
    def test_sweep_end_to_end(self, population):
        base = get_scenario("nutrimix_2_6")

        # Generate
        variants = generate_variants(base, VariantStrategy.SWEEP)
        assert len(variants) >= 10

        # Run (just first 10 for speed)
        runner = BatchSimulationRunner(population)
        results = runner.run_batch(variants[:10])
        assert len(results) == 10

        # Consolidate
        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=results,
            execution_time=1.0,
            strategy="sweep",
        )

        assert report.total_variants == 10
        assert report.best_result.adoption_rate >= report.worst_result.adoption_rate
        assert report.baseline_result.is_baseline

    def test_smart_end_to_end(self, population):
        base = get_scenario("nutrimix_2_6")
        base_result = run_static_simulation(population, base)

        variants = generate_variants(
            base, VariantStrategy.SMART, base_result=base_result,
        )
        assert len(variants) >= 5

        runner = BatchSimulationRunner(population)
        results = runner.run_batch(variants)

        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=results,
            execution_time=1.0,
            strategy="smart",
        )

        assert report.total_variants >= 5
