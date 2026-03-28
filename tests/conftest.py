"""
Shared test fixtures for the LittleJoys Persona Engine.

Provides pre-built personas, scenarios, and mock objects for unit tests.
"""

from __future__ import annotations

import pytest

from src.decision.scenarios import MarketingConfig, ProductConfig, ScenarioConfig
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
        region="West",
        urban_vs_periurban="urban",
        household_income_lpa=15.0,
        parent_age=32,
        parent_gender="female",
        marital_status="married",
        birth_order="experienced_parent",
        num_children=1,
        child_ages=[4],
        child_genders=["female"],
        youngest_child_age=4,
        oldest_child_age=4,
        family_structure="nuclear",
        elder_influence=0.35,
        spouse_involvement_in_purchases=0.6,
        income_stability="salaried",
        socioeconomic_class="B1",
        dual_income_household=True,
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
        cultural=CulturalAttributes(dietary_culture="vegetarian"),
        relationships=RelationshipAttributes(),
        career=CareerAttributes(employment_status="full_time", work_hours_per_week=42),
        education_learning=EducationLearningAttributes(education_level="masters"),
        lifestyle=LifestyleAttributes(),
        daily_routine=DailyRoutineAttributes(),
        values=ValueAttributes(),
        emotional=EmotionalAttributes(),
        media=MediaAttributes(),
    )


@pytest.fixture
def high_price_sensitivity_persona(sample_demographics: DemographicAttributes) -> Persona:
    """Persona with strong budget discipline for value-sensitive tests."""
    return Persona(
        id="test-persona-price-sensitive",
        generation_seed=42,
        generation_timestamp="2026-03-28T00:00:00Z",
        tier="statistical",
        demographics=sample_demographics,
        health=HealthAttributes(),
        psychology=PsychologyAttributes(),
        cultural=CulturalAttributes(dietary_culture="vegetarian"),
        relationships=RelationshipAttributes(),
        career=CareerAttributes(employment_status="full_time", work_hours_per_week=42),
        education_learning=EducationLearningAttributes(education_level="masters"),
        lifestyle=LifestyleAttributes(),
        daily_routine=DailyRoutineAttributes(
            budget_consciousness=0.95,
            health_spend_priority=0.35,
            deal_seeking_intensity=0.9,
            cashback_coupon_sensitivity=0.85,
            impulse_purchase_tendency=0.1,
            price_reference_point=350.0,
        ),
        values=ValueAttributes(
            best_for_my_child_intensity=0.45,
            guilt_driven_spending=0.2,
            supplement_necessity_belief=0.3,
        ),
        emotional=EmotionalAttributes(),
        media=MediaAttributes(),
    )


@pytest.fixture
def sample_scenario() -> ScenarioConfig:
    """Scenario tuned so a typical sample persona can progress through the funnel."""

    product = ProductConfig(
        name="LittleJoys Growth Mix",
        category="child nutrition powder",
        price_inr=420.0,
        age_range=(3, 10),
        key_benefits=["growth support", "immunity", "balanced nutrition"],
        form_factor="powder",
        taste_appeal=0.72,
        effort_to_acquire=0.25,
    )
    marketing = MarketingConfig(
        awareness_budget=0.65,
        channel_mix={"instagram": 0.4, "youtube": 0.35, "whatsapp": 0.25},
        pediatrician_endorsement=True,
        school_partnership=False,
        influencer_campaign=True,
    )
    return ScenarioConfig(
        id="test-scenario-001",
        name="Test scenario",
        description="Unit test scenario for funnel and simulation.",
        product=product,
        marketing=marketing,
        target_age_range=(3, 10),
        lj_pass_available=False,
    )
