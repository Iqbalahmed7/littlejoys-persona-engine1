"""Intervention quadrant engine for mapping insights to runnable scenario variants."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict

from src.decision.scenarios import ScenarioConfig  # noqa: TC001
from src.simulation.counterfactual import apply_scenario_modifications

if TYPE_CHECKING:
    from src.generation.population import Population

_QUADRANT_KEYS = (
    "general_temporal",
    "general_non_temporal",
    "cohort_temporal",
    "cohort_non_temporal",
)


def quadrant_key(scope: str, temporality: str) -> str:
    """Map intervention metadata to the 2x2 quadrant key used across pages."""

    mapping = {
        ("general", "temporal"): "general_temporal",
        ("general", "non_temporal"): "general_non_temporal",
        ("cohort_specific", "temporal"): "cohort_temporal",
        ("cohort_specific", "non_temporal"): "cohort_non_temporal",
    }
    return mapping.get((scope, temporality), "general_non_temporal")


class Intervention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    scope: Literal["general", "cohort_specific"]
    temporality: Literal["temporal", "non_temporal"]
    target_cohort_id: str | None
    parameter_modifications: dict[str, Any]
    expected_mechanism: str


class InterventionQuadrant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: str
    quadrants: dict[str, list[Intervention]]


class SimulationRunConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intervention_id: str
    intervention_name: str
    scope: str
    temporality: str
    target_cohort_id: str | None
    scenario_config: ScenarioConfig
    population_filter: dict[str, Any] | None
    duration_months: int


class InterventionInput(BaseModel):
    """Minimal input shape for intervention generation."""

    model_config = ConfigDict(extra="allow")

    problem_id: str


def _i(
    *,
    id: str,
    name: str,
    description: str,
    scope: Literal["general", "cohort_specific"],
    temporality: Literal["temporal", "non_temporal"],
    target_cohort_id: str | None,
    parameter_modifications: dict[str, Any],
    expected_mechanism: str,
) -> Intervention:
    return Intervention(
        id=id,
        name=name,
        description=description,
        scope=scope,
        temporality=temporality,
        target_cohort_id=target_cohort_id,
        parameter_modifications=parameter_modifications,
        expected_mechanism=expected_mechanism,
    )


def _templates() -> dict[str, dict[str, list[Intervention]]]:
    return {
        "nutrimix_2_6": {
            "general_non_temporal": [
                _i(
                    id="nm26_discount_returning_15",
                    name="15% Returning Customer Discount",
                    description="Apply a targeted 15% repeat-buyer discount.",
                    scope="general",
                    temporality="non_temporal",
                    target_cohort_id=None,
                    parameter_modifications={"marketing.discount_available": 0.15},
                    expected_mechanism="Reduces price friction at the reorder moment.",
                ),
                _i(
                    id="nm26_free_sample_flavor",
                    name="Free Sample of New Flavour",
                    description="Ship a free flavour trial to improve acceptance.",
                    scope="general",
                    temporality="non_temporal",
                    target_cohort_id=None,
                    parameter_modifications={"product.taste_appeal": 0.8},
                    expected_mechanism="Raises child acceptance and perceived novelty.",
                ),
                _i(
                    id="nm26_peds_campaign",
                    name="Pediatrician Endorsement Campaign",
                    description="Scale doctor-led trust messaging for repeat purchase.",
                    scope="general",
                    temporality="non_temporal",
                    target_cohort_id=None,
                    parameter_modifications={"marketing.pediatrician_endorsement": True},
                    expected_mechanism="Improves trust and reduces post-trial drop-off.",
                ),
            ],
            "general_temporal": [
                _i(
                    id="nm26_lj_pass_199_quarter",
                    name="LJ Pass (₹199/quarter)",
                    description="Auto-reorder + 5% cashback for subscribers.",
                    scope="general",
                    temporality="temporal",
                    target_cohort_id=None,
                    parameter_modifications={
                        "lj_pass_available": True,
                        "lj_pass.monthly_price_inr": 66.33,
                        "lj_pass.discount_percent": 5.0,
                    },
                    expected_mechanism="Locks in habit via commitment and lower friction.",
                ),
                _i(
                    id="nm26_recipe_subscription",
                    name="Monthly Recipe Content Subscription",
                    description="Monthly recipe drops to reduce taste fatigue.",
                    scope="general",
                    temporality="temporal",
                    target_cohort_id=None,
                    parameter_modifications={"product.taste_appeal": 0.82},
                    expected_mechanism="Mitigates boredom and sustains repeat usage.",
                ),
                _i(
                    id="nm26_brand_ambassador",
                    name="Brand Ambassador Program",
                    description="Community ambassador-led advocacy and reminders.",
                    scope="general",
                    temporality="temporal",
                    target_cohort_id=None,
                    parameter_modifications={"marketing.social_buzz": 0.75},
                    expected_mechanism="Sustains salience and social proof over time.",
                ),
            ],
            "cohort_non_temporal": [
                _i(
                    id="nm26_lapsed_coupon_100",
                    name='Lapsed Users: "We Miss You" ₹100 Coupon',
                    description="One-time ₹100 comeback coupon for lapsed users.",
                    scope="cohort_specific",
                    temporality="non_temporal",
                    target_cohort_id="lapsed_user",
                    parameter_modifications={"marketing.discount_available": 0.17},
                    expected_mechanism="Re-activates lapsed users via immediate value.",
                ),
                _i(
                    id="nm26_first_time_starter_kit",
                    name="First-time Buyers: Starter Kit Bundle Discount",
                    description="Discounted first-cycle bundle for new adopters.",
                    scope="cohort_specific",
                    temporality="non_temporal",
                    target_cohort_id="first_time_buyer",
                    parameter_modifications={"product.effort_to_acquire": 0.2},
                    expected_mechanism="Lowers onboarding friction in the first cycle.",
                ),
                _i(
                    id="nm26_current_referral_150",
                    name="Current Users: Referral Reward (₹150 per referral)",
                    description="Reward active users for bringing in peers.",
                    scope="cohort_specific",
                    temporality="non_temporal",
                    target_cohort_id="current_user",
                    parameter_modifications={"marketing.social_buzz": 0.7},
                    expected_mechanism="Turns loyal users into acquisition multipliers.",
                ),
            ],
            "cohort_temporal": [
                _i(
                    id="nm26_lapsed_day22_nudge",
                    name="Lapsed Users: Day-22 Reminder + Flavour Rotation",
                    description="Re-engagement nudges before expected pack depletion.",
                    scope="cohort_specific",
                    temporality="temporal",
                    target_cohort_id="lapsed_user",
                    parameter_modifications={"product.taste_appeal": 0.83},
                    expected_mechanism="Pre-empts lapse through timely reminder + novelty.",
                ),
                _i(
                    id="nm26_current_loyalty_tiers",
                    name="Current Users: Loyalty Tier Program (Bronze→Silver→Gold)",
                    description="Progressive loyalty perks for sustained repeats.",
                    scope="cohort_specific",
                    temporality="temporal",
                    target_cohort_id="current_user",
                    parameter_modifications={"lj_pass.retention_boost": 0.2},
                    expected_mechanism="Increases switching costs and repeat consistency.",
                ),
                _i(
                    id="nm26_first_time_90d_nudge",
                    name="First-time Buyers: 90-day Habit Formation Nudge Sequence",
                    description="Guided reminders and routines for first 90 days.",
                    scope="cohort_specific",
                    temporality="temporal",
                    target_cohort_id="first_time_buyer",
                    parameter_modifications={"marketing.awareness_budget": 0.65},
                    expected_mechanism="Builds routine before early habit decay.",
                ),
            ],
        },
        "nutrimix_7_14": {
            "general_non_temporal": [
                _i(
                    id="nm714_school_bundle_offer",
                    name="School Bundle Offer",
                    description="Bundle pricing for school-age families.",
                    scope="general",
                    temporality="non_temporal",
                    target_cohort_id=None,
                    parameter_modifications={"marketing.discount_available": 0.12},
                    expected_mechanism="Improves value perception for larger serving needs.",
                ),
                _i(
                    id="nm714_age_fit_creative",
                    name="Age-specific Creative Refresh",
                    description="Reposition benefits for older children.",
                    scope="general",
                    temporality="non_temporal",
                    target_cohort_id=None,
                    parameter_modifications={"product.health_relevance": 0.7},
                    expected_mechanism="Improves need recognition for the older-age segment.",
                ),
            ],
            "general_temporal": [
                _i(
                    id="nm714_weekly_school_challenge",
                    name="Weekly School Challenge Program",
                    description="Monthly challenge loops to reinforce usage.",
                    scope="general",
                    temporality="temporal",
                    target_cohort_id=None,
                    parameter_modifications={"marketing.school_partnership": True},
                    expected_mechanism="Adds routine hooks in school environments.",
                ),
            ],
            "cohort_non_temporal": [
                _i(
                    id="nm714_low_income_trial_pack",
                    name="Low-income Cohort Trial Pack",
                    description="Smaller, lower-cost trial pack for value-sensitive families.",
                    scope="cohort_specific",
                    temporality="non_temporal",
                    target_cohort_id="low_income_families",
                    parameter_modifications={"product.price_inr": 549.0},
                    expected_mechanism="Lowers trial barrier in price-sensitive cohorts.",
                ),
            ],
            "cohort_temporal": [
                _i(
                    id="nm714_high_need_reminder_path",
                    name="High-need Cohort Reminder Path",
                    description="Timed reminder path for high-need rejecters.",
                    scope="cohort_specific",
                    temporality="temporal",
                    target_cohort_id="high_need_rejecters",
                    parameter_modifications={"marketing.social_buzz": 0.55},
                    expected_mechanism="Increases follow-up touchpoints for reconsideration.",
                ),
            ],
        },
        "magnesium_gummies": {
            "general_non_temporal": [
                _i(
                    id="mg_demo_bundle",
                    name="Trial Gummy Demo Bundle",
                    description="Low-risk sample bundle for first purchase.",
                    scope="general",
                    temporality="non_temporal",
                    target_cohort_id=None,
                    parameter_modifications={"product.price_inr": 449.0},
                    expected_mechanism="Reduces skepticism through low-stakes trial.",
                ),
            ],
            "general_temporal": [
                _i(
                    id="mg_sleep_routine_plan",
                    name="30-day Sleep Routine Plan",
                    description="Guided sequence to anchor nightly habit.",
                    scope="general",
                    temporality="temporal",
                    target_cohort_id=None,
                    parameter_modifications={"marketing.awareness_budget": 0.6},
                    expected_mechanism="Converts one-off trial into routine use.",
                ),
            ],
            "cohort_non_temporal": [
                _i(
                    id="mg_skeptic_doctor_card",
                    name="Skeptic Cohort: Doctor FAQ Card",
                    description="Medical FAQ insert for trust-sensitive households.",
                    scope="cohort_specific",
                    temporality="non_temporal",
                    target_cohort_id="trust_skeptics",
                    parameter_modifications={"marketing.pediatrician_endorsement": True},
                    expected_mechanism="Addresses safety/efficacy concerns directly.",
                ),
            ],
            "cohort_temporal": [
                _i(
                    id="mg_dropoff_week3_nudge",
                    name="Week-3 Drop-off Cohort Nudge",
                    description="Retention nudges for early drop-off users.",
                    scope="cohort_specific",
                    temporality="temporal",
                    target_cohort_id="week3_dropoffs",
                    parameter_modifications={"marketing.social_buzz": 0.65},
                    expected_mechanism="Recaptures intent before habit collapses.",
                ),
            ],
        },
        "protein_mix": {
            "general_non_temporal": [
                _i(
                    id="pm_easy_prep_pack",
                    name="Easy-prep Starter Pack",
                    description="Lower prep friction with starter accessories.",
                    scope="general",
                    temporality="non_temporal",
                    target_cohort_id=None,
                    parameter_modifications={"product.effort_to_acquire": 0.2},
                    expected_mechanism="Reduces setup burden and improves first-use completion.",
                ),
            ],
            "general_temporal": [
                _i(
                    id="pm_weekly_recipe_feed",
                    name="Weekly Protein Recipe Feed",
                    description="Recipe cadence to maintain usage variety.",
                    scope="general",
                    temporality="temporal",
                    target_cohort_id=None,
                    parameter_modifications={"product.taste_appeal": 0.75},
                    expected_mechanism="Counteracts fatigue and extends repeat cycles.",
                ),
            ],
            "cohort_non_temporal": [
                _i(
                    id="pm_time_scarce_discount",
                    name="Time-scarce Cohort Convenience Discount",
                    description="Price support for convenience-seeking families.",
                    scope="cohort_specific",
                    temporality="non_temporal",
                    target_cohort_id="time_scarce_parents",
                    parameter_modifications={"marketing.discount_available": 0.14},
                    expected_mechanism="Offsets convenience premium perception.",
                ),
            ],
            "cohort_temporal": [
                _i(
                    id="pm_loyalty_commitment",
                    name="Committed Users Loyalty Ladder",
                    description="Tiered rewards for sustained subscription behavior.",
                    scope="cohort_specific",
                    temporality="temporal",
                    target_cohort_id="committed_users",
                    parameter_modifications={"marketing.social_buzz": 0.6},
                    expected_mechanism="Strengthens long-term commitment through escalating rewards.",
                ),
            ],
        },
    }


def generate_intervention_quadrant(
    decomposition: Any,
    scenario: ScenarioConfig,
) -> InterventionQuadrant:
    """Map sub-problems to a 2x2 intervention grid."""

    problem_id = getattr(decomposition, "problem_id", None)
    if not isinstance(problem_id, str) or not problem_id:
        raise ValueError("decomposition must include a non-empty problem_id")
    templates = _templates()
    scenario_templates = templates.get(scenario.id, templates["nutrimix_2_6"])
    quadrants = {key: list(scenario_templates.get(key, [])) for key in _QUADRANT_KEYS}
    return InterventionQuadrant(
        problem_id=problem_id,
        quadrants=quadrants,
    )


def _population_filter_for_cohort(cohort_id: str | None) -> dict[str, Any] | None:
    if cohort_id is None:
        return None
    mapping: dict[str, dict[str, Any]] = {
        "lapsed_users": {"cohort": "lapsed_users", "ever_adopted": True, "is_active": False},
        "lapsed_user": {"cohort": "lapsed_user", "ever_adopted": True, "is_active": False},
        "current_users": {"cohort": "current_users", "is_active": True},
        "current_user": {"cohort": "current_user", "is_active": True},
        "first_time_buyers": {"cohort": "first_time_buyers", "total_purchases_lte": 1},
        "first_time_buyer": {"cohort": "first_time_buyer", "total_purchases_lte": 1},
        "high_need_rejecters": {"cohort": "high_need_rejecters", "outcome": "reject"},
        "low_income_families": {"cohort": "low_income_families", "income_bracket": "low_income"},
        "trust_skeptics": {"cohort": "trust_skeptics", "medical_authority_trust_lte": 0.4},
        "week3_dropoffs": {"cohort": "week3_dropoffs", "churned_month": 1},
        "time_scarce_parents": {"cohort": "time_scarce_parents", "time_scarcity_gte": 0.7},
        "committed_users": {"cohort": "committed_users", "total_purchases_gte": 3},
    }
    return mapping.get(cohort_id, {"cohort": cohort_id})


def generate_simulation_configs(
    quadrant: InterventionQuadrant,
    base_scenario: ScenarioConfig,
    population: Population,
) -> list[SimulationRunConfig]:
    """Convert interventions into runnable simulation configs."""

    del population
    configs: list[SimulationRunConfig] = []
    for interventions in quadrant.quadrants.values():
        for intervention in interventions:
            scenario_config = apply_scenario_modifications(
                base_scenario,
                intervention.parameter_modifications,
            )
            duration_months = (
                max(1, int(base_scenario.months)) if intervention.temporality == "temporal" else 0
            )
            configs.append(
                SimulationRunConfig(
                    intervention_id=intervention.id,
                    intervention_name=intervention.name,
                    scope=intervention.scope,
                    temporality=intervention.temporality,
                    target_cohort_id=intervention.target_cohort_id,
                    scenario_config=scenario_config,
                    population_filter=_population_filter_for_cohort(intervention.target_cohort_id),
                    duration_months=duration_months,
                )
            )
    return configs
