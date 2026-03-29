"""Unit tests for batch simulation runner."""

from __future__ import annotations

from types import SimpleNamespace

from src.simulation.batch import BatchSimulationRunner


def _variant(
    *,
    variant_id: str,
    variant_name: str,
    scenario_config: object,
    modifications: dict[str, object],
    is_baseline: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        variant_id=variant_id,
        variant_name=variant_name,
        scenario_config=scenario_config,
        modifications=modifications,
        is_baseline=is_baseline,
    )


def test_run_batch_ranks_results_and_sets_rank(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    adoption_rates = {
        "scenario-low": 0.21,
        "scenario-high": 0.44,
        "scenario-mid": 0.31,
    }

    def fake_run_static_simulation(population, scenario_config, seed):
        rate = adoption_rates[scenario_config]
        return SimpleNamespace(
            adoption_rate=rate,
            adoption_count=int(rate * 100),
            population_size=100,
            rejection_distribution={"purchase": 10},
        )

    monkeypatch.setattr("src.simulation.batch.run_static_simulation", fake_run_static_simulation)

    runner = BatchSimulationRunner(population=object(), seed=7)
    variants = [
        _variant(
            variant_id="v-low",
            variant_name="Low",
            scenario_config="scenario-low",
            modifications={"product.price_inr": 799.0},
        ),
        _variant(
            variant_id="v-high",
            variant_name="High",
            scenario_config="scenario-high",
            modifications={"product.price_inr": 399.0},
            is_baseline=True,
        ),
        _variant(
            variant_id="v-mid",
            variant_name="Mid",
            scenario_config="scenario-mid",
            modifications={"marketing.awareness_budget": 0.7},
        ),
    ]

    results = runner.run_batch(variants)

    assert [result.variant_id for result in results] == ["v-high", "v-mid", "v-low"]
    assert [result.rank for result in results] == [1, 2, 3]
    assert results[0].is_baseline is True
    assert results[0].modifications == {"product.price_inr": 399.0}


def test_run_batch_calls_progress_callback(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_run_static_simulation(population, scenario_config, seed):
        return SimpleNamespace(
            adoption_rate=0.25,
            adoption_count=25,
            population_size=100,
            rejection_distribution={},
        )

    monkeypatch.setattr("src.simulation.batch.run_static_simulation", fake_run_static_simulation)

    progress: list[tuple[int, int]] = []
    runner = BatchSimulationRunner(population=object())
    variants = [
        _variant(
            variant_id="v1",
            variant_name="One",
            scenario_config="scenario-1",
            modifications={},
        ),
        _variant(
            variant_id="v2",
            variant_name="Two",
            scenario_config="scenario-2",
            modifications={},
        ),
    ]

    runner.run_batch(variants, progress_callback=lambda done, total: progress.append((done, total)))

    assert progress == [(1, 2), (2, 2)]


def test_estimated_time_per_variant_constant() -> None:
    runner = BatchSimulationRunner(population=object())
    assert runner.estimated_time_per_variant == 0.1
