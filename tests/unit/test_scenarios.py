"""Unit tests for Sprint 2 scenario configuration."""

from __future__ import annotations

from src.constants import SCENARIO_MODE_TEMPORAL
from src.decision.scenarios import get_all_scenarios, get_scenario


def test_get_scenario_returns_correct_config() -> None:
    """Baseline scenario should match the PRD shape and LJ Pass defaults."""

    scenario = get_scenario("nutrimix_2_6")

    assert scenario.id == "nutrimix_2_6"
    assert scenario.product.name == "Nutrimix"
    assert scenario.product.price_inr == 599.0
    assert scenario.marketing.pediatrician_endorsement is True
    assert scenario.lj_pass_available is True
    assert scenario.lj_pass is not None
    assert scenario.lj_pass.monthly_price_inr == 299.0


def test_get_all_scenarios_returns_four() -> None:
    """The scenario catalog should expose the four Sprint 2 business cases in order."""

    scenarios = get_all_scenarios()

    assert len(scenarios) == 4
    assert [scenario.id for scenario in scenarios] == [
        "nutrimix_2_6",
        "nutrimix_7_14",
        "magnesium_gummies",
        "protein_mix",
    ]


def test_scenario_age_ranges_are_valid() -> None:
    """Scenario target ages should sit within the concrete shipped product ranges."""

    for scenario in get_all_scenarios():
        product_low, product_high = scenario.product.age_range
        target_low, target_high = scenario.target_age_range

        assert product_low <= target_low <= target_high <= product_high


def test_scenario_prices_are_positive() -> None:
    """Each scenario should have a positive retail price."""

    for scenario in get_all_scenarios():
        assert scenario.product.price_inr > 0.0


def test_nutrimix_7_14_temporal_event_ready() -> None:
    """Sprint 18: 7-14 scenario runs monthly/event engine with PRD parameters."""
    scenario = get_scenario("nutrimix_7_14")
    assert scenario.mode == SCENARIO_MODE_TEMPORAL
    assert scenario.months == 12
    assert scenario.marketing.awareness_level == 0.35
    assert scenario.lj_pass_available is True
    assert scenario.product.age_range == (7, 14)
    assert scenario.product.price_inr == 649.0


def test_channel_mix_sums_to_approximately_one() -> None:
    """Marketing channel allocations should remain normalized."""

    for scenario in get_all_scenarios():
        assert abs(sum(scenario.marketing.channel_mix.values()) - 1.0) <= 0.01
