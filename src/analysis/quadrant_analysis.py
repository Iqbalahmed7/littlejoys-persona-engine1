"""Post-run analysis for intervention quadrant experiments."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from src.analysis.intervention_engine import InterventionQuadrant
    from src.simulation.quadrant_runner import QuadrantRunResult


class InterventionLift(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intervention_id: str
    intervention_name: str
    scope: str
    temporality: str
    target_cohort_id: str | None
    expected_mechanism: str

    adoption_lift_abs: float
    adoption_lift_pct: float

    active_rate_lift_abs: float | None = None
    active_rate_lift_pct: float | None = None
    revenue_lift: float | None = None

    rank: int
    quadrant_key: str


class QuadrantAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    baseline_adoption_rate: float
    baseline_active_rate: float | None

    ranked_interventions: list[InterventionLift]
    top_recommendation: InterventionLift

    quadrant_summaries: dict[str, dict[str, Any]]


def _quadrant_key(scope: str, temporality: str) -> str:
    mapping = {
        ("general", "temporal"): "general_temporal",
        ("general", "non_temporal"): "general_non_temporal",
        ("cohort_specific", "temporal"): "cohort_temporal",
        ("cohort_specific", "non_temporal"): "cohort_non_temporal",
    }
    return mapping.get((scope, temporality), "general_non_temporal")


def _safe_pct(delta: float, base: float) -> float:
    if base == 0:
        return 0.0
    return (delta / base) * 100.0


def analyze_quadrant_results(
    run_result: QuadrantRunResult,
    quadrant: InterventionQuadrant,
) -> QuadrantAnalysis:
    """Compute lifts, rank interventions, and produce recommendation."""

    intervention_lookup = {
        intervention.id: (intervention, quadrant_key)
        for quadrant_key, interventions in quadrant.quadrants.items()
        for intervention in interventions
    }

    baseline_adoption = float(getattr(run_result, "baseline_adoption_rate", 0.0))
    baseline_active = getattr(run_result, "baseline_active_rate", None)
    baseline_active = float(baseline_active) if baseline_active is not None else None
    baseline_revenue = getattr(run_result, "baseline_revenue", None)
    baseline_revenue = float(baseline_revenue) if baseline_revenue is not None else None

    lifts: list[InterventionLift] = []
    for run in run_result.results:
        meta, q_key = intervention_lookup.get(
            run.intervention_id,
            (None, _quadrant_key(run.scope, run.temporality)),
        )
        expected_mechanism = meta.expected_mechanism if meta is not None else ""
        adoption_rate = float(run.adoption_rate)
        adoption_lift_abs = adoption_rate - baseline_adoption
        adoption_lift_pct = _safe_pct(adoption_lift_abs, baseline_adoption)

        active_rate = (
            float(run.final_active_rate) if run.final_active_rate is not None else None
        )
        active_lift_abs = (
            (active_rate - baseline_active)
            if active_rate is not None and baseline_active is not None
            else None
        )
        active_lift_pct = (
            _safe_pct(active_lift_abs, baseline_active)
            if active_lift_abs is not None and baseline_active is not None
            else None
        )
        revenue = float(run.total_revenue) if run.total_revenue is not None else None
        revenue_lift = (
            (revenue - baseline_revenue)
            if revenue is not None and baseline_revenue is not None
            else None
        )

        lifts.append(
            InterventionLift(
                intervention_id=run.intervention_id,
                intervention_name=run.intervention_name,
                scope=run.scope,
                temporality=run.temporality,
                target_cohort_id=getattr(run, "target_cohort_id", None),
                expected_mechanism=expected_mechanism,
                adoption_lift_abs=adoption_lift_abs,
                adoption_lift_pct=adoption_lift_pct,
                active_rate_lift_abs=active_lift_abs,
                active_rate_lift_pct=active_lift_pct,
                revenue_lift=revenue_lift,
                rank=0,
                quadrant_key=q_key,
            )
        )

    lifts.sort(
        key=lambda item: (
            item.adoption_lift_pct,
            item.revenue_lift if item.revenue_lift is not None else float("-inf"),
        ),
        reverse=True,
    )
    for idx, row in enumerate(lifts, start=1):
        row.rank = idx

    if not lifts:
        raise ValueError("run_result does not include any intervention runs")

    quadrant_summaries: dict[str, dict[str, Any]] = {}
    for key in ("general_temporal", "general_non_temporal", "cohort_temporal", "cohort_non_temporal"):
        bucket = [item for item in lifts if item.quadrant_key == key]
        if not bucket:
            quadrant_summaries[key] = {"avg_lift": 0.0, "best": None, "count": 0}
            continue
        best = max(bucket, key=lambda item: item.adoption_lift_pct)
        avg_lift = sum(item.adoption_lift_pct for item in bucket) / len(bucket)
        quadrant_summaries[key] = {
            "avg_lift": avg_lift,
            "best": best.intervention_name,
            "count": len(bucket),
        }

    return QuadrantAnalysis(
        scenario_id=run_result.scenario_id,
        baseline_adoption_rate=baseline_adoption,
        baseline_active_rate=baseline_active,
        ranked_interventions=lifts,
        top_recommendation=lifts[0],
        quadrant_summaries=quadrant_summaries,
    )


def format_quadrant_table(analysis: QuadrantAnalysis) -> list[dict[str, Any]]:
    """Flatten analysis into rows suitable for dataframe display."""

    rows: list[dict[str, Any]] = []
    for row in analysis.ranked_interventions:
        intervention_adoption = analysis.baseline_adoption_rate + row.adoption_lift_abs
        rows.append(
            {
                "name": row.intervention_name,
                "scope": row.scope,
                "temporality": row.temporality,
                "cohort": row.target_cohort_id or "all",
                "baseline_adoption": analysis.baseline_adoption_rate,
                "intervention_adoption": intervention_adoption,
                "lift_pct": row.adoption_lift_pct,
                "rank": row.rank,
            }
        )
    return rows
