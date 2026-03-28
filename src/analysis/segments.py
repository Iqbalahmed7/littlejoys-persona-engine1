"""
Segment analysis — group personas by any attribute and compare outcomes.

Full implementation in PRD-008 (Cursor).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict

from src.constants import ANALYSIS_SEGMENT_TOP_BARRIER_REASONS


class SegmentAnalysis(BaseModel):
    """Analysis results for a single segment."""

    model_config = ConfigDict(extra="forbid")

    segment_key: str
    segment_value: str
    count: int
    adoption_rate: float
    avg_funnel_scores: dict[str, float]
    top_barriers: list[str]


class CrossScenarioSegment(BaseModel):
    """Cross-scenario comparison for one segment bucket (same ``group_by`` value)."""

    model_config = ConfigDict(extra="forbid")

    segment_key: str
    segment_value: str
    best_scenario_id: str
    worst_scenario_id: str
    best_adoption_rate: float
    worst_adoption_rate: float
    adoption_rate_spread: float
    scenario_adoption_rates: dict[str, float]


def analyze_segments(
    results: dict[str, dict[str, Any]],
    group_by: str,
) -> list[SegmentAnalysis]:
    """Analyze adoption and funnel performance by segment.

    Groups persona-level simulation results by the value of ``group_by``.
    For each segment, computes:

    - Persona count
    - Adoption rate (fraction with ``outcome == 'adopt'``)
    - Mean funnel scores (when present): ``need_score``, ``awareness_score``,
      ``consideration_score``, ``purchase_score``
    - Top 3 rejection reasons by frequency (from rows with ``outcome == 'reject'``)

    Args:
        results: Mapping of ``persona_id`` to a flat dict of persona attributes and
            simulation outputs.
        group_by: Attribute name to segment by.

    Returns:
        List of :class:`SegmentAnalysis` objects, sorted by ``adoption_rate``
        descending.
    """

    log = structlog.get_logger(__name__)

    if not results:
        return []

    score_keys = [
        "need_score",
        "awareness_score",
        "consideration_score",
        "purchase_score",
    ]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in results.values():
        if not isinstance(row, dict):
            continue
        if group_by not in row:
            continue
        value = row.get(group_by)
        if value is None:
            continue
        grouped[str(value)].append(row)

    if not grouped:
        return []

    segments: list[SegmentAnalysis] = []

    for segment_value, rows in grouped.items():
        count = len(rows)
        adopters = sum(1 for r in rows if r.get("outcome") == "adopt")
        adoption_rate = float(adopters) / float(count) if count else 0.0

        avg_funnel_scores: dict[str, float] = {}
        for score_key in score_keys:
            values: list[float] = []
            for r in rows:
                v = r.get(score_key)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    values.append(float(v))
            if values:
                avg_funnel_scores[score_key] = sum(values) / float(len(values))

        rejection_reason_counts: dict[str, int] = defaultdict(int)
        for r in rows:
            if r.get("outcome") != "reject":
                continue
            reason = r.get("rejection_reason")
            if reason is None:
                continue
            rejection_reason_counts[str(reason)] += 1

        sorted_reasons = sorted(
            rejection_reason_counts.items(),
            key=lambda kv: (-kv[1], kv[0]),
        )
        top_barriers = [
            reason for reason, _ in sorted_reasons[:ANALYSIS_SEGMENT_TOP_BARRIER_REASONS]
        ]

        segments.append(
            SegmentAnalysis(
                segment_key=str(group_by),
                segment_value=segment_value,
                count=count,
                adoption_rate=adoption_rate,
                avg_funnel_scores=avg_funnel_scores,
                top_barriers=top_barriers,
            )
        )

    segments.sort(key=lambda s: (-s.adoption_rate, s.segment_value))
    log.debug(
        "segments_analyzed",
        group_by=group_by,
        segments=len(segments),
    )
    return segments


def compare_segments_across_scenarios(
    scenarios_results: dict[str, dict[str, dict[str, Any]]],
    group_by: str,
) -> list[CrossScenarioSegment]:
    """
    Compare the same segment slice across multiple scenario result sets.

    For each segment value observed in any scenario, collects per-scenario adoption
    rates (via :func:`analyze_segments`), then ranks scenarios best/worst and
    computes spread ``max_rate - min_rate``.

    Args:
        scenarios_results: ``scenario_id`` → ``persona_id`` → result row (same shape
            as :func:`analyze_segments` expects).
        group_by: Attribute name passed through to :func:`analyze_segments`.

    Returns:
        :class:`CrossScenarioSegment` rows sorted by ``adoption_rate_spread`` descending
        (most divergent segments first), then ``segment_value``.
    """

    log = structlog.get_logger(__name__)

    if not scenarios_results:
        return []

    per_scenario: dict[str, list[SegmentAnalysis]] = {}
    for scenario_id, persona_results in scenarios_results.items():
        if not isinstance(persona_results, dict):
            continue
        per_scenario[scenario_id] = analyze_segments(persona_results, group_by=group_by)

    by_value: dict[str, dict[str, float]] = defaultdict(dict)
    for scenario_id, analyses in per_scenario.items():
        for seg in analyses:
            by_value[seg.segment_value][scenario_id] = seg.adoption_rate

    if not by_value:
        return []

    rows: list[CrossScenarioSegment] = []
    for segment_value, scenario_rates in sorted(by_value.items(), key=lambda kv: kv[0]):
        if not scenario_rates:
            continue
        best_id, best_rate = max(scenario_rates.items(), key=lambda x: (x[1], x[0]))
        worst_id, worst_rate = min(scenario_rates.items(), key=lambda x: (x[1], x[0]))
        spread = best_rate - worst_rate
        rows.append(
            CrossScenarioSegment(
                segment_key=str(group_by),
                segment_value=segment_value,
                best_scenario_id=best_id,
                worst_scenario_id=worst_id,
                best_adoption_rate=best_rate,
                worst_adoption_rate=worst_rate,
                adoption_rate_spread=spread,
                scenario_adoption_rates=dict(sorted(scenario_rates.items())),
            )
        )

    rows.sort(key=lambda r: (-r.adoption_rate_spread, r.segment_value))
    log.debug(
        "cross_scenario_segments_compared",
        group_by=group_by,
        segment_values=len(rows),
    )
    return rows
