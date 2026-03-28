"""Unit tests for the purchase funnel (layers 0-3)."""

from __future__ import annotations

from src.decision.funnel import (
    compute_awareness,
    compute_need_recognition,
    run_funnel,
)
from src.decision.scenarios import MarketingConfig, ProductConfig, ScenarioConfig
from src.taxonomy.schema import HealthAttributes, Persona, PsychologyAttributes


def _adoption_friendly_persona(sample_persona: Persona) -> Persona:
    """Persona tuned to clear consideration and purchase for LittleJoys-branded scenarios."""

    return sample_persona.model_copy(
        update={
            "psychology": PsychologyAttributes(
                health_anxiety=0.95,
                social_proof_bias=0.9,
                risk_tolerance=0.92,
            ),
            "health": HealthAttributes(
                nutrition_gap_awareness=0.95,
                child_health_proactivity=0.9,
                immunity_concern=0.9,
                medical_authority_trust=0.85,
            ),
            "education_learning": sample_persona.education_learning.model_copy(
                update={"research_before_purchase": 0.95, "science_literacy": 0.95}
            ),
            "values": sample_persona.values.model_copy(
                update={
                    "indie_brand_openness": 0.95,
                    "best_for_my_child_intensity": 0.95,
                    "guilt_driven_spending": 0.9,
                }
            ),
            "emotional": sample_persona.emotional.model_copy(
                update={"emotional_persuasion_susceptibility": 0.9}
            ),
            "daily_routine": sample_persona.daily_routine.model_copy(
                update={"budget_consciousness": 0.15}
            ),
        }
    )


def test_zero_awareness_produces_zero_adoption(sample_persona: Persona) -> None:
    """With no marketing mass, awareness stays at zero and the funnel stops there."""

    scenario = ScenarioConfig(
        id="z",
        name="z",
        description="",
        product=ProductConfig(
            name="LittleJoys Test",
            category="nutrition",
            price_inr=300.0,
            age_range=(3, 8),
            key_benefits=["nutrition"],
            form_factor="powder",
        ),
        marketing=MarketingConfig(
            awareness_budget=0.0,
            channel_mix={},
            pediatrician_endorsement=False,
            influencer_campaign=False,
            school_partnership=False,
        ),
        target_age_range=(3, 8),
    )
    result = run_funnel(
        sample_persona, scenario, {"need": 0.0, "consideration": 0.0, "purchase": 0.0}
    )
    assert result.awareness_score == 0.0
    assert result.outcome == "reject"
    assert result.rejection_stage == "awareness"
    assert result.rejection_reason == "low_awareness"


def test_high_need_high_awareness_produces_adoption(
    sample_persona: Persona,
    sample_scenario: ScenarioConfig,
) -> None:
    """Strong need and marketing should admit adoption when thresholds are permissive."""

    persona = _adoption_friendly_persona(sample_persona)
    thresholds = {"need": 0.05, "awareness": 0.05, "consideration": 0.05, "purchase": 0.05}
    result = run_funnel(persona, sample_scenario, thresholds)
    assert result.outcome == "adopt"
    assert result.rejection_reason is None


def test_price_sensitive_persona_rejects_expensive_product(
    high_price_sensitivity_persona: Persona,
    sample_scenario: ScenarioConfig,
) -> None:
    """Heavy budget focus rejects high absolute price at the purchase layer."""

    scenario = sample_scenario.model_copy(
        update={
            "product": sample_scenario.product.model_copy(update={"price_inr": 8_000.0}),
        }
    )
    thresholds = {"need": 0.01, "awareness": 0.01, "consideration": 0.01, "purchase": 0.45}
    result = run_funnel(high_price_sensitivity_persona, scenario, thresholds)
    assert result.outcome == "reject"
    assert result.rejection_stage == "purchase"
    assert result.rejection_reason == "price_too_high"


def test_dietary_incompatible_reduces_consideration(sample_persona: Persona) -> None:
    """Vegetarian persona facing a meat-positioned SKU should fail consideration."""

    scenario = ScenarioConfig(
        id="diet",
        name="diet",
        description="",
        product=ProductConfig(
            name="Chicken Protein Junior",
            category="non-vegetarian supplement",
            price_inr=400.0,
            age_range=(4, 10),
            key_benefits=["chicken protein"],
            form_factor="powder",
        ),
        marketing=MarketingConfig(awareness_budget=0.9, pediatrician_endorsement=False, channel_mix={"instagram": 1.0, "youtube": 0.0, "whatsapp": 0.0}),
        target_age_range=(4, 10),
    )
    thresholds = {"need": 0.01, "awareness": 0.01, "consideration": 0.5, "purchase": 0.01}
    result = run_funnel(sample_persona, scenario, thresholds)
    assert result.outcome == "reject"
    assert result.rejection_stage == "consideration"
    assert result.rejection_reason == "dietary_incompatible"


