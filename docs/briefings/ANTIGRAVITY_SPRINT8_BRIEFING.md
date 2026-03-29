# Antigravity — Sprint 8 Track D: Tests for Population Explorer Upgrades

**Branch:** `sprint-8-track-d-tests`
**Base:** `main`

## Context

Sprint 8 adds several new features to the Population Explorer page. This track writes comprehensive tests for all new components and utilities introduced by the other three tracks. Since the implementation code may not be merged yet, write tests that import the expected modules and validate the expected behavior — the tests will pass once all tracks merge.

## Deliverables

### 1. Demographic Filter Component Tests

**File:** `tests/test_demographic_filters.py` (NEW)

Test the shared filter component at `app/components/demographic_filters.py`.

```python
"""Tests for the shared demographic filter component."""

import pandas as pd
import pytest

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
```

### 2. Child Age Group Label Tests

**File:** `tests/test_child_age_group.py` (NEW)

Test the `child_age_group_label()` function being added to `src/utils/dashboard_data.py` by Track B.

```python
"""Tests for child age group labeling utility."""

import pytest
from src.utils.dashboard_data import child_age_group_label


class TestChildAgeGroupLabel:
    def test_toddler_age_2(self):
        assert child_age_group_label(2) == "Toddler (2-5)"

    def test_toddler_age_5(self):
        assert child_age_group_label(5) == "Toddler (2-5)"

    def test_school_age_6(self):
        assert child_age_group_label(6) == "School-age (6-10)"

    def test_school_age_10(self):
        assert child_age_group_label(10) == "School-age (6-10)"

    def test_preteen_11(self):
        assert child_age_group_label(11) == "Pre-teen (11-14)"

    def test_preteen_14(self):
        assert child_age_group_label(14) == "Pre-teen (11-14)"

    def test_none_returns_unknown(self):
        assert child_age_group_label(None) == "Unknown"
```

### 3. Scatter Insight Tests

**File:** `tests/test_scatter_insights.py` (NEW)

Test the product-aware scatter insight logic.

```python
"""Tests for product-contextual scatter insights."""

import pytest
from src.utils.display import SCENARIO_PRODUCT_NAMES


class TestScenarioProductNames:
    """Verify product name mapping exists for all scenarios."""

    def test_nutrimix_2_6_has_product_name(self):
        assert "nutrimix_2_6" in SCENARIO_PRODUCT_NAMES
        assert "NutriMix" in SCENARIO_PRODUCT_NAMES["nutrimix_2_6"]

    def test_nutrimix_7_14_has_product_name(self):
        assert "nutrimix_7_14" in SCENARIO_PRODUCT_NAMES

    def test_magnesium_gummies_has_product_name(self):
        assert "magnesium_gummies" in SCENARIO_PRODUCT_NAMES

    def test_protein_mix_has_product_name(self):
        assert "protein_mix" in SCENARIO_PRODUCT_NAMES

    def test_all_scenarios_covered(self):
        from src.constants import SCENARIO_IDS
        for sid in SCENARIO_IDS:
            assert sid in SCENARIO_PRODUCT_NAMES, f"Missing product name for scenario {sid}"


class TestQuadrantInsights:
    """Test quadrant rate computation logic."""

    def test_quadrant_lift_positive(self):
        """Best quadrant should have positive lift over baseline."""
        import pandas as pd
        df = pd.DataFrame({
            "x": [0.8, 0.9, 0.1, 0.2, 0.7, 0.3],
            "y": [0.7, 0.8, 0.2, 0.3, 0.6, 0.1],
            "outcome": ["adopt", "adopt", "reject", "reject", "adopt", "reject"],
        })
        median_x = df["x"].median()
        median_y = df["y"].median()
        hh = df[(df["x"] >= median_x) & (df["y"] >= median_y)]
        overall_rate = (df["outcome"] == "adopt").mean()
        hh_rate = (hh["outcome"] == "adopt").mean()
        # High-high quadrant should have higher rate than overall
        assert hh_rate >= overall_rate

    def test_quadrant_sizes_sum_to_total(self):
        import pandas as pd
        df = pd.DataFrame({
            "x": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
            "y": [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1],
        })
        median_x = df["x"].median()
        median_y = df["y"].median()
        hh = df[(df["x"] >= median_x) & (df["y"] >= median_y)]
        hl = df[(df["x"] >= median_x) & (df["y"] < median_y)]
        lh = df[(df["x"] < median_x) & (df["y"] >= median_y)]
        ll = df[(df["x"] < median_x) & (df["y"] < median_y)]
        assert len(hh) + len(hl) + len(lh) + len(ll) == len(df)
```

