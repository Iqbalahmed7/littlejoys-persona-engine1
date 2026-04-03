"""
Tier 2 (deep narrative) persona generation via progressive LLM attribute sampling.

Produces five enrichment layers beyond the statistical Tier 1 base:
  1. Anchor inference  — values, life attitude, parent motivations
  2. Life story        — 2-3 biographical snippets
  3. Narrative         — 300-500 word third-person biography
  4. First-person      — 120-150 word first-person diary-voice summary
  5. Purchase bullets  — 6-8 skimmable decision-driver bullets

Also derives three deterministic (no-LLM) insight blocks:
  - ParentTraits    — enum-resolved decision archetype
  - BudgetProfile   — concrete INR budget figures
  - DecisionRights  — per-domain authority mapping
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import BaseModel, Field

from src.utils.display import describe_attribute_value

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona
    from src.utils.llm import LLMClient

logger = structlog.get_logger(__name__)

_TRAIT_PHRASE_OVERRIDES: dict[str, tuple[str, str]] = {
    "health_anxiety": (
        "{subject_cap} worries constantly about whether the children are getting the right nutrition.",
        "{subject_cap} rarely lets health fears spiral and prefers a measured view of everyday nutrition questions.",
    ),
    "budget_consciousness": (
        "Every purchase goes through a mental cost-benefit analysis before it reaches the cart.",
        "{subject_cap} is willing to pay more when something feels genuinely useful and trustworthy.",
    ),
    "social_proof_bias": (
        "{subject_cap} trusts recommendations from other parents more than polished advertising.",
        "{subject_cap} rarely follows the crowd and prefers to make up {possessive} own mind.",
    ),
    "medical_authority_trust": (
        "A pediatrician's reassurance carries real weight in the final decision.",
        "{subject_cap} listens respectfully to doctors but still double-checks claims independently.",
    ),
    "authority_bias": (
        "Expert voices and formal trust signals make new products feel safer to try.",
        "{subject_cap} is skeptical of authority-led messaging unless it matches lived experience.",
    ),
    "supplement_necessity_belief": (
        "{subject_cap} sees supplements as a practical bridge when daily meals feel inconsistent.",
        "{subject_cap} would rather solve nutrition through ordinary food before adding another product.",
    ),
    "simplicity_preference": (
        "{subject_cap} gravitates toward routines that are easy to repeat on rushed mornings.",
        "{subject_cap} does not mind experimenting when a better routine seems possible.",
    ),
    "perceived_time_scarcity": (
        "Time always feels scarce, so convenience matters almost as much as trust.",
        "{subject_cap} can make room for slower routines when they feel worthwhile.",
    ),
    "child_taste_veto": (
        "If the child refuses the taste twice, the experiment is usually over.",
        "{subject_cap} is patient enough to keep trying even if the first reaction is mixed.",
    ),
    "ad_receptivity": (
        "{subject_cap} notices useful product messages quickly when they fit the family's stage of life.",
        "{subject_cap} tends to tune out most marketing unless it feels unusually relevant.",
    ),
}


# ---------------------------------------------------------------------------
# Deterministic derivation helpers (no LLM required)
# ---------------------------------------------------------------------------

def _derive_parent_traits(persona: Persona) -> "ParentTraits":  # noqa: F821
    """Derive enum-resolved ParentTraits from continuous psychographic attributes."""
    from src.taxonomy.schema import ParentTraits

    ps = persona.psychology
    em = persona.emotional
    val = persona.values
    rel = persona.relationships
    lf = persona.lifestyle
    rt = persona.daily_routine
    hl = persona.health
    cr = persona.career
    dm = persona.demographics
    ed = persona.education_learning

    # --- decision_style ---
    emotional_score = (em.emotional_persuasion_susceptibility + em.fear_appeal_responsiveness) / 2
    analytical_score = (ps.information_need + (1 - ps.analysis_paralysis_tendency)) / 2
    habitual_score = (ps.status_quo_bias + val.brand_loyalty_tendency) / 2
    social_score = (ps.social_proof_bias + rel.peer_influence_strength) / 2
    style_scores = {
        "emotional": emotional_score,
        "analytical": analytical_score,
        "habitual": habitual_score,
        "social": social_score,
    }
    decision_style = max(style_scores, key=style_scores.__getitem__)

    # --- risk_appetite ---
    rt_val = ps.risk_tolerance
    risk_appetite = "low" if rt_val < 0.38 else ("high" if rt_val > 0.62 else "medium")

    # --- decision_confidence ---
    confidence_raw = (ps.decision_speed + (1 - ps.analysis_paralysis_tendency)) / 2
    decision_confidence = "low" if confidence_raw < 0.38 else ("high" if confidence_raw > 0.62 else "medium")

    # --- primary_value_orientation ---
    if rt.budget_consciousness > 0.65:
        primary_value_orientation = "price"
    elif val.supplement_necessity_belief > 0.60 and hl.nutrition_gap_awareness > 0.60:
        primary_value_orientation = "nutrition"
    elif val.brand_loyalty_tendency > 0.65:
        primary_value_orientation = "brand"
    elif lf.convenience_food_acceptance > 0.65:
        primary_value_orientation = "convenience"
    else:
        primary_value_orientation = "features"

    # --- outcome_orientation ---
    prev = val.preventive_vs_reactive_health
    outcome_orientation = "long_term" if prev > 0.62 else ("immediate" if prev < 0.38 else "balanced")

    # --- value_tradeoff_style ---
    if rt.budget_consciousness > 0.65:
        value_tradeoff_style = "price_first"
    elif val.best_for_my_child_intensity > 0.65:
        value_tradeoff_style = "quality_first"
    elif lf.clean_label_importance > 0.62:
        value_tradeoff_style = "feature_first"
    else:
        value_tradeoff_style = "balanced"

    # --- trust_anchor ---
    if ps.social_proof_bias > 0.60 and rel.wom_receiver_openness > 0.60:
        trust_anchor = "peer"
    elif hl.medical_authority_trust > 0.65 and ps.authority_bias > 0.60:
        trust_anchor = "authority"
    elif rel.elder_advice_weight > 0.65:
        trust_anchor = "family"
    else:
        trust_anchor = "self"

    # --- coping_mechanism_type + sentence ---
    if ps.simplicity_preference > 0.62 and lf.meal_planning_habit > 0.58:
        coping_type = "routine_control"
        coping_text = (
            "Sticks firmly to a weekly meal plan and predictable purchase schedule "
            "to avoid last-minute stress and budget surprises."
        )
    elif ps.social_proof_bias > 0.65:
        coping_type = "social_validation"
        coping_text = (
            "Checks in with trusted peers or mom-groups before any new product trial "
            "to feel reassured the choice is widely accepted."
        )
    elif ps.information_need > 0.70 and ed.research_before_purchase > 0.65:
        coping_type = "research_deep_dive"
        coping_text = (
            "Reads reviews, compares labels, and watches YouTube demos before committing "
            "to an unfamiliar product — thoroughness reduces buyer anxiety."
        )
    elif ps.status_quo_bias > 0.65:
        coping_type = "denial"
        coping_text = (
            "Sticks with known brands and familiar routines, avoiding category disruption "
            "unless a trusted source forces reconsideration."
        )
    else:
        coping_type = "optimism_bias"
        coping_text = (
            "Approaches new products with measured optimism, willing to trial based on "
            "packaging trust and first impressions before deep research."
        )

    # --- parenting_load ---
    time_scarce = cr.perceived_time_scarcity
    youngest = dm.youngest_child_age or min(dm.child_ages)
    n_children = dm.num_children
    if (
        time_scarce > 0.65
        and (youngest <= 4 or n_children >= 3)
        and cr.employment_status in ("full_time", "part_time")
    ):
        parenting_load = "high"
    elif time_scarce < 0.38 and n_children == 1 and youngest >= 7:
        parenting_load = "low"
    else:
        parenting_load = "medium"

    # --- child_need_orientation ---
    growth_signal = (hl.immunity_concern + hl.growth_concern) / 2
    comfort_signal = em.fear_appeal_responsiveness + val.guilt_driven_spending
    prev_signal = val.preventive_vs_reactive_health
    if growth_signal > 0.62:
        child_need_orientation = "growth_driven"
    elif comfort_signal > 1.2:
        child_need_orientation = "comfort_first"
    elif prev_signal > 0.62:
        child_need_orientation = "prevention_focused"
    else:
        child_need_orientation = "balanced"

    # --- consistency_score (heuristic from internal attribute coherence) ---
    coherence_signals = [
        1.0 - abs(ps.risk_tolerance - (1.0 - rt.budget_consciousness)),
        1.0 - abs(val.brand_loyalty_tendency - (1.0 - val.indie_brand_openness)),
        1.0 - abs(hl.medical_authority_trust - ps.authority_bias),
        1.0 - abs(rt.deal_seeking_intensity - rt.budget_consciousness),
        1.0 - abs(ps.social_proof_bias - rel.peer_influence_strength),
    ]
    raw_consistency = sum(coherence_signals) / len(coherence_signals)
    consistency_score = int(round(40 + raw_consistency * 60))  # maps [0,1] → [40,100]
    consistency_band = (
        "low" if consistency_score < 60 else ("high" if consistency_score >= 80 else "medium")
    )

    return ParentTraits(
        decision_style=decision_style,
        risk_appetite=risk_appetite,
        decision_confidence=decision_confidence,
        primary_value_orientation=primary_value_orientation,
        outcome_orientation=outcome_orientation,
        value_tradeoff_style=value_tradeoff_style,
        trust_anchor=trust_anchor,
        coping_mechanism_type=coping_type,
        coping_mechanism=coping_text,
        consistency_score=consistency_score,
        consistency_band=consistency_band,
        parenting_load=parenting_load,
        child_need_orientation=child_need_orientation,
    )


def _derive_budget_profile(persona: Persona) -> "BudgetProfile":  # noqa: F821
    """Derive concrete INR budget figures from income and psychographic attributes."""
    from src.taxonomy.schema import BudgetProfile

    annual_income_inr = persona.demographics.household_income_lpa * 100_000
    monthly_income = annual_income_inr / 12

    # Food spend fraction varies by income tier and city tier
    city_tier = persona.demographics.city_tier
    if city_tier == "Tier1":
        food_fraction = 0.22
    elif city_tier == "Tier2":
        food_fraction = 0.27
    else:
        food_fraction = 0.32

    monthly_food_budget_inr = max(1500, int(monthly_income * food_fraction))

    # Discretionary child nutrition budget: 18-28% of food budget
    disc_fraction = 0.18 + persona.values.best_for_my_child_intensity * 0.10
    discretionary_child_nutrition_budget_inr = max(
        300, int(monthly_food_budget_inr * disc_fraction)
    )

    # School fee pressure: higher for more children, lower income, and Tier1 costs
    n_children = persona.demographics.num_children
    income_ratio = min(1.0, annual_income_inr / 1_200_000)
    tier_multiplier = {"Tier1": 1.4, "Tier2": 1.0, "Tier3": 0.7}[city_tier]
    school_fee_pressure_factor = round(
        min(1.0, (n_children * 0.25 * tier_multiplier) / max(0.5, income_ratio)), 2
    )

    # Price sensitivity from budget_consciousness
    bc = persona.daily_routine.budget_consciousness
    price_sensitivity = "low" if bc < 0.38 else ("high" if bc > 0.62 else "medium")

    # Brand switch tolerance is inverse of brand loyalty
    bl = persona.values.brand_loyalty_tendency
    brand_switch_tolerance = "high" if bl < 0.38 else ("low" if bl > 0.62 else "medium")

    return BudgetProfile(
        monthly_food_budget_inr=monthly_food_budget_inr,
        discretionary_child_nutrition_budget_inr=discretionary_child_nutrition_budget_inr,
        school_fee_pressure_factor=school_fee_pressure_factor,
        price_sensitivity=price_sensitivity,
        brand_switch_tolerance=brand_switch_tolerance,
    )


def _derive_decision_rights(persona: Persona) -> "DecisionRights":  # noqa: F821
    """Derive per-domain purchase authority mapping from relationship attributes."""
    from src.taxonomy.schema import DecisionRights

    dm = persona.relationships.primary_decision_maker
    elder_weight = persona.relationships.elder_advice_weight
    med_trust = persona.health.medical_authority_trust
    partner = persona.relationships.partner_involvement

    # child_nutrition
    if dm == "elder" or elder_weight > 0.72:
        child_nutrition = "elder_veto"
    elif dm == "spouse":
        child_nutrition = "father_final"
    elif dm == "joint" or partner > 0.65:
        child_nutrition = "joint"
    else:
        child_nutrition = "mother_final"

    # grocery_shopping — primary caregiver almost always leads
    if dm == "joint" and partner > 0.60:
        grocery_shopping = "joint"
    elif elder_weight > 0.70:
        grocery_shopping = "household_elder"
    elif dm == "spouse":
        grocery_shopping = "father_lead"
    else:
        grocery_shopping = "mother_lead"

    # supplements — doctor-gated when high medical trust
    if med_trust > 0.68:
        supplements = "doctor_gated"
    elif dm == "joint":
        supplements = "joint"
    else:
        supplements = "mother_final"

    return DecisionRights(
        child_nutrition=child_nutrition,
        grocery_shopping=grocery_shopping,
        supplements=supplements,
    )


def _stable_variant_index(value: str, modulo: int) -> int:
    digest = hashlib.md5(value.encode("utf-8")).hexdigest()
    return int(digest, 16) % modulo


def _pronouns(persona: Persona) -> tuple[str, str, str]:
    gender = persona.demographics.parent_gender.lower()
    if gender == "male":
        return ("he", "him", "his")
    if gender == "female":
        return ("she", "her", "her")
    return ("they", "them", "their")


def _trait_phrase(field: str, value: float, subject: str, possessive: str) -> str:
    template_pair = _TRAIT_PHRASE_OVERRIDES.get(field)
    if template_pair is not None:
        template = template_pair[0] if value >= 0.5 else template_pair[1]
        return template.format(
            subject=subject,
            subject_cap=subject.capitalize(),
            possessive=possessive,
        )

    description = describe_attribute_value(field, value)
    if value >= 0.5:
        return f"{subject.capitalize()} shows {description} in day-to-day family decisions."
    return f"{subject.capitalize()} tends to operate with {description} rather than extremes."


def _top_trait_phrases(persona: Persona, limit: int = 5) -> list[str]:
    flat = persona.to_flat_dict()
    subject, _, possessive = _pronouns(persona)
    scored = sorted(
        (
            (field, float(value))
            for field, value in flat.items()
            if isinstance(value, float) and 0.0 <= value <= 1.0
        ),
        key=lambda item: abs(item[1] - 0.5),
        reverse=True,
    )
    return [_trait_phrase(field, value, subject, possessive) for field, value in scored[:limit]]


class FirstPersonSummary(BaseModel):
    """Structured output for the first-person diary-voice summary step."""

    summary: str


class PurchaseBullets(BaseModel):
    """Structured output for the purchase decision bullet generation step."""

    bullets: list[str] = Field(min_length=5, max_length=8)


class AnchorInference(BaseModel):
    """Structured output for the anchor inference step."""

    core_values: list[str] = Field(min_length=3, max_length=6)
    life_attitude: str
    parent_motivations: list[str] = Field(min_length=2, max_length=6)


class LifeStorySnippet(BaseModel):
    """One biographical event used in the full narrative."""

    title: str
    event: str
    impact: str


class LifeStoryResponse(BaseModel):
    """Structured output for the life story step."""

    stories: list[LifeStorySnippet] = Field(min_length=2, max_length=3)


class Tier2NarrativeGenerator:
    """
    Generates biographical narratives for Tier 2 personas.

    Pipeline: anchor attributes -> values -> life story -> full narrative.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    async def generate_narrative(self, persona: Persona) -> Persona:
        """
        Enrich a Tier 1 persona with a deep narrative and all derived insight layers.

        Pipeline (deterministic steps run first, LLM steps follow):
          1. Derive ParentTraits, BudgetProfile, DecisionRights  (no LLM)
          2. Anchor inference  (LLM)
          3. Life story        (LLM)
          4. Third-person narrative  (LLM)
          5. First-person summary    (LLM)
          6. Purchase bullets        (LLM)

        Args:
            persona: Base Tier 1 persona.

        Returns:
            A copied persona with ``tier="deep"`` and all enrichment fields populated.
        """

        # Step 1: deterministic derived fields (always, regardless of mock mode)
        parent_traits = _derive_parent_traits(persona)
        budget_profile = _derive_budget_profile(persona)
        decision_rights = _derive_decision_rights(persona)

        if self.llm.config.llm_mock_enabled:
            return self._generate_mock_narrative(
                persona, parent_traits, budget_profile, decision_rights
            )

        anchor_payload = self._build_anchor_payload(persona)
        anchor_response = await self.llm.generate(
            prompt=self._build_anchor_prompt(anchor_payload),
            model="bulk",
            response_format="json",
            schema=AnchorInference,
        )
        anchor = AnchorInference.model_validate_json(anchor_response.text)

        story_response = await self.llm.generate(
            prompt=self._build_life_story_prompt(anchor_payload, anchor),
            model="bulk",
            response_format="json",
            schema=LifeStoryResponse,
        )
        stories = LifeStoryResponse.model_validate_json(story_response.text)

        narrative_response = await self.llm.generate(
            prompt=self._build_narrative_prompt(persona, anchor, stories.stories),
            model="bulk",
            response_format="text",
        )
        narrative = narrative_response.text.strip()
        self._validate_narrative(persona, narrative)

        fp_response = await self.llm.generate(
            prompt=self._build_first_person_prompt(persona, anchor, parent_traits, budget_profile),
            model="bulk",
            response_format="json",
            schema=FirstPersonSummary,
        )
        first_person_summary = FirstPersonSummary.model_validate_json(fp_response.text).summary

        bullets_response = await self.llm.generate(
            prompt=self._build_bullets_prompt(persona, parent_traits, budget_profile),
            model="bulk",
            response_format="json",
            schema=PurchaseBullets,
        )
        purchase_decision_bullets = PurchaseBullets.model_validate_json(
            bullets_response.text
        ).bullets

        semantic_memory = dict(persona.semantic_memory)
        semantic_memory["tier2_anchor"] = anchor.model_dump(mode="json")
        semantic_memory["tier2_stories"] = stories.model_dump(mode="json")

        logger.info("tier2_narrative_generated", persona_id=persona.id)
        return persona.model_copy(
            update={
                "tier": "deep",
                "narrative": narrative,
                "first_person_summary": first_person_summary,
                "purchase_decision_bullets": purchase_decision_bullets,
                "parent_traits": parent_traits,
                "budget_profile": budget_profile,
                "decision_rights": decision_rights,
                "semantic_memory": semantic_memory,
            }
        )

    async def generate_batch(
        self, personas: list[Persona], max_concurrency: int = 5
    ) -> list[Persona]:
        """
        Generate narratives for multiple personas with concurrency control.

        Args:
            personas: Personas to enrich.
            max_concurrency: Maximum number of concurrent tasks.

        Returns:
            Deep personas in the same order as the input list.
        """

        semaphore = asyncio.Semaphore(max_concurrency)

        async def _generate(persona: Persona) -> Persona:
            async with semaphore:
                return await self.generate_narrative(persona)

        return await asyncio.gather(*(_generate(persona) for persona in personas))

    def _build_anchor_payload(self, persona: Persona) -> dict[str, Any]:
        flat = persona.to_flat_dict()
        core_demographics = {
            "city_tier": persona.demographics.city_tier,
            "city_name": persona.demographics.city_name,
            "region": persona.demographics.region,
            "parent_age": persona.demographics.parent_age,
            "num_children": persona.demographics.num_children,
            "child_ages": persona.demographics.child_ages,
            "family_structure": persona.demographics.family_structure,
            "household_income_lpa": persona.demographics.household_income_lpa,
            "education_level": persona.education_learning.education_level,
            "employment_status": persona.career.employment_status,
            "dietary_culture": persona.cultural.dietary_culture,
        }

        top_psychographics = sorted(
            (
                (key, value)
                for key, value in flat.items()
                if isinstance(value, float) and 0.0 <= value <= 1.0
            ),
            key=lambda item: abs(item[1] - 0.5),
            reverse=True,
        )[:5]

        return {
            "demographics": core_demographics,
            "top_psychographics": dict(top_psychographics),
        }

    def _build_anchor_prompt(self, anchor_payload: dict[str, Any]) -> str:
        serialized = json.dumps(anchor_payload, indent=2, sort_keys=True)
        return (
            "You are creating a detailed biographical profile for a synthetic person.\n"
            "Here are their core attributes:\n"
            f"{serialized}\n\n"
            "Based on these attributes, infer:\n"
            "1. Their core personal values (3-5 values)\n"
            "2. Their life attitude / worldview (2-3 sentences)\n"
            "3. Their primary motivations as a parent\n\n"
            "Return JSON with keys core_values, life_attitude, parent_motivations."
        )

    def _build_life_story_prompt(
        self, anchor_payload: dict[str, Any], anchor: AnchorInference
    ) -> str:
        serialized = json.dumps(
            {
                "anchor_attributes": anchor_payload,
                "inferred_values": anchor.model_dump(mode="json"),
            },
            indent=2,
            sort_keys=True,
        )
        return (
            "Given this person's profile and values:\n"
            f"{serialized}\n\n"
            "Generate 2-3 specific life story snippets that shaped who they are today.\n"
            "These should be concrete and consistent with their demographics and values.\n"
            "Include at least one story related to their parenting journey.\n\n"
            "Return JSON with a single key stories, whose value is an array of objects "
            "with title, event, and impact."
        )

    def _build_narrative_prompt(
        self,
        persona: Persona,
        anchor: AnchorInference,
        stories: list[LifeStorySnippet],
    ) -> str:
        payload = {
            "persona_attributes": persona.to_flat_dict(),
            "anchor": anchor.model_dump(mode="json"),
            "stories": [story.model_dump(mode="json") for story in stories],
        }
        serialized = json.dumps(payload, indent=2, sort_keys=True)
        return (
            "You are writing a third-person biographical narrative for this person:\n"
            f"{serialized}\n\n"
            "Write a 300-500 word narrative that:\n"
            "- Naturally incorporates demographics, values, and life stories\n"
            "- References at least 10 specific persona attributes\n"
            "- Describes their daily routine and parenting approach\n"
            "- Is coherent with all numeric attributes\n"
            "- Uses Hindi-English code-mixing where culturally appropriate\n"
            "- Avoids generic template phrasing\n\n"
            "Do not list attributes. Weave them into a flowing biography."
        )

    def _build_first_person_prompt(
        self,
        persona: Persona,
        anchor: AnchorInference,
        parent_traits: "ParentTraits",  # noqa: F821
        budget_profile: "BudgetProfile",  # noqa: F821
    ) -> str:
        payload = {
            "city": persona.demographics.city_name,
            "parent_age": persona.demographics.parent_age,
            "num_children": persona.demographics.num_children,
            "child_ages": persona.demographics.child_ages,
            "employment": persona.career.employment_status,
            "income_lpa": persona.demographics.household_income_lpa,
            "monthly_food_budget_inr": budget_profile.monthly_food_budget_inr,
            "dietary_culture": persona.cultural.dietary_culture,
            "breakfast_routine": persona.daily_routine.breakfast_routine,
            "shopping_platform": persona.daily_routine.primary_shopping_platform,
            "core_values": anchor.core_values,
            "life_attitude": anchor.life_attitude,
            "coping_mechanism": parent_traits.coping_mechanism,
            "trust_anchor": parent_traits.trust_anchor,
        }
        serialized = json.dumps(payload, indent=2)
        return (
            "Write a first-person diary-voice summary (120-150 words) for this Indian parent.\n"
            "The summary should:\n"
            "- Start with a vivid, specific morning scene from their home city\n"
            "- Naturally weave in their parenting style, daily food decisions, and budget reality\n"
            "- Use Hindi-English code-mixing where it feels authentic (not forced)\n"
            "- Read like an intimate self-description, not a résumé\n"
            "- Avoid listing attributes — make them lived, felt experiences\n\n"
            f"Profile data:\n{serialized}\n\n"
            "Return JSON with a single key 'summary' containing the first-person text."
        )

    def _build_bullets_prompt(
        self,
        persona: Persona,
        parent_traits: "ParentTraits",  # noqa: F821
        budget_profile: "BudgetProfile",  # noqa: F821
    ) -> str:
        payload = {
            "decision_style": parent_traits.decision_style,
            "trust_anchor": parent_traits.trust_anchor,
            "primary_value_orientation": parent_traits.primary_value_orientation,
            "value_tradeoff_style": parent_traits.value_tradeoff_style,
            "coping_mechanism": parent_traits.coping_mechanism,
            "monthly_food_budget_inr": budget_profile.monthly_food_budget_inr,
            "discretionary_nutrition_budget_inr": budget_profile.discretionary_child_nutrition_budget_inr,
            "price_sensitivity": budget_profile.price_sensitivity,
            "brand_switch_tolerance": budget_profile.brand_switch_tolerance,
            "school_fee_pressure": budget_profile.school_fee_pressure_factor,
            "child_ages": persona.demographics.child_ages,
            "child_nutrition_concerns": persona.health.child_nutrition_concerns,
            "child_dietary_restrictions": persona.health.child_dietary_restrictions,
            "comparison_anchor": "home_food",
            "shopping_platform": persona.daily_routine.primary_shopping_platform,
            "parenting_load": parent_traits.parenting_load,
        }
        serialized = json.dumps(payload, indent=2)
        return (
            "Generate 6-8 concise purchase-decision bullets for this Indian parent evaluating "
            "a new child nutrition product.\n"
            "Each bullet should:\n"
            "- Be one sentence (max 20 words)\n"
            "- Describe a specific, actionable behavioral driver or barrier\n"
            "- Be directly usable by a product manager or brand team\n"
            "- Cover: budget reality, trust mechanism, child acceptance barrier, "
            "comparison anchor, purchase occasion, validation source\n\n"
            f"Profile data:\n{serialized}\n\n"
            "Return JSON with a single key 'bullets' containing an array of strings."
        )

    def _validate_narrative(self, persona: Persona, narrative: str) -> None:
        candidates = {
            persona.demographics.city_name.lower(),
            persona.demographics.city_tier.lower(),
            persona.demographics.region.lower(),
            str(persona.demographics.parent_age),
            str(persona.demographics.num_children),
            persona.demographics.family_structure.lower(),
            persona.education_learning.education_level.lower(),
            persona.career.employment_status.lower(),
            persona.cultural.dietary_culture.lower(),
            persona.cultural.primary_language.lower(),
            persona.daily_routine.primary_shopping_platform.lower(),
            persona.daily_routine.breakfast_routine.lower(),
            persona.daily_routine.milk_supplement_current.lower(),
            persona.media.primary_social_platform.lower(),
            persona.lifestyle.parenting_philosophy.lower(),
        }
        candidates.update(str(age) for age in persona.demographics.child_ages)

        lowered = narrative.lower()
        hits = sum(1 for candidate in candidates if candidate and candidate in lowered)
        if hits < 10:
            logger.warning(
                "tier2_narrative_validation_low_references", persona_id=persona.id, hits=hits
            )

    def _generate_mock_narrative(
        self,
        persona: Persona,
        parent_traits: "ParentTraits | None" = None,  # noqa: F821
        budget_profile: "BudgetProfile | None" = None,  # noqa: F821
        decision_rights: "DecisionRights | None" = None,  # noqa: F821
    ) -> Persona:
        name = persona.display_name or persona.id
        subject, _, possessive = _pronouns(persona)
        subject_cap = subject.capitalize()
        ages = persona.demographics.child_ages
        child_ages = ", ".join(str(age) for age in ages)
        eldest_age = max(ages) if ages else persona.demographics.oldest_child_age
        household_income = round(persona.demographics.household_income_lpa)
        employment = persona.career.employment_status.replace("_", " ")
        family_structure = persona.demographics.family_structure.replace("_", " ")
        urbanity = persona.demographics.urban_vs_periurban.replace("_", " ")
        dietary_culture = persona.cultural.dietary_culture.replace("_", " ")
        shopping_platform = persona.daily_routine.primary_shopping_platform.replace("_", " ")
        breakfast_routine = persona.daily_routine.breakfast_routine.replace("_", " ")
        milk_routine = persona.daily_routine.milk_supplement_current.replace("_", " ")
        social_platform = persona.media.primary_social_platform.replace("_", " ")
        trait_phrases = _top_trait_phrases(persona)

        anchor = AnchorInference(
            core_values=["care", "practicality", "trust", "consistency"],
            life_attitude=(
                f"{name} tries to balance ambition with steadiness at home. "
                f"{subject_cap} prefers choices that feel trustworthy, practical, and sustainable."
            ),
            parent_motivations=["steady growth", "strong immunity", "less daily friction"],
        )
        stories = LifeStoryResponse(
            stories=[
                LifeStorySnippet(
                    title="Morning reset",
                    event=(
                        f"When {name}'s oldest child reached age {eldest_age}, {subject} rebuilt the "
                        "family's morning routine so breakfast could stay reliable even on rushed days."
                    ),
                    impact=(
                        "That stretch made planning, labels, and convenience feel just as important "
                        "as good intentions."
                    ),
                ),
                LifeStorySnippet(
                    title="Trust, then try",
                    event=(
                        f"A reassuring conversation with a pediatrician, mixed with chats from other "
                        f"parents, helped {name} shift from worry to steadier everyday habits."
                    ),
                    impact=(
                        f"{subject_cap} now blends research, trusted advice, and realistic routines "
                        "before making a purchase."
                    ),
                ),
            ]
        )
        openings = (
            (
                f"Every morning in {persona.demographics.city_name}, {name} begins the day by scanning "
                f"the kitchen, the school schedule, and the mood of the children before {subject} even "
                "thinks about work."
            ),
            (
                f"Growing up in {persona.demographics.region}, {name} learned early that family care is "
                "measured less by grand promises and more by what shows up on the table every day."
            ),
            (
                f"{name} believes that parenting is a long game built on consistency, calm judgment, "
                "and small routines that children can actually live with."
            ),
            (
                f"When {name}'s {eldest_age}-year-old entered a more demanding school routine, {subject} "
                "started rethinking everything from breakfast habits to what counted as a trustworthy buy."
            ),
            (
                f"In the {urbanity} neighborhoods around {persona.demographics.city_name}, {name} moves "
                "through a world of school chatter, delivery apps, family advice, and constant health talk."
            ),
        )
        opening = openings[_stable_variant_index(persona.id, len(openings))]

        paragraph_1 = (
            f"{opening} At {persona.demographics.parent_age}, {subject} is a {employment} parent in a "
            f"{family_structure} household, raising {persona.demographics.num_children} child"
            f"{'' if persona.demographics.num_children == 1 else 'ren'} aged {child_ages}. "
            f"With roughly {household_income} lakh in annual household income and a "
            f"{persona.education_learning.education_level} education, {name} has learned to hold ambition "
            f"and practicality in the same frame."
        )
        paragraph_2 = (
            f"Daily life runs on a {breakfast_routine} breakfast rhythm, familiar {dietary_culture} food, "
            f"and a shopping pattern that leans on {shopping_platform} when it saves time. "
            f"{subject_cap} keeps {milk_routine} in the family's routine, checks in on new ideas through "
            f"{social_platform}, and notices quickly when a product promises convenience without fitting "
            "real family habits."
        )
        paragraph_3 = " ".join(
            [
                f"As a parent, {name} comes across as warm but deliberate.",
                *trait_phrases[:3],
            ]
        )
        paragraph_4 = " ".join(
            [
                f"That is why {possessive} purchase style is careful rather than impulsive.",
                *trait_phrases[3:],
                f"{subject_cap} usually says yes only when trust, daily fit, and visible value all line up at once.",
            ]
        )
        narrative = "\n\n".join([paragraph_1, paragraph_2, paragraph_3, paragraph_4])
        self._validate_narrative(persona, narrative)

        # --- Mock first-person summary ---
        income_monthly = int(persona.demographics.household_income_lpa * 100_000 / 12)
        supplement_ref = (
            f"whether the {milk_routine} is running low"
            if milk_routine != "none"
            else "what's in the fridge for tomorrow's lunch"
        )
        fp_openings = (
            f"Every morning I wake up in {persona.demographics.city_name} before the rest of the house, "
            f"already thinking about what to pack for school and {supplement_ref}.",
            f"My day in {persona.demographics.city_name} starts with the kitchen — "
            f"I have a {eldest_age}-year-old to feed, a schedule to keep, and a budget that keeps me honest.",
            f"I am a {employment} parent of {persona.demographics.num_children} in {persona.demographics.city_name}. "
            f"Mornings are my planning window — food, school bags, maybe a quick scroll on {social_platform}.",
        )
        fp_opening = fp_openings[_stable_variant_index(persona.id, len(fp_openings))]

        # Derive budget if not passed
        bp = budget_profile or _derive_budget_profile(persona)
        pt = parent_traits or _derive_parent_traits(persona)
        dr = decision_rights or _derive_decision_rights(persona)

        first_person_summary = (
            f"{fp_opening} "
            f"Our household runs on roughly ₹{bp.monthly_food_budget_inr:,} a month for food — "
            f"I try not to go over, but when it comes to my child's nutrition I make exceptions. "
            f"I prefer {dietary_culture} food and mostly shop on {shopping_platform}. "
            f"New products have to earn my trust; I rely on {pt.trust_anchor.replace('_', ' ')} more than ads. "
            f"{pt.coping_mechanism}"
        )

        # --- Mock purchase bullets ---
        purchase_decision_bullets = [
            f"Monthly discretionary child nutrition budget is ₹{bp.discretionary_child_nutrition_budget_inr:,} — sets a hard ceiling on trial.",
            f"Trust anchor is '{pt.trust_anchor}' — product must clear this source before consideration.",
            f"Decision style is {pt.decision_style} — messaging should match this cognitive mode.",
            f"Primary value orientation is {pt.primary_value_orientation} — lead with this in copy.",
            f"Comparison anchor is home-cooked food — product must justify the switch from familiar.",
            f"Brand switch tolerance is {bp.brand_switch_tolerance} — {('open to trial' if bp.brand_switch_tolerance == 'high' else 'needs strong reason to switch')}.",
            f"School fee pressure factor {bp.school_fee_pressure_factor:.1f} — {'budget is stretched' if bp.school_fee_pressure_factor > 0.5 else 'some discretionary headroom available'}.",
            f"Coping mechanism: {pt.coping_mechanism_type.replace('_', ' ')} — align product habit formation with this pattern.",
        ]

        semantic_memory = dict(persona.semantic_memory)
        semantic_memory["tier2_anchor"] = anchor.model_dump(mode="json")
        semantic_memory["tier2_stories"] = stories.model_dump(mode="json")

        return persona.model_copy(
            update={
                "tier": "deep",
                "narrative": narrative,
                "first_person_summary": first_person_summary,
                "purchase_decision_bullets": purchase_decision_bullets,
                "parent_traits": pt,
                "budget_profile": bp,
                "decision_rights": dr,
                "semantic_memory": semantic_memory,
            }
        )
