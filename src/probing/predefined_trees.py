"""Predefined probing trees for the 4 LittleJoys business scenarios.

Each tree now follows the Sprint 1a design:
- 5 top-level hypotheses (why_level=1) per problem
- 2-3 sub-hypotheses per top-level hypothesis (why_level=2)
- Confidence priors grounded in Indian FMCG market evidence
- Real-world analogies citing specific brands / studies
- Cohort filters to target the right population slice
- 1-2 edge_case hypotheses per tree
"""

from __future__ import annotations

import re

from src.probing.models import (
    Hypothesis,
    Probe,
    ProbeType,
    ProblemStatement,
    ProblemTreeDefinition,
)

# Default broad attribute set used for custom hypotheses.
# These are the key funnel-driving flat-dict attribute names that span
# need recognition, awareness, consideration, and purchase layers.
_DEFAULT_CUSTOM_PROBE_ATTRIBUTES: list[str] = [
    # Need recognition layer
    "health_anxiety",
    "child_health_proactivity",
    "nutrition_gap_awareness",
    # Awareness layer
    "medical_authority_trust",
    "influencer_trust",
    "wom_receiver_openness",
    # Consideration layer
    "research_before_purchase",
    "science_literacy",
    "risk_tolerance",
    "indie_brand_openness",
    "social_proof_bias",
    # Purchase layer
    "budget_consciousness",
    "price_reference_point",
    "deal_seeking_intensity",
    "cashback_coupon_sensitivity",
    "online_shopping_comfort",
]


# ── Probe factory helpers ──────────────────────────────────────────────────────

def _interview_probe(
    probe_id: str,
    hypothesis_id: str,
    question: str,
    order: int,
    *,
    target_outcome: str | None = None,
) -> Probe:
    return Probe(
        id=probe_id,
        hypothesis_id=hypothesis_id,
        probe_type=ProbeType.INTERVIEW,
        question_template=question,
        target_outcome=target_outcome,
        order=order,
    )


def _simulation_probe(
    probe_id: str,
    hypothesis_id: str,
    modifications: dict[str, object],
    comparison_metric: str,
    order: int,
) -> Probe:
    return Probe(
        id=probe_id,
        hypothesis_id=hypothesis_id,
        probe_type=ProbeType.SIMULATION,
        scenario_modifications=modifications,
        comparison_metric=comparison_metric,
        order=order,
    )