### 4. Display Name Coverage Tests

**File:** `tests/test_display_names_sprint8.py` (NEW)

Verify that all new display names added in Sprint 8 are properly mapped.

```python
"""Tests for Sprint 8 display name additions."""

import pytest
from src.utils.display import display_name, ATTRIBUTE_DISPLAY_NAMES


class TestFamilyDisplayNames:
    """Family structure values should have human-readable display names."""

    def test_nuclear_display_name(self):
        assert "nuclear" in ATTRIBUTE_DISPLAY_NAMES
        assert "Nuclear" in ATTRIBUTE_DISPLAY_NAMES["nuclear"]

    def test_joint_display_name(self):
        assert "joint" in ATTRIBUTE_DISPLAY_NAMES
        assert "Joint" in ATTRIBUTE_DISPLAY_NAMES["joint"]

    def test_single_parent_display_name(self):
        assert "single_parent" in ATTRIBUTE_DISPLAY_NAMES
        assert "Single" in ATTRIBUTE_DISPLAY_NAMES["single_parent"]


class TestChildDemographicDisplayNames:
    def test_num_children(self):
        assert display_name("num_children") != "num_children"

    def test_youngest_child_age(self):
        # Should have a human-readable name, not raw field
        name = display_name("youngest_child_age")
        assert "_" not in name or name != "youngest_child_age"

    def test_family_structure(self):
        name = display_name("family_structure")
        assert name != "family_structure"


class TestCityDisplayNames:
    def test_city_name(self):
        assert display_name("city_name") == "City"

    def test_city_tier(self):
        assert display_name("city_tier") == "City Classification"
```

### 5. Income Bracket Filter Tests

**File:** `tests/test_income_filters.py` (NEW)

```python
"""Tests for income-related filtering and bracketing."""

import pytest
from src.utils.dashboard_data import income_bracket_label


class TestIncomeBracketLabel:
    def test_low_income(self):
        assert income_bracket_label(5.0) == "low_income"

    def test_low_income_boundary(self):
        assert income_bracket_label(8.0) == "low_income"

    def test_middle_income(self):
        assert income_bracket_label(12.0) == "middle_income"

    def test_middle_income_boundary(self):
        assert income_bracket_label(15.0) == "middle_income"

    def test_high_income(self):
        assert income_bracket_label(25.0) == "high_income"

    def test_very_high_income(self):
        assert income_bracket_label(100.0) == "high_income"
```

### 6. Integration Test: Population DataFrame Columns

**File:** `tests/test_population_dataframe.py` (NEW)

Verify the dataframe produced by `tier1_dataframe_with_results()` contains all columns needed by Sprint 8 features.

```python
"""Tests verifying population dataframe has columns needed for Sprint 8 features."""

import pytest
from src.generation.population import Population
from src.utils.dashboard_data import tier1_dataframe_with_results
from pathlib import Path


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
```

## Files to Read Before Starting

1. `app/pages/1_population.py` — current implementation being modified by other tracks
2. `src/utils/display.py` — display helpers being extended
3. `src/utils/dashboard_data.py` — data helpers being extended
4. `src/constants.py` — scenario IDs and thresholds
5. `app/components/persona_card.py` — persona card used in browser
6. `tests/test_ux_tooltips.py` — existing test patterns for reference

## Constraints

- Python 3.11+, pytest
- Tests should work with the generated population data in `data/population/` (use `pytest.skip` if not available)
- Filter logic tests should use synthetic DataFrames (no dependency on generated data)
- Do NOT mock Streamlit — test the data logic, not the UI rendering
- Each test file should be independently runnable
- Total: aim for ~50 tests across all files

## Acceptance Criteria

- [ ] 6 test files created in `tests/`
- [ ] ~50 tests total
- [ ] All tests that don't depend on Sprint 8 code pass immediately (filter logic, income brackets, dataframe columns)
- [ ] Tests that depend on new Sprint 8 code (SCENARIO_PRODUCT_NAMES, child_age_group_label, family display names) are clearly structured so they'll pass once the code merges
- [ ] No Streamlit rendering in tests — pure data logic
- [ ] Synthetic test DataFrames used where possible
