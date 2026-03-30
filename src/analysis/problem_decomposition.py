"""Template-driven problem decomposition with cohort sizing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from src.analysis.problem_templates import PROBLEM_TEMPLATES

if TYPE_CHECKING:
    from src.analysis.cohort_classifier import PopulationCohorts
    from src.decision.scenarios import ScenarioConfig
    from src.generation.population import Population
    from src.probing.question_bank import BusinessQuestion


class SubProblem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    cohort_id: str
    probe_focus: str
    indicator_variables: list[str] = Field(default_factory=list)


class CohortDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    filter_criteria: dict[str, Any] = Field(default_factory=dict)
    size: int
    research_objective: str


class ProblemDecomposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: str
    problem_title: str
    sub_problems: list[SubProblem]
    cohorts: list[CohortDefinition]


_COHORT_DISPLAY = {
    "never_aware": (
        "Never Aware",
        "Rejected before awareness was established for this scenario.",
        "Raise salience and relevance enough to enter consideration.",
    ),
    "aware_not_tried": (
        "Aware But Not Tried",
        "Reached awareness but did not convert in baseline static evaluation.",
        "Identify trust/value barriers preventing first conversion.",
    ),
    "first_time_buyer": (
        "First-Time Buyer",
        "Adopted, then churned quickly in months 1-2.",
        "Find what breaks before a stable habit forms.",
    ),
    "current_user": (
        "Current User",
        "Adopted and stayed active through the baseline simulation horizon.",
        "Protect retention drivers and codify success patterns.",
    ),
    "lapsed_user": (
        "Lapsed User",
        "Adopted, built some momentum, then churned in month 3+.",
        "Understand delayed drop-off and re-engagement triggers.",
    ),
}


def _scenario_subproblems(scenario_id: str) -> list[dict[str, Any]]:
    specs: dict[str, list[dict[str, Any]]] = {
        "nutrimix_2_6": [
            {
                "title": "Perception decay",
                "description": "Value perception drops after initial novelty and first pack completion.",
                "cohort_id": "current_user",
                "probe_focus": "What sustains trust and reorder intent over time?",
                "indicator_variables": ["brand_salience", "trust", "perceived_value"],
            },
            {
                "title": "Child taste fatigue",
                "description": "Child acceptance weakens after repeated usage and routine monotony.",
                "cohort_id": "lapsed_user",
                "probe_focus": "Why did child acceptance decline after adoption?",
                "indicator_variables": ["child_acceptance", "fatigue", "habit_strength"],
            },
            {
                "title": "Cost comparison / switching",
                "description": "Families reassess value against mainstream alternatives at reorder points.",
                "cohort_id": "lapsed_user",
                "probe_focus": "What price-value tradeoff triggered switching or delay?",
                "indicator_variables": ["price_salience", "perceived_value", "discretionary_budget"],
            },
            {
                "title": "Habit formation failure",
                "description": "Initial trial does not convert into a durable household routine.",
                "cohort_id": "first_time_buyer",
                "probe_focus": "Why did the product remain a one-off trial?",
                "indicator_variables": ["habit_strength", "reorder_urgency", "effort_friction"],
            },
            {
                "title": "Re-engagement failure",
                "description": "Dropped users do not return despite prior trial and familiarity.",
                "cohort_id": "lapsed_user",
                "probe_focus": "What reminder or trigger would have brought them back?",
                "indicator_variables": ["brand_salience", "trust", "reorder_urgency"],
            },
        ],
        "nutrimix_7_14": [
            {
                "title": "Age-positioning mismatch",
                "description": "Older-child families perceive legacy toddler positioning as less relevant.",
                "cohort_id": "aware_not_tried",
                "probe_focus": "Which framing would make 7-14 relevance explicit?",
                "indicator_variables": ["need_score", "awareness_score", "consideration_score"],
            },
            {
                "title": "Peer-context credibility gap",
                "description": "School-age contexts raise social proof requirements before adoption.",
                "cohort_id": "aware_not_tried",
                "probe_focus": "What trust signal closes credibility gaps for older children?",
                "indicator_variables": ["trust", "social_proof_bias", "peer_influence_strength"],
            },
            {
                "title": "Taste and format drop-off",
                "description": "Taste expectations and usage rituals differ for older kids.",
                "cohort_id": "first_time_buyer",
                "probe_focus": "What drives early post-trial rejection in this age band?",
                "indicator_variables": ["child_acceptance", "fatigue", "effort_friction"],
            },
            {
                "title": "Category competition pressure",
                "description": "Alternative products outperform on perceived fit for older-child goals.",
                "cohort_id": "lapsed_user",
                "probe_focus": "Which competitor attributes outcompete repeat purchase?",
                "indicator_variables": ["perceived_value", "price_salience", "brand_salience"],
            },
            {
                "title": "Message-to-routine disconnect",
                "description": "Stated benefits fail to translate into daily-use consistency.",
                "cohort_id": "current_user",
                "probe_focus": "Which routines make retention resilient in this cohort?",
                "indicator_variables": ["habit_strength", "reorder_urgency", "trust"],
            },
        ],
        "magnesium_gummies": [
            {
                "title": "Awareness deficit",
                "description": "Large segments never accumulate enough category/product salience.",
                "cohort_id": "never_aware",
                "probe_focus": "Which channels produce first meaningful awareness lift?",
                "indicator_variables": ["brand_salience", "awareness_score", "ad_receptivity"],
            },
            {
                "title": "Trust threshold failure",
                "description": "Awareness exists but perceived medical legitimacy remains weak.",
                "cohort_id": "aware_not_tried",
                "probe_focus": "What evidence format moves trust into trial territory?",
                "indicator_variables": ["trust", "medical_authority_trust", "consideration_score"],
            },
            {
                "title": "Candy-vs-supplement confusion",
                "description": "Product framing ambiguity undermines sustained usage confidence.",
                "cohort_id": "first_time_buyer",
                "probe_focus": "Why does early curiosity fail to become routine use?",
                "indicator_variables": ["perceived_value", "trust", "habit_strength"],
            },
            {
                "title": "Benefit-proof mismatch",
                "description": "Claimed outcomes are not reinforced strongly enough post-trial.",
                "cohort_id": "lapsed_user",
                "probe_focus": "Which missing proof points cause delayed churn?",
                "indicator_variables": ["fatigue", "child_acceptance", "trust"],
            },
            {
                "title": "Retention driver concentration",
                "description": "Only a subset develops enough positive momentum to stay active.",
                "cohort_id": "current_user",
                "probe_focus": "What factors characterize durable users in this category?",
                "indicator_variables": ["habit_strength", "reorder_urgency", "perceived_value"],
            },
        ],
        "protein_mix": [
            {
                "title": "Effort friction at trial gate",
                "description": "Preparation burden blocks conversion despite baseline awareness.",
                "cohort_id": "aware_not_tried",
                "probe_focus": "Which routine constraints block first purchase decisions?",
                "indicator_variables": ["effort_friction", "purchase_score", "perceived_time_scarcity"],
            },
            {
                "title": "Routine complexity drop-off",
                "description": "Early adopters fail to sustain repeated preparation behavior.",
                "cohort_id": "first_time_buyer",
                "probe_focus": "What makes preparation habits collapse in months 1-2?",
                "indicator_variables": ["habit_strength", "effort_friction", "fatigue"],
            },
            {
                "title": "Value-for-effort imbalance",
                "description": "Perceived gains do not justify recurring time and cost burden.",
                "cohort_id": "lapsed_user",
                "probe_focus": "At what point does value no longer justify effort?",
                "indicator_variables": ["perceived_value", "price_salience", "effort_friction"],
            },
            {
                "title": "Need framing weakness",
                "description": "Some families never perceive strong protein need for their child context.",
                "cohort_id": "never_aware",
                "probe_focus": "How should need recognition be reframed for relevance?",
                "indicator_variables": ["need_score", "awareness_score", "supplement_necessity_belief"],
            },
            {
                "title": "Retention blueprint concentration",
                "description": "A narrow set of households maintains repeat behavior successfully.",
                "cohort_id": "current_user",
                "probe_focus": "Which behaviors protect consistency among current users?",
                "indicator_variables": ["habit_strength", "child_acceptance", "reorder_urgency"],
            },
        ],
    }
    return specs.get(scenario_id, [])


def _template_problem_title(scenario_id: str, question: BusinessQuestion) -> str:
    template = PROBLEM_TEMPLATES.get(scenario_id, {})
    template_title = str(template.get("problem", "")).strip()
    if template_title:
        return template_title
    return question.title


def decompose_problem(
    scenario: ScenarioConfig,
    question: BusinessQuestion,
    population: Population,
    cohorts: PopulationCohorts,
) -> ProblemDecomposition:
    """Decompose a business problem into sub-problems + cohorts."""

    _ = population
    subproblem_specs = _scenario_subproblems(scenario.id)
    sub_problems = [
        SubProblem(
            id=f"{scenario.id}_sp_{index}",
            title=spec["title"],
            description=spec["description"],
            cohort_id=spec["cohort_id"],
            probe_focus=spec["probe_focus"],
            indicator_variables=list(spec["indicator_variables"]),
        )
        for index, spec in enumerate(subproblem_specs, start=1)
    ]

    cohort_defs = [
        CohortDefinition(
            id=cohort_id,
            name=name,
            description=description,
            filter_criteria={"product_relationship": cohort_id},
            size=int(cohorts.summary.get(cohort_id, 0)),
            research_objective=objective,
        )
        for cohort_id, (name, description, objective) in _COHORT_DISPLAY.items()
    ]

    return ProblemDecomposition(
        problem_id=question.id,
        problem_title=_template_problem_title(scenario.id, question),
        sub_problems=sub_problems,
        cohorts=cohort_defs,
    )
