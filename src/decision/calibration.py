"""
Decision engine calibration — tune thresholds to match expected adoption rates.

Uses the Nutrimix 2-6 scenario as the default calibration baseline. If the
static simulation runner is still a stub, calibration falls back to a
deterministic local estimator built from the architecture equations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict

from src.constants import (
    ATTRIBUTE_MAX,
    ATTRIBUTE_MIN,
    CALIBRATION_BINARY_SEARCH_HIGH,
    CALIBRATION_BINARY_SEARCH_LOW,
    CALIBRATION_RESULTS_PATH,
    CALIBRATION_TARGET_ADOPTION_MAX,
    CALIBRATION_TARGET_ADOPTION_MIDPOINT,
    DEFAULT_CALIBRATION_MAX_ITERATIONS,
    DEFAULT_DECISION_THRESHOLDS,
    DEFAULT_POPULATION_SIZE,
    DEFAULT_SEED,
)
from src.decision.scenarios import ScenarioConfig, get_scenario
from src.generation.population import Population, PopulationGenerator
from src.simulation.static import run_static_simulation

log = structlog.get_logger(__name__)


class CalibrationResult(BaseModel):
    """Result of a calibration run."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    target_adoption_rate: float
    achieved_adoption_rate: float
    thresholds: dict[str, float]
    iterations: int
    population_size: int
    output_path: str


