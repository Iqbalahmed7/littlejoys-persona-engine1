"""Event grammar: event definitions, firing rules, and state impact functions.

Defines what events can happen during simulation, when they fire,
and how they affect a persona's mutable state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from src.constants import (
    EVENT_FATIGUE_THRESHOLD_BOREDOM,
    EVENT_IMPACT_BRAND_SALIENCE_INFLUENCER,
    EVENT_IMPACT_BRAND_SALIENCE_REMINDER,
    EVENT_IMPACT_CHILD_ACCEPTANCE_BOREDOM,
    EVENT_IMPACT_CHILD_ACCEPTANCE_POSITIVE,
    EVENT_IMPACT_DISCRETIONARY_BUDGET_BUDGET_PRESSURE_NEG,
    EVENT_IMPACT_FATIGUE_CHILD_BOREDOM,
    EVENT_IMPACT_FATIGUE_USAGE_DROP,
    EVENT_IMPACT_HABIT_STRENGTH_USAGE_DAILY,
    EVENT_IMPACT_PERCEIVED_VALUE_CHILD_POSITIVE,
    EVENT_IMPACT_PERCEIVED_VALUE_USAGE_DROP_NEG,
    EVENT_IMPACT_PRICE_SALIENCE_BUDGET_PRESSURE,
    EVENT_IMPACT_REORDER_URGENCY_REMINDER,
    EVENT_IMPACT_TRUST_INFLUENCER,
    EVENT_PASS_OFFER_MIN_PURCHASES,
    EVENT_PROB_BUDGET_PRESSURE_INCREASE_BASE,
    EVENT_PROB_CHILD_BOREDOM_BASE,
    EVENT_PROB_CHILD_POSITIVE_REACTION_BASE,
    EVENT_PROB_DOCTOR_RECOMMENDATION_BASE,
    EVENT_PROB_INFLUENCER_EXPOSURE_BASE,
    EVENT_PROB_PASS_OFFER_BASE,
    EVENT_PROB_REMINDER_BASE,
    EVENT_PROB_USAGE_DROP_BASE,
    EVENT_REMINDER_DAYS_SINCE_PURCHASE_THRESHOLD,
)
from src.simulation.state_model import CanonicalState, clip_state

if TYPE_CHECKING:
    from random import Random

    from src.decision.scenarios import ScenarioConfig
    from src.taxonomy.schema import Persona


class SimulationEvent(BaseModel):
    """One simulation event that can impact canonical persona state."""

    model_config = ConfigDict(extra="forbid")

    event_type: str
    day: int
    intensity: float = 1.0
    attributes: dict[str, object] = Field(default_factory=dict)


def fire_deterministic_events(
    state: CanonicalState,
    day: int,
    scenario: ScenarioConfig,
) -> list[SimulationEvent]:
    """Emit deterministic fallback events: weekly ads and pack-finished triggers."""

    events: list[SimulationEvent] = []
    if day % 7 == 0:
        events.append(SimulationEvent(event_type="ad_exposure", day=day, intensity=0.22))
    if state.is_active and state.current_pack_day >= state.pack_duration and state.pack_duration > 0:
        events.append(SimulationEvent(event_type="pack_finished", day=day, intensity=1.0))
    if day == 1 or day % 30 == 0:
        events.append(SimulationEvent(event_type="payday_relief", day=day, intensity=0.5))
    if scenario.lj_pass_available and state.is_active and day % 30 == 0:
        events.append(SimulationEvent(event_type="subscription_reminder", day=day, intensity=0.2))
    return events


def fire_stochastic_events(
    state: CanonicalState,
    persona: Persona,
    day: int,
    scenario: ScenarioConfig,
    rng: Random,
) -> list[SimulationEvent]:
    """Emit stochastic fallback events used for local deterministic testing."""


    events: list[SimulationEvent] = []
    if rng.random() < (0.04 + (0.08 * persona.media.ad_receptivity)):
        events.append(SimulationEvent(event_type="ad_exposure", day=day, intensity=0.15))
    if state.is_active and rng.random() < 0.05:
        events.append(SimulationEvent(event_type="child_rejection", day=day, intensity=0.25))
    if rng.random() < 0.03:
        events.append(SimulationEvent(event_type="competitor_discount", day=day, intensity=0.4))
    if rng.random() < (0.02 + (0.05 * persona.relationships.wom_receiver_openness)):
        events.append(SimulationEvent(event_type="peer_mention", day=day, intensity=0.2))

    # 1. child_positive_reaction
    if state.is_active and rng.random() < EVENT_PROB_CHILD_POSITIVE_REACTION_BASE:
        events.append(SimulationEvent(event_type="child_positive_reaction", day=day, intensity=0.3))

    # 2. child_boredom
    if (state.is_active and state.fatigue > EVENT_FATIGUE_THRESHOLD_BOREDOM
            and rng.random() < EVENT_PROB_CHILD_BOREDOM_BASE):
        events.append(SimulationEvent(event_type="child_boredom", day=day, intensity=0.2))

    # 3. usage_consistent — daily habit reinforcement when actively using
    if state.is_active and rng.random() < 0.8:
        events.append(SimulationEvent(event_type="usage_consistent", day=day, intensity=0.1))

    # 4. usage_drop — reduced usage when fatigue builds
    if state.is_active and state.fatigue > 0.4 and rng.random() < EVENT_PROB_USAGE_DROP_BASE:
        events.append(SimulationEvent(event_type="usage_drop", day=day, intensity=0.3))

    # 5. budget_pressure_increase
    if rng.random() < EVENT_PROB_BUDGET_PRESSURE_INCREASE_BASE:
        events.append(SimulationEvent(event_type="budget_pressure_increase", day=day, intensity=0.5))

    # 6. influencer_exposure
    if rng.random() < EVENT_PROB_INFLUENCER_EXPOSURE_BASE * (0.5 + persona.media.ad_receptivity):
        events.append(SimulationEvent(event_type="influencer_exposure", day=day, intensity=0.3))

    # 7. doctor_recommendation — rare but high impact
    if rng.random() < EVENT_PROB_DOCTOR_RECOMMENDATION_BASE:
        events.append(SimulationEvent(event_type="doctor_recommendation", day=day, intensity=0.8))

    # 8. reminder — only for inactive personas who previously adopted
    if (not state.is_active and state.ever_adopted
            and state.days_since_purchase > EVENT_REMINDER_DAYS_SINCE_PURCHASE_THRESHOLD
            and rng.random() < EVENT_PROB_REMINDER_BASE):
        events.append(SimulationEvent(event_type="reminder", day=day, intensity=0.4))

    # 9. pass_offer — for active multi-purchasers without a pass
    if (scenario.lj_pass_available and state.is_active
            and state.total_purchases >= EVENT_PASS_OFFER_MIN_PURCHASES
            and not state.has_lj_pass
            and rng.random() < EVENT_PROB_PASS_OFFER_BASE):
        events.append(SimulationEvent(event_type="pass_offer", day=day, intensity=0.5))

    return events


def apply_event_impact(state: CanonicalState, event: SimulationEvent, persona: Persona) -> None:
    """Apply basic event-driven deltas to canonical state variables."""

    intensity = float(event.intensity)
    if event.event_type == "ad_exposure":
        state.brand_salience += 0.25 * intensity
    elif event.event_type == "peer_mention":
        state.brand_salience += 0.15 * intensity
        state.trust += 0.08 * intensity
    elif event.event_type == "child_rejection":
        state.child_acceptance -= 0.2 * intensity
        state.fatigue += 0.08 * intensity
    elif event.event_type == "competitor_discount":
        state.price_salience += 0.18 * intensity
        state.perceived_value -= 0.1 * intensity
    elif event.event_type == "subscription_reminder":
        state.reorder_urgency += 0.1 * intensity
    elif event.event_type == "pack_finished":
        state.reorder_urgency = max(state.reorder_urgency, 0.6)
    elif event.event_type == "doctor_recommendation":
        state.trust += 0.2 * intensity
        state.perceived_value += 0.1 * intensity

    elif event.event_type == "child_positive_reaction":
        state.child_acceptance += EVENT_IMPACT_CHILD_ACCEPTANCE_POSITIVE * intensity
        state.perceived_value += EVENT_IMPACT_PERCEIVED_VALUE_CHILD_POSITIVE * intensity

    elif event.event_type == "child_boredom":
        state.child_acceptance -= EVENT_IMPACT_CHILD_ACCEPTANCE_BOREDOM * intensity
        state.fatigue += EVENT_IMPACT_FATIGUE_CHILD_BOREDOM * intensity

    elif event.event_type == "usage_consistent":
        state.habit_strength += EVENT_IMPACT_HABIT_STRENGTH_USAGE_DAILY * intensity

    elif event.event_type == "usage_drop":
        state.fatigue += EVENT_IMPACT_FATIGUE_USAGE_DROP * intensity
        state.perceived_value -= EVENT_IMPACT_PERCEIVED_VALUE_USAGE_DROP_NEG * intensity

    elif event.event_type == "budget_pressure_increase":
        state.price_salience += EVENT_IMPACT_PRICE_SALIENCE_BUDGET_PRESSURE * intensity
        state.discretionary_budget -= EVENT_IMPACT_DISCRETIONARY_BUDGET_BUDGET_PRESSURE_NEG * intensity

    elif event.event_type == "influencer_exposure":
        state.brand_salience += EVENT_IMPACT_BRAND_SALIENCE_INFLUENCER * intensity
        state.trust += EVENT_IMPACT_TRUST_INFLUENCER * intensity

    elif event.event_type == "reminder":
        state.reorder_urgency += EVENT_IMPACT_REORDER_URGENCY_REMINDER * intensity
        state.brand_salience += EVENT_IMPACT_BRAND_SALIENCE_REMINDER * intensity

    elif event.event_type == "pass_offer":
        state.reorder_urgency += 0.1 * intensity

    elif event.event_type == "payday_relief":
        state.price_salience -= 0.03
        state.discretionary_budget += 0.04

    _ = persona
    clip_state(state)


def is_decision_point(state: CanonicalState, events: list[SimulationEvent]) -> bool:
    """Determine whether the decision engine should evaluate this day.

    Decision points:
    1. pack_finished event fired (reorder decision)
    2. brand_salience crossed awareness threshold for first time (first purchase)
    3. pass_offer or subscription_reminder fired (subscription decision)
    4. reminder fired and persona is inactive (re-engagement)
    """
    event_types = {e.event_type for e in events}
    if "pack_finished" in event_types:
        return True
    if not state.ever_adopted and state.brand_salience > 0.3:
        return True
    if "pass_offer" in event_types or "subscription_reminder" in event_types:
        return True
    return "reminder" in event_types and not state.is_active
