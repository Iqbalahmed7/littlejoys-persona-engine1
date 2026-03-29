"""Scenario-specific business question catalog for probing research runs."""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field

from src.probing.models import Hypothesis, ProblemStatement, ProblemTreeDefinition
from src.probing.predefined_trees import (
    _attribute_probe,
    _interview_probe,
    _simulation_probe,
    get_problem_tree,
)


class BusinessQuestion(BaseModel):
    """A scenario-specific research question that drives the probing tree."""

    model_config = ConfigDict(extra="forbid")

    id: str
    scenario_id: str
    title: str
    description: str
    probing_tree_id: str | None
    success_metric: str
    tags: list[str] = Field(default_factory=list)


def _q(
    question_id: str,
    scenario_id: str,
    title: str,
    description: str,
    success_metric: str,
    *,
    probing_tree_id: str | None = None,
    tags: list[str] | None = None,
) -> BusinessQuestion:
    return BusinessQuestion(
        id=question_id,
        scenario_id=scenario_id,
        title=title,
        description=description,
        probing_tree_id=probing_tree_id,
        success_metric=success_metric,
        tags=tags or [],
    )


_QUESTIONS: list[BusinessQuestion] = [
    _q(
        "q_nm26_repeat_purchase",
        "nutrimix_2_6",
        "How can we improve repeat purchase for NutriMix?",
        (
            "Nutrimix gets healthy initial adoption but repeat behavior is inconsistent. "
            "We need to identify which levers create an enduring household habit."
        ),
        "repeat_rate",
        probing_tree_id="repeat_purchase_low",
        tags=["retention", "habit", "pricing"],
    ),
    _q(
        "q_nm26_first_trial",
        "nutrimix_2_6",
        "What drives first-time trial among health-anxious parents?",
        (
            "Some parents actively worry about immunity and growth yet still hesitate on trial. "
            "This question tests what combination of trust and messaging unlocks first purchase."
        ),
        "trial_openness",
        tags=["trial", "health_anxiety", "trust"],
    ),
    _q(
        "q_nm26_lj_pass_effectiveness",
        "nutrimix_2_6",
        "How effective is the LJ Pass in building purchase habits?",
        (
            "The LJ Pass is designed to reduce reorder friction and improve retention economics. "
            "We need to understand where it helps most and where it still fails."
        ),
        "repeat_rate",
        tags=["retention", "subscription", "lj_pass"],
    ),
    _q(
        "q_nm26_segment_potential",
        "nutrimix_2_6",
        "Which parent segments show highest untapped potential?",
        (
            "Current adoption may hide valuable micro-segments that are close to conversion. "
            "This question surfaces high-potential cohorts and the right activation levers."
        ),
        "barrier_reduction",
        tags=["segmentation", "targeting", "growth"],
    ),
    _q(
        "q_nm714_brand_extension",
        "nutrimix_7_14",
        "Can the NutriMix brand extend credibly to older children?",
        (
            "Nutrimix's toddler associations may weaken credibility for school-age kids. "
            "We need to test if positioning and proof can bridge that gap."
        ),
        "adoption_rate",
        probing_tree_id="nutrimix_7_14_expansion",
        tags=["positioning", "brand_extension", "school_age"],
    ),
    _q(
        "q_nm714_school_trust",
        "nutrimix_7_14",
        "What role do school partnerships play in building trust?",
        (
            "Schools and peer ecosystems can materially influence parent decisions for older kids. "
            "This question estimates trust lift from school-linked signals."
        ),
        "trust_lift",
        tags=["trust", "school_partnership", "channels"],
    ),
    _q(
        "q_nm714_taste_by_age",
        "nutrimix_7_14",
        "How do taste preferences differ between age groups?",
        (
            "Taste acceptability may be the core usage barrier as kids get older. "
            "This question identifies age-linked taste and format breakpoints."
        ),
        "taste_acceptance",
        tags=["taste", "age_group", "product_fit"],
    ),
    _q(
        "q_mg_trial_drivers",
        "magnesium_gummies",
        "What drives initial trial for a new gummy supplement?",
        (
            "Magnesium gummies are a newer category with uneven awareness and trust. "
            "We need to isolate which trial triggers matter most."
        ),
        "adoption_rate",
        probing_tree_id="magnesium_gummies_growth",
        tags=["trial", "category_creation", "awareness"],
    ),
    _q(
        "q_mg_doctor_vs_peer",
        "magnesium_gummies",
        "How important is pediatrician endorsement vs peer recommendation?",
        (
            "Parents often blend medical authority and social proof when evaluating supplements. "
            "This question quantifies which source drives stronger movement to trial."
        ),
        "trust_lift",
        tags=["trust", "pediatrician", "peer_influence"],
    ),
    _q(
        "q_mg_concern_match",
        "magnesium_gummies",
        "Which parent concerns does this product address most effectively?",
        (
            "The gummy proposition may resonate differently across sleep, calm, and focus concerns. "
            "This question maps concern fit to likelihood of conversion."
        ),
        "concern_match",
        tags=["positioning", "benefits", "concerns"],
    ),
    _q(
        "q_pm_adoption_barriers",
        "protein_mix",
        "What are the primary barriers to protein supplement adoption?",
        (
            "ProteinMix faces skepticism around need, routine fit, and child acceptance. "
            "We need to rank the biggest barriers and their segment concentration."
        ),
        "adoption_rate",
        probing_tree_id="protein_mix_launch",
        tags=["barriers", "protein", "adoption"],
    ),
    _q(
        "q_pm_price_point",
        "protein_mix",
        "How does the higher price point affect consideration?",
        (
            "At ₹799, ProteinMix may cross affordability thresholds for value-focused households. "
            "This question quantifies price sensitivity and value framing requirements."
        ),
        "price_elasticity",
        tags=["pricing", "consideration", "value"],
    ),
    _q(
        "q_pm_sports_partnership",
        "protein_mix",
        "Does sports club partnership move the needle for active families?",
        (
            "Sports-affiliated contexts may increase relevance for protein supplementation. "
            "This question tests whether those partnerships produce meaningful lift."
        ),
        "adoption_rate",
        tags=["partnerships", "sports", "targeting"],
    ),
]

