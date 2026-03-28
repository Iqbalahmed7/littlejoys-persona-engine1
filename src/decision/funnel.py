"""
Purchase funnel decision functions — Layer 0 through Layer 3.

Layer 0: Need Recognition (does the parent recognize a nutrition need?)
Layer 1: Awareness (has the parent heard of this product?)
Layer 2: Consideration (does the parent seriously consider purchasing?)
Layer 3: Purchase (does the parent actually buy?)

Each layer is a function of persona attributes and scenario parameters.
See ARCHITECTURE.md §8 for the full decision model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

from src.constants import (
    ATTRIBUTE_MAX,
    ATTRIBUTE_MIN,
    DEFAULT_CHANNEL_MIX_INSTAGRAM,
    DEFAULT_CHANNEL_MIX_WHATSAPP,
    DEFAULT_CHANNEL_MIX_YOUTUBE,
    FUNNEL_AGE_RELEVANCE_IN_RANGE,
    FUNNEL_AGE_RELEVANCE_OUTSIDE_RANGE,
    FUNNEL_BOOST_INFLUENCER_CAMPAIGN,
    FUNNEL_BOOST_PEDIATRICIAN_ENDORSEMENT,
    FUNNEL_BOOST_SCHOOL_PARTNERSHIP,
    FUNNEL_CONSIDERATION_DIETARY_MATCH,
    FUNNEL_CONSIDERATION_DIETARY_MISMATCH,
    FUNNEL_INFLUENCER_TRUST_THRESHOLD,
    FUNNEL_NON_PRIMARY_SOCIAL_PLATFORM_MATCH,
    FUNNEL_PURCHASE_COMBO_CLIP_MAX,
    FUNNEL_PURCHASE_COMBO_CLIP_MIN,
    FUNNEL_PURCHASE_PRICE_RATIO_CAP,
    FUNNEL_RISK_UNFAMILIAR_BRAND_WEIGHT,
    FUNNEL_SCHOOL_COMMUNITY_ENGAGEMENT_THRESHOLD,
    FUNNEL_THRESHOLD_AWARENESS,
    FUNNEL_THRESHOLD_CONSIDERATION,
    FUNNEL_THRESHOLD_NEED_RECOGNITION,
    FUNNEL_THRESHOLD_PURCHASE,
    FUNNEL_TRUST_SIGNAL_PEDIATRICIAN_TRUST,
    FUNNEL_WEIGHT_NEED_CHILD_PROACTIVITY,
    FUNNEL_WEIGHT_NEED_GROWTH,
    FUNNEL_WEIGHT_NEED_HEALTH_ANXIETY,
    FUNNEL_WEIGHT_NEED_IMMUNITY,
    FUNNEL_WEIGHT_NEED_NUTRITION_GAP,
)

if TYPE_CHECKING:
    from src.decision.scenarios import MarketingConfig, ProductConfig, ScenarioConfig
    from src.taxonomy.schema import Persona

log = structlog.get_logger(__name__)

_DEFAULT_THRESHOLDS: dict[str, float] = {
    "need": FUNNEL_THRESHOLD_NEED_RECOGNITION,
    "awareness": FUNNEL_THRESHOLD_AWARENESS,
    "consideration": FUNNEL_THRESHOLD_CONSIDERATION,
    "purchase": FUNNEL_THRESHOLD_PURCHASE,
}


@dataclass(frozen=True, slots=True)
class DecisionResult:
    """Result of running a persona through the purchase funnel (layers 0-3)."""

    persona_id: str
    need_score: float
    awareness_score: float
    consideration_score: float
    purchase_score: float
    outcome: str
    rejection_stage: str | None
    rejection_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for aggregation and static simulation outputs."""

        return {
            "persona_id": self.persona_id,
            "need_score": self.need_score,
            "awareness_score": self.awareness_score,
            "consideration_score": self.consideration_score,
            "purchase_score": self.purchase_score,
            "outcome": self.outcome,
            "rejection_stage": self.rejection_stage,
            "rejection_reason": self.rejection_reason,
        }


def _clip_unit(x: float) -> float:
    """Clip to the closed unit interval; map non-finite values to 0."""

    if not math.isfinite(x):
        return ATTRIBUTE_MIN
    return max(ATTRIBUTE_MIN, min(ATTRIBUTE_MAX, x))


def _child_in_target_age_range(persona: Persona, age_low: int, age_high: int) -> bool:
    """True if any child age falls inside ``[age_low, age_high]``."""

    ages = persona.demographics.child_ages
    return any(age_low <= a <= age_high for a in ages)


