"""Unit tests for static simulation runner."""

from __future__ import annotations

from src.generation.population import PopulationGenerator
from src.simulation.static import run_static_simulation


def test_static_returns_result_for_every_persona(sample_scenario) -> None:  # type: ignore[no-untyped-def]
    """Each Tier 1 persona receives a funnel decision payload."""

    gen = PopulationGenerator()
    pop = gen.generate(size=35, seed=11, deep_persona_count=3)
    result = run_static_simulation(pop, sample_scenario, seed=99)
    assert result.population_size == len(pop.tier1_personas)
    assert len(result.results_by_persona) == result.population_size
    for pid in result.results_by_persona:
        row = result.results_by_persona[pid]
        assert "outcome" in row
        assert "need_score" in row


def test_static_adoption_rate_between_0_and_1(sample_scenario) -> None:  # type: ignore[no-untyped-def]
    """Adoption rate stays inside the unit interval."""

    gen = PopulationGenerator()
    pop = gen.generate(size=40, seed=22, deep_persona_count=2)
    result = run_static_simulation(pop, sample_scenario, seed=1)
    assert 0.0 <= result.adoption_rate <= 1.0


def test_static_deterministic_with_seed(sample_scenario) -> None:  # type: ignore[no-untyped-def]
    """Identical population, scenario, and seed reproduce the same outcome."""

    gen = PopulationGenerator()
    pop_a = gen.generate(size=28, seed=555, deep_persona_count=2)
    pop_b = gen.generate(size=28, seed=555, deep_persona_count=2)
    r1 = run_static_simulation(pop_a, sample_scenario, seed=1234)
    r2 = run_static_simulation(pop_b, sample_scenario, seed=1234)
    assert r1.model_dump() == r2.model_dump()


def test_static_rejection_distribution_sums_to_rejections(sample_scenario) -> None:  # type: ignore[no-untyped-def]
    """Rejections partition non-adopters by funnel stage."""

    gen = PopulationGenerator()
    pop = gen.generate(size=32, seed=33, deep_persona_count=2)
    result = run_static_simulation(pop, sample_scenario, seed=7)
    rejected = result.population_size - result.adoption_count
    staged = sum(result.rejection_distribution.values())
    assert staged == rejected
