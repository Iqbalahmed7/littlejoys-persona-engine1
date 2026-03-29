"""Consolidation helpers for auto-scenario exploration runs."""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from src.constants import (
    EXPLORER_MISSED_INSIGHT_LIFT_THRESHOLD,
    EXPLORER_MISSED_INSIGHT_MAX_DISPLAY,
    EXPLORER_SENSITIVITY_MIN_SCORE,
)
from src.utils.display import display_name

if TYPE_CHECKING:
    from src.decision.scenarios import ScenarioConfig


class VariantResult(BaseModel):
    """Result of running one scenario variant."""

    model_config = ConfigDict(extra="forbid")

    variant_id: str
    variant_name: str
    adoption_rate: float
    adoption_count: int
    population_size: int
    rejection_distribution: dict[str, int]
    modifications: dict[str, Any]
    is_baseline: bool = False
    rank: int = 0


class ParameterSensitivity(BaseModel):
    """How much one parameter affects adoption rate."""

    model_config = ConfigDict(extra="forbid")

    parameter_path: str
    parameter_display_name: str
    min_value: Any
    max_value: Any
    adoption_rate_at_min: float
    adoption_rate_at_max: float
    sensitivity_score: float


class MissedInsight(BaseModel):
    """An auto-discovered configuration that outperforms the user's scenario."""

    model_config = ConfigDict(extra="forbid")

    variant_id: str
    variant_name: str
    adoption_rate: float
    lift_over_baseline: float
    key_differences: list[str]
    explanation: str


class ExplorationReport(BaseModel):
    """Consolidated results from running all variants."""

    model_config = ConfigDict(extra="forbid")

    base_scenario_id: str
    strategy: str
    total_variants: int
    execution_time_seconds: float
    baseline_result: VariantResult
    best_result: VariantResult
    worst_result: VariantResult
    median_adoption_rate: float
    all_results: list[VariantResult]
    parameter_sensitivities: list[ParameterSensitivity]
    missed_insights: list[MissedInsight]
    recommended_modifications: dict[str, Any]


def _get_nested_value(config: ScenarioConfig, dot_path: str) -> Any:
    """Read a value from a ScenarioConfig using dot-notation."""

    obj: Any = config
    for part in dot_path.split("."):
        obj = obj[part] if isinstance(obj, dict) else getattr(obj, part)
    return obj


def _format_modification(path: str, old_value: Any, new_value: Any) -> str:
    """Human-readable description of a parameter change."""

    field_name = display_name(path.split(".")[-1])

    if "price" in path.lower() and isinstance(old_value, (int, float)) and isinstance(
        new_value, (int, float)
    ):
        return f"{field_name}: ₹{old_value:.0f} -> ₹{new_value:.0f}"
    if isinstance(new_value, bool):
        return f"{field_name}: {'enabled' if new_value else 'disabled'}"
    if isinstance(new_value, float) and isinstance(old_value, float):
        return f"{field_name}: {old_value:.0%} -> {new_value:.0%}"
    return f"{field_name}: {old_value} -> {new_value}"


class ExplorationConsolidator:
    """Analyze batch results and produce actionable insights."""

    def consolidate(
        self,
        base_scenario_id: str,
        base_scenario: ScenarioConfig,
        all_results: list[VariantResult],
        execution_time: float,
        strategy: str,
    ) -> ExplorationReport:
        """Build a report from ranked batch simulation outputs."""

        if not all_results:
            raise ValueError("all_results cannot be empty")

        baseline = next((result for result in all_results if result.is_baseline), None)
        if baseline is None:
            raise ValueError("all_results must include one baseline result")

        best = all_results[0]
        worst = all_results[-1]
        median_rate = float(statistics.median(result.adoption_rate for result in all_results))
        sensitivities = self._compute_sensitivities(all_results)
        missed_insights = self._generate_missed_insights(baseline, all_results, base_scenario)

        return ExplorationReport(
            base_scenario_id=base_scenario_id,
            strategy=strategy,
            total_variants=len(all_results),
            execution_time_seconds=execution_time,
            baseline_result=baseline,
            best_result=best,
            worst_result=worst,
            median_adoption_rate=median_rate,
            all_results=all_results,
            parameter_sensitivities=sensitivities,
            missed_insights=missed_insights,
            recommended_modifications=dict(best.modifications),
        )

    def _compute_sensitivities(
        self,
        all_results: list[VariantResult],
    ) -> list[ParameterSensitivity]:
        grouped: dict[str, list[VariantResult]] = defaultdict(list)
        for result in all_results:
            for parameter_path in result.modifications:
                grouped[parameter_path].append(result)

        sensitivities: list[ParameterSensitivity] = []
        for parameter_path, variants in grouped.items():
            if len(variants) < 2:
                continue

            min_result = min(variants, key=lambda variant: variant.adoption_rate)
            max_result = max(variants, key=lambda variant: variant.adoption_rate)
            score = max_result.adoption_rate - min_result.adoption_rate
            if score < EXPLORER_SENSITIVITY_MIN_SCORE:
                continue

            sensitivities.append(
                ParameterSensitivity(
                    parameter_path=parameter_path,
                    parameter_display_name=display_name(parameter_path.split(".")[-1]),
                    min_value=min_result.modifications[parameter_path],
                    max_value=max_result.modifications[parameter_path],
                    adoption_rate_at_min=min_result.adoption_rate,
                    adoption_rate_at_max=max_result.adoption_rate,
                    sensitivity_score=score,
                )
            )

        sensitivities.sort(key=lambda sensitivity: sensitivity.sensitivity_score, reverse=True)
        return sensitivities

    def _generate_missed_insights(
        self,
        baseline: VariantResult,
        all_results: list[VariantResult],
        base_scenario: ScenarioConfig,
    ) -> list[MissedInsight]:
        insights: list[MissedInsight] = []
        for result in all_results:
            if result.is_baseline:
                continue

            lift = result.adoption_rate - baseline.adoption_rate
            if lift <= EXPLORER_MISSED_INSIGHT_LIFT_THRESHOLD:
                continue

            differences = [
                _format_modification(path, _get_nested_value(base_scenario, path), new_value)
                for path, new_value in result.modifications.items()
            ]
            key_differences = differences[:3]

            if key_differences:
                explanation = (
                    f"This variant achieves {result.adoption_rate:.0%} adoption (+{lift:.0%} over your "
                    f"scenario) by {', '.join(key_differences)}."
                )
            else:
                explanation = (
                    f"This variant achieves {result.adoption_rate:.0%} adoption (+{lift:.0%} over your scenario)."
                )

            insights.append(
                MissedInsight(
                    variant_id=result.variant_id,
                    variant_name=result.variant_name,
                    adoption_rate=result.adoption_rate,
                    lift_over_baseline=lift,
                    key_differences=differences,
                    explanation=explanation,
                )
            )

        insights.sort(key=lambda insight: insight.lift_over_baseline, reverse=True)
        return insights[:EXPLORER_MISSED_INSIGHT_MAX_DISPLAY]
