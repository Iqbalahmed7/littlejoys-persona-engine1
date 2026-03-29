"""Tests for demographic filter helpers (Sprint 8 Track A)."""

from __future__ import annotations

import pandas as pd

from app.components.demographic_filters import child_age_group_mask
from src.utils.display import (
    income_bracket_ui_label,
    scatter_attribute_pair_interpretation,
    scenario_product_display_name,
)


def test_child_age_group_mask_toddler() -> None:
    s = pd.Series([3, 7, 12])
    m = child_age_group_mask(s, ["Toddler (2-5)"])
    assert m.tolist() == [True, False, False]


def test_child_age_group_mask_multiple_bands() -> None:
    s = pd.Series([4, 8, 12])
    m = child_age_group_mask(s, ["Toddler (2-5)", "Pre-teen (11-14)"])
    assert m.tolist() == [True, False, True]


def test_child_age_group_mask_empty_means_all() -> None:
    s = pd.Series([1, 14])
    m = child_age_group_mask(s, [])
    assert m.all()


def test_income_bracket_ui_labels() -> None:
    assert "8L" in income_bracket_ui_label("middle_income")


def test_scenario_product_display_name_known() -> None:
    assert "NutriMix" in scenario_product_display_name("nutrimix_2_6")


def test_scatter_attribute_pair_interpretation_fallback() -> None:
    t = scatter_attribute_pair_interpretation("unknown_a", "unknown_b")
    assert len(t) > 20


def test_scatter_attribute_pair_interpretation_known_pair() -> None:
    t = scatter_attribute_pair_interpretation("deal_seeking_intensity", "diet_consciousness")
    assert "health" in t.lower() or "convenience" in t.lower()
