"""
Persona data model for the LittleJoys simulation engine.

Implements the three-layer architecture from ARCHITECTURE.md:
- Identity layer: frozen, taxonomy-backed attributes
- Memory layer: accumulated events and brand relationships
- State layer: scenario-specific, time-varying state
"""

from __future__ import annotations

from typing import Annotated, Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.constants import (
    ATTRIBUTE_MAX,
    ATTRIBUTE_MIN,
    CHILD_AGE_MAX,
    CHILD_AGE_MIN,
    MIN_PARENT_CHILD_AGE_GAP,
    PARENT_AGE_MAX,
    PARENT_AGE_MIN,
)

UnitInterval = Annotated[float, Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)]
SignedUnitInterval = Annotated[float, Field(ge=-1.0, le=1.0)]
ChildAge = Annotated[int, Field(ge=CHILD_AGE_MIN, le=CHILD_AGE_MAX)]
ParentAge = Annotated[int, Field(ge=PARENT_AGE_MIN, le=PARENT_AGE_MAX)]

Gender = Literal["female", "male"]
CityTier = Literal["Tier1", "Tier2", "Tier3"]
EducationLevel = Literal["high_school", "bachelors", "masters", "doctorate", "professional"]
EmploymentStatus = Literal["homemaker", "part_time", "full_time", "self_employed", "freelance"]
FamilyStructure = Literal["nuclear", "joint", "single_parent"]

IDENTITY_MODEL_CONFIG = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")