def _age_relevance_factor(persona: Persona, scenario: ScenarioConfig) -> float:
    """1.0 when a child is in the scenario target range; otherwise reduced relevance."""

    low, high = scenario.target_age_range
    if _child_in_target_age_range(persona, low, high):
        return FUNNEL_AGE_RELEVANCE_IN_RANGE
    return FUNNEL_AGE_RELEVANCE_OUTSIDE_RANGE


def _product_keyword_targets(product: ProductConfig, *keywords: str) -> bool:
    """True if any keyword appears in benefits, category, or name (case-insensitive)."""

    blob = " ".join(
        [product.name, product.category, *[b.lower() for b in product.key_benefits]]
    ).lower()
    return any(k in blob for k in keywords)


def _product_targets_immunity(product: ProductConfig) -> bool:
    return _product_keyword_targets(product, "immunity", "immune", "immun")


def _product_targets_growth(product: ProductConfig) -> bool:
    return _product_keyword_targets(product, "growth", "height", "weight gain")


def _is_littlejoys_product(product: ProductConfig) -> bool:
    return "littlejoy" in product.name.lower() or "littlejoy" in product.category.lower()


def _dietary_cultural_fit(persona: Persona, product: ProductConfig) -> float:
    """
    1.0 when dietary culture is compatible with the product profile; 0.5 when clearly mismatched.
    """

    diet = persona.cultural.dietary_culture
    restrictions = set(persona.health.child_dietary_restrictions)
    blob = f"{product.name} {product.category} {' '.join(product.key_benefits)}".lower()

    if diet == "vegan" and any(x in blob for x in ("dairy", "milk", "whey", "ghee")):
        return FUNNEL_CONSIDERATION_DIETARY_MISMATCH
    if diet == "vegetarian" and any(x in blob for x in ("chicken", "meat", "fish", "non-veg")):
        return FUNNEL_CONSIDERATION_DIETARY_MISMATCH
    if "lactose_intolerant" in restrictions and any(
        x in blob for x in ("dairy", "milk", "whey", "lactose")
    ):
        return FUNNEL_CONSIDERATION_DIETARY_MISMATCH
    return FUNNEL_CONSIDERATION_DIETARY_MATCH


def _channel_persona_match(persona: Persona, marketing: MarketingConfig) -> float:
    """
    Match marketing channel mix to persona media and social engagement (unit interval).

    Uses ``channel_mix`` spend weights with Instagram / YouTube / WhatsApp-style keys.
    """

    mix = marketing.channel_mix or {}
    if not mix:
        mix = {
            "instagram": DEFAULT_CHANNEL_MIX_INSTAGRAM,
            "youtube": DEFAULT_CHANNEL_MIX_YOUTUBE,
            "whatsapp": DEFAULT_CHANNEL_MIX_WHATSAPP,
        }

    insta_match = persona.media.ad_receptivity * (
        1.0
        if persona.media.primary_social_platform == "instagram"
        else FUNNEL_NON_PRIMARY_SOCIAL_PLATFORM_MATCH
    )
    youtube_match = persona.lifestyle.wellness_trend_follower * (
        1.0
        if persona.media.primary_social_platform == "youtube"
        else FUNNEL_NON_PRIMARY_SOCIAL_PLATFORM_MATCH
    )
    whatsapp_match = (0.5 + 0.5 * float(persona.cultural.mommy_group_membership)) * (
        persona.relationships.wom_receiver_openness
    )

    total_weight = sum(max(0.0, w) for w in mix.values()) or 1.0
    raw = (
        mix.get("instagram", 0.0) * insta_match
        + mix.get("youtube", 0.0) * youtube_match
        + mix.get("whatsapp", 0.0) * whatsapp_match
    ) / total_weight
    return _clip_unit(raw)


def _online_shopping_comfort(persona: Persona) -> float:
    """Composite comfort with digital purchase journeys."""

    return _clip_unit(
        persona.media.digital_payment_comfort * 0.4
        + persona.media.app_download_willingness * 0.3
        + persona.daily_routine.online_vs_offline_preference * 0.3
    )


def _school_community_engagement_proxy(persona: Persona) -> float:
    """Proxy for school-adjacent community engagement when not modeled explicitly."""

    return _clip_unit(
        persona.cultural.community_orientation * 0.5
        + persona.relationships.peer_influence_strength * 0.5
    )


def default_funnel_thresholds() -> dict[str, float]:
    """Return a copy of the default per-layer thresholds."""

    return dict(_DEFAULT_THRESHOLDS)


