"""Unit tests for demographic distribution sampling."""

from __future__ import annotations

import pandas as pd

from src.taxonomy.distributions import DistributionTables


def test_sample_demographics_returns_correct_count() -> None:
    """Sampling returns the requested row count."""

    demographics = DistributionTables().sample_demographics(n=25, seed=42)
    assert len(demographics) == 25


def test_sample_demographics_deterministic_with_seed() -> None:
    """The same seed produces identical samples."""

    sampler = DistributionTables()
    first = sampler.sample_demographics(n=20, seed=7)
    second = sampler.sample_demographics(n=20, seed=7)
    pd.testing.assert_frame_equal(first, second)


def test_city_tier_distribution_approximately_correct() -> None:
    """Observed city-tier frequencies stay near the target mixture."""

    demographics = DistributionTables().sample_demographics(n=4000, seed=21)
    frequencies = demographics["city_tier"].value_counts(normalize=True)

    assert abs(frequencies["Tier1"] - 0.45) < 0.05
    assert abs(frequencies["Tier2"] - 0.35) < 0.05
    assert abs(frequencies["Tier3"] - 0.20) < 0.05


def test_income_conditional_on_tier() -> None:
    """Tier 1 households should have higher sampled income than Tier 3 households."""

    demographics = DistributionTables().sample_demographics(n=4000, seed=84)
    tier_means = demographics.groupby("city_tier")["household_income_lpa"].mean()

    assert tier_means["Tier1"] > tier_means["Tier2"] > tier_means["Tier3"]


def test_child_age_within_valid_range() -> None:
    """Sampled child ages stay within the supported age band."""

    demographics = DistributionTables().sample_demographics(n=200, seed=5)
    for child_ages in demographics["child_ages"]:
        assert all(2 <= age <= 14 for age in child_ages)


def test_parent_age_within_valid_range() -> None:
    """Parent ages stay within the configured range and respect the age gap."""

    demographics = DistributionTables().sample_demographics(n=200, seed=9)

    assert demographics["parent_age"].between(22, 45).all()
    assert ((demographics["parent_age"] - demographics["oldest_child_age"]) >= 18).all()