class DemographicAttributes(BaseModel):
    """Section 1: Demographic information."""

    model_config = IDENTITY_MODEL_CONFIG

    city_tier: CityTier
    city_name: str = Field(min_length=1)
    region: Literal["North", "South", "East", "West", "NE"]
    urban_vs_periurban: Literal["urban", "periurban"] = "urban"
    household_income_lpa: float = Field(ge=1.0, le=100.0)
    parent_age: ParentAge
    parent_gender: Gender
    marital_status: Literal["married", "single", "divorced", "widowed", "separated"] = "married"
    birth_order: Literal["firstborn_parent", "experienced_parent"] = "experienced_parent"
    num_children: int = Field(ge=1, le=5)
    child_ages: list[ChildAge] = Field(min_length=1)
    child_genders: list[Gender] = Field(min_length=1)
    youngest_child_age: ChildAge | None = None
    oldest_child_age: ChildAge | None = None
    family_structure: FamilyStructure = "nuclear"
    elder_influence: UnitInterval = 0.5
    spouse_involvement_in_purchases: UnitInterval = 0.5
    income_stability: Literal["salaried", "business", "freelance", "gig"] = "salaried"
    socioeconomic_class: Literal["A1", "A2", "B1", "B2", "C1", "C2"] = "B1"
    dual_income_household: bool = False

    @model_validator(mode="before")
    @classmethod
    def _hydrate_child_age_bounds(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        child_ages = payload.get("child_ages")
        num_children = payload.get("num_children")
        youngest = payload.get("youngest_child_age")
        oldest = payload.get("oldest_child_age")

        if (
            child_ages is None
            and youngest is not None
            and oldest is not None
            and isinstance(num_children, int)
        ):
            if num_children == 1:
                payload["child_ages"] = [youngest]
            else:
                age_span = max(oldest - youngest, 0)
                if age_span == 0:
                    payload["child_ages"] = [youngest for _ in range(num_children)]
                else:
                    step = age_span / max(num_children - 1, 1)
                    payload["child_ages"] = [
                        round(youngest + (step * index)) for index in range(num_children)
                    ]

        if payload.get("youngest_child_age") is None and payload.get("child_ages"):
            payload["youngest_child_age"] = min(payload["child_ages"])
        if payload.get("oldest_child_age") is None and payload.get("child_ages"):
            payload["oldest_child_age"] = max(payload["child_ages"])

        return payload

    @model_validator(mode="after")
    def _validate_family_consistency(self) -> DemographicAttributes:
        if self.num_children != len(self.child_ages):
            raise ValueError("num_children must match the number of child_ages")
        if self.num_children != len(self.child_genders):
            raise ValueError("num_children must match the number of child_genders")

        youngest = min(self.child_ages)
        oldest = max(self.child_ages)

        if self.youngest_child_age != youngest:
            raise ValueError("youngest_child_age must equal min(child_ages)")
        if self.oldest_child_age != oldest:
            raise ValueError("oldest_child_age must equal max(child_ages)")
        if self.oldest_child_age < self.youngest_child_age:
            raise ValueError("oldest_child_age must be >= youngest_child_age")
        if self.parent_age - self.oldest_child_age < MIN_PARENT_CHILD_AGE_GAP:
            raise ValueError("parent_age must be at least 18 years greater than oldest_child_age")

        return self


class HealthAttributes(BaseModel):
    """Section 2: Physical and health characteristics."""

    model_config = IDENTITY_MODEL_CONFIG

    child_health_status: Literal["healthy", "recurring_issues", "chronic_condition"] = "healthy"
    child_nutrition_concerns: list[
        Literal["underweight", "picky_eater", "low_immunity", "low_energy", "focus_issues"]
    ] = Field(default_factory=list)
    child_dietary_restrictions: list[
        Literal["lactose_intolerant", "vegetarian", "vegan", "allergies"]
    ] = Field(default_factory=list)
    pediatrician_visit_frequency: Literal["monthly", "quarterly", "rarely", "only_when_sick"] = (
        "quarterly"
    )
    vaccination_attitude: Literal["proactive", "follows_schedule", "skeptical"] = "follows_schedule"
    own_supplement_usage: bool = False
    fitness_engagement: UnitInterval = 0.5
    diet_consciousness: UnitInterval = 0.5
    organic_preference: UnitInterval = 0.5
    health_info_sources: list[
        Literal["pediatrician", "google", "instagram", "friends", "family_elders", "apps"]
    ] = Field(default_factory=lambda: ["pediatrician"])
    medical_authority_trust: UnitInterval = 0.5
    self_research_tendency: UnitInterval = 0.5
    child_health_proactivity: UnitInterval = 0.5
    immunity_concern: UnitInterval = 0.5
    growth_concern: UnitInterval = 0.5
    nutrition_gap_awareness: UnitInterval = 0.5


class PsychologyAttributes(BaseModel):
    """Section 3: Psychological and cognitive aspects."""

    model_config = IDENTITY_MODEL_CONFIG

    decision_speed: UnitInterval = 0.5
    information_need: UnitInterval = 0.5
    risk_tolerance: UnitInterval = 0.5
    analysis_paralysis_tendency: UnitInterval = 0.5
    regret_sensitivity: UnitInterval = 0.5
    authority_bias: UnitInterval = 0.5
    social_proof_bias: UnitInterval = 0.5
    anchoring_bias: UnitInterval = 0.5
    status_quo_bias: UnitInterval = 0.5
    loss_aversion: UnitInterval = 0.5
    halo_effect_susceptibility: UnitInterval = 0.5
    health_anxiety: UnitInterval = 0.5
    comparison_anxiety: UnitInterval = 0.5
    guilt_sensitivity: UnitInterval = 0.5
    control_need: UnitInterval = 0.5
    mental_bandwidth: UnitInterval = 0.5
    decision_fatigue_level: UnitInterval = 0.5
    simplicity_preference: UnitInterval = 0.5


class CulturalAttributes(BaseModel):
    """Section 4: Cultural and social context."""

    model_config = IDENTITY_MODEL_CONFIG

    cultural_region: str = "General Urban Indian"
    dietary_culture: Literal["vegetarian", "eggetarian", "non_vegetarian", "vegan", "jain"] = (
        "non_vegetarian"
    )
    traditional_vs_modern_spectrum: UnitInterval = 0.5
    ayurveda_affinity: UnitInterval = 0.5
    western_brand_trust: UnitInterval = 0.5
    social_circle_ses: Literal["similar", "aspirational", "mixed"] = "mixed"
    mommy_group_membership: bool = False
    social_media_active: bool = True
    community_orientation: UnitInterval = 0.5
    primary_language: str = "Hindi"
    english_proficiency: UnitInterval = 0.5
    content_language_preference: Literal["hindi", "english", "regional", "bilingual"] = "bilingual"


class RelationshipAttributes(BaseModel):
    """Section 5: Relationships and social networks."""

    model_config = IDENTITY_MODEL_CONFIG

    primary_decision_maker: Literal["self", "spouse", "joint", "elder"] = "self"
    peer_influence_strength: UnitInterval = 0.5
    influencer_trust: UnitInterval = 0.5
    elder_advice_weight: UnitInterval = 0.5
    pediatrician_influence: UnitInterval = 0.5
    wom_receiver_openness: UnitInterval = 0.5
    wom_transmitter_tendency: UnitInterval = 0.5
    negative_wom_amplification: UnitInterval = 0.5
    child_pester_power: UnitInterval = 0.5
    child_taste_veto: UnitInterval = 0.5
    child_autonomy_given: UnitInterval = 0.5
    partner_involvement: UnitInterval = 0.5


class CareerAttributes(BaseModel):
    """Section 6: Career and work identity."""

    model_config = IDENTITY_MODEL_CONFIG

    employment_status: EmploymentStatus = "homemaker"
    work_hours_per_week: int = Field(ge=0, le=80, default=0)
    work_from_home: bool = False
    career_ambition: UnitInterval = 0.5
    perceived_time_scarcity: UnitInterval = 0.5
    morning_routine_complexity: UnitInterval = 0.5
    cooking_time_available: UnitInterval = 0.5


class EducationLearningAttributes(BaseModel):
    """Section 7: Education and learning."""

    model_config = IDENTITY_MODEL_CONFIG

    education_level: EducationLevel = "bachelors"
    science_literacy: UnitInterval = 0.5
    nutrition_knowledge: UnitInterval = 0.5
    label_reading_habit: UnitInterval = 0.5
    research_before_purchase: UnitInterval = 0.5
    content_consumption_depth: UnitInterval = 0.5
    ingredient_awareness: UnitInterval = 0.5


class LifestyleAttributes(BaseModel):
    """Section 8: Hobbies, interests, and lifestyle."""

    model_config = IDENTITY_MODEL_CONFIG

    cooking_enthusiasm: UnitInterval = 0.5
    recipe_experimentation: UnitInterval = 0.5
    meal_planning_habit: UnitInterval = 0.5
    convenience_food_acceptance: UnitInterval = 0.5
    wellness_trend_follower: UnitInterval = 0.5
    clean_label_importance: UnitInterval = 0.5
    superfood_awareness: UnitInterval = 0.5
    parenting_philosophy: Literal["helicopter", "free_range", "authoritative", "permissive"] = (
        "authoritative"
    )
    screen_time_strictness: UnitInterval = 0.5
    structured_vs_intuitive_feeding: UnitInterval = 0.5


class DailyRoutineAttributes(BaseModel):
    """Section 9: Lifestyle and daily routine."""

    model_config = IDENTITY_MODEL_CONFIG

    online_vs_offline_preference: UnitInterval = 0.5
    primary_shopping_platform: Literal[
        "amazon",
        "flipkart",
        "bigbasket",
        "dmart",
        "local_store",
        "brand_website",
        "quick_commerce",
    ] = "amazon"
    subscription_comfort: UnitInterval = 0.5
    bulk_buying_tendency: UnitInterval = 0.5
    deal_seeking_intensity: UnitInterval = 0.5
    impulse_purchase_tendency: UnitInterval = 0.5
    budget_consciousness: UnitInterval = 0.5
    health_spend_priority: UnitInterval = 0.5
    price_reference_point: float = Field(ge=0.0, le=5_000.0, default=500.0)
    value_perception_driver: Literal["price_per_unit", "brand", "ingredients", "results"] = (
        "ingredients"
    )
    cashback_coupon_sensitivity: UnitInterval = 0.5
    breakfast_routine: Literal["elaborate", "quick", "skipped"] = "quick"
    milk_supplement_current: Literal[
        "horlicks",
        "bournvita",
        "pediasure",
        "complan",
        "littlejoys",
        "other",
        "none",
    ] = "none"
    gummy_vitamin_usage: bool = False
    snacking_pattern: Literal["structured", "grazing", "restricted"] = "structured"


class ValueAttributes(BaseModel):
    """Section 10: Core values, beliefs, and philosophy."""

    model_config = IDENTITY_MODEL_CONFIG

    supplement_necessity_belief: UnitInterval = 0.5
    natural_vs_synthetic_preference: UnitInterval = 0.5
    food_first_belief: UnitInterval = 0.5
    preventive_vs_reactive_health: UnitInterval = 0.5
    brand_loyalty_tendency: UnitInterval = 0.5
    indie_brand_openness: UnitInterval = 0.5
    transparency_importance: UnitInterval = 0.5
    made_in_india_preference: UnitInterval = 0.5
    best_for_my_child_intensity: UnitInterval = 0.5
    guilt_driven_spending: UnitInterval = 0.5
    peer_comparison_drive: UnitInterval = 0.5


class EmotionalAttributes(BaseModel):
    """Section 11: Emotional and relational skills."""

    model_config = IDENTITY_MODEL_CONFIG

    emotional_persuasion_susceptibility: UnitInterval = 0.5
    fear_appeal_responsiveness: UnitInterval = 0.5
    aspirational_messaging_responsiveness: UnitInterval = 0.5
    testimonial_impact: UnitInterval = 0.5
    buyer_remorse_tendency: UnitInterval = 0.5
    confirmation_bias_strength: UnitInterval = 0.5
    review_writing_tendency: UnitInterval = 0.5


class MediaAttributes(BaseModel):
    """Section 12: Media consumption and engagement."""

    model_config = IDENTITY_MODEL_CONFIG

    primary_social_platform: Literal["instagram", "facebook", "youtube", "whatsapp", "none"] = (
        "instagram"
    )
    daily_social_media_hours: float = Field(ge=0.0, le=5.0, default=1.0)
    content_format_preference: Literal[
        "reels", "stories", "long_video", "text_posts", "podcasts"
    ] = "reels"
    ad_receptivity: UnitInterval = 0.5
    product_discovery_channel: Literal[
        "social_media", "search", "friend", "doctor", "store_shelf", "ad"
    ] = "search"
    review_platform_trust: Literal[
        "amazon_reviews", "google", "instagram", "youtube", "mom_blogs"
    ] = "amazon_reviews"
    search_behavior: Literal["active_seeker", "passive_absorber", "recommendation_dependent"] = (
        "active_seeker"
    )
    app_download_willingness: UnitInterval = 0.5
    wallet_topup_comfort: UnitInterval = 0.5
    digital_payment_comfort: UnitInterval = 0.5


class MemoryEntry(BaseModel):
    """A single episodic or semantic memory."""

    model_config = ConfigDict(extra="forbid")

    timestamp: str
    event_type: str
    content: str
    emotional_valence: SignedUnitInterval = 0.0
    salience: UnitInterval = 0.5


class BrandMemory(BaseModel):
    """Accumulated impressions of a specific brand."""

    model_config = ConfigDict(extra="forbid")

    brand_name: str
    first_exposure: str | None = None
    exposure_channel: str | None = None
    trust_level: UnitInterval = 0.0
    purchase_count: int = Field(ge=0, default=0)
    last_purchase_date: str | None = None
    satisfaction_history: list[float] = Field(default_factory=list)
    has_pass: bool = False
    word_of_mouth_received: list[str] = Field(default_factory=list)
    word_of_mouth_given: list[str] = Field(default_factory=list)


class PurchaseEvent(BaseModel):
    """Record of a purchase decision."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    timestamp: str = ""
    product: str = Field(alias="product_name")
    price_paid: float = Field(ge=0.0, default=0.0)
    channel: str = ""
    trigger: str = ""
    outcome: Literal["purchased", "repurchased", "churned"] = "purchased"
    satisfaction: UnitInterval = 0.5


class TemporalState(BaseModel):
    """Current simulation state for a persona."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    current_month: int = 0
    current_awareness: dict[str, float] = Field(default_factory=dict)
    current_consideration_set: list[str] = Field(default_factory=list)
    current_satisfaction: dict[str, float] = Field(default_factory=dict)
    has_purchased: bool = False
    consecutive_purchase_months: int = 0
    has_lj_pass: bool = False
    satisfaction_trajectory: list[float] = Field(default_factory=list)
    wom_received_from: list[str] = Field(default_factory=list)


class Persona(BaseModel):
    """Complete synthetic persona with identity, memory, and state."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    _IDENTITY_CATEGORY_MODELS: ClassVar[dict[str, type[BaseModel]]] = {
        "demographics": DemographicAttributes,
        "health": HealthAttributes,
        "psychology": PsychologyAttributes,
        "cultural": CulturalAttributes,
        "relationships": RelationshipAttributes,
        "career": CareerAttributes,
        "education_learning": EducationLearningAttributes,
        "lifestyle": LifestyleAttributes,
        "daily_routine": DailyRoutineAttributes,
        "values": ValueAttributes,
        "emotional": EmotionalAttributes,
        "media": MediaAttributes,
    }

    id: str
    generation_seed: int
    generation_timestamp: str
    tier: Literal["statistical", "deep"] = "deep"

    demographics: DemographicAttributes
    health: HealthAttributes
    psychology: PsychologyAttributes
    cultural: CulturalAttributes
    relationships: RelationshipAttributes
    career: CareerAttributes
    education_learning: EducationLearningAttributes = Field(alias="education")
    lifestyle: LifestyleAttributes = Field(alias="lifestyle_interests")
    daily_routine: DailyRoutineAttributes
    values: ValueAttributes
    emotional: EmotionalAttributes
    media: MediaAttributes

    narrative: str | None = None

    # Human-readable name generated post-construction for UX purposes.
    display_name: str | None = None

    episodic_memory: list[MemoryEntry] = Field(default_factory=list)
    semantic_memory: dict[str, Any] = Field(default_factory=dict)
    brand_memories: dict[str, BrandMemory] = Field(default_factory=dict)
    purchase_history: list[PurchaseEvent] = Field(default_factory=list)
    state: TemporalState = Field(default_factory=TemporalState, alias="time_state")

    @property
    def education(self) -> EducationLearningAttributes:
        """Compatibility accessor for the architecture naming."""

        return self.education_learning

    @property
    def lifestyle_interests(self) -> LifestyleAttributes:
        """Compatibility accessor for the architecture naming."""

        return self.lifestyle

    @property
    def time_state(self) -> TemporalState:
        """Compatibility accessor for the architecture naming."""

        return self.state

    def to_flat_dict(self) -> dict[str, Any]:
        """Flatten all nested identity attributes into a single dictionary."""

        flat: dict[str, Any] = {}
        for category_name in self._IDENTITY_CATEGORY_MODELS:
            category = getattr(self, category_name)
            flat.update(category.model_dump())
        return flat

    @classmethod
    def from_flat_dict(
        cls,
        flat: dict[str, Any],
        persona_id: str,
        seed: int,
        timestamp: str,
        tier: Literal["statistical", "deep"] = "deep",
    ) -> Persona:
        """Reconstruct a persona from a flattened identity attribute mapping.

        Args:
            flat: Flat attribute mapping created by ``to_flat_dict``.
            persona_id: Unique persona identifier.
            seed: Generation seed.
            timestamp: Generation timestamp.
            tier: Persona tier.

        Returns:
            A reconstructed persona instance.
        """

        identity_payload: dict[str, BaseModel] = {}
        remaining_fields = dict(flat)
        for category_name, model_cls in cls._IDENTITY_CATEGORY_MODELS.items():
            category_fields = {
                field_name: remaining_fields.pop(field_name)
                for field_name in model_cls.model_fields
                if field_name in remaining_fields
            }
            identity_payload[category_name] = model_cls.model_validate(category_fields)

        return cls(
            id=persona_id,
            generation_seed=seed,
            generation_timestamp=timestamp,
            tier=tier,
            **identity_payload,
        )


def _field_is_unit_interval(field_info: Any) -> bool:
    """True if the field is a float constrained to the closed [0, 1] interval."""

    if field_info.annotation is not float:
        return False
    ge_val: float | None = None
    le_val: float | None = None
    for meta in field_info.metadata:
        if type(meta).__name__ == "Ge":
            ge_val = meta.ge
        elif type(meta).__name__ == "Le":
            le_val = meta.le
    return ge_val == ATTRIBUTE_MIN and le_val == ATTRIBUTE_MAX


def list_psychographic_continuous_attributes() -> tuple[str, ...]:
    """Return flat names of all ``UnitInterval`` identity fields (excludes demographics).

    Used by the Gaussian copula to sample correlated [0, 1] psychographics.
    """
    names: list[str] = []
    for category_name, model_cls in Persona._IDENTITY_CATEGORY_MODELS.items():
        if category_name == "demographics":
            continue
        for field_name, field_info in model_cls.model_fields.items():
            if _field_is_unit_interval(field_info):
                names.append(field_name)
    return tuple(names)
