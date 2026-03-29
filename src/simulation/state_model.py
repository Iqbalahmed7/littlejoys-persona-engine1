"""Canonical mutable state model for day-level event simulation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from src.constants import (
    DEFAULT_PACK_DURATION_DAYS,
    EVENT_BRAND_SALIENCE_DECAY_PER_DAY,
    EVENT_FATIGUE_GROWTH_PER_DAY,
    EVENT_HABIT_DECAY_PER_DAY,
    EVENT_REORDER_URGENCY_RAMP_DAYS,
)

if TYPE_CHECKING:
    from src.decision.scenarios import ScenarioConfig
    from src.taxonomy.schema import Persona


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class CanonicalState(BaseModel):
    """Mutable state for one persona across the simulation. All values [0, 1]."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    trust: float = 0.0
    habit_strength: float = 0.0
    child_acceptance: float = 0.0
    price_salience: float = 0.0
    reorder_urgency: float = 0.0
    fatigue: float = 0.0
    perceived_value: float = 0.0
    brand_salience: float = 0.0
    effort_friction: float = 0.0
    discretionary_budget: float = 0.0

    days_since_purchase: int = 0
    total_purchases: int = 0
    consecutive_purchase_months: int = 0
    has_lj_pass: bool = False
    is_active: bool = False
    ever_adopted: bool = False
    churned: bool = False
    current_pack_day: int = 0
    pack_duration: int = DEFAULT_PACK_DURATION_DAYS


def clip_state(state: CanonicalState) -> None:
    """Clamp all canonical decision variables into the closed unit interval."""

    state.trust = _clip(state.trust)
    state.habit_strength = _clip(state.habit_strength)
    state.child_acceptance = _clip(state.child_acceptance)
    state.price_salience = _clip(state.price_salience)
    state.reorder_urgency = _clip(state.reorder_urgency)
    state.fatigue = _clip(state.fatigue)
    state.perceived_value = _clip(state.perceived_value)
    state.brand_salience = _clip(state.brand_salience)
    state.effort_friction = _clip(state.effort_friction)
    state.discretionary_budget = _clip(state.discretionary_budget)


def initialize_state(persona: Persona, scenario: ScenarioConfig) -> CanonicalState:
    """Initialize state from immutable persona identity + scenario config."""

    child_veto = getattr(
        persona.relationships,
        "child_taste_veto",
        getattr(persona.relationships, "child_taste_veto_power", 0.5),
    )
    online_comfort = getattr(
        persona.daily_routine,
        "online_shopping_comfort",
        persona.daily_routine.online_vs_offline_preference,
    )
    state = CanonicalState(
        trust=_clip(
            (persona.health.medical_authority_trust * 0.4)
            + (persona.psychology.social_proof_bias * 0.3)
            + (scenario.marketing.expert_endorsement * 0.2)
            + (0.1 if scenario.marketing.pediatrician_endorsement else 0.0)
        ),
        child_acceptance=_clip(
            scenario.product.taste_appeal * (1.0 - (0.3 * float(child_veto)))
        ),
        price_salience=_clip(persona.daily_routine.budget_consciousness * 0.5),
        perceived_value=_clip(
            (scenario.product.taste_appeal * 0.5)
            + (persona.education_learning.science_literacy * 0.3)
            + (persona.health.nutrition_gap_awareness * 0.2)
        ),
        effort_friction=_clip(scenario.product.effort_to_acquire * (1.0 - online_comfort)),
        discretionary_budget=_clip(1.0 - persona.daily_routine.budget_consciousness),
        brand_salience=_clip(scenario.marketing.awareness_level),
        has_lj_pass=False,
        pack_duration=DEFAULT_PACK_DURATION_DAYS,
    )
    clip_state(state)
    return state


def derive_thresholds(persona: Persona) -> dict[str, float]:
    """Derive persona-specific decision thresholds from identity attributes."""

    return {
        "awareness_threshold": 0.25 - (0.1 * persona.media.ad_receptivity),
        "trust_threshold": 0.4 + (0.2 * (1.0 - persona.psychology.risk_tolerance)),
        "price_reference_point": persona.daily_routine.price_reference_point,
    }


def apply_daily_dynamics(state: CanonicalState) -> None:
    """Apply natural decay/growth per day. Mutates state in-place."""

    state.brand_salience -= EVENT_BRAND_SALIENCE_DECAY_PER_DAY
    if state.is_active:
        state.fatigue += EVENT_FATIGUE_GROWTH_PER_DAY
        state.days_since_purchase += 1
        if state.current_pack_day > 0:
            state.current_pack_day += 1
        if state.pack_duration > 0 and state.current_pack_day > 0:
            remaining_days = state.pack_duration - state.current_pack_day
            if remaining_days <= 0:
                state.reorder_urgency = 1.0
            elif remaining_days <= EVENT_REORDER_URGENCY_RAMP_DAYS:
                ramp = (
                    EVENT_REORDER_URGENCY_RAMP_DAYS - remaining_days
                ) / EVENT_REORDER_URGENCY_RAMP_DAYS
                state.reorder_urgency = max(state.reorder_urgency, _clip(ramp))
    else:
        state.habit_strength -= EVENT_HABIT_DECAY_PER_DAY

    clip_state(state)
