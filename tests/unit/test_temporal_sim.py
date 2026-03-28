"""Unit tests for temporal simulation runner."""

from __future__ import annotations

from src.decision.repeat import compute_churn_probability
from src.decision.scenarios import ScenarioConfig
from src.generation.population import PopulationGenerator
from src.simulation.temporal import run_temporal_simulation


def test_temporal_runs_for_specified_months(sample_scenario) -> None:  # type: ignore[no-untyped-def]
    """Snapshot list length matches the requested horizon."""

    gen = PopulationGenerator()
    pop = gen.generate(size=25, seed=101, deep_persona_count=2)
    result = run_temporal_simulation(pop, sample_scenario, months=8, seed=5)
    assert len(result.monthly_snapshots) == 8


def test_awareness_increases_over_time(sample_scenario) -> None:  # type: ignore[no-untyped-def]
    """Marketing growth and boosts weakly lift mean modeled awareness."""

    gen = PopulationGenerator()
    pop = gen.generate(size=30, seed=202, deep_persona_count=2)
    result = run_temporal_simulation(pop, sample_scenario, months=10, seed=6)
    first = result.monthly_snapshots[0].awareness_level_mean
    last = result.monthly_snapshots[-1].awareness_level_mean
    assert last >= first


def test_cumulative_adopters_never_decrease(sample_scenario) -> None:  # type: ignore[no-untyped-def]
    """Ever-adopted counts are monotone non-decreasing."""

    gen = PopulationGenerator()
    pop = gen.generate(size=28, seed=303, deep_persona_count=2)
    result = run_temporal_simulation(pop, sample_scenario, months=9, seed=8)
    prev = -1
    for snap in result.monthly_snapshots:
        assert snap.cumulative_adopters >= prev
        prev = snap.cumulative_adopters


def test_temporal_deterministic_with_seed(sample_scenario) -> None:  # type: ignore[no-untyped-def]
    """Same population clone path and seed yields identical temporal outputs."""

    gen = PopulationGenerator()
    pop_a = gen.generate(size=26, seed=404, deep_persona_count=2)
    pop_b = gen.generate(size=26, seed=404, deep_persona_count=2)
    r1 = run_temporal_simulation(pop_a, sample_scenario, months=6, seed=77)
    r2 = run_temporal_simulation(pop_b, sample_scenario, months=6, seed=77)
    assert r1.model_dump() == r2.model_dump()


def test_lj_pass_holders_have_lower_churn(sample_persona) -> None:  # type: ignore[no-untyped-def]
    """Temporal model relies on churn dampening for pass holders (unit check)."""

    hist = [0.4, 0.38, 0.39]
    assert compute_churn_probability(sample_persona, hist, has_lj_pass=True) < compute_churn_probability(
        sample_persona, hist, has_lj_pass=False
    )


def test_temporal_lj_pass_scenario_assigns_holders() -> None:
    """When LJ Pass is enabled, some personas are flagged as pass holders."""

    from src.decision.scenarios import MarketingConfig, ProductConfig

    gen = PopulationGenerator()
    pop = gen.generate(size=80, seed=909, deep_persona_count=4)
    product = ProductConfig(
        name="LittleJoys Temporal",
        category="nutrition",
        price_inr=400.0,
        age_range=(3, 10),
        key_benefits=["nutrition"],
        form_factor="powder",
    )
    scenario = ScenarioConfig(
        id="lj",
        name="lj",
        description="",
        product=product,
        marketing=MarketingConfig(awareness_budget=0.5),
        target_age_range=(2, 14),
        lj_pass_available=True,
    )
    result = run_temporal_simulation(pop, scenario, months=4, seed=3)
    assert result.monthly_snapshots[-1].lj_pass_holders > 0
