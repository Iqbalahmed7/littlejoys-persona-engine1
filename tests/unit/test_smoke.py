"""
Smoke tests — verify all modules import correctly and basic schema works.

These tests should ALWAYS pass. If they don't, the project scaffold is broken.
"""

from __future__ import annotations


def test_config_imports() -> None:
    """Config module imports without error."""
    from src.config import Environment

    assert Environment.DEVELOPMENT.value == "development"


def test_constants_imports() -> None:
    """Constants module imports without error."""
    from src.constants import DEFAULT_POPULATION_SIZE, TOTAL_ATTRIBUTE_COUNT

    assert DEFAULT_POPULATION_SIZE == 300
    assert TOTAL_ATTRIBUTE_COUNT == 145


def test_schema_imports() -> None:
    """All schema models import without error."""


def test_persona_creation(sample_persona) -> None:  # type: ignore[no-untyped-def]
    """A persona can be created from the fixture."""
    assert sample_persona.id == "test-persona-001"
    assert sample_persona.tier == "statistical"
    assert sample_persona.demographics.city_tier == "Tier1"
    assert sample_persona.demographics.city_name == "Mumbai"


def test_persona_flat_dict(sample_persona) -> None:  # type: ignore[no-untyped-def]
    """Persona can be flattened to a dict."""
    flat = sample_persona.to_flat_dict()
    assert "city_tier" in flat
    assert "health_anxiety" in flat
    assert "budget_consciousness" in flat
    assert flat["city_tier"] == "Tier1"


def test_all_modules_import() -> None:
    """Every module in the project imports without error."""
