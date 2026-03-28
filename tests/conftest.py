"""
Shared test fixtures for the LittleJoys Persona Engine.

Provides pre-built personas, scenarios, and mock objects for unit tests.
"""

from __future__ import annotations

import pytest

from src.taxonomy.schema import (
    CareerAttributes,
    CulturalAttributes,
    DailyRoutineAttributes,
    DemographicAttributes,
    EducationLearningAttributes,
    EmotionalAttributes,
    HealthAttributes,
    LifestyleAttributes,
    MediaAttributes,
    Persona,
    PsychologyAttributes,
    RelationshipAttributes,
    ValueAttributes,
)


@pytest.fixture
def sample_demographics() -> DemographicAttributes:
    """A typical Tier 1 working mother persona demographics."""
    return DemographicAttributes(
        city_tier="Tier1",
        city_name="Mumbai",
        household_income_lpa=15.0,
        parent_age=32,
        parent_gender="female",
        num_children=1,
        youngest_child_age=4,
        oldest_child_age=4,
        education_level="masters",
        employment_status="full_time",
        family_structure="nuclear",
        dietary_culture="vegetarian",
    )


@pytest.fixture
def sample_persona(sample_demographics: DemographicAttributes) -> Persona:
    """A complete sample persona for testing."""
    return Persona(
        id="test-persona-001",
        generation_seed=42,
        generation_timestamp="2026-03-28T00:00:00Z",
        tier="statistical",
        demographics=sample_demographics,
        health=HealthAttributes(),
        psychology=PsychologyAttributes(),
        cultural=CulturalAttributes(),
        relationships=RelationshipAttributes(),
        career=CareerAttributes(),
        education_learning=EducationLearningAttributes(),
        lifestyle=LifestyleAttributes(),
        daily_routine=DailyRoutineAttributes(),
        values=ValueAttributes(),
        emotional=EmotionalAttributes(),
        media=MediaAttributes(),
    )


@pytest.fixture
def high_price_sensitivity_persona(sample_demographics: DemographicAttributes) -> Persona:
    """Persona with high price sensitivity — should reject expensive products."""
    return Persona(
        id="test-persona-price-sensitive",
        generation_seed=42,
        generation_timestamp="2026-03-28T00:00:00Z",
        tier="statistical",
        demographics=sample_demographics,
        health=HealthAttributes(),
        psychology=PsychologyAttributes(),
        cultural=CulturalAttributes(),
        relationships=RelationshipAttributes(),
        career=CareerAttributes(),
        education_learning=EducationLearningAttributes(),
        lifestyle=LifestyleAttributes(),
        daily_routine=DailyRoutineAttributes(),
        values=ValueAttributes(
            budget_consciousness=0.95,
            price_sensitivity=0.9,
            value_for_money_orientation=0.85,
            brand_premium_willingness=0.1,
            child_investment_priority=0.4,
            guilt_spending_on_self=0.3,
        ),
        emotional=EmotionalAttributes(),
        media=MediaAttributes(),
    )