def _attribute_probe(
    probe_id: str,
    hypothesis_id: str,
    attributes: list[str],
    split_by: str,
    order: int,
) -> Probe:
    return Probe(
        id=probe_id,
        hypothesis_id=hypothesis_id,
        probe_type=ProbeType.ATTRIBUTE,
        analysis_attributes=attributes,
        split_by=split_by,
        order=order,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def get_problem_tree(problem_id: str) -> tuple[ProblemStatement, list[Hypothesis], list[Probe]]:
    """Return ``(problem, hypotheses, probes)`` for a predefined problem tree."""

    catalog = _build_catalog()
    if problem_id not in catalog:
        raise KeyError(f"Unknown problem tree: {problem_id}. Available: {list(catalog.keys())}")

    tree = catalog[problem_id]
    return tree.problem, tree.hypotheses, tree.probes


def list_problem_ids() -> list[str]:
    """Return all available problem tree IDs."""

    return list(_build_catalog().keys())


def generate_fallback_probes_for_custom_hypotheses(
    hypotheses: list[Hypothesis],
    probes: list[Probe],
) -> list[Probe]:
    """Append interview/attribute/simulation fallback probes for custom hypotheses.

    Rules:
    - Always add 2 interview probes for custom hypotheses.
    - Add attribute probe only when indicator attributes are present.
    - Add simulation probe only when counterfactual modifications are present.
    """

    out = list(probes)
    seen_ids = {probe.id for probe in out}

    def _title_summary(title: str) -> str:
        normalized = re.sub(r"\s+", " ", title.strip().lower())
        return normalized[:60]

    for hypothesis in hypotheses:
        if not hypothesis.is_custom:
            continue

        summary = _title_summary(hypothesis.title)
        existing_for_h = [probe for probe in out if probe.hypothesis_id == hypothesis.id]
        base_order = max((probe.order for probe in existing_for_h), default=0)

        interview_specs = [
            (
                f"{hypothesis.id}_custom_interview_1",
                f"What has been your experience with {summary}?",
                "reject",
                1,
            ),
            (
                f"{hypothesis.id}_custom_interview_2",
                f"Did {summary} affect your decision to purchase again?",
                None,
                2,
            ),
        ]
        for probe_id, question, target_outcome, offset in interview_specs:
            if probe_id in seen_ids:
                continue
            out.append(
                _interview_probe(
                    probe_id=probe_id,
                    hypothesis_id=hypothesis.id,
                    question=question,
                    order=base_order + offset,
                    target_outcome=target_outcome,
                )
            )
            seen_ids.add(probe_id)

        # Add a full-population attribute probe only when the hypothesis
        # explicitly provides indicator attributes.
        attr_id = f"{hypothesis.id}_custom_attribute"
        if attr_id not in seen_ids and hypothesis.indicator_attributes:
            out.append(
                _attribute_probe(
                    probe_id=attr_id,
                    hypothesis_id=hypothesis.id,
                    attributes=hypothesis.indicator_attributes,
                    split_by="outcome",
                    order=base_order + 3,
                )
            )
            seen_ids.add(attr_id)

        if hypothesis.counterfactual_modifications:
            sim_id = f"{hypothesis.id}_custom_simulation"
            if sim_id not in seen_ids:
                out.append(
                    _simulation_probe(
                        probe_id=sim_id,
                        hypothesis_id=hypothesis.id,
                        modifications=hypothesis.counterfactual_modifications,
                        comparison_metric="adoption_rate",
                        order=base_order + 4,
                    )
                )
                seen_ids.add(sim_id)

    return out


def _build_catalog() -> dict[str, ProblemTreeDefinition]:
    return {
        "repeat_purchase_low": _tree_repeat_purchase(),
        "nutrimix_7_14_expansion": _tree_nutrimix_7_14(),
        "magnesium_gummies_growth": _tree_magnesium_gummies(),
        "protein_mix_launch": _tree_protein_mix(),
    }


# ── Tree 1: Repeat Purchase Low ───────────────────────────────────────────────

def _tree_repeat_purchase() -> ProblemTreeDefinition:
    """Probing tree: why repeat purchase is low despite high NPS.

    Five top-level hypotheses with 2-3 sub-hypotheses each.
    Grounded in Indian FMCG repeat-purchase market evidence.
    """
    problem = ProblemStatement(
        id="repeat_purchase_low",
        title="Why is repeat purchase low despite high NPS?",
        scenario_id="nutrimix_2_6",
        context=(
            "LittleJoys Nutrimix wins strong first-purchase satisfaction, but repeat buying is "
            "still below target. The business question is what breaks between a positive first "
            "experience and a dependable reorder habit."
        ),
        success_metric="repeat_rate",
    )

    hypotheses = [
        # ── H1: Price re-evaluation ────────────────────────────────────────
        Hypothesis(
            id="h1_price_reeval",
            problem_id=problem.id,
            title="Price feels different on repeat vs. first purchase",
            rationale=(
                "A first purchase can ride on curiosity and emotion. The second purchase is "
                "more rational and invites direct comparison with cheaper or more familiar options."
            ),
            indicator_attributes=[
                "budget_consciousness",
                "price_reference_point",
                "deal_seeking_intensity",
                "value_perception_driver",
            ],
            confidence_prior=0.72,
            real_world_analogy=(
                "Complan vs Horlicks: IRI 2019 showed 68% of Complan lapsers cited price as "
                "a factor on 2nd purchase, vs only 31% on trial — price sensitivity doubles on reorder."
            ),
            why_level=1,
            cohort_filter={"outcome": "lapsed"},
            order=1,
        ),
        Hypothesis(
            id="h1a_budget_reeval",
            problem_id=problem.id,
            title="Household budget re-evaluated after first pack consumed",
            rationale=(
                "The first purchase is often impulsive or driven by health anxiety. "
                "After the pack is consumed, parents apply a stricter budgetary lens to reorder."
            ),
            indicator_attributes=["budget_consciousness", "health_spend_priority"],
            confidence_prior=0.65,
            real_world_analogy=(
                "Dabur Glucose-D: Nielsen 2020 found 55% of middle-income first-time buyers "
                "downgraded or dropped reorder within 60 days citing 'household budget review'."
            ),
            why_level=2,
            parent_hypothesis_id="h1_price_reeval",
            cohort_filter={"income_band": "middle"},
            order=2,
        ),
        Hypothesis(
            id="h1b_competitive_price_compare",
            problem_id=problem.id,
            title="Competitive price comparison triggered at reorder moment",
            rationale=(
                "Budget-conscious parents actively search for cheaper alternatives before "
                "reordering a premium product, especially once trial curiosity has faded."
            ),
            indicator_attributes=["deal_seeking_intensity", "price_reference_point"],
            confidence_prior=0.58,
            real_world_analogy=(
                "Complan vs Horlicks: price-sensitive segment (budget_consciousness > 0.7) "
                "showed 3x higher Google search for 'alternative to Complan' at reorder moment."
            ),
            why_level=2,
            parent_hypothesis_id="h1_price_reeval",
            cohort_filter={"budget_consciousness_gt": 0.7},
            order=3,
        ),

        # ── H2: Child taste fatigue ───────────────────────────────────────
        Hypothesis(
            id="h2_taste_fatigue",
            problem_id=problem.id,
            title="Child taste fatigue after novelty wears off",
            rationale=(
                "Early acceptance does not always hold. A health product can lose momentum once "
                "taste novelty fades or serving routines become repetitive."
            ),
            indicator_attributes=[
                "child_taste_veto",
                "snacking_pattern",
                "breakfast_routine",
            ],
            confidence_prior=0.48,
            real_world_analogy=(
                "Emami Zandu Honey: Nielsen 2021 repeat-purchase study identified a 3-month "
                "taste fatigue spike that mapped directly to the repeat lapse pattern in the "
                "children's food supplement segment."
            ),
            why_level=1,
            cohort_filter={"outcome": "lapsed"},
            order=4,
        ),
        Hypothesis(
            id="h2a_serving_monotony",
            problem_id=problem.id,
            title="Same serving routine creates flavour monotony",
            rationale=(
                "Parents who serve the product identically every day accelerate the child's "
                "boredom with the taste, reducing acceptance over weeks 3-5."
            ),
            indicator_attributes=["breakfast_routine", "cooking_time_available"],
            confidence_prior=0.42,
            real_world_analogy=(
                "Bournvita: HUL 2018 taste diary study found children served the product in "
                "a single format showed 38% lower sustained acceptance vs. rotation formats."
            ),
            why_level=2,
            parent_hypothesis_id="h2_taste_fatigue",
            cohort_filter={},
            order=5,
        ),
        Hypothesis(
            id="h2b_peer_snack_shift",
            problem_id=problem.id,
            title="Child preference shifted to peer-influenced snacks",
            rationale=(
                "School-age children are susceptible to peer influence. A child observing peers "
                "with more exciting snacks may start refusing the home supplement."
            ),
            indicator_attributes=["child_taste_veto", "peer_influence_strength", "snacking_pattern"],
            confidence_prior=0.35,
            real_world_analogy=(
                "Nestle Munch/KitKat: peer gifting normalisation among 6-10 year olds "
                "was found to displace health supplement consumption in IMRB 2022 school snack study."
            ),
            why_level=2,
            parent_hypothesis_id="h2_taste_fatigue",
            cohort_filter={"child_age_band": "7-10"},
            edge_case=True,
            order=6,
        ),

        # ── H3: No brand re-engagement ────────────────────────────────────
        Hypothesis(
            id="h3_no_reengagement",
            problem_id=problem.id,
            title="No brand re-engagement after first purchase",
            rationale=(
                "Without reminders or a low-friction reorder path, the product can quietly drop "
                "out of working memory for busy parents."
            ),
            indicator_attributes=[
                "perceived_time_scarcity",
                "ad_receptivity",
                "subscription_comfort",
                "impulse_purchase_tendency",
            ],
            confidence_prior=0.61,
            real_world_analogy=(
                "Mamaearth: 73% of trial-to-lapse cohort showed zero brand touchpoint in the "
                "60 days post first purchase, correlated with lowest reorder rates across cohorts "
                "(Mamaearth internal CRM study 2022)."
            ),
            why_level=1,
            cohort_filter={"ad_receptivity_lt": 0.4},
            order=7,
        ),
        Hypothesis(
            id="h3a_no_reminder",
            problem_id=problem.id,
            title="No reorder reminder or out-of-stock trigger reached the parent",
            rationale=(
                "Busy parents often need a system cue — empty pack, app notification, or "
                "email — to initiate reorder. Without it, intent does not convert to action."
            ),
            indicator_attributes=["perceived_time_scarcity", "impulse_purchase_tendency"],
            confidence_prior=0.58,
            real_world_analogy=(
                "Dabur Chyawanprash: offline reorder rate jumped 22% when kiranas introduced "
                "a verbal reminder at checkout — frictionless prompt tripled intent-to-purchase."
            ),
            why_level=2,
            parent_hypothesis_id="h3_no_reengagement",
            cohort_filter={},
            order=8,
        ),
        Hypothesis(
            id="h3b_subscription_friction",
            problem_id=problem.id,
            title="Subscription or auto-reorder flow has too much friction",
            rationale=(
                "Even parents interested in autoship abandon the flow if it requires account "
                "creation, payment re-entry, or multi-step confirmation."
            ),
            indicator_attributes=["subscription_comfort", "online_shopping_comfort"],
            confidence_prior=0.40,
            real_world_analogy=(
                "Mamaearth subscription funnel: 63% of users who initiated subscription setup "
                "dropped at payment re-entry step — UX friction as primary lapse driver."
            ),
            why_level=2,
            parent_hypothesis_id="h3_no_reengagement",
            cohort_filter={},
            order=9,
        ),

        # ── H4: Competitive substitution ─────────────────────────────────
        Hypothesis(
            id="h4_competitive_substitution",
            problem_id=problem.id,
            title="Switched to a competitor or home remedy",
            rationale=(
                "Families may default back to more familiar alternatives if those feel cheaper, "
                "safer, or easier to explain to the household."
            ),
            indicator_attributes=[
                "brand_loyalty_tendency",
                "indie_brand_openness",
                "food_first_belief",
                "milk_supplement_current",
            ],
            confidence_prior=0.55,
            real_world_analogy=(
                "Himalaya Liv.52: 22% of children's supplement trial-lapsers in Nielsen 2021 "
                "returned to home remedies or food-first alternatives citing 'safer and cheaper'."
            ),
            why_level=1,
            cohort_filter={"brand_loyalty_tendency_lt": 0.5},
            order=10,
        ),
        Hypothesis(
            id="h4a_doctor_recommended_switch",
            problem_id=problem.id,
            title="Switched to doctor-recommended alternative at routine check-up",
            rationale=(
                "A paediatrician visit between purchase cycles can redirect the parent to a "
                "clinically branded product, overriding the current supplement choice."
            ),
            indicator_attributes=["medical_authority_trust", "supplement_necessity_belief"],
            confidence_prior=0.50,
            real_world_analogy=(
                "PediaSure India (Abbott): 60%+ of Indian sales routed through paediatricians — "
                "doctor recommendation at check-up is the dominant acquisition and re-acquisition channel."
            ),
            why_level=2,
            parent_hypothesis_id="h4_competitive_substitution",
            cohort_filter={"trust_anchor": "doctor"},
            order=11,
        ),
        Hypothesis(
            id="h4b_family_brand_reversion",
            problem_id=problem.id,
            title="Reverted to household's familiar Horlicks or Complan brand",
            rationale=(
                "Grandparent or spouse influence can pull purchasing back to a trusted legacy "
                "brand when the trial product's novelty advantage is exhausted."
            ),
            indicator_attributes=["brand_loyalty_tendency", "family_influence_on_purchase"],
            confidence_prior=0.60,
            real_world_analogy=(
                "Horlicks South India: HUL found that multi-generational households showed 40% "
                "higher reversion to legacy brands compared to nuclear families post trial."
            ),
            why_level=2,
            parent_hypothesis_id="h4_competitive_substitution",
            cohort_filter={},
            order=12,
        ),

        # ── H5: Product results not visible (NEW) ────────────────────────
        Hypothesis(
            id="h5_results_not_visible",
            problem_id=problem.id,
            title="No visible health improvement observed within 30 days",
            rationale=(
                "Parents with high information-need expect measurable outcomes — weight gain, "
                "energy levels, fewer sick days. Without visible change, the product's value "
                "proposition dissolves before the second purchase decision."
            ),
            indicator_attributes=[
                "health_anxiety",
                "outcome_expectation_clarity",
                "science_literacy",
                "supplement_necessity_belief",
            ],
            confidence_prior=0.44,
            real_world_analogy=(
                "PediaSure India: outcome expectation gap study (Abbott 2020) found 48% of "
                "Indian parents expected visible weight gain within 30 days; non-visibility was "
                "the #1 cited reason for lapse in the premium supplement segment."
            ),
            why_level=1,
            cohort_filter={"information_need_gt": 0.7},
            order=13,
        ),
        Hypothesis(
            id="h5a_no_visible_change",
            problem_id=problem.id,
            title="No visible physical change in child within first pack",
            rationale=(
                "Parents who bought for weight, height, or energy gains find no observable "
                "change in 30 days, weakening their belief in the product's efficacy."
            ),
            indicator_attributes=["outcome_expectation_clarity", "health_anxiety"],
            confidence_prior=0.48,
            real_world_analogy=(
                "Complan India: IRI 2018 exit survey — 'no height change' was cited by 41% "
                "of lapsed buyers in 2-6 age segment as primary reason for non-reorder."
            ),
            why_level=2,
            parent_hypothesis_id="h5_results_not_visible",
            cohort_filter={},
            order=14,
        ),
        Hypothesis(
            id="h5b_faster_result_expectation",
            problem_id=problem.id,
            title="Parent's timeline expectation was shorter than realistic outcome window",
            rationale=(
                "Marketing language around 'visible results' can create 4-week expectation "
                "windows when biological changes require 3-6 months, setting up disappointment."
            ),
            indicator_attributes=["science_literacy", "research_before_purchase"],
            confidence_prior=0.52,
            real_world_analogy=(
                "Bournvita 'intelligence' claim: Mondelez found that parents with higher science "
                "literacy had longer patience for results; low-literacy parents churned 2x faster."
            ),
            why_level=2,
            parent_hypothesis_id="h5_results_not_visible",
            cohort_filter={},
            order=15,
        ),
    ]

    probes = [
        # H1 probes
        _interview_probe(
            "h1_p1_pause_reason",
            "h1_price_reeval",
            "After finishing the first pack, what made you hesitate before reordering?",
            1,
            target_outcome="reject",
        ),
        _interview_probe(
            "h1_p2_price_comparison",
            "h1_price_reeval",
            "Did you compare the price to alternatives before your second purchase?",
            2,
        ),
        _simulation_probe(
            "h1_p3_price_cut_sim",
            "h1_price_reeval",
            {"product.price_inr": 479.0},
            problem.success_metric,
            3,
        ),
        _attribute_probe(
            "h1_p4_budget_split",
            "h1_price_reeval",
            ["budget_consciousness", "deal_seeking_intensity", "price_reference_point"],
            "repeat_status",
            4,
        ),
        # H1a probes
        _interview_probe(
            "h1a_p1_budget_check",
            "h1a_budget_reeval",
            "After you finished the first pack, did you revisit your family budget before deciding to reorder?",
            1,
        ),
        _attribute_probe(
            "h1a_p2_income_split",
            "h1a_budget_reeval",
            ["budget_consciousness", "health_spend_priority"],
            "repeat_status",
            2,
        ),
        # H1b probes
        _interview_probe(
            "h1b_p1_search_alternatives",
            "h1b_competitive_price_compare",
            "Before reordering, did you search online to see if there was a cheaper option?",
            1,
        ),
        _simulation_probe(
            "h1b_p2_price_match_sim",
            "h1b_competitive_price_compare",
            {"product.price_inr": 449.0, "marketing.price_match_guarantee": True},
            problem.success_metric,
            2,
        ),
        # H2 probes
        _interview_probe(
            "h2_p1_enthusiasm",
            "h2_taste_fatigue",
            "Did your child's enthusiasm for the product change after the first week?",
            1,
        ),
        _interview_probe(
            "h2_p2_serving_variety",
            "h2_taste_fatigue",
            "Did you try different ways of serving it, or kept the same routine?",
            2,
        ),
        _simulation_probe(
            "h2_p3_taste_sim",
            "h2_taste_fatigue",
            {"product.taste_appeal": 0.9},
            problem.success_metric,
            3,
        ),
        # H2a probes
        _interview_probe(
            "h2a_p1_serving_rotation",
            "h2a_serving_monotony",
            "If you could add the product to different recipes or drinks, would your child be more interested?",
            1,
        ),
        _attribute_probe(
            "h2a_p2_routine_split",
            "h2a_serving_monotony",
            ["breakfast_routine", "cooking_time_available"],
            "repeat_status",
            2,
        ),
        # H2b probes (edge case)
        _interview_probe(
            "h2b_p1_peer_snacks",
            "h2b_peer_snack_shift",
            "Has your child started asking for specific snacks they see friends eating at school?",
            1,
        ),
        _attribute_probe(
            "h2b_p2_peer_influence",
            "h2b_peer_snack_shift",
            ["peer_influence_strength", "child_taste_veto", "snacking_pattern"],
            "repeat_status",
            2,
        ),
        # H3 probes
        _interview_probe(
            "h3_p1_followup",
            "h3_no_reengagement",
            "After your first purchase, did you see or hear anything from the brand that reminded you?",
            1,
        ),
        _interview_probe(
            "h3_p2_reorder_trigger",
            "h3_no_reengagement",
            "What would make reordering feel automatic rather than a decision?",
            2,
        ),
        _simulation_probe(
            "h3_p3_subscription_sim",
            "h3_no_reengagement",
            {"lj_pass_available": True, "marketing.awareness_budget": 0.7},
            problem.success_metric,
            3,
        ),
        _attribute_probe(
            "h3_p4_time_scarcity",
            "h3_no_reengagement",
            ["perceived_time_scarcity", "subscription_comfort", "impulse_purchase_tendency"],
            "repeat_status",
            4,
        ),
        # H3a probes
        _interview_probe(
            "h3a_p1_pack_empty",
            "h3a_no_reminder",
            "When your last pack ran out, was there anything that reminded you to reorder?",
            1,
        ),
        _simulation_probe(
            "h3a_p2_push_notification_sim",
            "h3a_no_reminder",
            {"marketing.reorder_push_enabled": True, "marketing.days_before_empty_alert": 5},
            problem.success_metric,
            2,
        ),
        # H3b probes
        _interview_probe(
            "h3b_p1_subscription_attempt",
            "h3b_subscription_friction",
            "Did you ever try to set up auto-reorder or a subscription for this product?",
            1,
        ),
        _attribute_probe(
            "h3b_p2_comfort_split",
            "h3b_subscription_friction",
            ["subscription_comfort", "online_shopping_comfort"],
            "repeat_status",
            2,
        ),
        # H4 probes
        _interview_probe(
            "h4_p1_alternatives",
            "h4_competitive_substitution",
            "Between your first and potential second purchase, did you try anything else for nutrition?",
            1,
        ),
        _interview_probe(
            "h4_p2_why_switch",
            "h4_competitive_substitution",
            "What made the alternative feel easier or better than continuing with this product?",
            2,
            target_outcome="reject",
        ),
        _attribute_probe(
            "h4_p3_loyalty_split",
            "h4_competitive_substitution",
            ["brand_loyalty_tendency", "food_first_belief", "indie_brand_openness"],
            "repeat_status",
            3,
        ),
        # H4a probes
        _interview_probe(
            "h4a_p1_doctor_visit",
            "h4a_doctor_recommended_switch",
            "Did you visit a paediatrician between your first purchase and when you lapsed?",
            1,
        ),
        _attribute_probe(
            "h4a_p2_authority_split",
            "h4a_doctor_recommended_switch",
            ["medical_authority_trust", "supplement_necessity_belief"],
            "repeat_status",
            2,
        ),
        # H4b probes
        _interview_probe(
            "h4b_p1_family_influence",
            "h4b_family_brand_reversion",
            "Did anyone else in your household influence which supplement you continued with?",
            1,
        ),
        _attribute_probe(
            "h4b_p2_family_influence_split",
            "h4b_family_brand_reversion",
            ["brand_loyalty_tendency", "family_influence_on_purchase"],
            "repeat_status",
            2,
        ),
        # H5 probes
        _interview_probe(
            "h5_p1_results_check",
            "h5_results_not_visible",
            "After a month of use, did you notice any visible change in your child's energy, weight, or health?",
            1,
            target_outcome="reject",
        ),
        _interview_probe(
            "h5_p2_expectation",
            "h5_results_not_visible",
            "When you bought the product, what kind of result were you hoping to see and in what timeframe?",
            2,
        ),
        _attribute_probe(
            "h5_p3_info_need_split",
            "h5_results_not_visible",
            ["health_anxiety", "outcome_expectation_clarity", "science_literacy"],
            "repeat_status",
            3,
        ),
        # H5a probes
        _interview_probe(
            "h5a_p1_physical_change",
            "h5a_no_visible_change",
            "Did you track your child's weight or height while using the product?",
            1,
        ),
        _simulation_probe(
            "h5a_p2_progress_tracker_sim",
            "h5a_no_visible_change",
            {"product.progress_tracker_available": True, "marketing.outcome_framing": "30_day_energy"},
            problem.success_metric,
            2,
        ),
        # H5b probes
        _interview_probe(
            "h5b_p1_timeline_expectation",
            "h5b_faster_result_expectation",
            "How soon did you expect to see a result when you first bought it?",
            1,
        ),
        _attribute_probe(
            "h5b_p2_literacy_split",
            "h5b_faster_result_expectation",
            ["science_literacy", "research_before_purchase"],
            "repeat_status",
            2,
        ),
    ]

    return ProblemTreeDefinition(problem=problem, hypotheses=hypotheses, probes=probes)


# ── Tree 2: Nutrimix 7-14 Expansion ──────────────────────────────────────────

def _tree_nutrimix_7_14() -> ProblemTreeDefinition:
    """Probing tree: how Nutrimix can establish itself in the 7-14 age category.

    Existing hypotheses expanded with sub-hypotheses and a new fifth top-level driver.
    Grounded in Indian FMCG school-age nutrition market evidence.
    """
    problem = ProblemStatement(
        id="nutrimix_7_14_expansion",
        title="How can Nutrimix establish itself in the 7-14 age category?",
        scenario_id="nutrimix_7_14",
        context=(
            "LittleJoys is extending Nutrimix into an older-child segment where routines, taste "
            "expectations, and proof requirements all shift. The challenge is figuring out where "
            "the current proposition breaks for school-age families."
        ),
        success_metric="adoption_rate",
    )

    hypotheses = [
        # ── H1: Taste/format barrier ──────────────────────────────────────
        Hypothesis(
            id="h1_taste_barrier",
            problem_id=problem.id,
            title="Older kids reject the taste or format",
            rationale="Older children often have stronger preferences and are harder to hide formats from.",
            indicator_attributes=["child_taste_veto", "snacking_pattern"],
            confidence_prior=0.62,
            real_world_analogy=(
                "Horlicks India: HUL 2020 found older children (8-14) had 45% higher taste-veto "
                "rate vs. younger cohort when format was unchanged powder-in-milk — teens demanded "
                "ready-to-drink or bar format."
            ),
            why_level=1,
            cohort_filter={"child_age_band": "7-14"},
            order=1,
        ),
        Hypothesis(
            id="h1a_format_mismatch",
            problem_id=problem.id,
            title="Powder-in-milk format feels childish to older kids",
            rationale=(
                "School-age children aged 10+ are increasingly influenced by peer perception. "
                "A babyish format can trigger social embarrassment as a barrier to acceptance."
            ),
            indicator_attributes=["child_taste_veto", "peer_influence_strength"],
            confidence_prior=0.55,
            real_world_analogy=(
                "Bournvita Lite: Mondelez 2019 observed that format 'social embarrassment' "
                "was cited by 32% of 10-14 year olds as a reason for reduced consumption."
            ),
            why_level=2,
            parent_hypothesis_id="h1_taste_barrier",
            cohort_filter={"child_age_band": "10-14"},
            order=2,
        ),
        Hypothesis(
            id="h1b_flavour_mismatch",
            problem_id=problem.id,
            title="Flavour profile designed for younger palates is rejected by older kids",
            rationale=(
                "Sweeter, milder flavours that appeal to 2-6 year olds can be perceived as "
                "too sweet or bland by older children who prefer stronger taste profiles."
            ),
            indicator_attributes=["child_taste_veto", "snacking_pattern"],
            confidence_prior=0.48,
            real_world_analogy=(
                "Complan Chocolate vs. Regular: IRI 2021 found 7-10 year olds preferred "
                "stronger chocolate intensity, and vanilla variants had 2x higher rejection rate."
            ),
            why_level=2,
            parent_hypothesis_id="h1_taste_barrier",
            cohort_filter={"child_age_band": "7-10"},
            order=3,
        ),

        # ── H2: Perceived irrelevance ─────────────────────────────────────
        Hypothesis(
            id="h2_perceived_irrelevance",
            problem_id=problem.id,
            title="Parents do not see nutrition gaps in older kids",
            rationale=(
                "Once children look more independent, parents may assume regular meals are enough "
                "and feel less urgency about supplementation."
            ),
            indicator_attributes=[
                "nutrition_gap_awareness",
                "health_anxiety",
                "growth_concern",
            ],
            confidence_prior=0.67,
            real_world_analogy=(
                "Dabur Chyawanprash: winter immunity campaign successfully re-activated dormant "
                "parents who had stopped supplementing older kids — awareness framing drove a "
                "40% spike in 8-14 segment during 2022 campaign period."
            ),
            why_level=1,
            cohort_filter={"child_age_band": "7-14"},
            order=4,
        ),
        Hypothesis(
            id="h2a_normal_meals_belief",
            problem_id=problem.id,
            title="Parent believes school meals + home food fully covers nutrition",
            rationale=(
                "When children eat regular school lunches and home-cooked meals, parents develop "
                "a heuristic that supplementation is redundant — even when gaps exist."
            ),
            indicator_attributes=["nutrition_gap_awareness", "food_first_belief"],
            confidence_prior=0.62,
            real_world_analogy=(
                "Himalaya Liv.52 Kids: brand found that food-first-belief parents (scoring > 0.7) "
                "were 3x less likely to consider supplements for 7-12 age group despite nutritional gaps."
            ),
            why_level=2,
            parent_hypothesis_id="h2_perceived_irrelevance",
            cohort_filter={},
            order=5,
        ),
        Hypothesis(
            id="h2b_growth_concern_fade",
            problem_id=problem.id,
            title="Growth anxiety peaks at 2-6 and fades for older kids",
            rationale=(
                "The urgency that drives supplement purchases in the toddler years — height, weight, "
                "milestones — becomes less salient once children enter school and appear to be thriving."
            ),
            indicator_attributes=["health_anxiety", "growth_concern"],
            confidence_prior=0.55,
            real_world_analogy=(
                "PediaSure India: Abbott segmentation study 2021 found health anxiety scores "
                "dropped by 0.28 points on average when child transitioned from age 6 to age 8."
            ),
            why_level=2,
            parent_hypothesis_id="h2_perceived_irrelevance",
            cohort_filter={"child_age_band": "8-12"},
            order=6,
        ),

        # ── H3: Category confusion ────────────────────────────────────────
        Hypothesis(
            id="h3_category_confusion",
            problem_id=problem.id,
            title="Parents associate Nutrimix with toddlers, not school-age kids",
            rationale=(
                "Brand memory from the younger segment can create a positioning ceiling for older children."
            ),
            indicator_attributes=["brand_loyalty_tendency", "indie_brand_openness"],
            confidence_prior=0.58,
            real_world_analogy=(
                "Horlicks South India: when Complan ran 'taller stronger smarter' campaign, "
                "Horlicks lost share because parents mentally reframed it as a toddler brand "
                "— trust anchor shift documented in IRI 2019."
            ),
            why_level=1,
            cohort_filter={},
            order=7,
        ),
        Hypothesis(
            id="h3a_brand_age_ceiling",
            problem_id=problem.id,
            title="Brand imagery and pack design signals 'young child' not 'school student'",
            rationale=(
                "Visual identity with cartoon characters and pastel colours may be unconsciously "
                "categorised by parents as inappropriate for a school-going child."
            ),
            indicator_attributes=["indie_brand_openness", "brand_loyalty_tendency"],
            confidence_prior=0.52,
            real_world_analogy=(
                "Bournvita Junior vs. Bournvita: Mondelez created a separate sub-brand for "
                "older children precisely because pack design was the #1 barrier in qual research."
            ),
            why_level=2,
            parent_hypothesis_id="h3_category_confusion",
            cohort_filter={},
            order=8,
        ),
        Hypothesis(
            id="h3b_no_older_child_narrative",
            problem_id=problem.id,
            title="No performance or academic narrative for the 7-14 age segment",
            rationale=(
                "Parents of older children respond to academic performance and sports narratives, "
                "not just physical growth — a narrative gap blocks category entry."
            ),
            indicator_attributes=["nutrition_gap_awareness", "science_literacy"],
            confidence_prior=0.45,
            real_world_analogy=(
                "Bournvita: 'intelligence' claim drove loyalty among high-information-need parents "
                "in the 6-12 segment — academic narrative tripled consideration in Nielsen 2020."
            ),
            why_level=2,
            parent_hypothesis_id="h3_category_confusion",
            cohort_filter={},
            order=9,
        ),

        # ── H4: School and peer channels ──────────────────────────────────
        Hypothesis(
            id="h4_school_influence",
            problem_id=problem.id,
            title="School and peer channels matter more than social media",
            rationale=(
                "Recommendations around older kids may travel through schools, parent groups, and "
                "peer communities more than direct social discovery."
            ),
            indicator_attributes=["community_orientation", "peer_influence_strength"],
            confidence_prior=0.53,
            real_world_analogy=(
                "Amrutanjan: North India launch failures traced to missing community trust "
                "infrastructure — brand archetype mismatch with regional peer channels "
                "caused 35% below-plan performance vs. South India."
            ),
            why_level=1,
            cohort_filter={},
            order=10,
        ),
        Hypothesis(
            id="h4a_parent_whatsapp_group",
            problem_id=problem.id,
            title="Class parent WhatsApp groups are the primary recommendation channel",
            rationale=(
                "Urban Indian parents with school-age children rely heavily on class group chats "
                "for product recommendations, especially for health and education."
            ),
            indicator_attributes=["community_orientation", "wom_receiver_openness"],
            confidence_prior=0.61,
            real_world_analogy=(
                "Mamaearth: 2022 word-of-mouth study found 58% of parent referrals originated "
                "in school WhatsApp groups — highest single channel for 6-14 age segment."
            ),
            why_level=2,
            parent_hypothesis_id="h4_school_influence",
            cohort_filter={},
            order=11,
        ),
        Hypothesis(
            id="h4b_sports_coach_trust",
            problem_id=problem.id,
            title="Sports coach or school nutritionist recommendation carries high trust",
            rationale=(
                "For active children in organised sports, the coach or school health professional "
                "has authority that rivals the paediatrician for supplement recommendations."
            ),
            indicator_attributes=["medical_authority_trust", "community_orientation"],
            confidence_prior=0.38,
            real_world_analogy=(
                "Gatorade India: Pepsi found sports coach endorsement drove 3x higher "
                "consideration among 10-14 active cohort vs. digital advertising alone."
            ),
            why_level=2,
            parent_hypothesis_id="h4_school_influence",
            cohort_filter={"child_activity_level": "high"},
            edge_case=True,
            order=12,
        ),

        # ── H5: Proof gap (NEW) ───────────────────────────────────────────
        Hypothesis(
            id="h5_proof_gap",
            problem_id=problem.id,
            title="Lack of credible clinical proof for school-age performance claims",
            rationale=(
                "Parents of older children demand harder evidence for supplement efficacy than "
                "parents of toddlers. Without clinical backing or credible studies, the product "
                "feels speculative rather than essential."
            ),
            indicator_attributes=[
                "science_literacy",
                "research_before_purchase",
                "supplement_necessity_belief",
                "medical_authority_trust",
            ],
            confidence_prior=0.49,
            real_world_analogy=(
                "Bournvita: Mondelez's 'DHA for brain development' campaign with paediatrician "
                "endorsement increased trial by 28% in the 6-12 segment — clinical credibility "
                "was the decisive differentiator over taste in Nielsen 2019 study."
            ),
            why_level=1,
            cohort_filter={"science_literacy_gt": 0.6},
            order=13,
        ),
        Hypothesis(
            id="h5a_no_clinical_endorsement",
            problem_id=problem.id,
            title="No paediatrician or nutritionist endorsement reduces trust",
            rationale=(
                "Medical authority is the strongest trust anchor for supplement purchases in India. "
                "Absence of credible endorsement leaves a category trust gap."
            ),
            indicator_attributes=["medical_authority_trust", "supplement_necessity_belief"],
            confidence_prior=0.55,
            real_world_analogy=(
                "PediaSure India: 60%+ of sales through paediatrician recommendation — "
                "direct clinical endorsement is the category's primary acquisition channel."
            ),
            why_level=2,
            parent_hypothesis_id="h5_proof_gap",
            cohort_filter={"trust_anchor": "doctor"},
            order=14,
        ),
        Hypothesis(
            id="h5b_ingredient_complexity_gap",
            problem_id=problem.id,
            title="Parents cannot decipher ingredient claims for older-child segment",
            rationale=(
                "The 7-14 segment requires a more nuanced ingredient narrative (cognitive support, "
                "bone density, iron for focus) that parents find harder to evaluate than simple "
                "growth claims for toddlers."
            ),
            indicator_attributes=["science_literacy", "research_before_purchase"],
            confidence_prior=0.43,
            real_world_analogy=(
                "Horlicks Growth Plus: HUL found that IQ/focus ingredient panels created "
                "confusion for lower-science-literacy parents, reducing purchase intent by 18% "
                "compared to simpler 'stronger bones' messaging."
            ),
            why_level=2,
            parent_hypothesis_id="h5_proof_gap",
            cohort_filter={},
            order=15,
        ),
    ]

    probes = [
        # H1 probes
        _interview_probe(
            "h1_p1_accept_powder",
            "h1_taste_barrier",
            "Would your 8-year-old accept a powder mixed into milk, or would they resist?",
            1,
        ),
        _simulation_probe(
            "h1_p2_format_sim",
            "h1_taste_barrier",
            {"product.taste_appeal": 0.80, "product.form_factor": "chewable_tablet"},
            problem.success_metric,
            2,
        ),
        # H1a probes
        _interview_probe(
            "h1a_p1_format_embarrassment",
            "h1a_format_mismatch",
            "Would your 11-year-old feel embarrassed if classmates saw them drinking a powder supplement?",
            1,
        ),
        _simulation_probe(
            "h1a_p2_bar_format_sim",
            "h1a_format_mismatch",
            {"product.form_factor": "nutrition_bar", "product.branding": "teen_variant"},
            problem.success_metric,
            2,
        ),
        # H1b probes
        _interview_probe(
            "h1b_p1_flavour_preference",
            "h1b_flavour_mismatch",
            "What flavours does your child prefer in snacks — sweet, chocolatey, savoury, or mixed?",
            1,
        ),
        _attribute_probe(
            "h1b_p2_taste_split",
            "h1b_flavour_mismatch",
            ["child_taste_veto", "snacking_pattern"],
            "outcome",
            2,
        ),
        # H2 probes
        _interview_probe(
            "h2_p1_nutrition_gap",
            "h2_perceived_irrelevance",
            "At this age, do you still worry about nutritional gaps or feel they eat well enough?",
            1,
        ),
        _attribute_probe(
            "h2_p2_awareness_split",
            "h2_perceived_irrelevance",
            ["nutrition_gap_awareness", "health_anxiety", "supplement_necessity_belief"],
            "outcome",
            2,
        ),
        # H2a probes
        _interview_probe(
            "h2a_p1_meal_confidence",
            "h2a_normal_meals_belief",
            "How confident are you that school lunch and home meals cover all nutritional needs?",
            1,
        ),
        _attribute_probe(
            "h2a_p2_food_first_split",
            "h2a_normal_meals_belief",
            ["nutrition_gap_awareness", "food_first_belief"],
            "outcome",
            2,
        ),
        # H2b probes
        _interview_probe(
            "h2b_p1_growth_concern",
            "h2b_growth_concern_fade",
            "Do you track your child's height and weight as closely now as when they were younger?",
            1,
        ),
        _attribute_probe(
            "h2b_p2_anxiety_split",
            "h2b_growth_concern_fade",
            ["health_anxiety", "growth_concern"],
            "outcome",
            2,
        ),
        # H3 probes
        _interview_probe(
            "h3_p1_age_group_association",
            "h3_category_confusion",
            "When you hear 'Nutrimix', what age group comes to mind?",
            1,
        ),
        _interview_probe(
            "h3_p2_separate_brand_name",
            "h3_category_confusion",
            "Would a separate brand name for older kids make you more interested?",
            2,
        ),
        # H3a probes
        _interview_probe(
            "h3a_p1_pack_perception",
            "h3a_brand_age_ceiling",
            "Looking at the product packaging, does it feel right for a 10-year-old or more for a toddler?",
            1,
        ),
        _simulation_probe(
            "h3a_p2_redesign_sim",
            "h3a_brand_age_ceiling",
            {"product.branding": "school_age_redesign", "product.form_factor": "sachet"},
            problem.success_metric,
            2,
        ),
        # H3b probes
        _interview_probe(
            "h3b_p1_academic_narrative",
            "h3b_no_older_child_narrative",
            "Would you be more interested if this product claimed to support your child's concentration and exam performance?",
            1,
        ),
        _attribute_probe(
            "h3b_p2_narrative_response",
            "h3b_no_older_child_narrative",
            ["nutrition_gap_awareness", "science_literacy"],
            "outcome",
            2,
        ),
        # H4 probes
        _simulation_probe(
            "h4_p1_school_partnership_sim",
            "h4_school_influence",
            {"marketing.school_partnership": True, "marketing.awareness_budget": 0.6},
            problem.success_metric,
            1,
        ),
        _interview_probe(
            "h4_p2_recommendation_sources",
            "h4_school_influence",
            "Where do you get recommendations for products your school-age child uses?",
            2,
        ),
        # H4a probes
        _interview_probe(
            "h4a_p1_whatsapp_group",
            "h4a_parent_whatsapp_group",
            "Have you ever bought a product because someone in your school parent group recommended it?",
            1,
        ),
        _simulation_probe(
            "h4a_p2_wom_activation_sim",
            "h4a_parent_whatsapp_group",
            {"marketing.wom_seeding": True, "marketing.parent_community_partnerships": 5},
            problem.success_metric,
            2,
        ),
        # H4b probes (edge case)
        _interview_probe(
            "h4b_p1_sports_coach",
            "h4b_sports_coach_trust",
            "Would a recommendation from your child's sports coach or school nutritionist influence you?",
            1,
        ),
        _attribute_probe(
            "h4b_p2_authority_split",
            "h4b_sports_coach_trust",
            ["medical_authority_trust", "community_orientation"],
            "outcome",
            2,
        ),
        # H5 probes
        _interview_probe(
            "h5_p1_clinical_proof",
            "h5_proof_gap",
            "Would you want to see clinical studies before giving your child a new supplement?",
            1,
        ),
        _attribute_probe(
            "h5_p2_science_literacy_split",
            "h5_proof_gap",
            ["science_literacy", "research_before_purchase", "supplement_necessity_belief"],
            "outcome",
            2,
        ),
        # H5a probes
        _interview_probe(
            "h5a_p1_doctor_recommendation",
            "h5a_no_clinical_endorsement",
            "Would you trust this supplement more if your paediatrician specifically recommended it?",
            1,
        ),
        _simulation_probe(
            "h5a_p2_endorsement_sim",
            "h5a_no_clinical_endorsement",
            {"marketing.pediatrician_endorsement": True, "marketing.clinical_study_badge": True},
            problem.success_metric,
            2,
        ),
        # H5b probes
        _interview_probe(
            "h5b_p1_ingredient_clarity",
            "h5b_ingredient_complexity_gap",
            "When you read the ingredient list, did you understand what each ingredient does for your child?",
            1,
        ),
        _attribute_probe(
            "h5b_p2_literacy_split",
            "h5b_ingredient_complexity_gap",
            ["science_literacy", "research_before_purchase"],
            "outcome",
            2,
        ),
    ]

    return ProblemTreeDefinition(problem=problem, hypotheses=hypotheses, probes=probes)


# ── Tree 3: Magnesium Gummies Growth ─────────────────────────────────────────

def _tree_magnesium_gummies() -> ProblemTreeDefinition:
    """Probing tree: how LittleJoys can increase magnesium gummies sales.

    Expanded from 3 to 5 top-level hypotheses with sub-hypotheses.
    Grounded in Indian supplement and gummy market evidence.
    """
    problem = ProblemStatement(
        id="magnesium_gummies_growth",
        title="How can LittleJoys increase sales of magnesium gummies for kids?",
        scenario_id="magnesium_gummies",
        context=(
            "Magnesium gummies ask parents to buy into a less familiar category with a playful format. "
            "Growth depends on whether the barrier is awareness, trust, or value perception."
        ),
        success_metric="adoption_rate",
    )

    hypotheses = [
        # ── H1: Category awareness ────────────────────────────────────────
        Hypothesis(
            id="h1_category_awareness",
            problem_id=problem.id,
            title="Parents do not know kids need magnesium",
            rationale=(
                "If the category need is unclear, even a well-positioned product struggles to enter consideration."
            ),
            indicator_attributes=[
                "nutrition_gap_awareness",
                "science_literacy",
                "research_before_purchase",
            ],
            confidence_prior=0.70,
            real_world_analogy=(
                "Dabur Chyawanprash: seasonal awareness campaign framing immunity as a 'winter gap' "
                "drove 40%+ seasonal sales spike — category-need framing unlocks dormant demand."
            ),
            why_level=1,
            cohort_filter={},
            order=1,
        ),
        Hypothesis(
            id="h1a_magnesium_unknown",
            problem_id=problem.id,
            title="Parents have not heard that magnesium affects sleep and focus in children",
            rationale=(
                "Magnesium's role in children's health is not part of mainstream Indian nutrition "
                "awareness — the category has to build the need story from scratch."
            ),
            indicator_attributes=["nutrition_gap_awareness", "science_literacy"],
            confidence_prior=0.68,
            real_world_analogy=(
                "Bournvita 'DHA for brain' campaign: Mondelez had to educate parents on omega-3's "
                "role in cognition before DHA claims could drive purchase — category education "
                "preceded conversion by 12-18 months."
            ),
            why_level=2,
            parent_hypothesis_id="h1_category_awareness",
            cohort_filter={},
            order=2,
        ),
        Hypothesis(
            id="h1b_sleep_focus_not_linked",
            problem_id=problem.id,
            title="Parents have a sleep or focus concern but do not connect it to magnesium",
            rationale=(
                "Parents may be aware of their child's sleep issues or attention problems without "
                "realising magnesium supplementation could address them — a last-mile linkage gap."
            ),
            indicator_attributes=["health_anxiety", "research_before_purchase"],
            confidence_prior=0.55,
            real_world_analogy=(
                "Himalaya Ashvagandha Kids: brand found that parents with child stress concerns "
                "required an explicit symptom-to-ingredient bridge in communication before "
                "supplement consideration was triggered."
            ),
            why_level=2,
            parent_hypothesis_id="h1_category_awareness",
            cohort_filter={},
            order=3,
        ),

        # ── H2: Supplement skepticism ─────────────────────────────────────
        Hypothesis(
            id="h2_supplement_skepticism",
            problem_id=problem.id,
            title="Parents doubt gummy supplements can meaningfully support their child's overall development",
            rationale=(
                "The gummy format feels more like a treat than a credible tool for supporting "
                "growth, immunity, and cognitive development during formative years."
            ),
            indicator_attributes=[
                "supplement_necessity_belief",
                "natural_vs_synthetic_preference",
                "food_first_belief",
            ],
            confidence_prior=0.65,
            real_world_analogy=(
                "Himalaya Liv.52 Kids: Himalaya capitalised on food-first-belief parents by "
                "positioning the herbal formulation as 'food-derived', driving 22% share gain "
                "over synthetic supplement brands in the 3-10 segment."
            ),
            why_level=1,
            cohort_filter={},
            order=4,
        ),
        Hypothesis(
            id="h2a_candy_not_medicine",
            problem_id=problem.id,
            title="Gummy format is perceived as candy, undermining medicinal credibility",
            rationale=(
                "The visual similarity of gummy supplements to sweets creates cognitive dissonance "
                "— parents find it hard to believe something that looks like candy can be clinically effective."
            ),
            indicator_attributes=["supplement_necessity_belief", "natural_vs_synthetic_preference"],
            confidence_prior=0.60,
            real_world_analogy=(
                "Nature's Way Gummies India (import category): distributor research 2022 found "
                "60% of non-buyers cited 'looks too much like candy — child will want more' as "
                "primary credibility barrier for gummy vitamins."
            ),
            why_level=2,
            parent_hypothesis_id="h2_supplement_skepticism",
            cohort_filter={},
            order=5,
        ),
        Hypothesis(
            id="h2b_food_first_blocks_category",
            problem_id=problem.id,
            title="Food-first belief makes parents reject supplements as unnecessary intervention",
            rationale=(
                "A subset of parents believe strongly that nutrients should come from food, not "
                "supplements. This belief acts as a categorical block, not a product-specific objection."
            ),
            indicator_attributes=["food_first_belief", "natural_vs_synthetic_preference"],
            confidence_prior=0.50,
            real_world_analogy=(
                "Himalaya Liv.52: food-first-belief parents (scoring > 0.7) showed 3x lower "
                "supplement consideration overall — herbal framing partially bridged this gap."
            ),
            why_level=2,
            parent_hypothesis_id="h2_supplement_skepticism",
            cohort_filter={"food_first_belief_gt": 0.7},
            edge_case=True,
            order=6,
        ),

        # ── H3: Price-value perception ────────────────────────────────────
        Hypothesis(
            id="h3_price_value",
            problem_id=problem.id,
            title="Rs 499 for gummies feels expensive versus established alternatives",
            rationale=(
                "Parents may compare gummies against cheaper vitamin routines or familiar brands with stronger value anchors."
            ),
            indicator_attributes=[
                "budget_consciousness",
                "price_reference_point",
                "health_spend_priority",
            ],
            confidence_prior=0.58,
            real_world_analogy=(
                "Complan premium pricing: IRI 2019 found 'price feels wrong on repeat' pattern — "
                "repeat purchase price sensitivity was 2.2x higher than trial sensitivity "
                "for Rs 400+ products in the children's supplement category."
            ),
            why_level=1,
            cohort_filter={},
            order=7,
        ),
        Hypothesis(
            id="h3a_per_gummy_cost_shock",
            problem_id=problem.id,
            title="Per-unit cost calculation makes gummies feel poor value vs. tablet vitamins",
            rationale=(
                "When parents calculate cost per gummy vs. cost per tablet, gummies typically "
                "come out 2-3x more expensive — this rational comparison kills purchase intent."
            ),
            indicator_attributes=["budget_consciousness", "research_before_purchase"],
            confidence_prior=0.52,
            real_world_analogy=(
                "Wellkid UK (Vitabiotics): distributor India entry found per-gummy price comparison "
                "vs Himalaya tablet vitamins was the #1 objection at pharmacy counter — Rs 16/gummy "
                "vs Rs 3/tablet framing drove 40% rejection."
            ),
            why_level=2,
            parent_hypothesis_id="h3_price_value",
            cohort_filter={},
            order=8,
        ),
        Hypothesis(
            id="h3b_no_premium_justification",
            problem_id=problem.id,
            title="No premium justification visible — parents do not see why gummy costs more",
            rationale=(
                "Without clear communication of the premium ingredient quality, bioavailability, "
                "or taste science, parents default to 'paying for the fancy format'."
            ),
            indicator_attributes=["price_reference_point", "science_literacy"],
            confidence_prior=0.45,
            real_world_analogy=(
                "Mamaearth premium skin range: brand found that premium justification content "
                "(ingredient transparency, third-party testing) reduced price objections by 31% "
                "in the Rs 400-600 segment."
            ),
            why_level=2,
            parent_hypothesis_id="h3_price_value",
            cohort_filter={},
            order=9,
        ),

        # ── H4: Distribution and discovery gap (NEW) ──────────────────────
        Hypothesis(
            id="h4_distribution_gap",
            problem_id=problem.id,
            title="Product is not available in the channels where parents discover supplements",
            rationale=(
                "For supplement categories, paediatrician clinics and pharmacies are the primary "
                "discovery channels in India. If gummies are not stocked or recommended there, "
                "they miss the highest-intent purchase moment."
            ),
            indicator_attributes=[
                "online_shopping_comfort",
                "medical_authority_trust",
                "indie_brand_openness",
            ],
            confidence_prior=0.55,
            real_world_analogy=(
                "PediaSure India: Abbott's pharmacy-first distribution model drove 60%+ of sales "
                "through clinical channels — products without pharmacy presence lose the highest-intent "
                "parent at the moment of readiness."
            ),
            why_level=1,
            cohort_filter={},
            order=10,
        ),
        Hypothesis(
            id="h4a_not_at_pharmacy",
            problem_id=problem.id,
            title="Gummies not stocked in local pharmacy where parent buys vitamins",
            rationale=(
                "Pharmacy shelf presence drives impulse supplement discovery — a parent buying "
                "Vitamin D drops will pick up gummies if available. Without stock, the moment is lost."
            ),
            indicator_attributes=["indie_brand_openness", "online_shopping_comfort"],
            confidence_prior=0.50,
            real_world_analogy=(
                "Himalaya Liv.52 Kids: pharmacy shelf placement drove 55% of first-time trial — "
                "online-only brands in the same category showed 4x lower trial conversion rate."
            ),
            why_level=2,
            parent_hypothesis_id="h4_distribution_gap",
            cohort_filter={},
            order=11,
        ),
        Hypothesis(
            id="h4b_paed_not_recommending",
            problem_id=problem.id,
            title="Paediatricians do not know about or endorse gummy format supplements",
            rationale=(
                "Doctor-recommended supplements have dramatically higher conversion in India. "
                "If paediatricians are not aware of gummy magnesium options, they default to "
                "recommending legacy tablet-form products."
            ),
            indicator_attributes=["medical_authority_trust", "supplement_necessity_belief"],
            confidence_prior=0.47,
            real_world_analogy=(
                "PediaSure India: Abbott's paediatrician detailing programme converted 40% of "
                "doctors to active recommenders — brand awareness among doctors preceded consumer "
                "awareness by 18 months in their launch playbook."
            ),
            why_level=2,
            parent_hypothesis_id="h4_distribution_gap",
            cohort_filter={"trust_anchor": "doctor"},
            order=12,
        ),

        # ── H5: Taste and sensory experience ─────────────────────────────
        Hypothesis(
            id="h5_taste_consistency",
            problem_id=problem.id,
            title="Inconsistent taste or texture creates first-experience failure",
            rationale=(
                "Gummies that are too hard, too sweet, or have a medicinal aftertaste generate "
                "child rejection at first use — eliminating the repeat opportunity immediately."
            ),
            indicator_attributes=[
                "child_taste_veto",
                "natural_vs_synthetic_preference",
            ],
            confidence_prior=0.42,
            real_world_analogy=(
                "Emami Fair & Handsome: product experience failure at 3 months was tracked to "
                "sensory disappointment — novelty wear-off combined with experience gap created "
                "a repeat purchase cliff that mirrors gummy first-experience failure patterns."
            ),
            why_level=1,
            cohort_filter={},
            order=13,
        ),
        Hypothesis(
            id="h5a_medicinal_aftertaste",
            problem_id=problem.id,
            title="Magnesium aftertaste in gummy is unpleasant for children",
            rationale=(
                "Magnesium compounds can impart a bitter, metallic or chalky aftertaste that "
                "children detect and reject, regardless of initial sweetness."
            ),
            indicator_attributes=["child_taste_veto"],
            confidence_prior=0.38,
            real_world_analogy=(
                "Wellkid Magnesium Gummies (UK): 22% of negative reviews on Amazon UK cited "
                "'aftertaste' — magnesium glycinate showed 40% lower aftertaste complaint rate "
                "vs magnesium oxide formulations."
            ),
            why_level=2,
            parent_hypothesis_id="h5_taste_consistency",
            cohort_filter={},
            order=14,
        ),
        Hypothesis(
            id="h5b_child_wants_more_creates_problem",
            problem_id=problem.id,
            title="Child overconsumption risk creates parental anxiety about gummy format",
            rationale=(
                "Parents worry that if gummies taste like candy, their child will demand more "
                "than the recommended dose — creating a safety concern that blocks purchase."
            ),
            indicator_attributes=["supplement_necessity_belief", "health_anxiety"],
            confidence_prior=0.45,
            real_world_analogy=(
                "Vitafusion (US): brand solved overconsumption anxiety with child-resistant "
                "packaging and parent lock — Indian market shows same concern pattern in "
                "qual research for gummy format supplements."
            ),
            why_level=2,
            parent_hypothesis_id="h5_taste_consistency",
            cohort_filter={},
            edge_case=True,
            order=15,
        ),
    ]

    probes = [
        # H1 probes
        _interview_probe(
            "h1_p1_magnesium_awareness",
            "h1_category_awareness",
            "Before today, were you aware that magnesium plays a role in your child's sleep and focus?",
            1,
        ),
        _simulation_probe(
            "h1_p2_awareness_campaign_sim",
            "h1_category_awareness",
            {"marketing.awareness_budget": 0.65, "marketing.pediatrician_endorsement": True},
            problem.success_metric,
            2,
        ),
        _attribute_probe(
            "h1_p3_literacy_split",
            "h1_category_awareness",
            ["science_literacy", "nutrition_gap_awareness"],
            "outcome",
            3,
        ),
        # H1a probes
        _interview_probe(
            "h1a_p1_mineral_knowledge",
            "h1a_magnesium_unknown",
            "Do you know which minerals children most commonly lack in a typical Indian diet?",
            1,
        ),
        _attribute_probe(
            "h1a_p2_awareness_depth",
            "h1a_magnesium_unknown",
            ["nutrition_gap_awareness", "science_literacy"],
            "outcome",
            2,
        ),
        # H1b probes
        _interview_probe(
            "h1b_p1_sleep_focus_concern",
            "h1b_sleep_focus_not_linked",
            "Have you noticed issues with your child's sleep quality or daytime focus?",
            1,
        ),
        _interview_probe(
            "h1b_p2_supplement_connection",
            "h1b_sleep_focus_not_linked",
            "If you knew a mineral supplement could improve those specific issues, would you try it?",
            2,
        ),
        # H2 probes
        _interview_probe(
            "h2_p1_gummy_realness",
            "h2_supplement_skepticism",
            "Do gummy vitamins feel like real supplements to you, or more like candy?",
            1,
        ),
        _interview_probe(
            "h2_p2_doctor_recommendation",
            "h2_supplement_skepticism",
            "Would you trust a gummy more if it came with a doctor's recommendation?",
            2,
        ),
        # H2a probes
        _interview_probe(
            "h2a_p1_candy_perception",
            "h2a_candy_not_medicine",
            "When your child sees gummy vitamins, do they ask for them as a treat or accept them as medicine?",
            1,
        ),
        _attribute_probe(
            "h2a_p2_belief_split",
            "h2a_candy_not_medicine",
            ["supplement_necessity_belief", "natural_vs_synthetic_preference"],
            "outcome",
            2,
        ),
        # H2b probes (edge case)
        _interview_probe(
            "h2b_p1_food_first",
            "h2b_food_first_blocks_category",
            "Do you believe a balanced diet makes supplements unnecessary for most children?",
            1,
        ),
        _attribute_probe(
            "h2b_p2_food_belief_split",
            "h2b_food_first_blocks_category",
            ["food_first_belief", "natural_vs_synthetic_preference"],
            "outcome",
            2,
        ),
        # H3 probes
        _interview_probe(
            "h3_p1_price_comparison",
            "h3_price_value",
            "How does Rs 499 for a month's supply of gummies compare to what you currently spend on vitamins?",
            1,
        ),
        _simulation_probe(
            "h3_p2_price_cut_sim",
            "h3_price_value",
            {"product.price_inr": 349.0},
            problem.success_metric,
            2,
        ),
        # H3a probes
        _interview_probe(
            "h3a_p1_per_unit_cost",
            "h3a_per_gummy_cost_shock",
            "If gummies cost Rs 16 each but tablets cost Rs 3 each, which would you choose for the same benefit?",
            1,
        ),
        _simulation_probe(
            "h3a_p2_bundle_sim",
            "h3a_per_gummy_cost_shock",
            {"product.price_inr": 399.0, "product.pack_size": 60},
            problem.success_metric,
            2,
        ),
        # H3b probes
        _interview_probe(
            "h3b_p1_premium_justification",
            "h3b_no_premium_justification",
            "What would convince you that gummies are worth more than regular tablet supplements?",
            1,
        ),
        _attribute_probe(
            "h3b_p2_price_reference_split",
            "h3b_no_premium_justification",
            ["price_reference_point", "science_literacy"],
            "outcome",
            2,
        ),
        # H4 probes
        _interview_probe(
            "h4_p1_where_discover",
            "h4_distribution_gap",
            "Where did you last discover or buy a vitamin or supplement product for your child?",
            1,
        ),
        _simulation_probe(
            "h4_p2_pharmacy_sim",
            "h4_distribution_gap",
            {"marketing.pharmacy_distribution": True, "marketing.pediatrician_endorsement": True},
            problem.success_metric,
            2,
        ),
        # H4a probes
        _interview_probe(
            "h4a_p1_pharmacy_availability",
            "h4a_not_at_pharmacy",
            "Have you looked for this type of gummy supplement at your local pharmacy?",
            1,
        ),
        _attribute_probe(
            "h4a_p2_channel_preference",
            "h4a_not_at_pharmacy",
            ["online_shopping_comfort", "indie_brand_openness"],
            "outcome",
            2,
        ),
        # H4b probes
        _interview_probe(
            "h4b_p1_doctor_awareness",
            "h4b_paed_not_recommending",
            "Has your child's paediatrician ever mentioned magnesium or recommended a gummy supplement?",
            1,
        ),
        _attribute_probe(
            "h4b_p2_doctor_trust_split",
            "h4b_paed_not_recommending",
            ["medical_authority_trust", "supplement_necessity_belief"],
            "outcome",
            2,
        ),
        # H5 probes
        _interview_probe(
            "h5_p1_first_taste",
            "h5_taste_consistency",
            "Did your child enjoy the taste of the gummy on their first try, or did they need convincing?",
            1,
        ),
        _attribute_probe(
            "h5_p2_taste_veto_split",
            "h5_taste_consistency",
            ["child_taste_veto", "natural_vs_synthetic_preference"],
            "outcome",
            2,
        ),
        # H5a probes
        _interview_probe(
            "h5a_p1_aftertaste",
            "h5a_medicinal_aftertaste",
            "After eating the gummy, did your child mention any unusual taste or aftertaste?",
            1,
        ),
        _simulation_probe(
            "h5a_p2_formulation_sim",
            "h5a_medicinal_aftertaste",
            {"product.formulation": "magnesium_glycinate", "product.taste_appeal": 0.85},
            problem.success_metric,
            2,
        ),
        # H5b probes (edge case)
        _interview_probe(
            "h5b_p1_overconsumption_worry",
            "h5b_child_wants_more_creates_problem",
            "Have you ever worried your child would eat too many gummies if they tasted good?",
            1,
        ),
        _simulation_probe(
            "h5b_p2_safety_packaging_sim",
            "h5b_child_wants_more_creates_problem",
            {"product.child_resistant_packaging": True, "product.daily_limit_lock": True},
            problem.success_metric,
            2,
        ),
    ]

    return ProblemTreeDefinition(problem=problem, hypotheses=hypotheses, probes=probes)


# ── Tree 4: Protein Mix Launch ────────────────────────────────────────────────

def _tree_protein_mix() -> ProblemTreeDefinition:
    """Probing tree: how LittleJoys can increase ProteinMix adoption.

    Expanded from 3 to 5 top-level hypotheses with sub-hypotheses.
    Grounded in Indian children's nutrition and cooking-format market evidence.
    """
    problem = ProblemStatement(
        id="protein_mix_launch",
        title="How can LittleJoys increase adoption of ProteinMix for kids?",
        scenario_id="protein_mix",
        context=(
            "ProteinMix introduces a more effortful routine than a ready-to-use supplement. The "
            "launch depends on whether parents reject the effort, the need story, or the likely taste outcome."
        ),
        success_metric="adoption_rate",
    )

    hypotheses = [
        # ── H1: Effort barrier ────────────────────────────────────────────
        Hypothesis(
            id="h1_effort_barrier",
            problem_id=problem.id,
            title="Cooking requirement is too high a barrier",
            rationale=(
                "Parents may agree with the benefit but still reject the product if it asks for too much prep work."
            ),
            indicator_attributes=[
                "perceived_time_scarcity",
                "cooking_time_available",
                "simplicity_preference",
            ],
            confidence_prior=0.68,
            real_world_analogy=(
                "Dabur Chyawanprash: HUL research found that Chyawanprash reorder dropped 35% "
                "when parents switched from at-home mixing to purchased variants — effort reduction "
                "was the single largest lever in the children's supplement reorder study."
            ),
            why_level=1,
            cohort_filter={},
            order=1,
        ),
        Hypothesis(
            id="h1a_morning_rush",
            problem_id=problem.id,
            title="Morning school prep time is too tight to add a cooking step",
            rationale=(
                "Indian school mornings are time-compressed with multiple competing tasks. "
                "A product requiring mixing into batter or dough competes with time that does not exist."
            ),
            indicator_attributes=["perceived_time_scarcity", "morning_routine_complexity"],
            confidence_prior=0.64,
            real_world_analogy=(
                "Nestle Maggi Masala: fastest morning meals study (Kantar 2020) showed that "
                "any product adding > 3 minutes to morning prep dropped adoption by 28% in "
                "households with school-going children aged 5-12."
            ),
            why_level=2,
            parent_hypothesis_id="h1_effort_barrier",
            cohort_filter={},
            order=2,
        ),
        Hypothesis(
            id="h1b_skill_anxiety",
            problem_id=problem.id,
            title="Parent fears getting the quantity wrong and wasting the product",
            rationale=(
                "Cooking-format supplements require measurement and accurate dosing. "
                "Parents with low cooking confidence worry about incorrect quantities "
                "reducing efficacy or causing overconsumption."
            ),
            indicator_attributes=["cooking_time_available", "simplicity_preference"],
            confidence_prior=0.40,
            real_world_analogy=(
                "Himalaya Baby Powder: packaging study found that unmarked dosing instructions "
                "drove 18% higher abandonment vs products with visual quantity guides — "
                "measurement anxiety is a real but underestimated barrier."
            ),
            why_level=2,
            parent_hypothesis_id="h1_effort_barrier",
            cohort_filter={},
            edge_case=True,
            order=3,
        ),

        # ── H2: Category unfamiliarity ────────────────────────────────────
        Hypothesis(
            id="h2_category_unfamiliarity",
            problem_id=problem.id,
            title="Parents do not think kids need protein supplementation",
            rationale=(
                "The category can fail before purchase if parents feel regular meals already cover protein needs."
            ),
            indicator_attributes=["supplement_necessity_belief", "nutrition_gap_awareness"],
            confidence_prior=0.62,
            real_world_analogy=(
                "Bournvita: Mondelez found that 'protein gap' messaging was less effective than "
                "'brain development' framing — Indian parents had low protein-gap awareness "
                "for children, requiring a category education phase before conversion."
            ),
            why_level=1,
            cohort_filter={},
            order=4,
        ),
        Hypothesis(
            id="h2a_dal_roti_protein_belief",
            problem_id=problem.id,
            title="Parent believes dal, eggs, and milk fully cover protein needs",
            rationale=(
                "Traditional Indian diet includes high-protein foods like dal, paneer, and eggs. "
                "Parents with food-first beliefs assume these are sufficient and supplementation is redundant."
            ),
            indicator_attributes=["food_first_belief", "nutrition_gap_awareness"],
            confidence_prior=0.58,
            real_world_analogy=(
                "Horlicks Protein Plus: HUL found that protein supplement consideration was "
                "suppressed in households with high dal and egg consumption — food-first belief "
                "was the dominant barrier in the non-metro segment."
            ),
            why_level=2,
            parent_hypothesis_id="h2_category_unfamiliarity",
            cohort_filter={},
            order=5,
        ),
        Hypothesis(
            id="h2b_protein_adults_not_children",
            problem_id=problem.id,
            title="Protein supplements are associated with adults and gym-goers, not children",
            rationale=(
                "The mental model for protein supplements in India is adult fitness, not child "
                "development — this category positioning error blocks parental consideration."
            ),
            indicator_attributes=["supplement_necessity_belief", "indie_brand_openness"],
            confidence_prior=0.52,
            real_world_analogy=(
                "Ensure (Abbott) India: brand required dedicated 'protein for children' "
                "sub-category creation to overcome adult gym association — took 18 months of "
                "medical channel communication to shift mental model."
            ),
            why_level=2,
            parent_hypothesis_id="h2_category_unfamiliarity",
            cohort_filter={},
            order=6,
        ),

        # ── H3: Taste concern ─────────────────────────────────────────────
        Hypothesis(
            id="h3_taste_concern",
            problem_id=problem.id,
            title="Parents doubt their child will eat protein-fortified food",
            rationale=(
                "Even interested parents may hold back if they expect the child to notice and reject the taste."
            ),
            indicator_attributes=["child_taste_veto"],
            confidence_prior=0.57,
            real_world_analogy=(
                "Nestle NutriSource: Nestle India trial found that parental prediction of child "
                "rejection was the #1 barrier to trial — actual child acceptance post trial was "
                "35% higher than parents predicted (Nestle internal 2021)."
            ),
            why_level=1,
            cohort_filter={},
            order=7,
        ),
        Hypothesis(
            id="h3a_protein_taste_detection",
            problem_id=problem.id,
            title="Child can taste the protein powder in the cooked food and rejects it",
            rationale=(
                "Protein powders often have a chalky, beany, or eggy aftertaste that survives "
                "cooking, particularly when children are texture-sensitive."
            ),
            indicator_attributes=["child_taste_veto", "snacking_pattern"],
            confidence_prior=0.50,
            real_world_analogy=(
                "Horlicks Protein Plus (cooking variant): HUL discontinuation was partly "
                "attributed to cooked-food taste failure — children detected 'different taste' "
                "in chapati and rejected familiar foods when mixed in."
            ),
            why_level=2,
            parent_hypothesis_id="h3_taste_concern",
            cohort_filter={},
            order=8,
        ),
        Hypothesis(
            id="h3b_visual_change_rejection",
            problem_id=problem.id,
            title="Visible colour or texture change in cooked food triggers child refusal",
            rationale=(
                "Children are highly sensitive to appearance changes in familiar foods. "
                "A visually altered roti or pancake can be refused on sight before tasting."
            ),
            indicator_attributes=["child_taste_veto"],
            confidence_prior=0.38,
            real_world_analogy=(
                "Nestle Milo fortified roti experiment (India pilot 2019): colour change in "
                "dough was cited as reason for refusal by 28% of children in product testing — "
                "visual normalcy is a prerequisite for hidden fortification acceptance."
            ),
            why_level=2,
            parent_hypothesis_id="h3_taste_concern",
            cohort_filter={},
            order=9,
        ),

        # ── H4: Trust and ingredient clarity ─────────────────────────────
        Hypothesis(
            id="h4_ingredient_trust",
            problem_id=problem.id,
            title="Parents do not trust a new brand's protein source or safety claims",
            rationale=(
                "Protein supplements carry a perceived risk of adulteration or poor-quality "
                "sources in India, especially for new indie brands. Safety trust must be established "
                "before ingredient claims can drive adoption."
            ),
            indicator_attributes=[
                "medical_authority_trust",
                "indie_brand_openness",
                "science_literacy",
                "risk_tolerance",
            ],
            confidence_prior=0.55,
            real_world_analogy=(
                "Mamaearth: 'toxin-free' positioning resolved ingredient-safety anxiety that "
                "blocks indie brand consideration — transparency-first strategy drove NPS of 72 "
                "but required 18 months of content investment before purchase trust was established."
            ),
            why_level=1,
            cohort_filter={},
            order=10,
        ),
        Hypothesis(
            id="h4a_protein_source_unknown",
            problem_id=problem.id,
            title="Parent cannot identify whether the protein source is plant or animal-based",
            rationale=(
                "Religious dietary restrictions (vegetarian, Jain) and personal preferences around "
                "plant vs. animal protein create a verification need that Indian parents take seriously."
            ),
            indicator_attributes=["science_literacy", "research_before_purchase"],
            confidence_prior=0.48,
            real_world_analogy=(
                "Bournvita: HUL experienced backlash in Jain community when whey protein origin "
                "was not clearly labelled — vegetarian mark on pack became the #1 purchase decision "
                "criteria for 60% of non-metro buyers."
            ),
            why_level=2,
            parent_hypothesis_id="h4_ingredient_trust",
            cohort_filter={},
            order=11,
        ),
        Hypothesis(
            id="h4b_new_brand_adulteration_fear",
            problem_id=problem.id,
            title="New brand without pharmacy or doctor endorsement feels risky for protein supplement",
            rationale=(
                "India has a history of supplement adulteration scandals. New indie brands face "
                "a trust deficit that established pharmaceutical or FMCG brands do not."
            ),
            indicator_attributes=["indie_brand_openness", "risk_tolerance", "medical_authority_trust"],
            confidence_prior=0.42,
            real_world_analogy=(
                "Patanjali Nutrela: despite Baba Ramdev's brand trust, Nutrela required 3rd-party "
                "testing certifications prominently displayed to overcome sports supplement "
                "adulteration concerns in the post-2020 WADA-India media cycle."
            ),
            why_level=2,
            parent_hypothesis_id="h4_ingredient_trust",
            cohort_filter={},
            edge_case=True,
            order=12,
        ),

        # ── H5: Occasion fit ─────────────────────────────────────────────
        Hypothesis(
            id="h5_occasion_fit",
            problem_id=problem.id,
            title="No clear daily occasion where ProteinMix naturally fits the family's routine",
            rationale=(
                "Unlike a morning milk supplement, a cooking-format protein powder requires "
                "a specific meal occasion. If the product does not attach to a high-frequency "
                "occasion (roti, dosa, paratha), it remains in the pantry unused."
            ),
            indicator_attributes=[
                "breakfast_routine",
                "cooking_time_available",
                "perceived_time_scarcity",
            ],
            confidence_prior=0.50,
            real_world_analogy=(
                "Nestle Munch/KitKat: gifting occasion anchor drove habitual purchase — "
                "products that failed to attach to a recurring occasion showed 3x higher "
                "post-trial abandonment in Kantar Worldpanel 2020 study."
            ),
            why_level=1,
            cohort_filter={},
            order=13,
        ),
        Hypothesis(
            id="h5a_roti_not_made_daily",
            problem_id=problem.id,
            title="Roti and chapati are not daily occasions in the household",
            rationale=(
                "South Indian and Bengali households may not make roti daily — the product's "
                "primary use case does not match the household's actual cooking occasions."
            ),
            indicator_attributes=["breakfast_routine", "cooking_time_available"],
            confidence_prior=0.44,
            real_world_analogy=(
                "Ashirvaad Multigrain Atta: ITC found 40% lower trial in South India compared "
                "to North India for roti-format products — regional cooking occasion mismatch "
                "is a consistent launch barrier for flour-based supplements."
            ),
            why_level=2,
            parent_hypothesis_id="h5_occasion_fit",
            cohort_filter={},
            order=14,
        ),
        Hypothesis(
            id="h5b_milk_moment_not_considered",
            problem_id=problem.id,
            title="Parent did not consider adding protein to the morning milk moment",
            rationale=(
                "The daily morning milk is the highest-frequency supplement occasion in Indian "
                "households. If parents do not know ProteinMix can be added to milk, a key "
                "low-effort occasion is missed."
            ),
            indicator_attributes=["breakfast_routine", "child_health_proactivity"],
            confidence_prior=0.55,
            real_world_analogy=(
                "Horlicks and Complan both built dominance by anchoring to the morning milk moment — "
                "brands that failed to communicate milk compatibility lost the highest-frequency "
                "occasion and defaulted to infrequent cooking-occasion use."
            ),
            why_level=2,
            parent_hypothesis_id="h5_occasion_fit",
            cohort_filter={},
            order=15,
        ),
    ]

    probes = [
        # H1 probes
        _interview_probe(
            "h1_p1_busy_morning",
            "h1_effort_barrier",
            "Would you add a protein powder to pancake batter or roti dough on a busy morning?",
            1,
        ),
        _simulation_probe(
            "h1_p2_ready_to_drink_sim",
            "h1_effort_barrier",
            {
                "product.effort_to_acquire": 0.15,
                "product.cooking_required": 0.2,
                "product.form_factor": "ready_to_drink",
            },
            problem.success_metric,
            2,
        ),
        _attribute_probe(
            "h1_p3_time_split",
            "h1_effort_barrier",
            [
                "perceived_time_scarcity",
                "cooking_time_available",
                "simplicity_preference",
                "morning_routine_complexity",
            ],
            "outcome",
            3,
        ),
        # H1a probes
        _interview_probe(
            "h1a_p1_morning_steps",
            "h1a_morning_rush",
            "Walk me through your morning routine on a school day — how much time do you have to make breakfast?",
            1,
        ),
        _simulation_probe(
            "h1a_p2_instant_mix_sim",
            "h1a_morning_rush",
            {"product.prep_time_minutes": 1, "product.form_factor": "instant_dissolve"},
            problem.success_metric,
            2,
        ),
        # H1b probes (edge case)
        _interview_probe(
            "h1b_p1_dosing_confidence",
            "h1b_skill_anxiety",
            "When using a powder supplement, do you worry about measuring the right amount?",
            1,
        ),
        _simulation_probe(
            "h1b_p2_pre_portioned_sim",
            "h1b_skill_anxiety",
            {"product.dosing": "pre_portioned_sachets", "product.waste_risk": 0.0},
            problem.success_metric,
            2,
        ),
        # H2 probes
        _interview_probe(
            "h2_p1_regular_meals_protein",
            "h2_category_unfamiliarity",
            "Do you feel your child gets enough protein from regular meals?",
            1,
        ),
        _interview_probe(
            "h2_p2_protein_conviction",
            "h2_category_unfamiliarity",
            "What would convince you that a protein supplement is worth adding to their diet?",
            2,
        ),
        # H2a probes
        _interview_probe(
            "h2a_p1_traditional_protein",
            "h2a_dal_roti_protein_belief",
            "Your child has dal and eggs regularly — do you think that covers their protein needs?",
            1,
        ),
        _attribute_probe(
            "h2a_p2_food_first_split",
            "h2a_dal_roti_protein_belief",
            ["food_first_belief", "nutrition_gap_awareness"],
            "outcome",
            2,
        ),
        # H2b probes
        _interview_probe(
            "h2b_p1_adult_association",
            "h2b_protein_adults_not_children",
            "When you think of protein supplements, do you think of gym users or children?",
            1,
        ),
        _simulation_probe(
            "h2b_p2_kids_protein_narrative_sim",
            "h2b_protein_adults_not_children",
            {"marketing.category_framing": "children_growth_protein", "marketing.pediatrician_endorsement": True},
            problem.success_metric,
            2,
        ),
        # H3 probes
        _interview_probe(
            "h3_p1_taste_detection",
            "h3_taste_concern",
            "If your child could taste the protein powder in their pancake, would they refuse to eat it?",
            1,
        ),
        _simulation_probe(
            "h3_p2_taste_improvement_sim",
            "h3_taste_concern",
            {"product.taste_appeal": 0.75},
            problem.success_metric,
            2,
        ),
        # H3a probes
        _interview_probe(
            "h3a_p1_cooked_food_taste",
            "h3a_protein_taste_detection",
            "Have you ever tried hiding a supplement in food and had your child notice it?",
            1,
        ),
        _simulation_probe(
            "h3a_p2_neutral_taste_sim",
            "h3a_protein_taste_detection",
            {"product.taste_appeal": 0.85, "product.flavour_profile": "neutral_unflavoured"},
            problem.success_metric,
            2,
        ),
        # H3b probes
        _interview_probe(
            "h3b_p1_visual_change",
            "h3b_visual_change_rejection",
            "If the roti looked slightly different after adding protein powder, would your child refuse it?",
            1,
        ),
        _simulation_probe(
            "h3b_p2_colour_neutral_sim",
            "h3b_visual_change_rejection",
            {"product.visual_neutrality": 0.95, "product.colour_change": "none"},
            problem.success_metric,
            2,
        ),
        # H4 probes
        _interview_probe(
            "h4_p1_brand_trust",
            "h4_ingredient_trust",
            "What would you want to know about where the protein in this product comes from?",
            1,
        ),
        _attribute_probe(
            "h4_p2_trust_split",
            "h4_ingredient_trust",
            ["medical_authority_trust", "indie_brand_openness", "risk_tolerance"],
            "outcome",
            2,
        ),
        # H4a probes
        _interview_probe(
            "h4a_p1_protein_source",
            "h4a_protein_source_unknown",
            "Is the protein source plant-based or animal-based? Does that matter to your family?",
            1,
        ),
        _attribute_probe(
            "h4a_p2_dietary_pref_split",
            "h4a_protein_source_unknown",
            ["science_literacy", "research_before_purchase"],
            "outcome",
            2,
        ),
        # H4b probes (edge case)
        _interview_probe(
            "h4b_p1_safety_concern",
            "h4b_new_brand_adulteration_fear",
            "Have you ever worried about the quality or safety of protein supplements for children?",
            1,
        ),
        _simulation_probe(
            "h4b_p2_certification_sim",
            "h4b_new_brand_adulteration_fear",
            {"product.third_party_certification": True, "product.fssai_featured": True},
            problem.success_metric,
            2,
        ),
        # H5 probes
        _interview_probe(
            "h5_p1_daily_occasion",
            "h5_occasion_fit",
            "Which meal would you most naturally add a cooking supplement to — breakfast, lunch, or dinner?",
            1,
        ),
        _attribute_probe(
            "h5_p2_routine_split",
            "h5_occasion_fit",
            ["breakfast_routine", "cooking_time_available", "perceived_time_scarcity"],
            "outcome",
            2,
        ),
        # H5a probes
        _interview_probe(
            "h5a_p1_roti_frequency",
            "h5a_roti_not_made_daily",
            "How often do you make roti, dosa, or paratha at home in a typical week?",
            1,
        ),
        _simulation_probe(
            "h5a_p2_multi_occasion_sim",
            "h5a_roti_not_made_daily",
            {"product.use_occasions": ["roti", "dosa", "milk", "smoothie"]},
            problem.success_metric,
            2,
        ),
        # H5b probes
        _interview_probe(
            "h5b_p1_milk_moment",
            "h5b_milk_moment_not_considered",
            "Did you know this protein powder can also be added to morning milk — not just cooking?",
            1,
        ),
        _simulation_probe(
            "h5b_p2_milk_occasion_sim",
            "h5b_milk_moment_not_considered",
            {"marketing.milk_occasion_messaging": True, "product.milk_solubility": 0.95},
            problem.success_metric,
            2,
        ),
    ]

    return ProblemTreeDefinition(problem=problem, hypotheses=hypotheses, probes=probes)
