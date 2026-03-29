"""Unit tests for event grammar."""

from __future__ import annotations

import random

from src.simulation.event_grammar import (
    SimulationEvent,
    apply_event_impact,
    fire_deterministic_events,
    fire_stochastic_events,
    is_decision_point,
)
from src.simulation.state_model import CanonicalState


class MockMedia:
    def __init__(self, ad_receptivity: float):
        self.ad_receptivity = ad_receptivity


class MockLifestyle:
    def __init__(self, wellness_trend_follower: float):
        self.wellness_trend_follower = wellness_trend_follower


class MockHealth:
    def __init__(self, medical_authority_trust: float):
        self.medical_authority_trust = medical_authority_trust


class MockRelationships:
    def __init__(self, wom_receiver_openness: float, child_taste_veto: float):
        self.wom_receiver_openness = wom_receiver_openness
        self.child_taste_veto = child_taste_veto


class MockPsychology:
    def __init__(self, social_proof_bias: float):
        self.social_proof_bias = social_proof_bias


class MockDailyRoutine:
    def __init__(self, budget_consciousness: float, deal_seeking_intensity: float):
        self.budget_consciousness = budget_consciousness
        self.deal_seeking_intensity = deal_seeking_intensity


class MockProduct:
    def __init__(self, taste_appeal: float):
        self.taste_appeal = taste_appeal


class MockMarketing:
    def __init__(
        self,
        awareness_budget: float,
        influencer_campaign: bool,
        pediatrician_endorsement: bool,
    ):
        self.awareness_budget = awareness_budget
        self.influencer_campaign = influencer_campaign
        self.pediatrician_endorsement = pediatrician_endorsement


class MockScenarioConfig:
    def __init__(
        self,
        product: MockProduct,
        marketing: MockMarketing,
        lj_pass_available: bool,
    ):
        self.product = product
        self.marketing = marketing
        self.lj_pass_available = lj_pass_available


class MockPersona:
    def __init__(self):
        self.media = MockMedia(ad_receptivity=0.8)
        self.lifestyle = MockLifestyle(wellness_trend_follower=0.6)
        self.health = MockHealth(medical_authority_trust=0.9)
        self.relationships = MockRelationships(wom_receiver_openness=0.7, child_taste_veto=0.4)
        self.psychology = MockPsychology(social_proof_bias=0.5)
        self.daily_routine = MockDailyRoutine(budget_consciousness=0.6, deal_seeking_intensity=0.7)


def test_simulation_event_model():
    """SimulationEvent model creates correctly."""
    event = SimulationEvent(event_type="test", day=5, intensity=0.7)
    assert event.event_type == "test"
    assert event.day == 5
    assert event.intensity == 0.7
    assert event.attributes == {}


def test_fire_deterministic_events_pack_finished():
    """fire_deterministic_events returns pack_finished when pack expires."""
    state = CanonicalState(current_pack_day=26, pack_duration=25, is_active=True)
    scenario = MockScenarioConfig(MockProduct(0.7), MockMarketing(0.5, True, True), True)
    events = fire_deterministic_events(state, day=10, scenario=scenario)
    assert any(e.event_type == "pack_finished" for e in events)


def test_fire_deterministic_events_payday():
    """fire_deterministic_events returns payday_relief on day 1."""
    state = CanonicalState(is_active=False)
    scenario = MockScenarioConfig(MockProduct(0.7), MockMarketing(0.5, True, True), True)
    events = fire_deterministic_events(state, day=1, scenario=scenario)
    assert any(e.event_type == "payday_relief" for e in events)


def test_fire_stochastic_events_deterministic_seed():
    """fire_stochastic_events is deterministic with same seed."""
    state = CanonicalState(is_active=True, fatigue=0.2)
    persona = MockPersona()
    scenario = MockScenarioConfig(MockProduct(0.7), MockMarketing(0.5, True, True), True)
    rng1 = random.Random(42)
    events1 = fire_stochastic_events(state, persona, day=10, scenario=scenario, rng=rng1)
    rng2 = random.Random(42)
    events2 = fire_stochastic_events(state, persona, day=10, scenario=scenario, rng=rng2)
    assert events1 == events2


def test_apply_event_impact_clips_values():
    """apply_event_impact clips values to [0, 1]."""
    state = CanonicalState(brand_salience=0.95)
    persona = MockPersona()
    event = SimulationEvent(event_type="ad_exposure", day=1, intensity=1.0)
    apply_event_impact(state, event, persona)
    # 0.95 + 0.25*1.0 = 1.20, should be clipped to 1.0
    assert state.brand_salience == 1.0


def test_is_decision_point_pack_finished():
    """is_decision_point returns True on pack_finished."""
    state = CanonicalState()
    events = [SimulationEvent(event_type="pack_finished", day=1, intensity=1.0)]
    assert is_decision_point(state, events) is True


def test_apply_event_impact_doctor_recommendation():
    """doctor_recommendation increases trust."""
    state = CanonicalState(trust=0.5)
    persona = MockPersona()
    event = SimulationEvent(event_type="doctor_recommendation", day=1, intensity=1.0)
    apply_event_impact(state, event, persona)
    assert state.trust > 0.5  # Increases by 0.10


def test_apply_event_impact_child_rejection():
    """child_rejection decreases child_acceptance."""
    state = CanonicalState(child_acceptance=0.6)
    persona = MockPersona()
    event = SimulationEvent(event_type="child_rejection", day=1, intensity=1.0)
    apply_event_impact(state, event, persona)
    assert state.child_acceptance < 0.6  # Decreases by 0.10