def test_age_outside_range_reduces_need(sample_persona: Persona, sample_scenario: ScenarioConfig) -> None:
    """Targeting only teens while the child is a toddler should damp need via age relevance."""

    scenario = ScenarioConfig(
        id="age",
        name="age",
        description="",
        product=ProductConfig(
            name="Teen Fuel",
            category="nutrition",
            price_inr=350.0,
            age_range=(13, 17),
            key_benefits=["teen growth"],
            form_factor="powder",
        ),
        marketing=MarketingConfig(awareness_budget=0.5, channel_mix={"instagram": 1.0, "youtube": 0.0, "whatsapp": 0.0}),
        target_age_range=(13, 17),
    )
    need = compute_need_recognition(sample_persona, scenario)
    wide = sample_scenario
    need_wide = compute_need_recognition(sample_persona, wide)
    assert need <= need_wide


def test_rejection_reason_always_populated_for_rejections(sample_persona: Persona) -> None:
    """Every rejection carries a concrete reason string."""

    scenario = ScenarioConfig(
        id="r",
        name="r",
        description="",
        product=ProductConfig(
            name="LittleJoys X",
            category="nutrition",
            price_inr=300.0,
            age_range=(3, 8),
            key_benefits=["nutrition"],
            form_factor="powder",
        ),
        marketing=MarketingConfig(awareness_budget=0.0, pediatrician_endorsement=False, channel_mix={"instagram": 1.0, "youtube": 0.0, "whatsapp": 0.0}),
        target_age_range=(3, 8),
    )
    result = run_funnel(sample_persona, scenario, {"need": 0.99})
    assert result.outcome == "reject"
    assert result.rejection_reason is not None
    assert len(result.rejection_reason) > 2


def test_adoption_never_has_rejection_reason(
    sample_persona: Persona,
    sample_scenario: ScenarioConfig,
) -> None:
    """Adopted personas must not carry rejection metadata."""

    persona = _adoption_friendly_persona(sample_persona)
    thresholds = {"need": 0.05, "awareness": 0.05, "consideration": 0.05, "purchase": 0.05}
    result = run_funnel(persona, sample_scenario, thresholds)
    assert result.outcome == "adopt"
    assert result.rejection_reason is None
    assert result.rejection_stage is None


def test_funnel_scores_monotonically_decrease_or_equal(
    sample_persona: Persona,
    sample_scenario: ScenarioConfig,
) -> None:
    """After layer 1, awareness weakly dominates consideration and purchase."""

    result = run_funnel(sample_persona, sample_scenario, {"need": 0.0})
    assert result.awareness_score + 1e-9 >= result.consideration_score
    assert result.consideration_score + 1e-9 >= result.purchase_score


def test_pediatrician_endorsement_boosts_awareness(
    sample_persona: Persona,
    sample_scenario: ScenarioConfig,
) -> None:
    """Pediatrician flag plus high medical trust increases awareness versus control."""

    persona = sample_persona.model_copy(
        update={"health": HealthAttributes(medical_authority_trust=0.85)},
    )
    product = sample_scenario.product
    base = ScenarioConfig(
        id="ped-base",
        name="ped-base",
        description="",
        product=product,
        marketing=MarketingConfig(
            awareness_budget=0.4,
            channel_mix={"instagram": 1.0, "youtube": 0.0, "whatsapp": 0.0},
            pediatrician_endorsement=False,
            influencer_campaign=False,
            school_partnership=False,
        ),
        target_age_range=sample_scenario.target_age_range,
    )
    boosted = base.model_copy(
        update={
            "marketing": base.marketing.model_copy(update={"pediatrician_endorsement": True}),
        }
    )
    a0 = compute_awareness(persona, base)
    a1 = compute_awareness(persona, boosted)
    assert a1 > a0


def test_school_partnership_boosts_awareness(
    sample_persona: Persona,
    sample_scenario: ScenarioConfig,
) -> None:
    """School partnership adds mass when community engagement is above the threshold."""

    persona = sample_persona.model_copy(
        update={
            "cultural": sample_persona.cultural.model_copy(update={"community_orientation": 0.95}),
            "relationships": sample_persona.relationships.model_copy(
                update={"peer_influence_strength": 0.95}
            ),
        }
    )
    product = sample_scenario.product
    base = ScenarioConfig(
        id="sch-base",
        name="sch-base",
        description="",
        product=product,
        marketing=MarketingConfig(
            awareness_budget=0.35,
            channel_mix={"instagram": 1.0, "youtube": 0.0, "whatsapp": 0.0},
            school_partnership=False,
            pediatrician_endorsement=False,
            influencer_campaign=False,
        ),
        target_age_range=sample_scenario.target_age_range,
    )
    with_school = base.model_copy(
        update={
            "marketing": base.marketing.model_copy(update={"school_partnership": True}),
        }
    )
    assert compute_awareness(persona, with_school) > compute_awareness(persona, base)
