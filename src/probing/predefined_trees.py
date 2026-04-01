"""Predefined probing trees for the 4 LittleJoys business scenarios."""

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

        # Always add a full-population attribute probe.
        # If the hypothesis has specific indicator attributes use those;
        # otherwise fall back to the default broad funnel-driving set so
        # the engine always compares adopters vs non-adopters across all
        # 200 personas — not just the 30-persona interview sample.
        attr_id = f"{hypothesis.id}_custom_attribute"
        if attr_id not in seen_ids:
            attrs = hypothesis.indicator_attributes or _DEFAULT_CUSTOM_PROBE_ATTRIBUTES
            out.append(
                _attribute_probe(
                    probe_id=attr_id,
                    hypothesis_id=hypothesis.id,
                    attributes=attrs,
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


def _tree_repeat_purchase() -> ProblemTreeDefinition:
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
            order=1,
        ),
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
            order=2,
        ),
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
            order=3,
        ),
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
            order=4,
        ),
    ]

    probes = [
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
    ]

    return ProblemTreeDefinition(problem=problem, hypotheses=hypotheses, probes=probes)


def _tree_nutrimix_7_14() -> ProblemTreeDefinition:
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
        Hypothesis(
            id="h1_taste_barrier",
            problem_id=problem.id,
            title="Older kids reject the taste or format",
            rationale="Older children often have stronger preferences and are harder to hide formats from.",
            indicator_attributes=["child_taste_veto", "snacking_pattern"],
            order=1,
        ),
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
            order=2,
        ),
        Hypothesis(
            id="h3_category_confusion",
            problem_id=problem.id,
            title="Parents associate Nutrimix with toddlers, not school-age kids",
            rationale=(
                "Brand memory from the younger segment can create a positioning ceiling for older children."
            ),
            indicator_attributes=["brand_loyalty_tendency", "indie_brand_openness"],
            order=3,
        ),
        Hypothesis(
            id="h4_school_influence",
            problem_id=problem.id,
            title="School and peer channels matter more than social media",
            rationale=(
                "Recommendations around older kids may travel through schools, parent groups, and "
                "peer communities more than direct social discovery."
            ),
            indicator_attributes=["community_orientation", "peer_influence_strength"],
            order=4,
        ),
    ]

    probes = [
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
    ]

    return ProblemTreeDefinition(problem=problem, hypotheses=hypotheses, probes=probes)


def _tree_magnesium_gummies() -> ProblemTreeDefinition:
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
            order=1,
        ),
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
            order=2,
        ),
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
            order=3,
        ),
    ]

    probes = [
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
    ]

    return ProblemTreeDefinition(problem=problem, hypotheses=hypotheses, probes=probes)


def _tree_protein_mix() -> ProblemTreeDefinition:
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
            order=1,
        ),
        Hypothesis(
            id="h2_category_unfamiliarity",
            problem_id=problem.id,
            title="Parents do not think kids need protein supplementation",
            rationale=(
                "The category can fail before purchase if parents feel regular meals already cover protein needs."
            ),
            indicator_attributes=["supplement_necessity_belief", "nutrition_gap_awareness"],
            order=2,
        ),
        Hypothesis(
            id="h3_taste_concern",
            problem_id=problem.id,
            title="Parents doubt their child will eat protein-fortified food",
            rationale=(
                "Even interested parents may hold back if they expect the child to notice and reject the taste."
            ),
            indicator_attributes=["child_taste_veto"],
            order=3,
        ),
    ]

    probes = [
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
    ]

    return ProblemTreeDefinition(problem=problem, hypotheses=hypotheses, probes=probes)
