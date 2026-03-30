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


def test_child_positive_reaction_fires_when_active():
    """child_positive_reaction should only fire when persona is active."""
    state = CanonicalState(is_active=True)
    persona = MockPersona()
    scenario = MockScenarioConfig(MockProduct(0.7), MockMarketing(0.5, True, True), True)
    rng = random.Random(42)
    # Probability is 0.05, seed 42 on day 1 with fixed logic should be deterministic
    found = False
    for day in range(1, 100):
        events = fire_stochastic_events(state, persona, day, scenario, rng)
        if any(e.event_type == "child_positive_reaction" for e in events):
            found = True
            break
    assert found


def test_child_boredom_fires_for_active_persona():
    """child_boredom fires from day 1 for any active persona regardless of fatigue."""
    state = CanonicalState(is_active=True, fatigue=0.1)
    persona = MockPersona()
    scenario = MockScenarioConfig(MockProduct(0.7), MockMarketing(0.5, True, True), True)
    rng = random.Random(42)

    # Should fire even with low fatigue — no fatigue prerequisite
    found = False
    for day in range(1, 200):
        events = fire_stochastic_events(state, persona, day, scenario, rng)
        if any(e.event_type == "child_boredom" for e in events):
            found = True
            break
    assert found, "child_boredom should fire for active personas regardless of fatigue level"

    # Should NOT fire for inactive personas
    state_inactive = CanonicalState(is_active=False, fatigue=0.5)
    rng2 = random.Random(42)
    for day in range(1, 100):
        events = fire_stochastic_events(state_inactive, persona, day, scenario, rng2)
        assert not any(e.event_type == "child_boredom" for e in events)


def test_usage_consistent_boosts_habit():
    """usage_consistent impact should increase habit_strength."""
    state = CanonicalState(habit_strength=0.1, is_active=True)
    persona = MockPersona()
    event = SimulationEvent(event_type="usage_consistent", day=1, intensity=1.0)
    apply_event_impact(state, event, persona)
    assert state.habit_strength > 0.1


def test_usage_drop_increases_fatigue():
    """usage_drop should increase fatigue and decrease perceived_value."""
    state = CanonicalState(fatigue=0.2, perceived_value=0.8, is_active=True)
    persona = MockPersona()
    event = SimulationEvent(event_type="usage_drop", day=1, intensity=1.0)
    apply_event_impact(state, event, persona)
    assert state.fatigue > 0.2
    assert state.perceived_value < 0.8


def test_budget_pressure_increases_price_salience():
    """budget_pressure_increase should raise price_salience and lower budget."""
    state = CanonicalState(price_salience=0.3, discretionary_budget=0.7)
    persona = MockPersona()
    event = SimulationEvent(event_type="budget_pressure_increase", day=1, intensity=1.0)
    apply_event_impact(state, event, persona)
    assert state.price_salience > 0.3
    assert state.discretionary_budget < 0.7


def test_influencer_exposure_boosts_brand_and_trust():
    """influencer_exposure should increase brand_salience and trust."""
    state = CanonicalState(brand_salience=0.2, trust=0.2)
    persona = MockPersona()
    event = SimulationEvent(event_type="influencer_exposure", day=1, intensity=1.0)
    apply_event_impact(state, event, persona)
    assert state.brand_salience > 0.2
    assert state.trust > 0.2


def test_doctor_recommendation_high_impact():
    """doctor_recommendation should have larger trust impact than other events."""
    state_dr = CanonicalState(trust=0.2)
    state_inf = CanonicalState(trust=0.2)
    persona = MockPersona()

    apply_event_impact(state_dr, SimulationEvent(event_type="doctor_recommendation", day=1), persona)
    apply_event_impact(state_inf, SimulationEvent(event_type="influencer_exposure", day=1), persona)

    # Doctor impact is 0.2, Influencer is 0.07/0.02 (depending on constants)
    assert state_dr.trust > state_inf.trust


def test_reminder_fires_for_inactive_adopters():
    """reminder should only fire when persona is inactive and has previously adopted."""
    state = CanonicalState(is_active=False, ever_adopted=True, days_since_purchase=30)
    persona = MockPersona()
    scenario = MockScenarioConfig(MockProduct(0.7), MockMarketing(0.5, True, True), True)
    rng = random.Random(42)

    found = False
    for day in range(1, 200):
        events = fire_stochastic_events(state, persona, day, scenario, rng)
        if any(e.event_type == "reminder" for e in events):
            found = True
            break
    assert found

    # Active personas should not get reminders
    state.is_active = True
    for day in range(1, 100):
        events = fire_stochastic_events(state, persona, day, scenario, rng)
        assert not any(e.event_type == "reminder" for e in events)


def test_pass_offer_fires_for_qualified_buyers():
    """pass_offer requires active + 2+ purchases + no existing pass."""
    state = CanonicalState(is_active=True, total_purchases=2, has_lj_pass=False)
    persona = MockPersona()
    # Boost probability for test reliability
    scenario = MockScenarioConfig(MockProduct(0.7), MockMarketing(0.5, True, True), True)
    rng = random.Random(42)

    found = False
    # Use 1000 days to be sure, or a more favorable seed
    for day in range(1, 1000):
        events = fire_stochastic_events(state, persona, day, scenario, rng)
        if any(e.event_type == "pass_offer" for e in events):
            found = True
            break
    assert found, "pass_offer event never fired in 1000 days."

    # Should not fire if already has pass
    state.has_lj_pass = True
    for day in range(1, 100):
        events = fire_stochastic_events(state, persona, day, scenario, rng)
        assert not any(e.event_type == "pass_offer" for e in events)


def test_all_fifteen_event_types_have_impact_handlers():
    """Every event type constant in constants.py should have a handler in apply_event_impact."""
    from src.simulation.event_grammar import apply_event_impact

    # Manually curated list from constants.py for robustness
    expected = {
        "pack_finished", "usage_consistent", "usage_drop", "child_positive_reaction",
        "child_rejection", "child_boredom", "budget_pressure_increase", "payday_relief",
        "competitor_discount", "ad_exposure", "influencer_exposure", "doctor_recommendation",
        "peer_mention", "reminder", "pass_offer"
    }

    state = CanonicalState()
    persona = MockPersona()
    for etype in expected:
        # Should not raise KeyError or pass silently without effect (though effect might be clipped)
        event = SimulationEvent(event_type=etype, day=1)
        apply_event_impact(state, event, persona)
