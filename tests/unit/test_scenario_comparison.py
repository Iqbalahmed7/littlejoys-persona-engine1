"""Unit tests for the side-by-side scenario comparison engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.analysis.scenario_comparison import ScenarioComparisonResult, compare_scenarios
from src.constants import DASHBOARD_DEFAULT_POPULATION_PATH, DEFAULT_SEED
from src.decision.scenarios import get_scenario
from src.generation.population import Population, PopulationGenerator


@pytest.fixture(scope="module")
def population():
    """Load or generate a small population for comparison tests."""
    path = Path(DASHBOARD_DEFAULT_POPULATION_PATH)
    if (path / "population_meta.json").exists():
        return Population.load(path)
    return PopulationGenerator().generate(seed=DEFAULT_SEED, size=10)


def test_compare_same_scenario_zero_delta(population):
    """Comparing a scenario with itself should produce zero adoption_delta."""
    scenario_a = get_scenario("nutrimix_2_6")
    
    # Compare with identical scenario config
    result = compare_scenarios(population, scenario_a, scenario_a, seed=42)
    
    assert isinstance(result, ScenarioComparisonResult)
    assert result.scenario_a_id == result.scenario_b_id
    assert result.adoption_delta == pytest.approx(0.0)
    # Check that individual barrier deltas are zero
    for b in result.barrier_comparison:
        assert b.delta == 0


def test_compare_different_scenarios(population):
    """Comparing Nutrimix vs Magnesium Gummies should produce non-zero deltas."""
    scenario_a = get_scenario("nutrimix_2_6")
    scenario_b = get_scenario("magnesium_gummies")
    
    result = compare_scenarios(population, scenario_a, scenario_b, seed=42)
    
    assert result.adoption_delta != 0.0
    assert result.adoption_rate_a != result.adoption_rate_b


def test_comparison_result_structure(population):
    """Verify all required fields of ScenarioComparisonResult are populated."""
    scenario_a = get_scenario("nutrimix_2_6")
    scenario_b = get_scenario("nutrimix_7_14")
    
    result = compare_scenarios(population, scenario_a, scenario_b, seed=42)
    
    # These fields should be present
    assert result.scenario_a_name is not None
    assert result.scenario_b_name is not None
    assert isinstance(result.barrier_comparison, list)
    assert isinstance(result.driver_comparison, list)
    
    # Nutrimix 7-14 is temporal, so active_delta should exist
    if scenario_a.mode == "temporal" and scenario_b.mode == "temporal":
        assert result.active_delta is not None
        assert result.revenue_delta is not None


def test_comparison_barrier_deltas(population):
    """Ensure barrier comparison includes counts from both sides."""
    scenario_a = get_scenario("nutrimix_2_6")
    scenario_b = get_scenario("magnesium_gummies")
    
    result = compare_scenarios(population, scenario_a, scenario_b, seed=42)
    
    assert len(result.barrier_comparison) > 0
    first_barrier = result.barrier_comparison[0]
    assert hasattr(first_barrier, "count_a")
    assert hasattr(first_barrier, "count_b")
    assert first_barrier.delta == first_barrier.count_b - first_barrier.count_a


def test_comparison_determinism(population):
    """Verify that using the same seed produces identical results."""
    scenario_a = get_scenario("nutrimix_2_6")
    scenario_b = get_scenario("magnesium_gummies")
    
    res1 = compare_scenarios(population, scenario_a, scenario_b, seed=42)
    res2 = compare_scenarios(population, scenario_a, scenario_b, seed=42)
    
    assert res1.adoption_delta == res2.adoption_delta
    assert res1.driver_comparison[0].delta == res2.driver_comparison[0].delta
