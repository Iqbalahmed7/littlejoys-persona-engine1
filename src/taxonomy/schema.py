"""
Persona data model — Pydantic v2 schema for all 145 attributes.

Implements the three-layer persona architecture from ARCHITECTURE.md §4-5:
- Identity Layer (immutable): demographics, psychographics, values
- Memory Layer (mutable): episodic, semantic, brand memories
- State Layer (volatile): awareness, consideration, purchase history

Full implementation in PRD-001 (Codex).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, confloat

# === IDENTITY LAYER (Immutable) ===


class DemographicAttributes(BaseModel):
    """Section 1: Demographic Information. See ARCHITECTURE.md §4.3."""

    model_config = ConfigDict(frozen=True)

    city_tier: Literal["Tier1", "Tier2", "Tier3"]
    city_name: str
    household_income_lpa: float = Field(ge=1.0, le=100.0)
    parent_age: int = Field(ge=22, le=45)
    parent_gender: Literal["female", "male"]
    num_children: int = Field(ge=1, le=5)
    youngest_child_age: int = Field(ge=2, le=14)
    oldest_child_age: int = Field(ge=2, le=14)
    education_level: Literal["high_school", "bachelors", "masters", "doctorate", "professional"]
    employment_status: Literal["homemaker", "part_time", "full_time", "self_employed", "freelance"]
    family_structure: Literal["nuclear", "joint", "single_parent"]
    dietary_culture: Literal["vegetarian", "eggetarian", "non_vegetarian", "vegan"]


class HealthAttributes(BaseModel):
    """Section 2: Physical and Health attributes."""

    model_config = ConfigDict(frozen=True)

    health_anxiety: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    supplement_belief: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    natural_preference: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    child_health_proactivity: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    immunity_concern: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    growth_concern: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    nutrition_gap_awareness: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]


class PsychologyAttributes(BaseModel):
    """Section 3: Psychological and Cognitive attributes."""

    model_config = ConfigDict(frozen=True)

    risk_aversion: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    novelty_seeking: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    information_seeking: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    decision_speed: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    analytical_thinking: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    authority_bias: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    social_proof_sensitivity: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    brand_loyalty: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    status_consciousness: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]


class CulturalAttributes(BaseModel):
    """Section 4: Cultural and Social Context."""

    model_config = ConfigDict(frozen=True)

    tradition_modernity_spectrum: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    joint_family_influence: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    peer_conformity: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    religious_dietary_strictness: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    generational_health_beliefs: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]


class RelationshipAttributes(BaseModel):
    """Section 5: Relationships and Social Networks."""

    model_config = ConfigDict(frozen=True)

    partner_involvement: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    extended_family_influence: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    mom_group_participation: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    pediatrician_trust: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    school_community_engagement: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    wom_transmitter_score: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]


class CareerAttributes(BaseModel):
    """Section 6: Career and Work Identity."""

    model_config = ConfigDict(frozen=True)

    time_scarcity: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    work_guilt: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    income_stability: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    career_ambition: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]


class EducationLearningAttributes(BaseModel):
    """Section 7: Education and Learning Style."""

    model_config = ConfigDict(frozen=True)

    research_before_purchase: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    label_reading_habit: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    scientific_literacy: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    ingredient_awareness: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]


class LifestyleAttributes(BaseModel):
    """Section 8: Hobbies, Interests, Lifestyle."""

    model_config = ConfigDict(frozen=True)

    online_shopping_comfort: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    subscription_openness: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    organic_premium_willingness: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    convenience_priority: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    digital_comfort: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]


class DailyRoutineAttributes(BaseModel):
    """Section 9: Daily Routine and Habits."""

    model_config = ConfigDict(frozen=True)

    morning_routine_strictness: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    meal_planning_discipline: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    snack_control: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    supplement_routine_existing: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    screen_time_guilt: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]


class ValueAttributes(BaseModel):
    """Section 10: Core Values, Beliefs, Philosophy."""

    model_config = ConfigDict(frozen=True)

    budget_consciousness: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    price_sensitivity: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    value_for_money_orientation: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    brand_premium_willingness: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    child_investment_priority: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    guilt_spending_on_self: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]


class EmotionalAttributes(BaseModel):
    """Section 11: Emotional and Relational Skills."""

    model_config = ConfigDict(frozen=True)

    parenting_confidence: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    first_child_anxiety: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    comparison_with_other_parents: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    mom_guilt: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    emotional_purchase_tendency: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]


class MediaAttributes(BaseModel):
    """Section 12: Media Consumption and Engagement."""

    model_config = ConfigDict(frozen=True)

    instagram_engagement: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    youtube_parenting_content: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    whatsapp_group_activity: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    influencer_trust: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    ad_receptivity: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    primary_shopping_platform: Literal[
        "amazon", "flipkart", "bigbasket", "local_store", "brand_website", "quick_commerce"
    ] = "amazon"


# === MEMORY LAYER (Mutable) ===


class MemoryEntry(BaseModel):
    """A single episodic or semantic memory."""

    timestamp: str
    event_type: str
    content: str
    emotional_valence: confloat(ge=-1, le=1) = 0.0  # type: ignore[valid-type]
    source: str = ""


class BrandMemory(BaseModel):
    """Accumulated impressions of a specific brand."""

    brand_name: str
    familiarity: confloat(ge=0, le=1) = 0.0  # type: ignore[valid-type]
    trust: confloat(ge=0, le=1) = 0.0  # type: ignore[valid-type]
    sentiment: confloat(ge=-1, le=1) = 0.0  # type: ignore[valid-type]
    touchpoints: list[str] = Field(default_factory=list)
    last_interaction: str = ""


class PurchaseEvent(BaseModel):
    """Record of a purchase decision."""

    month: int
    product_name: str
    outcome: Literal["purchased", "repurchased", "churned"]
    satisfaction: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    price_paid: float = 0.0


# === STATE LAYER (Volatile — changes each simulation step) ===


class TemporalState(BaseModel):
    """Current simulation state for a persona. Updated each month in temporal mode."""

    current_month: int = 0
    awareness_level: confloat(ge=0, le=1) = 0.0  # type: ignore[valid-type]
    consideration_level: confloat(ge=0, le=1) = 0.0  # type: ignore[valid-type]
    has_purchased: bool = False
    consecutive_purchase_months: int = 0
    has_lj_pass: bool = False
    satisfaction_trajectory: list[float] = Field(default_factory=list)
    wom_received_from: list[str] = Field(default_factory=list)


# === TOP-LEVEL PERSONA ===


class Persona(BaseModel):
    """
    Complete synthetic persona with three-layer architecture.

    - Identity: immutable attributes set at generation time
    - Memory: mutable records accumulated during simulation
    - State: volatile per-timestep simulation state

    See ARCHITECTURE.md §4-5 for full specification.
    """

    # Metadata
    id: str
    generation_seed: int
    generation_timestamp: str
    tier: Literal["statistical", "deep"]

    # Identity Layer (12 attribute categories)
    demographics: DemographicAttributes
    health: HealthAttributes
    psychology: PsychologyAttributes
    cultural: CulturalAttributes
    relationships: RelationshipAttributes
    career: CareerAttributes
    education_learning: EducationLearningAttributes
    lifestyle: LifestyleAttributes
    daily_routine: DailyRoutineAttributes
    values: ValueAttributes
    emotional: EmotionalAttributes
    media: MediaAttributes

    # Tier 2 only — deep narrative
    narrative: str | None = None

    # Memory Layer
    episodic_memory: list[MemoryEntry] = Field(default_factory=list)
    semantic_memory: dict[str, Any] = Field(default_factory=dict)
    brand_memories: dict[str, BrandMemory] = Field(default_factory=dict)
    purchase_history: list[PurchaseEvent] = Field(default_factory=list)

    # State Layer
    state: TemporalState = Field(default_factory=TemporalState)

    def to_flat_dict(self) -> dict[str, Any]:
        """Flatten all nested identity attributes into a single-level dict."""
        flat: dict[str, Any] = {}
        for category_name in [
            "demographics",
            "health",
            "psychology",
            "cultural",
            "relationships",
            "career",
            "education_learning",
            "lifestyle",
            "daily_routine",
            "values",
            "emotional",
            "media",
        ]:
            category = getattr(self, category_name)
            for field_name, value in category.model_dump().items():
                flat[field_name] = value
        return flat

    @classmethod
    def from_flat_dict(
        cls,
        flat: dict[str, Any],
        persona_id: str,
        seed: int,
        timestamp: str,
        tier: Literal["statistical", "deep"] = "statistical",
    ) -> Persona:
        """Reconstruct a Persona from a flat attribute dictionary."""
        raise NotImplementedError("Full implementation in PRD-001")
