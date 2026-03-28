"""
Temporal simulation runner (Mode B) — month-by-month with repeat purchase and WOM.

Runs for N months, each month: awareness grows, new adopters enter, repeat purchases occur,
word-of-mouth spreads, churn happens.
See ARCHITECTURE.md §9.2.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog
from pydantic import BaseModel

from src.constants import (
    DEFAULT_WOM_TRANSMISSION_RATE,
    TEMPORAL_LJ_PASS_FRACTION_DENOMINATOR,
    TEMPORAL_LJ_PASS_FRACTION_NUMERATOR,
    TEMPORAL_MONTHLY_AWARENESS_INCREMENT,
)
from src.decision.funnel import compute_awareness, run_funnel
from src.decision.repeat import (
    compute_churn_probability,
    compute_repeat_probability,
    compute_satisfaction,
)
from src.simulation.wom import propagate_wom

if TYPE_CHECKING:
    from src.decision.scenarios import ScenarioConfig
    from src.generation.population import Population

log = structlog.get_logger(__name__)


class MonthlySnapshot(BaseModel):
    """State of the simulation at a given month."""

    month: int
    new_adopters: int
    repeat_purchasers: int
    churned: int
    total_active: int
    cumulative_adopters: int
    awareness_level_mean: float
    lj_pass_holders: int


class TemporalSimulationResult(BaseModel):
    """Results from a temporal (multi-month) simulation."""

    scenario_id: str
    months: int
    population_size: int
    monthly_snapshots: list[MonthlySnapshot]
    final_adoption_rate: float
    final_active_rate: float
    total_revenue_estimate: float
    random_seed: int = 42


@dataclass
class _PersonaTemporalState:
    awareness_boost: float = 0.0
    ever_adopted: bool = False
    active: bool = False
    consecutive_months: int = 0
    has_lj_pass: bool = False
    satisfaction_trajectory: list[float] = field(default_factory=list)


def _lj_pass_assigned(persona_id: str, scenario: ScenarioConfig) -> bool:
    if not scenario.lj_pass_available:
        return False
    bucket = hash(persona_id) % TEMPORAL_LJ_PASS_FRACTION_DENOMINATOR
    return bucket < TEMPORAL_LJ_PASS_FRACTION_NUMERATOR


def run_temporal_simulation(
    population: Population,
    scenario: ScenarioConfig,
    thresholds: dict[str, float] | None = None,
    months: int = 12,
    seed: int = 42,
) -> TemporalSimulationResult:
    """
    Run a month-by-month simulation with marketing growth, WOM, repeat purchase, and churn.

    Args:
        population: Generated population (Tier 1 personas drive the loop).
        scenario: Scenario configuration.
        thresholds: Optional funnel threshold overrides.
        months: Number of months to simulate.
        seed: RNG seed for churn/repeat stochastic draws and WOM sampling.

    Returns:
        ``TemporalSimulationResult`` with per-month snapshots and headline metrics.
    """

    rng = random.Random(seed)
    personas = population.tier1_personas
    n = len(personas)
    states: dict[str, _PersonaTemporalState] = {
        p.id: _PersonaTemporalState(has_lj_pass=_lj_pass_assigned(p.id, scenario)) for p in personas
    }

    snapshots: list[MonthlySnapshot] = []
    total_revenue_estimate = 0.0
    price = scenario.product.price_inr

    log.info("temporal_simulation_started", scenario_id=scenario.id, months=months, seed=seed)

    for month in range(1, months + 1):
        for st in states.values():
            st.awareness_boost = min(
                1.0,
                st.awareness_boost
                + TEMPORAL_MONTHLY_AWARENESS_INCREMENT * scenario.marketing.awareness_budget,
            )

        active_ids = [pid for pid, st in states.items() if st.active]
        wom_deltas = propagate_wom(
            population,
            active_ids,
            month,
            transmission_rate=DEFAULT_WOM_TRANSMISSION_RATE,
            seed=seed,
        )
        for pid, delta in wom_deltas.items():
            states[pid].awareness_boost = min(1.0, states[pid].awareness_boost + min(0.4, delta))

        active_at_start = {pid for pid, st in states.items() if st.active}
        new_adopters = 0

        for persona in personas:
            st = states[persona.id]
            if st.ever_adopted:
                continue
            decision = run_funnel(
                persona,
                scenario,
                thresholds,
                awareness_boost=st.awareness_boost,
            )
            if decision.outcome == "adopt":
                st.ever_adopted = True
                st.active = True
                st.consecutive_months = 1
                new_adopters += 1
                sat0 = compute_satisfaction(persona, scenario.product, month)
                st.satisfaction_trajectory.append(sat0)

        repeat_purchasers = 0
        churned = 0

        for pid in active_at_start:
            st = states[pid]
            if not st.active:
                continue
            persona = population.get_persona(pid)
            sat = compute_satisfaction(persona, scenario.product, month)
            st.satisfaction_trajectory.append(sat)
            churn_p = compute_churn_probability(
                persona,
                st.satisfaction_trajectory,
                st.has_lj_pass,
            )
            if rng.random() < churn_p:
                st.active = False
                st.consecutive_months = 0
                churned += 1
                continue

            repeat_p = compute_repeat_probability(
                persona,
                sat,
                st.consecutive_months,
                st.has_lj_pass,
            )
            if rng.random() < repeat_p:
                repeat_purchasers += 1
                total_revenue_estimate += price
            st.consecutive_months += 1

        total_revenue_estimate += new_adopters * price

        total_active = sum(1 for st in states.values() if st.active)
        cumulative_adopters = sum(1 for st in states.values() if st.ever_adopted)
        awareness_values = [
            compute_awareness(
                p,
                scenario,
                awareness_boost=states[p.id].awareness_boost,
            )
            for p in personas
        ]
        awareness_mean = sum(awareness_values) / n if n else 0.0
        lj_holders = sum(1 for st in states.values() if st.has_lj_pass)

        snapshots.append(
            MonthlySnapshot(
                month=month,
                new_adopters=new_adopters,
                repeat_purchasers=repeat_purchasers,
                churned=churned,
                total_active=total_active,
                cumulative_adopters=cumulative_adopters,
                awareness_level_mean=awareness_mean,
                lj_pass_holders=lj_holders,
            )
        )

    final_cumulative = sum(1 for st in states.values() if st.ever_adopted)
    final_active = sum(1 for st in states.values() if st.active)
    final_adoption_rate = final_cumulative / n if n else 0.0
    final_active_rate = final_active / n if n else 0.0

    log.info(
        "temporal_simulation_complete",
        final_adoption_rate=final_adoption_rate,
        total_revenue_estimate=total_revenue_estimate,
    )

    return TemporalSimulationResult(
        scenario_id=scenario.id,
        months=months,
        population_size=n,
        monthly_snapshots=snapshots,
        final_adoption_rate=final_adoption_rate,
        final_active_rate=final_active_rate,
        total_revenue_estimate=total_revenue_estimate,
        random_seed=seed,
    )
