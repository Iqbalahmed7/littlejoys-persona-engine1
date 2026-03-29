"""
Scenario configuration for the 4 LittleJoys business problems.

Each scenario defines a product, target segment, and marketing parameters.
See PRD-005 for the exact Sprint 2 configuration values.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.constants import (
    ATTRIBUTE_MAX,
    ATTRIBUTE_MIN,
    DEFAULT_AWARENESS_THRESHOLD,
    DEFAULT_CONSIDERATION_THRESHOLD,
    DEFAULT_DECISION_THRESHOLDS,
    DEFAULT_LJ_PASS_CHURN_REDUCTION,
    DEFAULT_LJ_PASS_DISCOUNT_PERCENT,
    DEFAULT_LJ_PASS_FREE_TRIAL_MONTHS,
    DEFAULT_LJ_PASS_MONTHLY_PRICE_INR,
    DEFAULT_LJ_PASS_RETENTION_BOOST,
    DEFAULT_NEED_RECOGNITION_THRESHOLD,
    DEFAULT_PURCHASE_THRESHOLD,
    DEFAULT_SIMULATION_MONTHS,
    SCENARIO_IDS,
    SCENARIO_MODE_STATIC,
    SCENARIO_MODE_TEMPORAL,
)

UnitInterval = Annotated[float, Field(ge=ATTRIBUTE_MIN, le=ATTRIBUTE_MAX)]
PositiveFloat = Annotated[float, Field(gt=0.0)]


class ProductConfig(BaseModel):
    """Product attributes for simulation."""

    model_config = ConfigDict(extra="forbid")

    name: str
    category: str
    price_inr: PositiveFloat
    age_range: tuple[int, int]
    key_benefits: list[str] = Field(default_factory=list)
    form_factor: str
    taste_appeal: UnitInterval = 0.5
    effort_to_acquire: UnitInterval = 0.5
    category_need_baseline: UnitInterval = 0.5
    clean_label_score: UnitInterval = 0.5
    health_relevance: UnitInterval = 0.5
    complexity: UnitInterval = 0.0
    cooking_required: UnitInterval = 0.0
    premium_positioning: UnitInterval = 0.5
    superfood_score: UnitInterval = 0.5
    subscription_available: bool = False
    addresses_concerns: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_age_range(self) -> ProductConfig:
        minimum, maximum = self.age_range
        if minimum > maximum:
            raise ValueError("product.age_range must be ordered as (min, max)")
        return self


class MarketingConfig(BaseModel):
    """Marketing and distribution parameters."""

    model_config = ConfigDict(extra="forbid")

    awareness_budget: UnitInterval = 0.3
    channel_mix: dict[str, float] = Field(default_factory=dict)
    trust_signals: list[str] = Field(default_factory=list)
    school_partnership: bool = False
    influencer_campaign: bool = False
    pediatrician_endorsement: bool = False
    sports_club_partnership: bool = False
    perceived_quality: UnitInterval = 0.5
    trust_signal: UnitInterval = 0.5
    expert_endorsement: UnitInterval = 0.5
    social_proof: UnitInterval = 0.5
    influencer_signal: UnitInterval = 0.5
    awareness_level: UnitInterval = 0.3
    social_buzz: UnitInterval = 0.3
    discount_available: UnitInterval = 0.0

    @model_validator(mode="after")
    def _validate_channel_mix(self) -> MarketingConfig:
        total = sum(self.channel_mix.values())
        if self.channel_mix and not 0.99 <= total <= 1.01:
            raise ValueError("marketing.channel_mix must sum to approximately 1.0")
        return self

    @property
    def marketing_channels(self) -> tuple[str, ...]:
        """Ordered channel names used by the scenario."""

        return tuple(self.channel_mix.keys())


class LJPassConfig(BaseModel):
    """Configuration for Little Joys Pass in repeat-purchase scenarios."""

    model_config = ConfigDict(extra="forbid")

    monthly_price_inr: float = DEFAULT_LJ_PASS_MONTHLY_PRICE_INR
    discount_percent: float = DEFAULT_LJ_PASS_DISCOUNT_PERCENT
    free_trial_months: int = DEFAULT_LJ_PASS_FREE_TRIAL_MONTHS
    retention_boost: float = DEFAULT_LJ_PASS_RETENTION_BOOST
    churn_reduction: float = DEFAULT_LJ_PASS_CHURN_REDUCTION


class ScenarioConfig(BaseModel):
    """Complete scenario configuration for a business problem."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    product: ProductConfig
    marketing: MarketingConfig
    target_age_range: tuple[int, int]
    lj_pass_available: bool = False
    lj_pass: LJPassConfig | None = None
    mode: Literal["static", "temporal"] = SCENARIO_MODE_STATIC
    months: int = DEFAULT_SIMULATION_MONTHS
    thresholds: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_DECISION_THRESHOLDS))

    @model_validator(mode="after")
    def _validate_config(self) -> ScenarioConfig:
        scenario_min, scenario_max = self.target_age_range
        product_min, product_max = self.product.age_range
        if scenario_min > scenario_max:
            raise ValueError("target_age_range must be ordered as (min, max)")
        if scenario_max < product_min or scenario_min > product_max:
            raise ValueError("target_age_range must overlap product.age_range")
        if self.lj_pass_available and self.lj_pass is None:
            self.lj_pass = LJPassConfig()
        if not self.lj_pass_available:
            self.lj_pass = None
        return self

    @property
    def funnel_thresholds(self) -> dict[str, float]:
        """Compatibility mapping for funnel code that still expects ``need``."""

        thresholds = dict(self.thresholds)
        if "need" not in thresholds and "need_recognition" in thresholds:
            thresholds["need"] = thresholds["need_recognition"]
        return {
            key: thresholds[key]
            for key in ("need", "awareness", "consideration", "purchase")
            if key in thresholds
        }


