"""Tests for income-related filtering and bracketing."""

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
