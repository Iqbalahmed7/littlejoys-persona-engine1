"""Side-by-side scenario comparison engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from src.analysis.barriers import analyze_barriers
from src.analysis.causal import compute_variable_importance
from src.decision.calibration import evaluate_scenario_adoption
from src.simulation.event_engine import run_event_simulation

if TYPE_CHECKING:
    from src.decision.scenarios import ScenarioConfig
    from src.generation.population import Population


class BarrierDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    barrier: str
    count_a: int
    count_b: int
    delta: int


class DriverDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    importance_a: float
    importance_b: float
    delta: float


class ScenarioComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_a_id: str
    scenario_b_id: str
    scenario_a_name: str
    scenario_b_name: str

    adoption_rate_a: float
    adoption_rate_b: float
    adoption_delta: float

    active_rate_a: float | None = None
    active_rate_b: float | None = None
    active_delta: float | None = None
    revenue_a: float | None = None
    revenue_b: float | None = None
    revenue_delta: float | None = None

    barrier_comparison: list[BarrierDelta] = Field(default_factory=list)
    driver_comparison: list[DriverDelta] = Field(default_factory=list)


def _barrier_counts(results_by_persona: dict[str, dict[str, Any]]) -> dict[tuple[str, str], int]:
    rows = analyze_barriers(results_by_persona)
    return {(row.stage, row.barrier): row.count for row in rows}


def _merged_rows(
    population: Population,
    results_by_persona: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for persona_id, result in results_by_persona.items():
        try:
            persona = population.get_persona(persona_id)
        except KeyError:
            continue
        merged.append({**persona.to_flat_dict(), **result})
    return merged


def _driver_map(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {item.variable_name: item.shap_mean_abs for item in compute_variable_importance(rows)}


def _duration_days(scenario: ScenarioConfig) -> int:
    months = max(1, int(scenario.months))
    return months * 30


def compare_scenarios(
    population: Population,
    scenario_a: ScenarioConfig,
    scenario_b: ScenarioConfig,
    seed: int = 42,
) -> ScenarioComparisonResult:
    """Run both scenarios and produce a structured comparison."""

    static_a = evaluate_scenario_adoption(population=population, scenario=scenario_a, seed=seed)
    static_b = evaluate_scenario_adoption(population=population, scenario=scenario_b, seed=seed)

    counts_a = _barrier_counts(static_a.results_by_persona)
    counts_b = _barrier_counts(static_b.results_by_persona)
    barrier_keys = sorted(set(counts_a) | set(counts_b), key=lambda item: (item[0], item[1]))
    barrier_comparison = [
        BarrierDelta(
            stage=stage,
            barrier=barrier,
            count_a=counts_a.get((stage, barrier), 0),
            count_b=counts_b.get((stage, barrier), 0),
            delta=counts_b.get((stage, barrier), 0) - counts_a.get((stage, barrier), 0),
        )
        for stage, barrier in barrier_keys
    ]

    drivers_a = _driver_map(_merged_rows(population, static_a.results_by_persona))
    drivers_b = _driver_map(_merged_rows(population, static_b.results_by_persona))
    driver_keys = sorted(set(drivers_a) | set(drivers_b))
    driver_comparison = [
        DriverDelta(
            variable=variable,
            importance_a=float(drivers_a.get(variable, 0.0)),
            importance_b=float(drivers_b.get(variable, 0.0)),
            delta=float(drivers_b.get(variable, 0.0) - drivers_a.get(variable, 0.0)),
        )
        for variable in driver_keys
    ]
    driver_comparison.sort(key=lambda item: abs(item.delta), reverse=True)

    active_rate_a: float | None = None
    active_rate_b: float | None = None
    revenue_a: float | None = None
    revenue_b: float | None = None

    if scenario_a.mode == "temporal":
        temporal_a = run_event_simulation(
            population=population,
            scenario=scenario_a,
            duration_days=_duration_days(scenario_a),
            seed=seed,
        )
        active_rate_a = temporal_a.final_active_rate
        revenue_a = temporal_a.total_revenue_estimate
    if scenario_b.mode == "temporal":
        temporal_b = run_event_simulation(
            population=population,
            scenario=scenario_b,
            duration_days=_duration_days(scenario_b),
            seed=seed,
        )
        active_rate_b = temporal_b.final_active_rate
        revenue_b = temporal_b.total_revenue_estimate

    active_delta = (
        (active_rate_b - active_rate_a)
        if active_rate_a is not None and active_rate_b is not None
        else None
    )
    revenue_delta = (
        (revenue_b - revenue_a) if revenue_a is not None and revenue_b is not None else None
    )

    return ScenarioComparisonResult(
        scenario_a_id=scenario_a.id,
        scenario_b_id=scenario_b.id,
        scenario_a_name=scenario_a.name,
        scenario_b_name=scenario_b.name,
        adoption_rate_a=static_a.adoption_rate,
        adoption_rate_b=static_b.adoption_rate,
        adoption_delta=static_b.adoption_rate - static_a.adoption_rate,
        active_rate_a=active_rate_a,
        active_rate_b=active_rate_b,
        active_delta=active_delta,
        revenue_a=revenue_a,
        revenue_b=revenue_b,
        revenue_delta=revenue_delta,
        barrier_comparison=barrier_comparison,
        driver_comparison=driver_comparison,
    )
