"""
Counterfactual engine — "what if" analysis by modifying scenario parameters.

Compares baseline vs. modified scenarios to quantify the impact of interventions.
See ARCHITECTURE.md §9.3 and PRD-007.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from src.constants import (
    CHILD_AGE_GROUP_EARLY_MAX,
    CHILD_AGE_GROUP_MIDDLE_MAX,
    COUNTERFACTUAL_TOP_SEGMENTS,
    DEFAULT_SEED,
    INCOME_BRACKET_LOW_MAX_LPA,
    INCOME_BRACKET_MID_MAX_LPA,
    SEGMENT_IMPACT_ATTRIBUTES,
)
from src.decision.calibration import evaluate_scenario_adoption
from src.decision.scenarios import ScenarioConfig, get_scenario

if TYPE_CHECKING:
    from src.generation.population import Population


class SegmentImpact(BaseModel):
    """Impact of a counterfactual on a demographic segment."""

    model_config = ConfigDict(extra="forbid")

    segment_attribute: str
    segment_value: str
    baseline_adoption_rate: float
    counterfactual_adoption_rate: float
    lift: float


class CounterfactualResult(BaseModel):
    """Comparison between baseline and counterfactual scenarios."""

    model_config = ConfigDict(extra="forbid")

    baseline_scenario_id: str
    counterfactual_name: str
    parameter_changes: dict[str, tuple[Any, Any]]
    baseline_adoption_rate: float
    counterfactual_adoption_rate: float
    absolute_lift: float
    relative_lift_percent: float
    most_affected_segments: list[SegmentImpact] = Field(default_factory=list)


def _get_nested_value(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"Unknown scenario modification path: {path}")
        current = current[part]
    return current


def _set_nested_value(payload: dict[str, Any], path: str, value: Any) -> None:
    current: Any = payload
    parts = path.split(".")
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"Unknown scenario modification path: {path}")
        current = current[part]
    if not isinstance(current, dict) or parts[-1] not in current:
        raise KeyError(f"Unknown scenario modification path: {path}")
    current[parts[-1]] = value


def _apply_modifications(
    scenario: ScenarioConfig,
    modifications: dict[str, Any],
) -> tuple[ScenarioConfig, dict[str, tuple[Any, Any]]]:
    payload = scenario.model_dump(mode="python")
    parameter_changes: dict[str, tuple[Any, Any]] = {}

    for path, new_value in modifications.items():
        old_value = deepcopy(_get_nested_value(payload, path))
        replacement = deepcopy(new_value)
        _set_nested_value(payload, path, replacement)
        parameter_changes[path] = (old_value, replacement)

    return ScenarioConfig.model_validate(payload), parameter_changes


def _income_bracket(flat: dict[str, Any]) -> str:
    income = float(flat.get("household_income_lpa", 0.0))
    if income <= INCOME_BRACKET_LOW_MAX_LPA:
        return "low_income"
    if income <= INCOME_BRACKET_MID_MAX_LPA:
        return "middle_income"
    return "high_income"


def _child_age_group(flat: dict[str, Any]) -> str:
    child_ages = flat.get("child_ages", [])
    if child_ages:
        mean_age = sum(child_ages) / len(child_ages)
    else:
        mean_age = float(flat.get("youngest_child_age", 0))

    if mean_age <= CHILD_AGE_GROUP_EARLY_MAX:
        return "ages_2_6"
    if mean_age <= CHILD_AGE_GROUP_MIDDLE_MAX:
        return "ages_7_10"
    return "ages_11_14"


def _segment_value(attribute: str, flat: dict[str, Any]) -> str:
    if attribute == "income_bracket":
        return _income_bracket(flat)
    if attribute == "child_age_group":
        return _child_age_group(flat)
    return str(flat.get(attribute, "unknown"))


def _segment_impacts(
    population: Population,
    baseline_results: dict[str, dict[str, Any]],
    counterfactual_results: dict[str, dict[str, Any]],
) -> list[SegmentImpact]:
    personas = population.tier1_personas if population.tier1_personas else population.tier2_personas
    aggregates: dict[tuple[str, str], dict[str, int]] = {}

    for persona in personas:
        if persona.id not in baseline_results or persona.id not in counterfactual_results:
            continue

        flat = persona.to_flat_dict()
        baseline_adopted = int(baseline_results[persona.id]["outcome"] == "adopt")
        counterfactual_adopted = int(counterfactual_results[persona.id]["outcome"] == "adopt")

        for attribute in SEGMENT_IMPACT_ATTRIBUTES:
            key = (attribute, _segment_value(attribute, flat))
            segment = aggregates.setdefault(
                key,
                {"count": 0, "baseline_adopters": 0, "counterfactual_adopters": 0},
            )
            segment["count"] += 1
            segment["baseline_adopters"] += baseline_adopted
            segment["counterfactual_adopters"] += counterfactual_adopted

    impacts: list[SegmentImpact] = []
    for (attribute, value), counts in aggregates.items():
        count = counts["count"]
        baseline_rate = counts["baseline_adopters"] / count if count else 0.0
        counterfactual_rate = counts["counterfactual_adopters"] / count if count else 0.0
        impacts.append(
            SegmentImpact(
                segment_attribute=attribute,
                segment_value=value,
                baseline_adoption_rate=baseline_rate,
                counterfactual_adoption_rate=counterfactual_rate,
                lift=counterfactual_rate - baseline_rate,
            )
        )

    impacts.sort(
        key=lambda impact: (
            impact.lift,
            impact.counterfactual_adoption_rate,
            impact.segment_attribute,
            impact.segment_value,
        ),
        reverse=True,
    )
    return impacts[:COUNTERFACTUAL_TOP_SEGMENTS]


def _counterfactual_catalog() -> dict[str, dict[str, dict[str, Any]]]:
    nutrimix_7_14 = get_scenario("nutrimix_7_14")

    return {
        "nutrimix_2_6": {
            "price_reduction_20": {"product.price_inr": 479.0},
            "school_partnership": {"marketing.school_partnership": True},
            "free_trial": {"product.effort_to_acquire": 0.1},
            "influencer_blitz": {"marketing.awareness_budget": 0.8},
        },
        "nutrimix_7_14": {
            "taste_improvement": {"product.taste_appeal": 0.75},
            "age_specific_branding": {
                "marketing.trust_signals": [
                    *nutrimix_7_14.marketing.trust_signals,
                    "made_for_tweens",
                ]
            },
            "pediatrician_push": {"marketing.pediatrician_endorsement": True},
        },
        "magnesium_gummies": {
            "awareness_campaign": {"marketing.awareness_budget": 0.60},
            "price_premium_reduction": {"product.price_inr": 349.0},
            "doctor_endorsement": {"marketing.pediatrician_endorsement": True},
        },
        "protein_mix": {
            "convenience_format": {
                "product.form_factor": "ready_to_drink",
                "product.effort_to_acquire": 0.2,
            },
            "taste_improvement": {"product.taste_appeal": 0.75},
            "school_sports_partnership": {"marketing.school_partnership": True},
        },
    }


def get_predefined_counterfactuals(
    scenario_id: str | None = None,
) -> dict[str, dict[str, dict[str, Any]]] | dict[str, dict[str, Any]]:
    """Return predefined counterfactual modification maps from PRD-007."""

    catalog = _counterfactual_catalog()
    if scenario_id is None:
        return deepcopy(catalog)
    if scenario_id not in catalog:
        raise KeyError(f"Unknown scenario_id: {scenario_id}")
    return deepcopy(catalog[scenario_id])


def run_predefined_counterfactual(
    population: Population,
    scenario_id: str,
    counterfactual_name: str,
    seed: int = DEFAULT_SEED,
) -> CounterfactualResult:
    """Resolve a named scenario/counterfactual pair and run it."""

    catalog = get_predefined_counterfactuals(scenario_id)
    if counterfactual_name not in catalog:
        raise KeyError(f"Unknown counterfactual '{counterfactual_name}' for scenario '{scenario_id}'")
    return run_counterfactual(
        population=population,
        baseline_scenario=get_scenario(scenario_id),
        modifications=catalog[counterfactual_name],
        counterfactual_name=counterfactual_name,
        seed=seed,
    )


def run_counterfactual(
    population: Population,
    baseline_scenario: ScenarioConfig,
    modifications: dict[str, Any],
    counterfactual_name: str = "",
    seed: int = DEFAULT_SEED,
) -> CounterfactualResult:
    """Run baseline vs. modified scenario and compare results."""

    modified_scenario, parameter_changes = _apply_modifications(baseline_scenario, modifications)
    baseline_result = evaluate_scenario_adoption(
        population=population,
        scenario=baseline_scenario,
        seed=seed,
    )
    counterfactual_result = evaluate_scenario_adoption(
        population=population,
        scenario=modified_scenario,
        seed=seed,
    )

    absolute_lift = counterfactual_result.adoption_rate - baseline_result.adoption_rate
    relative_lift_percent = (
        0.0
        if baseline_result.adoption_rate <= 0.0
        else (absolute_lift / baseline_result.adoption_rate) * 100.0
    )

    return CounterfactualResult(
        baseline_scenario_id=baseline_scenario.id,
        counterfactual_name=counterfactual_name or "custom",
        parameter_changes=parameter_changes,
        baseline_adoption_rate=baseline_result.adoption_rate,
        counterfactual_adoption_rate=counterfactual_result.adoption_rate,
        absolute_lift=absolute_lift,
        relative_lift_percent=relative_lift_percent,
        most_affected_segments=_segment_impacts(
            population=population,
            baseline_results=baseline_result.results_by_persona,
            counterfactual_results=counterfactual_result.results_by_persona,
        ),
    )
