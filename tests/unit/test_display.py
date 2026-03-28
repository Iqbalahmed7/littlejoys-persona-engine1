"""Unit tests for ``src.utils.display`` (PRD-013 Sprint 6)."""

from __future__ import annotations

from src.utils.display import (
    ATTRIBUTE_CATEGORIES,
    ATTRIBUTE_DISPLAY_NAMES,
    SEC_DESCRIPTIONS,
    describe_attribute_value,
    display_name,
    outcome_label,
    persona_display_name,
)


def test_display_name_known_field() -> None:
    assert display_name("budget_consciousness") == "Price Sensitivity"


def test_display_name_unknown_field() -> None:
    assert display_name("some_random_field") == "Some Random Field"


def test_describe_attribute_value_high() -> None:
    result = describe_attribute_value("health_anxiety", 0.85)
    assert "very high" in result


def test_describe_attribute_value_boundary_moderate() -> None:
    assert "moderate" in describe_attribute_value("risk_tolerance", 0.5)


def test_sec_descriptions_complete() -> None:
    assert len(SEC_DESCRIPTIONS) == 6


def test_attribute_categories_reference_valid_attrs() -> None:
    for cat, attrs in ATTRIBUTE_CATEGORIES.items():
        for attr in attrs:
            assert attr in ATTRIBUTE_DISPLAY_NAMES, f"{attr} in {cat} missing display name"


def test_outcome_label_maps_known_codes() -> None:
    assert outcome_label("adopt") == "Adopted"
    assert outcome_label("reject") == "Did not adopt"


def test_persona_display_name_contains_city_and_age(sample_persona) -> None:
    label = persona_display_name(sample_persona)
    assert "Mumbai" in label
    assert "32" in label
