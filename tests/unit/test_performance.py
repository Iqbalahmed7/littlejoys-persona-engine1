"""Unit tests for performance and throughput SLAs."""

from __future__ import annotations

import time

import pytest

from src.constants import DEFAULT_SEED
from src.decision.scenarios import get_scenario
from src.generation.population import PopulationGenerator
from src.simulation.event_engine import run_event_simulation
from src.simulation.static import run_static_simulation


@pytest.fixture(scope="module")
def perf_population():
    """100 personas for performance benchmarking."""
    # We use a fixed seed to ensure repeatability
    return PopulationGenerator().generate(size=100, seed=DEFAULT_SEED)


def test_static_simulation_performance(perf_population):
    """Execution of static adoption for 100 personas should be < 5s."""
    scenario = get_scenario("nutrimix_2_6")

    start = time.time()
    result = run_static_simulation(perf_population, scenario, seed=DEFAULT_SEED)
    duration = time.time() - start

    assert result.population_size == 100
    # Performance SLA: 100 personas < 5s.
    # Usually it takes < 0.1s in mock mode, but we use a generous bound for CI.
    assert duration < 5.0


def test_event_simulation_performance(perf_population):
    """360-day event simulation for 100 personas should be < 15s."""
    scenario = get_scenario("nutrimix_2_6")

    start = time.time()
    # 360 days is the standard simulation length
    result = run_event_simulation(
        population=perf_population,
        scenario=scenario,
        duration_days=360,
        seed=DEFAULT_SEED
    )
    duration = time.time() - start

    assert result.population_size == 100
    # Performance SLA: 100 personas x 360 days < 15s.
    assert duration < 15.0


def test_scenario_adoption_under_load():
    """Repeated runs of scenario adoption should maintain stable performance."""
    pop = PopulationGenerator().generate(size=30, seed=DEFAULT_SEED)
    scenario = get_scenario("nutrimix_2_6")

    durations = []
    for _ in range(5):
        start = time.time()
        run_static_simulation(pop, scenario, seed=DEFAULT_SEED)
        durations.append(time.time() - start)

    avg_duration = sum(durations) / len(durations)
    # Average 30-persona run should be very fast
    assert avg_duration < 1.0
