"""Day-level event simulation engine built on the canonical state model."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from src.constants import EVENT_DEFAULT_DURATION_DAYS
from src.simulation.event_grammar import (
    SimulationEvent,
    apply_event_impact,
    fire_deterministic_events,
    fire_stochastic_events,
    is_decision_point,
)
from src.simulation.state_model import (
    CanonicalState,
    apply_daily_dynamics,
    derive_thresholds,
    initialize_state,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.decision.scenarios import ScenarioConfig
    from src.generation.population import Population


STATE_FIELDS = (
    "trust",
    "habit_strength",
    "child_acceptance",
    "price_salience",
    "reorder_urgency",
    "fatigue",
    "perceived_value",
    "brand_salience",
    "effort_friction",
    "discretionary_budget",
)


class DaySnapshot(BaseModel):
    """State capture for one persona on one day."""

    model_config = ConfigDict(extra="forbid")

    day: int
    state: dict[str, float]
    events_fired: list[str]
    decision: str | None = None
    decision_rationale: dict[str, float] | None = None
    is_active: bool = False
    has_lj_pass: bool = False


class PersonaDayTrajectory(BaseModel):
    """Full day-by-day trajectory for one persona."""

    model_config = ConfigDict(extra="forbid")

    persona_id: str
    days: list[DaySnapshot] = Field(default_factory=list)
    total_purchases: int
    churned_day: int | None = None
    first_purchase_day: int | None = None


class EventSimulationResult(BaseModel):
    """Output of the day-level event simulation."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    duration_days: int
    population_size: int
    trajectories: list[PersonaDayTrajectory]
    aggregate_monthly: list[dict[str, int | float]]
    final_active_count: int
    final_active_rate: float
    total_revenue_estimate: float
    random_seed: int = 42


def _state_snapshot(state: CanonicalState) -> dict[str, float]:
    return {name: float(getattr(state, name)) for name in STATE_FIELDS}


def _rationale_candidates_first_purchase(
    state: CanonicalState,
    thresholds: dict[str, float],
    scenario: ScenarioConfig,
) -> dict[str, float]:
    price_ref = max(float(thresholds["price_reference_point"]), 1.0)
    price_ratio = scenario.product.price_inr / price_ref
    return {
        "brand_salience": abs(state.brand_salience - thresholds["awareness_threshold"]),
        "trust": abs(state.trust - thresholds["trust_threshold"]),
        "value_vs_price": abs(state.perceived_value - state.price_salience),
        "discretionary_budget": abs(state.discretionary_budget - (price_ratio * 0.3)),
        "effort_friction": abs(0.7 - state.effort_friction),
    }


def _rationale_candidates_repeat(
    state: CanonicalState,
    thresholds: dict[str, float],
    scenario: ScenarioConfig,
) -> dict[str, float]:
    price_ref = max(float(thresholds["price_reference_point"]), 1.0)
    price_ratio = scenario.product.price_inr / price_ref
    return {
        "reorder_urgency": abs(state.reorder_urgency - 0.4),
        "habit_strength": abs(state.habit_strength - 0.2),
        "child_acceptance": abs(state.child_acceptance - 0.3),
        "value_vs_price": abs(state.perceived_value - state.price_salience),
        "fatigue": abs(0.6 - state.fatigue),
        "discretionary_budget": abs(state.discretionary_budget - (price_ratio * 0.25)),
    }


def _top_three(scores: dict[str, float]) -> dict[str, float]:
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:3]
    return {key: round(float(value), 4) for key, value in ranked}


