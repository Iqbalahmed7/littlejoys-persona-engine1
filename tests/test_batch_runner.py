"""Tests for batch simulation runner."""

from pathlib import Path

import pytest

try:
    from src.decision.scenarios import get_scenario
    from src.simulation.batch import BatchSimulationRunner
    from src.simulation.explorer import ScenarioVariant, generate_sweep_variants
except ImportError:
    pytest.skip("Sprint 10 modules not merged", allow_module_level=True)


@pytest.fixture
def population():
    pop_path = Path("data/population")
    if not pop_path.exists():
        pytest.skip("Population data not generated")
    from src.generation.population import Population
    return Population.load(pop_path)


class TestBatchRunner:
    def test_runs_all_variants(self, population):
        base = get_scenario("nutrimix_2_6")
        # Use just a few sweep variants for speed
        variants = generate_sweep_variants(base)[:5]
        baseline = ScenarioVariant(
            variant_id="baseline",
            variant_name="Baseline",
            strategy="sweep",
            modifications={},
            scenario_config=base,
            is_baseline=True,
        )

        runner = BatchSimulationRunner(population)
        results = runner.run_batch([baseline, *variants])

        assert len(results) == len(variants) + 1  # +1 for baseline

    def test_results_sorted_by_adoption(self, population):
        base = get_scenario("nutrimix_2_6")
        variants = generate_sweep_variants(base)[:5]
        baseline = ScenarioVariant(
            variant_id="baseline",
            variant_name="Baseline",
            strategy="sweep",
            modifications={},
            scenario_config=base,
            is_baseline=True,
        )

        runner = BatchSimulationRunner(population)
        results = runner.run_batch([baseline, *variants])

        rates = [r.adoption_rate for r in results]
        assert rates == sorted(rates, reverse=True)

    def test_progress_callback_invoked(self, population):
        base = get_scenario("nutrimix_2_6")
        baseline = ScenarioVariant(
            variant_id="baseline",
            variant_name="Baseline",
            strategy="sweep",
            modifications={},
            scenario_config=base,
            is_baseline=True,
        )

        calls = []
        def callback(done, total):
            calls.append((done, total))

        runner = BatchSimulationRunner(population)
        runner.run_batch([baseline], progress_callback=callback)

        assert len(calls) == 1
        assert calls[0] == (1, 1)

    def test_results_have_ranks(self, population):
        base = get_scenario("nutrimix_2_6")
        variants = generate_sweep_variants(base)[:3]
        baseline = ScenarioVariant(
            variant_id="baseline",
            variant_name="Baseline",
            strategy="sweep",
            modifications={},
            scenario_config=base,
            is_baseline=True,
        )

        runner = BatchSimulationRunner(population)
        results = runner.run_batch([baseline, *variants])

        ranks = [r.rank for r in results]
        assert ranks == list(range(1, len(results) + 1))
