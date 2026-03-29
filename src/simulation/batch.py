"""Batch simulation runner for auto-scenario exploration."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog

from src.constants import DEFAULT_SEED
from src.simulation.consolidation import VariantResult
from src.simulation.static import run_static_simulation

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.generation.population import Population

logger = structlog.get_logger(__name__)


class BatchSimulationRunner:
    """Run multiple scenario variants against a population."""

    def __init__(
        self,
        population: Population | Any,
        seed: int = DEFAULT_SEED,
    ) -> None:
        self.population = population
        self.seed = seed

    def run_batch(
        self,
        variants: list[Any],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[VariantResult]:
        """
        Run all variants sequentially and return ranked results.

        Each variant's ScenarioConfig is run through run_static_simulation().
        Results are sorted by adoption_rate descending and ranked 1..N.
        """

        start_time = time.monotonic()
        results: list[VariantResult] = []

        for i, variant in enumerate(variants):
            sim_result = run_static_simulation(
                self.population,
                variant.scenario_config,
                seed=self.seed,
            )
            results.append(
                VariantResult(
                    variant_id=variant.variant_id,
                    variant_name=variant.variant_name,
                    adoption_rate=sim_result.adoption_rate,
                    adoption_count=sim_result.adoption_count,
                    population_size=sim_result.population_size,
                    rejection_distribution=dict(sim_result.rejection_distribution),
                    modifications=dict(variant.modifications),
                    is_baseline=variant.is_baseline,
                )
            )

            if progress_callback:
                progress_callback(i + 1, len(variants))

        results.sort(key=lambda result: result.adoption_rate, reverse=True)
        for rank, result in enumerate(results, start=1):
            result.rank = rank

        elapsed = time.monotonic() - start_time
        logger.info(
            "batch_simulation_complete",
            total_variants=len(results),
            elapsed_seconds=round(elapsed, 2),
            best_rate=results[0].adoption_rate if results else 0.0,
        )
        return results

    @property
    def estimated_time_per_variant(self) -> float:
        """Rough estimate: ~0.1s per variant for 300 personas."""

        return 0.1