def evaluate_decision(
    state: CanonicalState,
    thresholds: dict[str, float],
    scenario: ScenarioConfig,
    active_events: list[SimulationEvent],
) -> str:
    """Evaluate what decision the persona makes at this decision point."""

    price_ref = max(float(thresholds["price_reference_point"]), 1.0)
    price_ratio = scenario.product.price_inr / price_ref

    if not state.ever_adopted:
        can_purchase = (
            state.brand_salience > thresholds["awareness_threshold"]
            and state.trust > thresholds["trust_threshold"]
            and state.perceived_value > state.price_salience
            and state.discretionary_budget > (price_ratio * 0.3)
            and state.effort_friction < 0.7
        )
        return "purchase" if can_purchase else "delay"

    if not state.is_active:
        return "delay"

    has_pack_event = any(event.event_type == "pack_finished" for event in active_events)
    if not has_pack_event:
        return "delay"

    habit_threshold = 0.05 if state.total_purchases < 3 else 0.2
    can_reorder = (
        state.reorder_urgency > 0.4
        and state.habit_strength > habit_threshold
        and state.child_acceptance > 0.3
        and state.perceived_value > state.price_salience
        and state.fatigue < 0.6
        and state.discretionary_budget > (price_ratio * 0.25)
    )
    if can_reorder:
        can_subscribe = (
            scenario.lj_pass_available
            and state.habit_strength > 0.5
            and state.reorder_urgency > 0.3
            and state.discretionary_budget > (price_ratio * 0.2)
        )
        return "subscribe" if can_subscribe else "reorder"

    competitor_discount = any(
        event.event_type == "competitor_discount" for event in active_events
    )
    if state.price_salience > 0.6 and competitor_discount and state.trust < 0.5:
        return "switch"

    if state.child_acceptance < 0.2 or state.fatigue > 0.7 or state.trust < 0.3:
        return "churn"

    return "delay"


def decision_rationale(
    state: CanonicalState,
    thresholds: dict[str, float],
    scenario: ScenarioConfig,
) -> dict[str, float]:
    """Return top three variables with largest threshold gap."""

    if not state.ever_adopted:
        return _top_three(_rationale_candidates_first_purchase(state, thresholds, scenario))
    return _top_three(_rationale_candidates_repeat(state, thresholds, scenario))


def apply_decision(state: CanonicalState, decision: str, scenario: ScenarioConfig) -> None:
    """Apply decision side-effects to mutable state."""

    if decision in {"purchase", "reorder", "subscribe"}:
        state.total_purchases += 1
        state.ever_adopted = True
        state.is_active = True
        state.churned = False
        state.days_since_purchase = 0
        state.current_pack_day = 1
        state.reorder_urgency = 0.0
        habit_boost = 0.15 if state.total_purchases <= 1 else 0.08
        state.habit_strength = min(1.0, state.habit_strength + habit_boost)
        state.consecutive_purchase_months += 1
        if decision == "subscribe" and scenario.lj_pass_available:
            state.has_lj_pass = True
            state.effort_friction = max(0.0, state.effort_friction - 0.1)
        return

    if decision in {"switch", "churn"}:
        state.is_active = False
        state.churned = True
        state.current_pack_day = 0
        state.reorder_urgency = 0.0
        state.consecutive_purchase_months = 0
        if decision == "switch":
            state.trust = max(0.0, state.trust - 0.1)
        return

    if decision == "delay" and state.is_active:
        state.habit_strength = max(0.0, state.habit_strength - 0.02)


def rollup_to_monthly(
    trajectories: list[PersonaDayTrajectory],
    duration_days: int,
) -> list[dict[str, int | float]]:
    """Aggregate day-level trajectories into monthly snapshots."""

    if not trajectories:
        return []

    monthly: list[dict[str, int | float]] = []
    months = math.ceil(duration_days / 30)
    for month in range(1, months + 1):
        start_day = (month - 1) * 30 + 1
        end_day = min(month * 30, duration_days)

        new_adopters = sum(
            1
            for trajectory in trajectories
            if trajectory.first_purchase_day is not None
            and start_day <= trajectory.first_purchase_day <= end_day
        )
        churned = sum(
            1
            for trajectory in trajectories
            if trajectory.churned_day is not None and start_day <= trajectory.churned_day <= end_day
        )
        repeat_purchasers = 0
        total_active = 0
        cumulative_adopters = 0
        awareness_values: list[float] = []
        lj_pass_holders = 0

        for trajectory in trajectories:
            for snap in trajectory.days:
                if start_day <= snap.day <= end_day and snap.decision in {"reorder", "subscribe"}:
                    repeat_purchasers += 1
            end_snapshot = trajectory.days[end_day - 1]
            if end_snapshot.state.get("brand_salience") is not None:
                awareness_values.append(float(end_snapshot.state["brand_salience"]))
            if end_snapshot.is_active:
                total_active += 1
            if trajectory.first_purchase_day is not None and trajectory.first_purchase_day <= end_day:
                cumulative_adopters += 1
            if end_snapshot.has_lj_pass:
                lj_pass_holders += 1

        monthly.append(
            {
                "month": month,
                "new_adopters": new_adopters,
                "repeat_purchasers": repeat_purchasers,
                "churned": churned,
                "total_active": total_active,
                "cumulative_adopters": cumulative_adopters,
                "awareness_level_mean": (
                    sum(awareness_values) / len(awareness_values) if awareness_values else 0.0
                ),
                "lj_pass_holders": lj_pass_holders,
            }
        )

    return monthly