_QUESTION_BY_ID: dict[str, BusinessQuestion] = {question.id: question for question in _QUESTIONS}
_QUESTIONS_BY_SCENARIO: dict[str, list[BusinessQuestion]] = defaultdict(list)
for _question in _QUESTIONS:
    _QUESTIONS_BY_SCENARIO[_question.scenario_id].append(_question)


def _lightweight_tree(
    *,
    question_id: str,
    scenario_id: str,
    title: str,
    context: str,
    success_metric: str,
    hypotheses: list[Hypothesis],
) -> ProblemTreeDefinition:
    probes = []
    order = 1
    for hypothesis in hypotheses:
        probes.append(
            _interview_probe(
                f"{hypothesis.id}_i1",
                hypothesis.id,
                f"From your perspective, what is the strongest signal for: {title.lower()}",
                order,
            )
        )
        order += 1
        probes.append(
            _simulation_probe(
                f"{hypothesis.id}_s1",
                hypothesis.id,
                hypothesis.counterfactual_modifications or {},
                success_metric,
                order,
            )
        )
        order += 1
        probes.append(
            _attribute_probe(
                f"{hypothesis.id}_a1",
                hypothesis.id,
                hypothesis.indicator_attributes[:3],
                "outcome",
                order,
            )
        )
        order += 1

    return ProblemTreeDefinition(
        problem=ProblemStatement(
            id=f"light_{question_id}",
            title=title,
            scenario_id=scenario_id,
            context=context,
            success_metric=success_metric,
        ),
        hypotheses=hypotheses,
        probes=probes,
    )


