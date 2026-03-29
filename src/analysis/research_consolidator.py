"""Research results consolidation for Results-page-ready data payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from src.analysis.barriers import analyze_barriers
from src.analysis.causal import compute_variable_importance
from src.analysis.segments import analyze_segments
from src.analysis.waterfall import compute_funnel_waterfall
from src.constants import INCOME_BRACKET_LOW_MAX_LPA, INCOME_BRACKET_MID_MAX_LPA
from src.decision.scenarios import get_scenario
from src.probing.clustering import cluster_responses_mock
from src.probing.question_bank import get_question

if TYPE_CHECKING:
    from src.generation.population import Population
    from src.simulation.research_runner import AlternativeRunSummary, ResearchResult


class FunnelSummary(BaseModel):
    """Quantitative overview of the primary funnel run."""

    model_config = ConfigDict(extra="forbid")

    population_size: int
    adoption_count: int
    adoption_rate: float
    rejection_distribution: dict[str, int]
    top_barriers: list[dict[str, str | int]]
    waterfall_data: dict[str, int]


class SegmentInsight(BaseModel):
    """One segment's adoption insight."""

    model_config = ConfigDict(extra="forbid")

    segment_name: str
    segment_value: str
    adoption_rate: float
    persona_count: int
    delta_vs_population: float


class QualitativeCluster(BaseModel):
    """One theme from interview clustering."""

    model_config = ConfigDict(extra="forbid")

    theme: str
    description: str
    persona_count: int
    percentage: float
    representative_quotes: list[str]
    dominant_attributes: dict[str, float]


class AlternativeInsight(BaseModel):
    """Top alternative scenario with business context."""

    model_config = ConfigDict(extra="forbid")

    rank: int
    variant_id: str
    business_rationale: str
    adoption_rate: float
    delta_vs_primary: float
    parameter_changes: dict[str, object]


class ConsolidatedReport(BaseModel):
    """Complete consolidated research report ready for rendering."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    scenario_name: str
    question_title: str
    question_description: str
    funnel: FunnelSummary
    segments_by_tier: list[SegmentInsight]
    segments_by_income: list[SegmentInsight]
    causal_drivers: list[dict[str, object]]
    interview_count: int
    clusters: list[QualitativeCluster]
    top_alternatives: list[AlternativeInsight]
    worst_alternatives: list[AlternativeInsight]
    mock_mode: bool
    duration_seconds: float
    llm_calls_made: int
    estimated_cost_usd: float


def _income_bracket(household_income_lpa: Any) -> str:
    if not isinstance(household_income_lpa, (int, float)) or isinstance(household_income_lpa, bool):
        return "unknown"
    if household_income_lpa <= INCOME_BRACKET_LOW_MAX_LPA:
        return "low_income"
    if household_income_lpa <= INCOME_BRACKET_MID_MAX_LPA:
        return "middle_income"
    return "high_income"


def _segment_insights(
    merged: dict[str, dict[str, Any]],
    *,
    group_by: str,
    overall_rate: float,
) -> list[SegmentInsight]:
    insights: list[SegmentInsight] = []
    for segment in analyze_segments(merged, group_by=group_by):
        insights.append(
            SegmentInsight(
                segment_name=segment.segment_key,
                segment_value=segment.segment_value,
                adoption_rate=segment.adoption_rate,
                persona_count=segment.count,
                delta_vs_population=segment.adoption_rate - overall_rate,
            )
        )
    return insights


def _alternative_rows(
    alternatives: list[AlternativeRunSummary],
    *,
    reverse: bool,
    limit: int,
) -> list[AlternativeInsight]:
    ordered = sorted(alternatives, key=lambda item: item.delta_vs_primary, reverse=reverse)[:limit]
    return [
        AlternativeInsight(
            rank=index + 1,
            variant_id=alt.variant_id,
            business_rationale=alt.business_rationale,
            adoption_rate=alt.adoption_rate,
            delta_vs_primary=alt.delta_vs_primary,
            parameter_changes=alt.parameter_changes,
        )
        for index, alt in enumerate(ordered)
    ]


def consolidate_research(
    result: ResearchResult,
    population: Population,
) -> ConsolidatedReport:
    """Transform raw ResearchResult into a structured report."""

    scenario = get_scenario(result.metadata.scenario_id)
    question = get_question(result.metadata.question_id)

    waterfall = compute_funnel_waterfall(result.primary_funnel.results_by_persona)
    barrier_rows = analyze_barriers(result.primary_funnel.results_by_persona)
    top_barriers = [
        {"stage": row.stage, "reason": row.barrier, "count": row.count} for row in barrier_rows[:5]
    ]
    funnel_summary = FunnelSummary(
        population_size=result.primary_funnel.population_size,
        adoption_count=result.primary_funnel.adoption_count,
        adoption_rate=result.primary_funnel.adoption_rate,
        rejection_distribution=dict(result.primary_funnel.rejection_distribution),
        top_barriers=top_barriers,
        waterfall_data={row.stage: row.passed for row in waterfall},
    )

    merged: dict[str, dict[str, Any]] = {}
    for persona_id, row in result.primary_funnel.results_by_persona.items():
        flat = population.get_persona(persona_id).to_flat_dict()
        merged_row = {**flat, **row}
        if "income_bracket" not in merged_row:
            merged_row["income_bracket"] = _income_bracket(merged_row.get("household_income_lpa"))
        merged[persona_id] = merged_row

    overall_rate = result.primary_funnel.adoption_rate
    segments_by_tier = _segment_insights(merged, group_by="city_tier", overall_rate=overall_rate)
    segments_by_income = _segment_insights(
        merged,
        group_by="income_bracket",
        overall_rate=overall_rate,
    )

    causal_importance = compute_variable_importance(merged)
    causal_drivers = [
        {
            "variable": item.variable_name,
            "importance": item.shap_mean_abs,
            "direction": item.direction,
        }
        for item in causal_importance[:8]
    ]

    response_pairs: list[tuple[Any, str]] = []
    for interview_result in result.interview_results:
        persona = population.get_persona(interview_result.persona_id)
        combined_text = " ".join(response["answer"] for response in interview_result.responses)
        response_pairs.append((persona, combined_text))

    clusters = [
        QualitativeCluster(
            theme=cluster.theme,
            description=cluster.description,
            persona_count=cluster.persona_count,
            percentage=cluster.percentage,
            representative_quotes=list(cluster.representative_quotes),
            dominant_attributes=dict(cluster.dominant_attributes),
        )
        for cluster in cluster_responses_mock(response_pairs)
    ]

    top_alternatives = _alternative_rows(result.alternative_runs, reverse=True, limit=10)
    worst_alternatives = _alternative_rows(result.alternative_runs, reverse=False, limit=3)

    return ConsolidatedReport(
        scenario_id=result.metadata.scenario_id,
        scenario_name=scenario.name,
        question_title=question.title,
        question_description=question.description,
        funnel=funnel_summary,
        segments_by_tier=segments_by_tier,
        segments_by_income=segments_by_income,
        causal_drivers=causal_drivers,
        interview_count=len(result.interview_results),
        clusters=clusters,
        top_alternatives=top_alternatives,
        worst_alternatives=worst_alternatives,
        mock_mode=result.metadata.mock_mode,
        duration_seconds=result.metadata.duration_seconds,
        llm_calls_made=result.metadata.llm_calls_made,
        estimated_cost_usd=result.metadata.estimated_cost_usd,
    )
