"""Unit tests for dashboard data helpers."""

from __future__ import annotations

from src.utils.dashboard_data import child_age_group_label


def test_child_age_group_label_boundaries() -> None:
    assert child_age_group_label(2) == "Toddler (2-5)"
    assert child_age_group_label(5) == "Toddler (2-5)"
    assert child_age_group_label(6) == "School-age (6-10)"
    assert child_age_group_label(10) == "School-age (6-10)"
    assert child_age_group_label(11) == "Pre-teen (11-14)"


def test_child_age_group_label_unknown_for_missing() -> None:
    assert child_age_group_label(None) == "Unknown"
