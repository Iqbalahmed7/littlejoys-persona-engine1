"""Unit tests for the persona schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.constants import TOTAL_ATTRIBUTE_COUNT
from src.taxonomy.schema import DemographicAttributes, HealthAttributes, Persona


def test_persona_creation_with_all_fields(sample_persona) -> None:  # type: ignore[no-untyped-def]
    """A sample persona exposes the complete flattened identity surface."""

    flat = sample_persona.to_flat_dict()
    assert len(flat) == TOTAL_ATTRIBUTE_COUNT
    assert flat["city_name"] == "Mumbai"
    assert flat["employment_status"] == "full_time"


def test_persona_from_flat_dict_roundtrip(sample_persona) -> None:  # type: ignore[no-untyped-def]
    """Flat serialization and reconstruction are inverse operations."""

    flat = sample_persona.to_flat_dict()
    reconstructed = Persona.from_flat_dict(
        flat=flat,
        persona_id=sample_persona.id,
        seed=sample_persona.generation_seed,
        timestamp=sample_persona.generation_timestamp,
        tier=sample_persona.tier,
    )

    assert reconstructed.to_flat_dict() == flat


def test_demographics_frozen_after_creation(sample_persona) -> None:  # type: ignore[no-untyped-def]
    """Identity-layer models are immutable after creation."""

    with pytest.raises((ValidationError, TypeError, AttributeError)):
        sample_persona.demographics.city_name = "Delhi"


def test_cross_field_validator_child_age() -> None:
    """Invalid parent-child age gaps are rejected."""

    with pytest.raises(ValidationError):
        DemographicAttributes(
            city_tier="Tier1",
            city_name="Mumbai",
            region="West",
            urban_vs_periurban="urban",
            household_income_lpa=12.0,
            parent_age=22,
            parent_gender="female",
            marital_status="married",
            birth_order="experienced_parent",
            num_children=1,
            child_ages=[5],
            child_genders=["female"],
            youngest_child_age=5,
            oldest_child_age=5,
            family_structure="nuclear",
            elder_influence=0.4,
            spouse_involvement_in_purchases=0.6,
            income_stability="salaried",
            socioeconomic_class="B1",
            dual_income_household=True,
        )


def test_continuous_attributes_bounded_0_1() -> None:
    """Continuous attributes are bounded by validation rules."""

    with pytest.raises(ValidationError):
        HealthAttributes(fitness_engagement=1.1)


def test_categorical_attributes_valid_enum() -> None:
    """Invalid categorical values raise validation errors."""

    with pytest.raises(ValidationError):
        DemographicAttributes(
            city_tier="Tier1",
            city_name="Mumbai",
            region="West",
            urban_vs_periurban="urban",
            household_income_lpa=12.0,
            parent_age=32,
            parent_gender="female",
            marital_status="married",
            birth_order="experienced_parent",
            num_children=1,
            child_ages=[5],
            child_genders=["female"],
            youngest_child_age=5,
            oldest_child_age=5,
            family_structure="unknown",  # type: ignore[arg-type]
            elder_influence=0.4,
            spouse_involvement_in_purchases=0.6,
            income_stability="salaried",
            socioeconomic_class="B1",
            dual_income_household=True,
        )
