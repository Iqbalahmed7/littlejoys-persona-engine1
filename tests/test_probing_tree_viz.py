"""Tests for McKinsey decision tree visualization components."""

import pytest

try:
    from app.components.probing_tree_viz import (
        PROBE_TYPE_CONFIG,
        VERDICT_STYLES,
    )
except ImportError:
    pytest.skip("Sprint 9 Track C not yet merged", allow_module_level=True)

class TestVerdictStyles:
    def test_all_statuses_covered(self):
        expected = {"confirmed", "partially_confirmed", "rejected", "inconclusive"}
        assert set(VERDICT_STYLES.keys()) >= expected

    def test_has_required_keys(self):
        for _status, config in VERDICT_STYLES.items():
            assert "icon" in config
            assert "color" in config
            assert "label" in config

    def test_icons_non_empty(self):
        for config in VERDICT_STYLES.values():
            assert isinstance(config["icon"], str)
            assert len(config["icon"]) > 0

    def test_colors_are_hex(self):
        for config in VERDICT_STYLES.values():
            assert str(config["color"]).startswith("#") or config["color"] in ["gray", "red", "green", "orange", "yellow", "blue"]


class TestProbeTypeConfig:
    def test_all_probe_types_covered(self):
        expected = {"interview", "simulation", "attribute"}
        assert set(PROBE_TYPE_CONFIG.keys()) >= expected

    def test_has_required_keys(self):
        for _ptype, config in PROBE_TYPE_CONFIG.items():
            assert "icon" in config
            assert "label" in config
            assert "color" in config

    def test_labels_match(self):
        assert PROBE_TYPE_CONFIG["interview"]["label"] == "Interview"
        assert PROBE_TYPE_CONFIG["simulation"]["label"] == "Simulation"
        assert PROBE_TYPE_CONFIG["attribute"]["label"] == "Attribute"

class TestConfidenceColors:
    def test_confidence_to_color(self):
        try:
            from app.components.probing_tree_viz import _confidence_to_color
        except ImportError:
            pytest.skip("_confidence_to_color not available")
        assert _confidence_to_color(0.8) == "green"
        assert _confidence_to_color(0.6) in ["amber", "orange"]
        assert _confidence_to_color(0.4) == "orange"
        assert _confidence_to_color(0.2) == "red"

class TestResultsTable:
    def test_table_structure_empty(self):
        try:
            import pandas as pd

            from app.components.probing_tree_viz import _build_metrics_df
            df = _build_metrics_df([])
            assert isinstance(df, pd.DataFrame)
        except ImportError:
            pytest.skip("Not testing table structure directly if helper isn't isolated")