def compute_need_recognition(persona: Persona, scenario: ScenarioConfig) -> float:
    """
    Layer 0: weighted health/nutrition drivers scaled by child age relevance.

    Args:
        persona: Synthetic parent persona.
        scenario: Scenario including product target ages.

    Returns:
        Need score in ``[0, 1]``.
    """

    product = scenario.product
    h = persona.health
    p = persona.psychology

    immunity_term = (
        FUNNEL_WEIGHT_NEED_IMMUNITY * h.immunity_concern
        if _product_targets_immunity(product)
        else 0.0
    )
    growth_term = (
        FUNNEL_WEIGHT_NEED_GROWTH * h.growth_concern if _product_targets_growth(product) else 0.0
    )

    core = (
        FUNNEL_WEIGHT_NEED_HEALTH_ANXIETY * p.health_anxiety
        + FUNNEL_WEIGHT_NEED_NUTRITION_GAP * h.nutrition_gap_awareness
        + FUNNEL_WEIGHT_NEED_CHILD_PROACTIVITY * h.child_health_proactivity
        + immunity_term
        + growth_term
    )
    return _clip_unit(core * _age_relevance_factor(persona, scenario))


def compute_awareness(
    persona: Persona,
    scenario: ScenarioConfig,
    *,
    awareness_boost: float = 0.0,
) -> float:
    """
    Layer 1: marketing budget x channel match plus trust and partnership boosts.

    Args:
        persona: Synthetic parent persona.
        scenario: Scenario with marketing configuration.
        awareness_boost: Extra awareness mass from temporal dynamics (e.g. WOM), clipped in.

    Returns:
        Awareness score in ``[0, 1]``.
    """

    marketing = scenario.marketing
    base = marketing.awareness_budget * _channel_persona_match(persona, marketing)
    score = base

    if marketing.pediatrician_endorsement and (
        persona.health.medical_authority_trust > FUNNEL_TRUST_SIGNAL_PEDIATRICIAN_TRUST
    ):
        score += FUNNEL_BOOST_PEDIATRICIAN_ENDORSEMENT

    if marketing.school_partnership and (
        _school_community_engagement_proxy(persona) > FUNNEL_SCHOOL_COMMUNITY_ENGAGEMENT_THRESHOLD
    ):
        score += FUNNEL_BOOST_SCHOOL_PARTNERSHIP

    if marketing.influencer_campaign and (
        persona.relationships.influencer_trust > FUNNEL_INFLUENCER_TRUST_THRESHOLD
    ):
        score += FUNNEL_BOOST_INFLUENCER_CAMPAIGN

    score += awareness_boost
    return _clip_unit(score)


def compute_consideration(
    persona: Persona,
    scenario: ScenarioConfig,
    awareness: float,
) -> float:
    """
    Layer 2: awareness scaled by trust, research depth, culture, brand, and risk.

    Args:
        persona: Synthetic parent persona.
        scenario: Scenario configuration.
        awareness: Layer-1 awareness score (already clipped).

    Returns:
        Consideration score in ``[0, 1]``.
    """

    product = scenario.product
    trust_factor = _clip_unit(
        (persona.health.medical_authority_trust + persona.psychology.social_proof_bias) / 2.0
    )
    research_factor = _clip_unit(
        persona.education_learning.research_before_purchase
        * persona.education_learning.science_literacy
    )
    cultural_fit = _dietary_cultural_fit(persona, product)

    if _is_littlejoys_product(product):
        brand_factor = _clip_unit(persona.values.indie_brand_openness)
    else:
        brand_factor = _clip_unit(persona.values.brand_loyalty_tendency)

    unfamiliar = _is_littlejoys_product(product)
    if unfamiliar:
        risk_dampener = FUNNEL_RISK_UNFAMILIAR_BRAND_WEIGHT * (
            1.0 - persona.psychology.risk_tolerance
        )
        risk_factor = _clip_unit(1.0 - risk_dampener)
    else:
        risk_factor = 1.0

    multiplier = _clip_unit(
        trust_factor * research_factor * cultural_fit * brand_factor * risk_factor
    )
    return _clip_unit(awareness * multiplier)


