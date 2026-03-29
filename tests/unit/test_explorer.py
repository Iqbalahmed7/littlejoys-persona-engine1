"""Tests for scenario variant generator (Sprint 10)."""

from __future__ import annotations

import pytest

from src.decision.scenarios import get_scenario
from src.simulation.explorer import (
    GRID_PARAMETERS,
    VariantStrategy,
    generate_grid_variants,
    generate_random_variants,
    generate_smart_variants,
    generate_sweep_variants,
    generate_variants,
)
from src.simulation.static import StaticSimulationResult


@pytest.fixture
def nutrimix() -> object:
    return get_scenario("nutrimix_2_6")


def _assert_channel_mix_unit_sum(scenario) -> None:
    mix = scenario.marketing.channel_mix
    if not mix:
        return
    s = sum(mix.values())
    assert 0.99 <= s <= 1.01


def test_generate_variants_baseline_first(nutrimix) -> None:
    out = generate_variants(nutrimix, VariantStrategy.GRID)
    assert out[0].variant_id == "baseline"
    assert out[0].is_baseline is True
    assert out[0].modifications == {}


def test_generate_variants_smart_requires_result(nutrimix) -> None:
    with pytest.raises(ValueError, match="base_result"):
        generate_variants(nutrimix, VariantStrategy.SMART)


def test_sweep_skips_baseline_price_and_adds_presets(nutrimix) -> None:
    variants = generate_sweep_variants(nutrimix)
    assert len(variants) >= 30
    price_names = [v.variant_name for v in variants if v.variant_name.startswith("Price ₹")]
    base_price = int(nutrimix.product.price_inr)
    assert not any(f"Price ₹{base_price}" in n for n in price_names)
    assert any("Channel:" in v.variant_name for v in variants)
    for v in variants:
        _assert_channel_mix_unit_sum(v.scenario_config)


def test_grid_cartesian_count_and_cap(nutrimix) -> None:
    full = generate_grid_variants(nutrimix)
    assert len(full) == 4 * 4 * 3
    assert "P₹299" in full[0].variant_name or any("P₹299" in v.variant_name for v in full)

    capped = generate_grid_variants(nutrimix, max_combinations=10)
    assert len(capped) == 10


def test_grid_default_uses_grid_parameters() -> None:
    assert set(GRID_PARAMETERS) <= set(
        {
            "product.price_inr",
            "marketing.awareness_budget",
            "product.taste_appeal",
        }
    )


def test_random_reproducible(nutrimix) -> None:
    a = generate_random_variants(nutrimix, n_variants=25, seed=7)
    b = generate_random_variants(nutrimix, n_variants=25, seed=7)
    assert [v.modifications for v in a] == [v.modifications for v in b]
    assert a[0].variant_id == "random_001"
    for v in a:
        _assert_channel_mix_unit_sum(v.scenario_config)


def test_smart_variants_from_rejection_distribution(nutrimix) -> None:
    result = StaticSimulationResult(
        scenario_id=nutrimix.id,
        population_size=500,
        adoption_count=50,
        adoption_rate=0.1,
        rejection_distribution={"awareness": 120, "purchase": 80},
        random_seed=1,
    )
    smart = generate_smart_variants(nutrimix, result, n_variants=50)
    assert any("Kitchen Sink" in v.variant_name for v in smart)
    assert any("Awareness" in v.variant_name for v in smart)
    for v in smart:
        _assert_channel_mix_unit_sum(v.scenario_config)


def test_smart_respects_n_variants_cap(nutrimix) -> None:
    result = StaticSimulationResult(
        scenario_id=nutrimix.id,
        population_size=100,
        adoption_count=1,
        adoption_rate=0.01,
        rejection_distribution={"awareness": 50, "consideration": 40, "purchase": 9},
        random_seed=1,
    )
    smart = generate_smart_variants(nutrimix, result, n_variants=5)
    assert len(smart) <= 5
