"""Tests for product-contextual scatter insights."""

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
