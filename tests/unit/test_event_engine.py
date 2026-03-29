"""Unit tests for the day-level simulation engine logic and trajectory management."""

from __future__ import annotations

import pytest

from src.decision.scenarios import get_scenario
from src.generation.population import PopulationGenerator
from src.simulation.event_engine import run_event_simulation


@pytest.fixture(scope="module")
def population():
    """Generate a stable population for testing."""
    return PopulationGenerator().generate(seed=42, size=20)


@pytest.fixture(scope="module")
def result(population):
    """Run the day-level simulation on a baseline scenario."""
    scenario = get_scenario("nutrimix_2_6") # mode="temporal"
    return run_event_simulation(
        population=population,
        scenario=scenario,
        duration_days=60, # 2 month sim
        seed=42,
    )


def test_event_simulation_returns_result(result):
    """Verify simulation returns the expected result object."""
    from src.simulation.event_engine import EventSimulationResult
    assert isinstance(result, EventSimulationResult)
    assert result.duration_days == 60


def test_trajectories_match_population(result, population):
    """Verify 1:1 mapping between personas and trajectories."""
    assert len(result.trajectories) == len(population.personas)
    trajectory_ids = {t.persona_id for t in result.trajectories}
    persona_ids = {p.id for p in population.personas}
    assert trajectory_ids == persona_ids


def test_trajectory_days_match_duration(result):
    """Each trajectory must have exactly duration_days snapshots."""
    for trajectory in result.trajectories:
        assert len(trajectory.days) == 60


def test_determinism(population):
    """Simulation should be deterministic for identical seeds."""
    scenario = get_scenario("nutrimix_2_6")

    r1 = run_event_simulation(population, scenario, 30, seed=42)
    r2 = run_event_simulation(population, scenario, 30, seed=42)

    assert r1.final_active_count == r2.final_active_count
    assert r1.total_revenue_estimate == r2.total_revenue_estimate


def test_decisions_are_valid(result):
    """All decisions must be in the specified set."""
    valid_decisions = {"purchase", "reorder", "churn", "switch", "delay", "subscribe", None}
    for trajectory in result.trajectories:
        for snap in trajectory.days:
            assert snap.decision in valid_decisions


def test_pack_finished_triggers_decision(result):
    """When pack_finished occurs, a decision point must be triggered."""
    found_pack_finished = False
    for trajectory in result.trajectories:
        for snap in trajectory.days:
            if "pack_finished" in snap.events_fired:
                found_pack_finished = True
                assert snap.decision is not None, "pack_finished event fired but no decision was recorded."

    assert found_pack_finished, "No pack_finished event found during 2-month simulation."


def test_monthly_rollup_has_months(result):
    """Rolling up should produce exactly 2 months for 60 days."""
    assert len(result.aggregate_monthly) == 2


def test_first_purchase_requires_brand_salience(population):
    """Personas with 0 brand_salience should not convert on day 1."""
    scenario = get_scenario("nutrimix_2_6")
    # Toggling thresholds to be very high for awareness

    # We create a dummy run where we force brand_salience initialization to 0
    # Actually, initialize_state uses persona attributes. If brand_salience was 0,
    # it won't trigger decision point until brand_salience > 0.3 (deterministic).

    res = run_event_simulation(population, scenario, duration_days=1, seed=42)
    for trajectory in res.trajectories:
        snap = trajectory.days[0]
        if snap.state["brand_salience"] == 0:
            assert snap.decision is None or snap.decision == "delay"
