"""Tests for Sprint 8 display name additions."""

from src.utils.display import ATTRIBUTE_DISPLAY_NAMES, display_name


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