def compute_purchase(
    persona: Persona,
    scenario: ScenarioConfig,
    consideration: float,
) -> tuple[float, str | None]:
    """
    Layer 3: purchase propensity and optional diagnostic rejection label.

    Args:
        persona: Synthetic parent persona.
        scenario: Scenario configuration.
        consideration: Layer-2 score (already clipped).

    Returns:
        ``(purchase_score, rejection_hint)`` where ``rejection_hint`` flags dominant barriers
        when the raw composite is weak (used for traceable rejection reasons).
    """

    product = scenario.product
    ref = max(persona.daily_routine.price_reference_point, 1.0)
    price_ratio = min(FUNNEL_PURCHASE_PRICE_RATIO_CAP, product.price_inr / ref)
    price_barrier = _clip_unit(persona.daily_routine.budget_consciousness * price_ratio / 2.0)
    effort_barrier = _clip_unit(
        product.effort_to_acquire * (1.0 - _online_shopping_comfort(persona))
    )

    benefit_mix = _clip_unit(
        product.taste_appeal * 0.5 + min(1.0, len(product.key_benefits) / 5.0) * 0.5
    )
    value_core = _clip_unit(
        persona.values.transparency_importance * 0.5
        + persona.education_learning.ingredient_awareness * 0.5
    )
    value = _clip_unit(value_core * benefit_mix)

    emotional = _clip_unit(
        persona.emotional.emotional_persuasion_susceptibility
        * persona.values.guilt_driven_spending
        * persona.values.best_for_my_child_intensity
    )

    combo = value + emotional - price_barrier - effort_barrier
    combo = max(FUNNEL_PURCHASE_COMBO_CLIP_MIN, min(FUNNEL_PURCHASE_COMBO_CLIP_MAX, combo))
    purchase_score = _clip_unit(consideration * combo)

    hint: str | None = None
    if purchase_score < FUNNEL_THRESHOLD_PURCHASE:
        if price_barrier >= effort_barrier and price_barrier >= 0.15:
            hint = "price_too_high"
        elif effort_barrier > price_barrier and effort_barrier >= 0.15:
            hint = "effort_too_high"
        else:
            hint = "insufficient_trust"

    return purchase_score, hint


def run_funnel(
    persona: Persona,
    scenario: ScenarioConfig,
    thresholds: dict[str, float] | None = None,
    *,
    awareness_boost: float = 0.0,
) -> DecisionResult:
    """
    Execute layers 0→3 with clipping, early exits, and explicit rejection reasons.

    Args:
        persona: Persona to evaluate.
        scenario: Scenario configuration.
        thresholds: Optional overrides for keys ``need``, ``awareness``, ``consideration``,
            ``purchase``.
        awareness_boost: Additional awareness mass (temporal / WOM), added inside layer 1.

    Returns:
        Structured ``DecisionResult`` including per-layer scores.
    """

    t = {**_DEFAULT_THRESHOLDS, **(thresholds or {})}
    pid = persona.id

    need = compute_need_recognition(persona, scenario)
    if need < t["need"]:
        reason = (
            "age_irrelevant"
            if _age_relevance_factor(persona, scenario) < FUNNEL_AGE_RELEVANCE_IN_RANGE
            else "low_need"
        )
        log.debug("funnel_reject_need", persona_id=pid, need=need, reason=reason)
        return DecisionResult(
            persona_id=pid,
            need_score=need,
            awareness_score=0.0,
            consideration_score=0.0,
            purchase_score=0.0,
            outcome="reject",
            rejection_stage="need_recognition",
            rejection_reason=reason,
        )

    awareness = compute_awareness(persona, scenario, awareness_boost=awareness_boost)
    if awareness < t["awareness"]:
        log.debug("funnel_reject_awareness", persona_id=pid, awareness=awareness)
        return DecisionResult(
            persona_id=pid,
            need_score=need,
            awareness_score=awareness,
            consideration_score=0.0,
            purchase_score=0.0,
            outcome="reject",
            rejection_stage="awareness",
            rejection_reason="low_awareness",
        )

    consideration = compute_consideration(persona, scenario, awareness)
    if consideration < t["consideration"]:
        product = scenario.product
        if _dietary_cultural_fit(persona, product) < FUNNEL_CONSIDERATION_DIETARY_MATCH:
            reason = "dietary_incompatible"
        elif (
            persona.health.medical_authority_trust + persona.psychology.social_proof_bias
        ) / 2.0 < 0.25:
            reason = "insufficient_trust"
        else:
            reason = "insufficient_trust"
        log.debug("funnel_reject_consideration", persona_id=pid, consideration=consideration)
        return DecisionResult(
            persona_id=pid,
            need_score=need,
            awareness_score=awareness,
            consideration_score=consideration,
            purchase_score=0.0,
            outcome="reject",
            rejection_stage="consideration",
            rejection_reason=reason,
        )

    purchase_score, purchase_hint = compute_purchase(persona, scenario, consideration)
    if purchase_score < t["purchase"]:
        reason = purchase_hint or "insufficient_trust"
        log.debug("funnel_reject_purchase", persona_id=pid, purchase_score=purchase_score)
        return DecisionResult(
            persona_id=pid,
            need_score=need,
            awareness_score=awareness,
            consideration_score=consideration,
            purchase_score=purchase_score,
            outcome="reject",
            rejection_stage="purchase",
            rejection_reason=reason,
        )

    log.debug("funnel_adopt", persona_id=pid, purchase_score=purchase_score)
    return DecisionResult(
        persona_id=pid,
        need_score=need,
        awareness_score=awareness,
        consideration_score=consideration,
        purchase_score=purchase_score,
        outcome="adopt",
        rejection_stage=None,
        rejection_reason=None,
    )