def _scenario_catalog() -> dict[str, ScenarioConfig]:
    return {
        "nutrimix_2_6": ScenarioConfig(
            id="nutrimix_2_6",
            name="Nutrimix for 2-6 year olds",
            description="Existing core product — repeat purchase and LJ Pass modeling",
            product=ProductConfig(
                name="Nutrimix",
                category="nutrition_powder",
                price_inr=599.0,
                age_range=(2, 6),
                key_benefits=["immunity", "growth", "brain_development"],
                form_factor="powder_mix",
                taste_appeal=0.7,
                effort_to_acquire=0.3,
                category_need_baseline=0.65,
                clean_label_score=0.85,
                health_relevance=0.75,
                complexity=0.10,
                cooking_required=0.0,
                premium_positioning=0.60,
                superfood_score=0.70,
                subscription_available=True,
                addresses_concerns=["low_immunity", "underweight", "picky_eater", "low_energy"],
            ),
            marketing=MarketingConfig(
                awareness_budget=0.5,
                channel_mix={
                    "instagram": 0.40,
                    "youtube": 0.30,
                    "whatsapp": 0.30,
                },
                trust_signals=["pediatrician_approved", "clean_label", "no_added_sugar"],
                pediatrician_endorsement=True,
                influencer_campaign=True,
                perceived_quality=0.75,
                trust_signal=0.70,
                expert_endorsement=0.50,
                social_proof=0.70,
                influencer_signal=0.50,
                awareness_level=0.60,
                social_buzz=0.50,
                discount_available=0.07,
            ),
            target_age_range=(2, 6),
            lj_pass_available=True,
            lj_pass=LJPassConfig(),
            mode=SCENARIO_MODE_TEMPORAL,
            months=6,
            thresholds={
                "need_recognition": DEFAULT_NEED_RECOGNITION_THRESHOLD,
                "awareness": DEFAULT_AWARENESS_THRESHOLD,
                "consideration": DEFAULT_CONSIDERATION_THRESHOLD,
                "purchase": DEFAULT_PURCHASE_THRESHOLD,
            },
        ),
        "nutrimix_7_14": ScenarioConfig(
            id="nutrimix_7_14",
            name="Nutrimix expansion to 7-14 year olds",
            description="Can the same product work for older children?",
            product=ProductConfig(
                name="Nutrimix 7+",
                category="nutrition_powder",
                price_inr=649.0,
                age_range=(7, 14),
                key_benefits=["focus", "energy", "immunity"],
                form_factor="powder_mix",
                taste_appeal=0.55,
                effort_to_acquire=0.3,
                category_need_baseline=0.45,
                clean_label_score=0.85,
                health_relevance=0.60,
                complexity=0.10,
                cooking_required=0.0,
                premium_positioning=0.55,
                superfood_score=0.70,
                subscription_available=True,
                addresses_concerns=["low_immunity", "low_energy", "focus_issues", "picky_eater"],
            ),
            marketing=MarketingConfig(
                awareness_budget=0.35,
                channel_mix={
                    "instagram": 0.35,
                    "youtube": 0.40,
                    "whatsapp": 0.25,
                },
                trust_signals=["school_approved", "clean_label"],
                school_partnership=True,
                perceived_quality=0.65,
                trust_signal=0.55,
                expert_endorsement=0.40,
                social_proof=0.40,
                influencer_signal=0.40,
                awareness_level=0.35,
                social_buzz=0.30,
                discount_available=0.07,
            ),
            target_age_range=(7, 14),
            lj_pass_available=True,
            lj_pass=LJPassConfig(),
            mode=SCENARIO_MODE_TEMPORAL,
            months=12,
            thresholds={
                "need_recognition": DEFAULT_NEED_RECOGNITION_THRESHOLD,
                "awareness": DEFAULT_AWARENESS_THRESHOLD,
                "consideration": DEFAULT_CONSIDERATION_THRESHOLD,
                "purchase": DEFAULT_PURCHASE_THRESHOLD,
            },
        ),
        "magnesium_gummies": ScenarioConfig(
            id="magnesium_gummies",
            name="Magnesium Gummies for Kids",
            description="New supplement category — awareness is the primary challenge",
            product=ProductConfig(
                name="MagBites",
                category="supplement_gummies",
                price_inr=499.0,
                age_range=(4, 12),
                key_benefits=["sleep", "calm", "focus"],
                form_factor="gummy",
                taste_appeal=0.85,
                effort_to_acquire=0.4,
                category_need_baseline=0.30,
                clean_label_score=0.85,
                health_relevance=0.55,
                complexity=0.05,
                cooking_required=0.0,
                premium_positioning=0.50,
                superfood_score=0.30,
                subscription_available=True,
                addresses_concerns=["focus_issues", "low_energy", "low_immunity"],
            ),
            marketing=MarketingConfig(
                awareness_budget=0.25,
                channel_mix={"instagram": 0.40, "youtube": 0.30, "whatsapp": 0.30},
                trust_signals=["imported_ingredients", "pediatrician_recommended"],
                influencer_campaign=True,
                perceived_quality=0.60,
                trust_signal=0.50,
                expert_endorsement=0.30,
                social_proof=0.25,
                influencer_signal=0.30,
                awareness_level=0.20,
                social_buzz=0.15,
                discount_available=0.09,
            ),
            target_age_range=(4, 12),
            lj_pass_available=False,
            mode=SCENARIO_MODE_STATIC,
        ),
        "protein_mix": ScenarioConfig(
            id="protein_mix",
            name="ProteinMix for Active Kids",
            description="Protein supplement — effort and routine are the primary barriers",
            product=ProductConfig(
                name="ProteinMix",
                category="protein_supplement",
                price_inr=799.0,
                age_range=(6, 14),
                key_benefits=["muscle", "growth", "energy"],
                form_factor="powder_shake",
                taste_appeal=0.50,
                effort_to_acquire=0.6,
                category_need_baseline=0.40,
                clean_label_score=0.85,
                health_relevance=0.60,
                complexity=0.60,
                cooking_required=0.80,
                premium_positioning=0.50,
                superfood_score=0.60,
                subscription_available=True,
                addresses_concerns=["underweight", "picky_eater", "low_energy"],
            ),
            marketing=MarketingConfig(
                awareness_budget=0.30,
                channel_mix={
                    "instagram": 0.35,
                    "youtube": 0.40,
                    "whatsapp": 0.25,
                },
                trust_signals=["sports_nutrition_certified", "no_artificial_sweeteners"],
                sports_club_partnership=True,
                perceived_quality=0.60,
                trust_signal=0.50,
                expert_endorsement=0.30,
                social_proof=0.15,
                influencer_signal=0.30,
                awareness_level=0.20,
                social_buzz=0.15,
                discount_available=0.08,
            ),
            target_age_range=(6, 14),
            lj_pass_available=False,
            mode=SCENARIO_MODE_STATIC,
        ),
    }


def get_scenario(scenario_id: str) -> ScenarioConfig:
    """
    Get a predefined scenario configuration by ID.

    Args:
        scenario_id: Scenario identifier.

    Returns:
        A deep-copied ``ScenarioConfig`` for the requested scenario.

    Raises:
        KeyError: If ``scenario_id`` is unknown.
    """

    scenarios = _scenario_catalog()
    if scenario_id not in scenarios:
        raise KeyError(f"Unknown scenario_id: {scenario_id}")
    return scenarios[scenario_id].model_copy(deep=True)


def get_all_scenarios() -> list[ScenarioConfig]:
    """
    Get all predefined scenario configurations.

    Returns:
        The four Sprint 2 scenarios in stable ID order.
    """

    return [get_scenario(scenario_id) for scenario_id in SCENARIO_IDS]
