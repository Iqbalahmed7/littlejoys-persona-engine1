"""Batch orchestrator for 2x2 intervention quadrant simulation runs."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from src.analysis.intervention_engine import (
    InterventionQuadrant,
    generate_simulation_configs,
)
from src.decision.calibration import evaluate_scenario_adoption
from src.simulation.event_engine import run_event_simulation

if TYPE_CHECKING:
    from src.decision.scenarios import ScenarioConfig
    from src.generation.population import Population

log = structlog.get_logger(__name__)


class InterventionRunResult(BaseModel):
    """Result of running one intervention through simulation."""

    model_config = ConfigDict(extra="forbid")

    intervention_id: str
    intervention_name: str
    scope: str
    temporality: str
    target_cohort_id: str | None

    adoption_rate: float
    adoption_count: int
    population_tested: int

    final_active_rate: float | None = None
    total_revenue: float | None = None
    monthly_snapshots: list[dict[str, Any]] | None = None

    rejection_distribution: dict[str, int] = Field(default_factory=dict)


class QuadrantRunResult(BaseModel):
    """Full result of running an intervention quadrant."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    baseline_adoption_rate: float
    baseline_active_rate: float | None = None
    baseline_revenue: float | None = None

    results: list[InterventionRunResult]
    duration_seconds: float
    population_size: int
    seed: int


def run_intervention_quadrant(
    quadrant: InterventionQuadrant,
    population: Population,
    scenario: ScenarioConfig,
    seed: int = 42,
) -> QuadrantRunResult:
    """Run every intervention in the quadrant against the population."""

    t0 = time.perf_counter()

    baseline_static = evaluate_scenario_adoption(population, scenario, seed=seed)
    baseline_active_rate: float | None = None
    baseline_revenue: float | None = None
    if scenario.mode == "temporal":
        baseline_days = max(1, int(scenario.months) * 30)
        baseline_event = run_event_simulation(
            population=population,
            scenario=scenario,
            duration_days=baseline_days,
            seed=seed,
        )
        baseline_active_rate = baseline_event.final_active_rate
        baseline_revenue = baseline_event.total_revenue_estimate

    run_results: list[InterventionRunResult] = []
    simulation_configs = generate_simulation_configs(quadrant, scenario, population)

    for config in simulation_configs:
        sub_pop = population
        if config.target_cohort_id is not None:
            sub_pop = population.filter_by_cohort(config.target_cohort_id)

        tested = len(sub_pop.personas)
        if tested == 0:
            log.warning(
                "quadrant_run_empty_cohort",
                intervention_id=config.intervention_id,
                target_cohort_id=config.target_cohort_id,
            )
            run_results.append(
                InterventionRunResult(
                    intervention_id=config.intervention_id,
                    intervention_name=config.intervention_name,
                    scope=config.scope,
                    temporality=config.temporality,
                    target_cohort_id=config.target_cohort_id,
                    adoption_rate=0.0,
                    adoption_count=0,
                    population_tested=0,
                )
            )
            continue

        static_result = evaluate_scenario_adoption(sub_pop, config.scenario_config, seed=seed)

        final_active_rate: float | None = None
        total_revenue: float | None = None
        monthly_snapshots: list[dict[str, Any]] | None = None
        should_run_temporal = config.temporality == "temporal" and scenario.mode == "temporal"
        if should_run_temporal:
            duration_days = max(1, int(config.duration_months) * 30)
            event_result = run_event_simulation(
                population=sub_pop,
                scenario=config.scenario_config,
                duration_days=duration_days,
                seed=seed,
            )
            final_active_rate = event_result.final_active_rate
            total_revenue = event_result.total_revenue_estimate
            monthly_snapshots = event_result.aggregate_monthly

        run_results.append(
            InterventionRunResult(
                intervention_id=config.intervention_id,
                intervention_name=config.intervention_name,
                scope=config.scope,
                temporality=config.temporality,
                target_cohort_id=config.target_cohort_id,
                adoption_rate=static_result.adoption_rate,
                adoption_count=static_result.adoption_count,
                population_tested=tested,
                final_active_rate=final_active_rate,
                total_revenue=total_revenue,
                monthly_snapshots=monthly_snapshots,
                rejection_distribution=dict(static_result.rejection_distribution),
            )
        )

    return QuadrantRunResult(
        scenario_id=scenario.id,
        baseline_adoption_rate=baseline_static.adoption_rate,
        baseline_active_rate=baseline_active_rate,
        baseline_revenue=baseline_revenue,
        results=run_results,
        duration_seconds=time.perf_counter() - t0,
        population_size=len(population.personas),
        seed=seed,
    )
