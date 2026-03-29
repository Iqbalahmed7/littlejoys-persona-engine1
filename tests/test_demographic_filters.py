"""Tests for the shared demographic filter component."""

import pandas as pd

# The component will be created by Track A
# These tests validate the filtering logic


def _sample_population_df() -> pd.DataFrame:
    """Minimal population dataframe for filter testing."""
    return pd.DataFrame({
        "id": [f"persona_{i}" for i in range(20)],
        "city_tier": ["Tier1"] * 8 + ["Tier2"] * 7 + ["Tier3"] * 5,
        "city_name": (["Mumbai", "Delhi", "Bangalore", "Chennai"] * 2
                      + ["Jaipur", "Lucknow", "Kochi"] * 2 + ["Jaipur"]
                      + ["Mangalore", "Mysore", "Dehradun", "Udaipur", "Raipur"]),
        "region": (["West", "North", "South", "South"] * 2
                   + ["North", "North", "South"] * 2 + ["North"]
                   + ["South", "South", "North", "West", "East"]),
        "socioeconomic_class": (["A1", "A2", "B1", "B2"] * 3
                                 + ["C1", "C2", "A1", "A2"]
                                 + ["B1", "B2", "C1", "C2"]),
        "household_income_lpa": ([25, 18, 10, 6] * 3 + [4, 3, 30, 20] + [8, 5, 3, 2]),
        "income_bracket": (["high_income", "high_income", "middle_income", "low_income"] * 3
                           + ["low_income", "low_income", "high_income", "high_income"]
                           + ["middle_income", "low_income", "low_income", "low_income"]),
        "num_children": [1, 2, 3, 1, 2, 3, 1, 2, 1, 2, 3, 1, 2, 3, 1, 2, 1, 2, 3, 1],
        "youngest_child_age": [3, 5, 7, 10, 2, 4, 8, 12, 3, 6, 9, 11, 2, 5, 7, 13, 4, 8, 3, 14],
        "outcome": (["adopt"] * 10 + ["reject"] * 10),
    })


class TestFilterLogic:
    """Test the filtering logic that will be used by render_demographic_filters."""

    def test_filter_by_city_tier(self):
        df = _sample_population_df()
        filtered = df[df["city_tier"].isin(["Tier1"])]
        assert len(filtered) == 8
        assert all(filtered["city_tier"] == "Tier1")

    def test_filter_by_sec_class(self):
        df = _sample_population_df()
        filtered = df[df["socioeconomic_class"].isin(["A1", "A2"])]
        assert len(filtered) > 0
        assert set(filtered["socioeconomic_class"].unique()) <= {"A1", "A2"}

    def test_filter_by_region(self):
        df = _sample_population_df()
        filtered = df[df["region"] == "South"]
        assert len(filtered) > 0
        assert all(filtered["region"] == "South")

    def test_filter_by_income_bracket(self):
        df = _sample_population_df()
        filtered = df[df["income_bracket"] == "high_income"]
        assert len(filtered) > 0
        assert all(filtered["household_income_lpa"] > 15)

    def test_filter_by_num_children(self):
        df = _sample_population_df()
        filtered = df[df["num_children"].isin([1, 2])]
        assert len(filtered) > 0
        assert all(filtered["num_children"].isin([1, 2]))

    def test_child_age_group_filter_toddler(self):
        df = _sample_population_df()
        filtered = df[df["youngest_child_age"].between(2, 5)]
        assert len(filtered) > 0
        assert all(filtered["youngest_child_age"] <= 5)

    def test_child_age_group_filter_school_age(self):
        df = _sample_population_df()
        filtered = df[df["youngest_child_age"].between(6, 10)]
        assert len(filtered) > 0

    def test_child_age_group_filter_preteen(self):
        df = _sample_population_df()
        filtered = df[df["youngest_child_age"].between(11, 14)]
        assert len(filtered) > 0

    def test_combined_filters(self):
        df = _sample_population_df()
        filtered = df[
            df["city_tier"].isin(["Tier1"])
            & df["socioeconomic_class"].isin(["A1", "A2"])
        ]
        assert len(filtered) > 0
        assert all(filtered["city_tier"] == "Tier1")
        assert all(filtered["socioeconomic_class"].isin(["A1", "A2"]))

    def test_no_filters_returns_all(self):
        df = _sample_population_df()
        all_tiers = sorted(df["city_tier"].unique())
        all_sec = sorted(df["socioeconomic_class"].unique())
        filtered = df[
            df["city_tier"].isin(all_tiers)
            & df["socioeconomic_class"].isin(all_sec)
        ]
        assert len(filtered) == len(df)

    def test_empty_filter_returns_empty(self):
        df = _sample_population_df()
        filtered = df[df["city_tier"].isin([])]
        assert len(filtered) == 0
