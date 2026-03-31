"""
Temporal simulation runner (Mode B) — month-by-month with repeat purchase and WOM.

Runs for N months, each month: awareness grows, new adopters enter, repeat purchases occur,
word-of-mouth spreads, churn happens.
See ARCHITECTURE.md §9.2.
"""

from __future__ import annotations

import random
from collections.abc import Callable
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
from src.taxonomy.schema import PurchaseEvent

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


class MonthState(BaseModel):
    """Per-month state for one persona in the temporal simulation."""

    month: int
    is_active: bool
    satisfaction: float
    consecutive_months: int
    has_lj_pass: bool
    churned_this_month: bool
    adopted_this_month: bool


class PersonaTrajectory(BaseModel):
    """Month-by-month trajectory for one persona."""

    persona_id: str
    monthly_states: list[MonthState]


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
    progress_callback: Callable[[int, int], None] | None = None,
) -> TemporalSimulationResult:
    """
    Run a month-by-month simulation with marketing growth, WOM, repeat purchase, and churn.

    Args:
        population: Generated population (Tier 1 personas drive the loop).
        scenario: Scenario configuration.
        thresholds: Optional funnel threshold overrides.
        months: Number of months to simulate.
        seed: RNG seed for churn/repeat stochastic draws and WOM sampling.
        progress_callback: Optional ``(current_month, total_months) -> None`` called
            after each month completes — use for live progress bars in the UI.

    Returns:
        ``TemporalSimulationResult`` with per-month snapshots and headline metrics.
    """

    snapshots, total_revenue_estimate, states, _trajectories = _simulate_temporal(
        population=population,
        scenario=scenario,
        thresholds=thresholds,
        months=months,
        seed=seed,
        collect_trajectories=False,
        progress_callback=progress_callback,
    )

    n = len(population.personas)

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


def _simulate_temporal(
    population: Population,
    scenario: ScenarioConfig,
    thresholds: dict[str, float] | None,
    months: int,
    seed: int,
    *,
    collect_trajectories: bool,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[
    list[MonthlySnapshot],
    float,
    dict[str, _PersonaTemporalState],
    dict[str, list[MonthState]],
]:
    rng = random.Random(seed)
    personas = population.personas
    n = len(personas)
    states: dict[str, _PersonaTemporalState] = {
        p.id: _PersonaTemporalState(has_lj_pass=_lj_pass_assigned(p.id, scenario)) for p in personas
    }
    trajectories: dict[str, list[MonthState]] = {p.id: [] for p in personas}
    snapshots: list[MonthlySnapshot] = []
    total_revenue_estimate = 0.0
    price = scenario.product.price_inr

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

        # Referral program boost — additional WoM from incentivized sharing
        referral_boost = scenario.marketing.referral_program_boost
        if referral_boost > 0 and active_ids:
            referral_deltas = propagate_wom(
                population,
                active_ids,
                month,
                transmission_rate=referral_boost,
                seed=seed ^ 0xBEEF,
            )
            for pid, delta in referral_deltas.items():
                states[pid].awareness_boost = min(1.0, states[pid].awareness_boost + min(0.3, delta))

        active_at_start = {pid for pid, st in states.items() if st.active}
        adopted_this_month: set[str] = set()
        churned_this_month: set[str] = set()
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
                adopted_this_month.add(persona.id)
                sat0 = compute_satisfaction(persona, scenario.product, month)
                st.satisfaction_trajectory.append(sat0)
                # Write first-purchase event to persona's purchase_history
                persona.purchase_history.append(
                    PurchaseEvent(
                        product_name=scenario.product.name,
                        timestamp=f"month_{month}",
                        price_paid=float(scenario.product.price_inr),
                        channel="simulation",
                        trigger="funnel_adopt",
                        outcome="purchased",
                        satisfaction=round(float(sat0), 4),
                    )
                )

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
                churned_this_month.add(pid)
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
                # Write repeat-purchase event to persona's purchase_history
                persona.purchase_history.append(
                    PurchaseEvent(
                        product_name=scenario.product.name,
                        timestamp=f"month_{month}",
                        price_paid=float(price),
                        channel="simulation",
                        trigger="repeat_purchase",
                        outcome="repurchased",
                        satisfaction=round(float(sat), 4),
                    )
                )
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

        if progress_callback is not None:
            progress_callback(month, months)

        if collect_trajectories:
            for persona in personas:
                st = states[persona.id]
                satisfaction = st.satisfaction_trajectory[-1] if st.satisfaction_trajectory else 0.0
                trajectories[persona.id].append(
                    MonthState(
                        month=month,
                        is_active=st.active,
                        satisfaction=float(satisfaction),
                        consecutive_months=st.consecutive_months,
                        has_lj_pass=st.has_lj_pass,
                        churned_this_month=persona.id in churned_this_month,
                        adopted_this_month=persona.id in adopted_this_month,
                    )
                )

    return snapshots, total_revenue_estimate, states, trajectories


def extract_persona_trajectories(
    population: Population,
    scenario: ScenarioConfig,
    months: int = 12,
    seed: int = 42,
) -> list[PersonaTrajectory]:
    """Return per-persona month-by-month temporal simulation trajectories."""

    _snapshots, _revenue, _states, trajectories = _simulate_temporal(
        population=population,
        scenario=scenario,
        thresholds=None,
        months=months,
        seed=seed,
        collect_trajectories=True,
    )
    return [
        PersonaTrajectory(persona_id=persona_id, monthly_states=monthly_states)
        for persona_id, monthly_states in trajectories.items()
    ]
