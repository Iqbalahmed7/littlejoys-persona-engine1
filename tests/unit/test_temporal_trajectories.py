"""Tests for extracting persona trajectories from temporal simulation."""

from __future__ import annotations

import pytest

from src.decision.scenarios import get_scenario
from src.generation.population import Population, PopulationGenerator
from src.simulation.temporal import extract_persona_trajectories


@pytest.fixture(scope="module")
def population() -> Population:
    """Generate a stable population for trajectory tests."""
    return PopulationGenerator().generate(seed=42, size=50)


@pytest.fixture(scope="module")
def scenario():
    return get_scenario("nutrimix_2_6")


@pytest.fixture(scope="module")
def trajectories(population, scenario):
    """Run baseline traversal on the target scenario."""
    return extract_persona_trajectories(
        population=population,
        scenario=scenario,
        months=6,
        seed=42,
    )


def test_trajectory_count_matches_population(trajectories, population):
    """Ensure exactly one trajectory per persona exists."""
    assert len(trajectories) == len(population.personas)

    trajectory_ids = {t.persona_id for t in trajectories}
    population_ids = {p.id for p in population.personas}
    assert trajectory_ids == population_ids


def test_trajectory_months_match(trajectories):
    """Ensure every trajectory features exactly 6 months of states."""
    for trajectory in trajectories:
        assert len(trajectory.monthly_states) == 6
        assert [s.month for s in trajectory.monthly_states] == list(range(1, 7))


def test_adopted_persona_active(trajectories):
    """If a persona ever adopted, they must have is_active=True at some point."""
    adopted_trajectories = [
        t for t in trajectories
        if any(state.adopted_this_month for state in t.monthly_states)
    ]

    # Assert at least someone adopted so the test is meaningful
    assert len(adopted_trajectories) > 0

    for trajectory in adopted_trajectories:
        assert any(state.is_active for state in trajectory.monthly_states)


def test_churned_flag_set(trajectories):
    """If a persona churned, they churn exactly once and flag is True."""
    churned_trajectories = [
        t for t in trajectories
        if any(state.churned_this_month for state in t.monthly_states)
    ]

    for trajectory in churned_trajectories:
        churns = [state for state in trajectory.monthly_states if state.churned_this_month]
        # A person can theoretically churn multiple times if active=True->False->True, but
        # currently ever_adopted locks adoption so they only re-purchase if they didn't churn
        # If they churned, they should have a true churn flag
        assert len(churns) == 1

        # After churn, they must not be active that month
        for churn_state in churns:
            assert churn_state.is_active is False


def test_determinism(population, scenario):
    """Running extraction twice with same seed outputs strictly matching trajectories."""
    run_1 = extract_persona_trajectories(
        population=population,
        scenario=scenario,
        months=6,
        seed=100,
    )

    run_2 = extract_persona_trajectories(
        population=population,
        scenario=scenario,
        months=6,
        seed=100,
    )

    t1_dump = [t.model_dump() for t in sorted(run_1, key=lambda p: p.persona_id)]
    t2_dump = [t.model_dump() for t in sorted(run_2, key=lambda p: p.persona_id)]

    assert t1_dump == t2_dump


def test_non_adopter_always_inactive(trajectories):
    """If a persona never adopted, their active flag must remain False forever."""
    non_adopter_trajectories = [
        t for t in trajectories
        if not any(state.adopted_this_month for state in t.monthly_states)
    ]

    assert len(non_adopter_trajectories) > 0

    for trajectory in non_adopter_trajectories:
        assert all(state.is_active is False for state in trajectory.monthly_states)