_LIGHTWEIGHT_TREES: dict[str, ProblemTreeDefinition] = {
    "q_nm26_first_trial": _lightweight_tree(
        question_id="q_nm26_first_trial",
        scenario_id="nutrimix_2_6",
        title="What drives first-time trial among health-anxious parents?",
        context="Tests trial unlocks across trust, proof, and routine fit for anxious parents.",
        success_metric="trial_openness",
        hypotheses=[
            Hypothesis(
                id="h_trial_medical_proof",
                problem_id="light_q_nm26_first_trial",
                title="Doctor-backed proof unlocks first trial",
                rationale="Health-anxious parents often need authoritative validation before first use.",
                indicator_attributes=["health_anxiety", "medical_authority_trust", "self_research_tendency"],
                counterfactual_modifications={"marketing.pediatrician_endorsement": True},
                order=1,
            ),
            Hypothesis(
                id="h_trial_low_friction",
                problem_id="light_q_nm26_first_trial",
                title="Lower effort and price-framing improve trial",
                rationale="First trial converts when perceived risk and setup effort are reduced.",
                indicator_attributes=["budget_consciousness", "deal_seeking_intensity", "mental_bandwidth"],
                counterfactual_modifications={"product.effort_to_acquire": 0.2, "product.price_inr": 499.0},
                order=2,
            ),
        ],
    ),
    "q_nm26_lj_pass_effectiveness": _lightweight_tree(
        question_id="q_nm26_lj_pass_effectiveness",
        scenario_id="nutrimix_2_6",
        title="How effective is the LJ Pass in building purchase habits?",
        context="Evaluates whether pass mechanics improve reorder consistency and lower churn risk.",
        success_metric="repeat_rate",
        hypotheses=[
            Hypothesis(
                id="h_pass_habit_loop",
                problem_id="light_q_nm26_lj_pass_effectiveness",
                title="Pass nudges convert occasional users into habitual users",
                rationale="Subscription-like mechanics may make repeat decisions less effortful.",
                indicator_attributes=["subscription_comfort", "perceived_time_scarcity", "impulse_purchase_tendency"],
                counterfactual_modifications={"lj_pass_available": True},
                order=1,
            ),
            Hypothesis(
                id="h_pass_value_signal",
                problem_id="light_q_nm26_lj_pass_effectiveness",
                title="Pass value proposition matters more than mechanics",
                rationale="Parents adopt pass behavior only when monthly savings feel tangible.",
                indicator_attributes=["budget_consciousness", "deal_seeking_intensity", "value_perception_driver"],
                counterfactual_modifications={"marketing.discount_available": 0.15},
                order=2,
            ),
        ],
    ),
    "q_nm26_segment_potential": _lightweight_tree(
        question_id="q_nm26_segment_potential",
        scenario_id="nutrimix_2_6",
        title="Which parent segments show highest untapped potential?",
        context="Finds high-opportunity segments that are close to conversion but under-targeted.",
        success_metric="barrier_reduction",
        hypotheses=[
            Hypothesis(
                id="h_seg_persuadable_mid_income",
                problem_id="light_q_nm26_segment_potential",
                title="Mid-income urban households are under-converted",
                rationale="These households often have need but stall at consideration and purchase.",
                indicator_attributes=["city_tier", "socioeconomic_class", "budget_consciousness"],
                counterfactual_modifications={"product.price_inr": 529.0},
                order=1,
            ),
            Hypothesis(
                id="h_seg_trust_sensitive",
                problem_id="light_q_nm26_segment_potential",
                title="Trust-sensitive segments need stronger authority cues",
                rationale="Certain cohorts need stronger proof and familiar recommendation channels.",
                indicator_attributes=["medical_authority_trust", "pediatrician_influence", "peer_influence_strength"],
                counterfactual_modifications={"marketing.pediatrician_endorsement": True},
                order=2,
            ),
        ],
    ),
    "q_nm714_school_trust": _lightweight_tree(
        question_id="q_nm714_school_trust",
        scenario_id="nutrimix_7_14",
        title="What role do school partnerships play in building trust?",
        context="Assesses trust impact of school-origin endorsements and contexts for older kids.",
        success_metric="trust_lift",
        hypotheses=[
            Hypothesis(
                id="h_school_social_proof",
                problem_id="light_q_nm714_school_trust",
                title="School signals raise perceived legitimacy",
                rationale="Parents see school-linked products as safer and more vetted.",
                indicator_attributes=["community_orientation", "peer_influence_strength", "risk_tolerance"],
                counterfactual_modifications={"marketing.school_partnership": True},
                order=1,
            ),
            Hypothesis(
                id="h_school_channel_fit",
                problem_id="light_q_nm714_school_trust",
                title="School channel helps only for specific parent segments",
                rationale="School trust gains vary with city context and social decision norms.",
                indicator_attributes=["city_tier", "socioeconomic_class", "community_orientation"],
                counterfactual_modifications={"marketing.school_partnership": True, "marketing.social_proof": 0.7},
                order=2,
            ),
        ],
    ),
    "q_nm714_taste_by_age": _lightweight_tree(
        question_id="q_nm714_taste_by_age",
        scenario_id="nutrimix_7_14",
        title="How do taste preferences differ between age groups?",
        context="Explores whether taste resistance increases with age and drives rejection.",
        success_metric="taste_acceptance",
        hypotheses=[
            Hypothesis(
                id="h_taste_older_resistance",
                problem_id="light_q_nm714_taste_by_age",
                title="Older children have sharper taste rejection",
                rationale="School-age children can veto products more strongly than toddlers.",
                indicator_attributes=["child_taste_veto", "oldest_child_age", "snacking_pattern"],
                counterfactual_modifications={"product.taste_appeal": 0.85},
                order=1,
            ),
            Hypothesis(
                id="h_taste_format_mismatch",
                problem_id="light_q_nm714_taste_by_age",
                title="Format mismatch drives perceived taste dislike",
                rationale="Powder format can be perceived as effortful and less acceptable.",
                indicator_attributes=["convenience_food_acceptance", "mental_bandwidth", "child_taste_veto"],
                counterfactual_modifications={"product.form_factor": "ready_to_drink"},
                order=2,
            ),
        ],
    ),
    "q_mg_doctor_vs_peer": _lightweight_tree(
        question_id="q_mg_doctor_vs_peer",
        scenario_id="magnesium_gummies",
        title="How important is pediatrician endorsement vs peer recommendation?",
        context="Compares authority and social pathways in a newer supplement category.",
        success_metric="trust_lift",
        hypotheses=[
            Hypothesis(
                id="h_doctor_authority",
                problem_id="light_q_mg_doctor_vs_peer",
                title="Doctor endorsement drives larger trust gains",
                rationale="Medical signaling may reduce perceived category risk more effectively than peers.",
                indicator_attributes=["medical_authority_trust", "risk_tolerance", "science_literacy"],
                counterfactual_modifications={"marketing.pediatrician_endorsement": True},
                order=1,
            ),
            Hypothesis(
                id="h_peer_social_norm",
                problem_id="light_q_mg_doctor_vs_peer",
                title="Peer recommendation matters more for routine adoption",
                rationale="Parents may adopt faster when recommendations arrive via familiar parent networks.",
                indicator_attributes=["peer_influence_strength", "social_proof_bias", "community_orientation"],
                counterfactual_modifications={"marketing.social_proof": 0.75},
                order=2,
            ),
        ],
    ),
    "q_mg_concern_match": _lightweight_tree(
        question_id="q_mg_concern_match",
        scenario_id="magnesium_gummies",
        title="Which parent concerns does this product address most effectively?",
        context="Maps product resonance across calming, sleep, and focus-related parent concerns.",
        success_metric="concern_match",
        hypotheses=[
            Hypothesis(
                id="h_concern_sleep_focus",
                problem_id="light_q_mg_concern_match",
                title="Sleep and focus concerns are strongest entry points",
                rationale="Concern-to-benefit match can drive faster movement through consideration.",
                indicator_attributes=["health_anxiety", "nutrition_gap_awareness", "child_health_proactivity"],
                counterfactual_modifications={"marketing.perceived_quality": 0.75},
                order=1,
            ),
            Hypothesis(
                id="h_concern_message_clarity",
                problem_id="light_q_mg_concern_match",
                title="Clarity of concern framing drives conversion",
                rationale="Parents convert when messaging is concrete and tied to daily issues.",
                indicator_attributes=["information_need", "self_research_tendency", "decision_speed"],
                counterfactual_modifications={"marketing.trust_signal": 0.7},
                order=2,
            ),
        ],
    ),
    "q_pm_price_point": _lightweight_tree(
        question_id="q_pm_price_point",
        scenario_id="protein_mix",
        title="How does the higher price point affect consideration?",
        context="Tests price elasticity and perceived value barriers for ProteinMix at ₹799.",
        success_metric="price_elasticity",
        hypotheses=[
            Hypothesis(
                id="h_pm_price_barrier",
                problem_id="light_q_pm_price_point",
                title="High ticket price causes consideration drop-off",
                rationale="At current price, many households may not progress beyond evaluation.",
                indicator_attributes=["budget_consciousness", "deal_seeking_intensity", "price_reference_point"],
                counterfactual_modifications={"product.price_inr": 699.0},
                order=1,
            ),
            Hypothesis(
                id="h_pm_value_bundle",
                problem_id="light_q_pm_price_point",
                title="Value framing can offset higher price perception",
                rationale="If benefits are clearer, parents accept a premium more readily.",
                indicator_attributes=["value_perception_driver", "medical_authority_trust", "brand_loyalty_tendency"],
                counterfactual_modifications={"marketing.perceived_quality": 0.75, "marketing.discount_available": 0.1},
                order=2,
            ),
        ],
    ),
    "q_pm_sports_partnership": _lightweight_tree(
        question_id="q_pm_sports_partnership",
        scenario_id="protein_mix",
        title="Does sports club partnership move the needle for active families?",
        context="Evaluates relevance lift from sports-linked distribution and credibility cues.",
        success_metric="adoption_rate",
        hypotheses=[
            Hypothesis(
                id="h_pm_sports_relevance",
                problem_id="light_q_pm_sports_partnership",
                title="Sports context increases perceived relevance",
                rationale="Parents of active kids may view protein benefits as more immediate and justified.",
                indicator_attributes=["fitness_engagement", "community_orientation", "peer_influence_strength"],
                counterfactual_modifications={"marketing.school_partnership": True},
                order=1,
            ),
            Hypothesis(
                id="h_pm_sports_trust",
                problem_id="light_q_pm_sports_partnership",
                title="Partnerships improve trust and trial confidence",
                rationale="Formal affiliations can reduce skepticism for newer supplements.",
                indicator_attributes=["risk_tolerance", "medical_authority_trust", "social_proof_bias"],
                counterfactual_modifications={"marketing.school_partnership": True, "marketing.trust_signal": 0.75},
                order=2,
            ),
        ],
    ),
}


def list_all_questions() -> list[BusinessQuestion]:
    """Return all questions across all scenarios."""

    return list(_QUESTIONS)


def get_questions_for_scenario(scenario_id: str) -> list[BusinessQuestion]:
    """Return all business questions for a scenario."""

    return list(_QUESTIONS_BY_SCENARIO.get(scenario_id, []))


def get_question(question_id: str) -> BusinessQuestion:
    """Return a single question by ID. Raises KeyError if not found."""

    if question_id not in _QUESTION_BY_ID:
        raise KeyError(f"Unknown question_id: {question_id}")
    return _QUESTION_BY_ID[question_id]


def get_tree_for_question(question_id: str) -> ProblemTreeDefinition:
    """Return probing tree definition for a question (predefined or lightweight)."""

    question = get_question(question_id)
    if question.probing_tree_id:
        problem, hypotheses, probes = get_problem_tree(question.probing_tree_id)
        return ProblemTreeDefinition(problem=problem, hypotheses=hypotheses, probes=probes)
    if question_id not in _LIGHTWEIGHT_TREES:
        raise KeyError(f"No probing tree configured for question_id: {question_id}")
    return _LIGHTWEIGHT_TREES[question_id]

