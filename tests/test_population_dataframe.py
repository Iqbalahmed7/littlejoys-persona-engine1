"""Tests verifying population dataframe has columns needed for Sprint 8 features."""

from pathlib import Path

import pytest

from src.generation.population import Population
from src.utils.dashboard_data import tier1_dataframe_with_results


@pytest.fixture
def population():
    pop_path = Path("data/population")
    if not pop_path.exists():
        pytest.skip("Population data not generated yet")
    return Population.load(pop_path)


class TestDataFrameColumns:
    """Verify all Sprint 8 required columns exist in the Tier 1 dataframe."""

    def test_city_columns_exist(self, population):
        df = tier1_dataframe_with_results(population, None)
        assert "city_name" in df.columns
        assert "city_tier" in df.columns

    def test_children_columns_exist(self, population):
        df = tier1_dataframe_with_results(population, None)
        assert "num_children" in df.columns
        assert "youngest_child_age" in df.columns

    def test_family_structure_exists(self, population):
        df = tier1_dataframe_with_results(population, None)
        assert "family_structure" in df.columns

    def test_filter_columns_exist(self, population):
        df = tier1_dataframe_with_results(population, None)
        required = ["city_tier", "socioeconomic_class", "region",
                     "income_bracket", "num_children", "youngest_child_age"]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_income_bracket_values(self, population):
        df = tier1_dataframe_with_results(population, None)
        valid_brackets = {"low_income", "middle_income", "high_income"}
        actual = set(df["income_bracket"].unique())
        assert actual <= valid_brackets

    def test_city_tier_values(self, population):
        df = tier1_dataframe_with_results(population, None)
        valid_tiers = {"Tier1", "Tier2", "Tier3"}
        actual = set(df["city_tier"].unique())
        assert actual <= valid_tiers
