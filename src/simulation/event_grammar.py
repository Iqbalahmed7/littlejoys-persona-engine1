"""Event grammar: event definitions, firing rules, and state impact functions.

Defines what events can happen during simulation, when they fire,
and how they affect a persona's mutable state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

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

    del scenario
    events: list[SimulationEvent] = []
    if rng.random() < (0.04 + (0.08 * persona.media.ad_receptivity)):
        events.append(SimulationEvent(event_type="ad_exposure", day=day, intensity=0.15))
    if state.is_active and rng.random() < 0.05:
        events.append(SimulationEvent(event_type="child_rejection", day=day, intensity=0.25))
    if rng.random() < 0.03:
        events.append(SimulationEvent(event_type="competitor_discount", day=day, intensity=0.4))
    if rng.random() < (0.02 + (0.05 * persona.relationships.wom_receiver_openness)):
        events.append(SimulationEvent(event_type="peer_mention", day=day, intensity=0.2))
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
