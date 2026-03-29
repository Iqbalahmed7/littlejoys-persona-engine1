"""Unit tests for CanonicalState, initialization, and daily dynamics."""

from __future__ import annotations

import pytest

from src.decision.scenarios import get_scenario
from src.generation.population import PopulationGenerator
from src.simulation.state_model import (
    CanonicalState,
    apply_daily_dynamics,
    derive_thresholds,
    initialize_state,
)


@pytest.fixture(scope="module")
def persona():
    """Generate a single persona for testing."""
    population = PopulationGenerator().generate(seed=42, size=1)
    return population.personas[0]


@pytest.fixture(scope="module")
def scenario():
    """Get a baseline scenario."""
    return get_scenario("nutrimix_2_6")


def test_initialize_state_all_in_range(persona, scenario):
    """Verify all 10 state variables are in the closed unit interval [0, 1]."""
    state = initialize_state(persona, scenario)

    fields = [
        "trust", "habit_strength", "child_acceptance", "price_salience",
        "reorder_urgency", "fatigue", "perceived_value", "brand_salience",
        "effort_friction", "discretionary_budget"
    ]

    for field in fields:
        val = getattr(state, field)
        assert 0.0 <= val <= 1.0, f"Field {field} value {val} is out of range [0, 1]."


def test_initialize_state_deterministic(persona, scenario):
    """Initializing state twice for the same persona/scenario should be identical."""
    s1 = initialize_state(persona, scenario)
    s2 = initialize_state(persona, scenario)
    assert s1.model_dump() == s2.model_dump()


def test_derive_thresholds_range(persona):
    """Thresholds should be within reasonable bounds."""
    thresholds = derive_thresholds(persona)
    assert 0.0 < thresholds["awareness_threshold"] < 1.0
    assert 0.0 < thresholds["trust_threshold"] < 1.0
    assert thresholds["price_reference_point"] > 0


def test_apply_daily_dynamics_fatigue_grows():
    """Fatigue should increase when active."""
    state = CanonicalState(fatigue=0.1, is_active=True)
    apply_daily_dynamics(state)
    assert state.fatigue > 0.1


def test_apply_daily_dynamics_habit_decays():
    """Habit strength should decrease when inactive."""
    state = CanonicalState(habit_strength=0.5, is_active=False)
    apply_daily_dynamics(state)
    assert state.habit_strength < 0.5


def test_apply_daily_dynamics_clips():
    """Deltas should be clipped into [0, 1]."""
    # Test clipping at 0.0
    state_0 = CanonicalState(brand_salience=0.0, habit_strength=0.0, is_active=False)
    apply_daily_dynamics(state_0)
    assert state_0.brand_salience == 0.0
    assert state_0.habit_strength == 0.0

    # Test clipping at 1.0 (fatigue grows)
    state_1 = CanonicalState(fatigue=1.0, is_active=True)
    apply_daily_dynamics(state_1)
    assert state_1.fatigue == 1.0


def test_apply_daily_dynamics_resets_overstayed_pack():
    """Overstayed active packs should reset tracking to avoid endless pack_finished loops."""

    state = CanonicalState(
        is_active=True,
        current_pack_day=40,
        pack_duration=25,
        reorder_urgency=0.2,
    )
    apply_daily_dynamics(state)

    assert state.current_pack_day == 0
    assert state.reorder_urgency >= 0.8