def run_event_simulation(
    population: Population,
    scenario: ScenarioConfig,
    duration_days: int = EVENT_DEFAULT_DURATION_DAYS,
    seed: int = 42,
    progress_callback: Callable[[float], None] | None = None,
) -> EventSimulationResult:
    """Run the day-level event simulation for all personas."""

    rng = random.Random(seed)
    personas = population.personas
    trajectories: list[PersonaDayTrajectory] = []
    final_states: dict[str, CanonicalState] = {}
    total_steps = max(1, len(personas) * duration_days)
    processed_steps = 0

    for persona in personas:
        state = initialize_state(persona, scenario)
        thresholds = derive_thresholds(persona)
        day_snapshots: list[DaySnapshot] = []
        churned_day: int | None = None
        first_purchase_day: int | None = None

        for day in range(1, duration_days + 1):
            events = fire_deterministic_events(state, day, scenario)
            events.extend(fire_stochastic_events(state, persona, day, scenario, rng))

            for event in events:
                apply_event_impact(state, event, persona)

            apply_daily_dynamics(state)

            decision: str | None = None
            rationale: dict[str, float] | None = None
            if is_decision_point(state, events):
                was_adopted = state.ever_adopted
                decision = evaluate_decision(state, thresholds, scenario, events)
                rationale = decision_rationale(state, thresholds, scenario)
                apply_decision(state, decision, scenario)
                if not was_adopted and decision in {"purchase", "reorder", "subscribe"}:
                    first_purchase_day = day
                if decision in {"churn", "switch"} and churned_day is None:
                    churned_day = day

            day_snapshots.append(
                DaySnapshot(
                    day=day,
                    state=_state_snapshot(state),
                    events_fired=[event.event_type for event in events],
                    decision=decision,
                    decision_rationale=rationale,
                    is_active=state.is_active,
                    has_lj_pass=state.has_lj_pass,
                )
            )

            processed_steps += 1
            if progress_callback and (
                processed_steps % max(1, duration_days // 4) == 0 or processed_steps == total_steps
            ):
                progress_callback(min(1.0, processed_steps / total_steps))

        trajectories.append(
            PersonaDayTrajectory(
                persona_id=persona.id,
                days=day_snapshots,
                total_purchases=state.total_purchases,
                churned_day=churned_day,
                first_purchase_day=first_purchase_day,
            )
        )
        final_states[persona.id] = state

    final_active_count = sum(1 for state in final_states.values() if state.is_active)
    population_size = len(personas)
    total_revenue_estimate = sum(state.total_purchases for state in final_states.values()) * float(
        scenario.product.price_inr
    )

    return EventSimulationResult(
        scenario_id=scenario.id,
        duration_days=duration_days,
        population_size=population_size,
        trajectories=trajectories,
        aggregate_monthly=rollup_to_monthly(trajectories, duration_days),
        final_active_count=final_active_count,
        final_active_rate=(final_active_count / population_size) if population_size else 0.0,
        total_revenue_estimate=total_revenue_estimate,
        random_seed=seed,
    )
