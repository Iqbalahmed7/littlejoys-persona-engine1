"""Tests for child age group labeling utility."""

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