class ScenarioEvaluationResult(BaseModel):
    """Structured output from the fallback static estimator."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    population_size: int
    adoption_count: int
    adoption_rate: float
    results_by_persona: dict[str, dict[str, Any]]
    rejection_distribution: dict[str, int]


def _clip(value: float) -> float:
    return max(ATTRIBUTE_MIN, min(ATTRIBUTE_MAX, value))


def _iter_primary_personas(population: Population) -> list[Any]:
    return population.tier1_personas if population.tier1_personas else population.tier2_personas


def _mean_child_age(flat: dict[str, Any]) -> float:
    child_ages = flat.get("child_ages", [])
    if child_ages:
        return float(sum(child_ages) / len(child_ages))
    return float(flat.get("youngest_child_age", 0))


def _age_fit(flat: dict[str, Any], scenario: ScenarioConfig) -> float:
    low, high = scenario.target_age_range
    child_ages = flat.get("child_ages", [])
    if child_ages:
        matching = [age for age in child_ages if low <= age <= high]
        return len(matching) / len(child_ages)
    youngest = flat.get("youngest_child_age")
    oldest = flat.get("oldest_child_age")
    if isinstance(youngest, int) and isinstance(oldest, int):
        return 1.0 if youngest <= high and oldest >= low else 0.0
    return 0.0


def _concern_match(flat: dict[str, Any], scenario: ScenarioConfig) -> float:
    concerns = set(flat.get("child_nutrition_concerns", []))
    if not concerns or not scenario.product.addresses_concerns:
        return 0.0
    overlap = concerns.intersection(scenario.product.addresses_concerns)
    return len(overlap) / len(scenario.product.addresses_concerns)


def _channel_affinity(channel: str, flat: dict[str, Any], scenario: ScenarioConfig) -> float:
    primary_social_platform = str(flat.get("primary_social_platform", "none"))
    content_pref = str(flat.get("content_format_preference", ""))

    if channel == "instagram":
        return 0.55 * float(flat.get("ad_receptivity", 0.5)) + 0.45 * float(
            primary_social_platform == "instagram"
        )
    if channel == "youtube":
        return 0.55 * float(flat.get("ad_receptivity", 0.5)) + 0.45 * float(
            primary_social_platform == "youtube" or content_pref == "long_video"
        )
    if channel == "whatsapp":
        return 0.50 * float(flat.get("wom_receiver_openness", 0.5)) + 0.50 * float(
            flat.get("mommy_group_membership", False)
        )
    if channel == "pediatrician":
        return 0.50 * float(flat.get("medical_authority_trust", 0.5)) + 0.50 * float(
            flat.get("pediatrician_influence", 0.5)
        )
    if channel == "school":
        return 0.60 * float(flat.get("peer_influence_strength", 0.5)) + 0.40 * _clip(
            (_mean_child_age(flat) - 6.0) / 8.0
        )
    if channel == "sports_clubs":
        return 0.60 * float(flat.get("wellness_trend_follower", 0.5)) + 0.40 * _clip(
            (_mean_child_age(flat) - 7.0) / 7.0
        )
    return 0.5


def _estimate_persona_result(flat: dict[str, Any], scenario: ScenarioConfig) -> dict[str, Any]:
    age_fit = _age_fit(flat, scenario)
    concern_match = _concern_match(flat, scenario)
    mean_child_age = _mean_child_age(flat)

    need_score = (
        scenario.product.category_need_baseline * 0.45
        + float(flat.get("health_anxiety", 0.5)) * 0.20
        + float(flat.get("supplement_necessity_belief", 0.5)) * 0.15
        + float(flat.get("comparison_anxiety", 0.5)) * 0.08
        + float(flat.get("guilt_sensitivity", 0.5)) * 0.07
        + age_fit * 0.15
        + concern_match * 0.10
        - float(flat.get("food_first_belief", 0.5)) * 0.15
    )
    if scenario.target_age_range[0] >= 7:
        need_score -= (1.0 - float(flat.get("health_anxiety", 0.5))) * 0.08
    need_score = _clip(need_score)

    channel_score = 0.0
    for channel, weight in scenario.marketing.channel_mix.items():
        channel_score += weight * _channel_affinity(channel, flat, scenario)

    awareness_score = _clip(
        scenario.marketing.awareness_level * 0.45
        + scenario.marketing.awareness_budget * 0.20
        + channel_score * 0.20
        + scenario.marketing.social_buzz * float(flat.get("wom_receiver_openness", 0.5)) * 0.10
        + float(flat.get("ad_receptivity", 0.5)) * 0.05
    )

    trust_score = _clip(
        scenario.marketing.trust_signal * 0.28
        + scenario.marketing.expert_endorsement * float(flat.get("authority_bias", 0.5)) * 0.18
        + scenario.marketing.social_proof * float(flat.get("social_proof_bias", 0.5)) * 0.18
        + scenario.marketing.influencer_signal * float(flat.get("influencer_trust", 0.5)) * 0.14
        + min(len(scenario.marketing.trust_signals), 4)
        / 4.0
        * float(flat.get("transparency_importance", 0.5))
        * 0.12
        + float(scenario.marketing.school_partnership) * age_fit * 0.05
        + float(scenario.marketing.pediatrician_endorsement)
        * float(flat.get("pediatrician_influence", 0.5))
        * 0.05
    )

    switching_barrier = (
        float(flat.get("status_quo_bias", 0.5)) * 0.18
        + float(flat.get("brand_loyalty_tendency", 0.5)) * 0.12
        + float(flat.get("loss_aversion", 0.5)) * 0.10
        if str(flat.get("milk_supplement_current", "none")) not in {"none", "littlejoys"}
        else 0.0
    )

    consideration_score = _clip(
        awareness_score * 0.55
        + trust_score * 0.30
        + age_fit * 0.10
        + scenario.product.taste_appeal * 0.05
        - switching_barrier
    )

    price_reference = max(float(flat.get("price_reference_point", scenario.product.price_inr)), 1.0)
    income_anchor = max(float(flat.get("household_income_lpa", 1.0)), 1.0)
    price_pain = (
        float(flat.get("budget_consciousness", 0.5))
        * (scenario.product.price_inr / price_reference)
        * 0.18
        + float(flat.get("deal_seeking_intensity", 0.5))
        * (scenario.product.price_inr / (income_anchor * 40.0))
        * 0.14
    )

    effort_pain = (
        float(flat.get("perceived_time_scarcity", 0.5)) * scenario.product.effort_to_acquire * 0.18
        + float(flat.get("simplicity_preference", 0.5)) * scenario.product.complexity * 0.12
        + (1.0 - float(flat.get("cooking_enthusiasm", 0.5)))
        * scenario.product.cooking_required
        * 0.12
    )

    perceived_value = _clip(
        scenario.marketing.perceived_quality * 0.20
        + scenario.product.clean_label_score * float(flat.get("clean_label_importance", 0.5)) * 0.15
        + scenario.product.health_relevance * float(flat.get("health_anxiety", 0.5)) * 0.15
        + scenario.product.premium_positioning
        * float(flat.get("best_for_my_child_intensity", 0.5))
        * 0.10
        + scenario.product.superfood_score * float(flat.get("superfood_awareness", 0.5)) * 0.10
        + scenario.product.taste_appeal * float(flat.get("child_taste_veto", 0.5)) * 0.05
        + float(flat.get("health_spend_priority", 0.5)) * 0.10
        + concern_match * 0.15
    )

    deal_boost = (
        float(flat.get("cashback_coupon_sensitivity", 0.5))
        * scenario.marketing.discount_available
        * 0.10
    )
    convenience_bonus = 0.0
    if scenario.product.form_factor == "ready_to_drink":
        convenience_bonus = (
            float(flat.get("perceived_time_scarcity", 0.5)) * 0.05
            + float(flat.get("simplicity_preference", 0.5)) * 0.05
        )
    elif scenario.product.form_factor == "gummy":
        convenience_bonus = float(flat.get("child_taste_veto", 0.5)) * 0.04

    lj_pass_bonus = 0.0
    if scenario.lj_pass_available and scenario.lj_pass is not None:
        lj_pass_bonus = (
            (scenario.lj_pass.discount_percent / 100.0) * 0.04
            + scenario.lj_pass.retention_boost * 0.03
            + scenario.lj_pass.churn_reduction * 0.02
        )

    purchase_score = _clip(
        consideration_score * 0.35
        + perceived_value
        + deal_boost
        + convenience_bonus
        + lj_pass_bonus
        - price_pain
        - effort_pain
    )

    thresholds = scenario.thresholds
    if age_fit <= 0.0:
        outcome = "reject"
        rejection_stage = "target_mismatch"
    elif need_score < thresholds["need_recognition"]:
        outcome = "reject"
        rejection_stage = "need_recognition"
    elif awareness_score < thresholds["awareness"]:
        outcome = "reject"
        rejection_stage = "awareness"
    elif consideration_score < thresholds["consideration"]:
        outcome = "reject"
        rejection_stage = "consideration"
    elif purchase_score < thresholds["purchase"]:
        outcome = "reject"
        rejection_stage = "purchase"
    else:
        outcome = "adopt"
        rejection_stage = None

    return {
        "need_score": need_score,
        "awareness_score": awareness_score,
        "consideration_score": consideration_score,
        "purchase_score": purchase_score,
        "outcome": outcome,
        "rejection_stage": rejection_stage,
        "mean_child_age": mean_child_age,
    }


def evaluate_scenario_adoption(
    population: Population,
    scenario: ScenarioConfig,
    seed: int = DEFAULT_SEED,
) -> ScenarioEvaluationResult:
    """
    Evaluate a scenario against the population.

    Args:
        population: Population to score.
        scenario: Scenario configuration.
        seed: Simulation seed.

    Returns:
        Static-style evaluation result. Uses the real static runner if available,
        otherwise a deterministic local estimator.
    """

    try:
        result = run_static_simulation(
            population=population,
            scenario=scenario,
            thresholds=scenario.funnel_thresholds,
            seed=seed,
        )
        if 0 < result.adoption_count < result.population_size:
            return ScenarioEvaluationResult(
                scenario_id=result.scenario_id,
                population_size=result.population_size,
                adoption_count=result.adoption_count,
                adoption_rate=result.adoption_rate,
                results_by_persona=result.results_by_persona,
                rejection_distribution=result.rejection_distribution,
            )
        log.info(
            "static_simulation_degenerate_fallback",
            scenario_id=scenario.id,
            adoption_count=result.adoption_count,
            population_size=result.population_size,
        )
    except NotImplementedError:
        log.info("static_simulation_unavailable_fallback", scenario_id=scenario.id)

    results_by_persona: dict[str, dict[str, Any]] = {}
    rejection_distribution: dict[str, int] = {}
    adoption_count = 0
    personas = _iter_primary_personas(population)

    for persona in personas:
        persona_result = _estimate_persona_result(persona.to_flat_dict(), scenario)
        results_by_persona[persona.id] = persona_result
        if persona_result["outcome"] == "adopt":
            adoption_count += 1
        elif persona_result["rejection_stage"] is not None:
            stage = str(persona_result["rejection_stage"])
            rejection_distribution[stage] = rejection_distribution.get(stage, 0) + 1

    population_size = len(personas)
    adoption_rate = adoption_count / population_size if population_size else 0.0
    return ScenarioEvaluationResult(
        scenario_id=scenario.id,
        population_size=population_size,
        adoption_count=adoption_count,
        adoption_rate=adoption_rate,
        results_by_persona=results_by_persona,
        rejection_distribution=rejection_distribution,
    )


def calibrate_thresholds(
    target_adoption_rate: float = CALIBRATION_TARGET_ADOPTION_MIDPOINT,
    scenario_id: str = "nutrimix_2_6",
    tolerance: float = CALIBRATION_TARGET_ADOPTION_MAX - CALIBRATION_TARGET_ADOPTION_MIDPOINT,
    max_iterations: int = DEFAULT_CALIBRATION_MAX_ITERATIONS,
    population_size: int = DEFAULT_POPULATION_SIZE,
    seed: int = DEFAULT_SEED,
    output_path: str | Path = CALIBRATION_RESULTS_PATH,
) -> CalibrationResult:
    """
    Calibrate decision thresholds to achieve a target adoption rate.

    Args:
        target_adoption_rate: Target midpoint adoption rate.
        scenario_id: Scenario to calibrate.
        tolerance: Allowed deviation from the target midpoint.
        max_iterations: Maximum binary-search iterations.
        population_size: Population size used during calibration.
        seed: Master seed for population generation and evaluation.
        output_path: JSON path to save the calibration result.

    Returns:
        Persisted calibration result.
    """

    generator = PopulationGenerator()
    population = generator.generate(size=population_size, seed=seed, deep_persona_count=0)
    base_scenario = get_scenario(scenario_id)

    lower = CALIBRATION_BINARY_SEARCH_LOW
    upper = CALIBRATION_BINARY_SEARCH_HIGH
    target_min = target_adoption_rate - tolerance
    target_max = target_adoption_rate + tolerance
    best_result: ScenarioEvaluationResult | None = None
    best_thresholds = dict(DEFAULT_DECISION_THRESHOLDS)

    for iteration in range(1, max_iterations + 1):
        delta = (lower + upper) / 2.0
        thresholds = {
            stage: _clip(value + delta) for stage, value in DEFAULT_DECISION_THRESHOLDS.items()
        }
        scenario = base_scenario.model_copy(update={"thresholds": thresholds}, deep=True)
        evaluation = evaluate_scenario_adoption(population=population, scenario=scenario, seed=seed)

        if best_result is None or abs(evaluation.adoption_rate - target_adoption_rate) < abs(
            best_result.adoption_rate - target_adoption_rate
        ):
            best_result = evaluation
            best_thresholds = thresholds

        log.info(
            "calibration_iteration",
            scenario_id=scenario_id,
            iteration=iteration,
            adoption_rate=evaluation.adoption_rate,
            thresholds=thresholds,
        )

        if target_min <= evaluation.adoption_rate <= target_max:
            best_result = evaluation
            best_thresholds = thresholds
            break
        if evaluation.adoption_rate > target_max:
            lower = delta
        else:
            upper = delta

    assert best_result is not None

    result = CalibrationResult(
        scenario_id=scenario_id,
        target_adoption_rate=target_adoption_rate,
        achieved_adoption_rate=best_result.adoption_rate,
        thresholds=best_thresholds,
        iterations=iteration,
        population_size=population_size,
        output_path=str(output_path),
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8")
    log.info("calibration_saved", scenario_id=scenario_id, output_path=str(output))
    return result
