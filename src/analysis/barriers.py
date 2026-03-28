"""
Barrier distribution analyzer — where and why personas drop off the funnel.

Full implementation in PRD-008 (Cursor).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict

from src.constants import ANALYSIS_STAGE_SUMMARY_TOP_REASONS


class BarrierDistribution(BaseModel):
    """Distribution of rejection reasons across the funnel."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    barrier: str
    count: int
    percentage: float


class StageSummary(BaseModel):
    """Aggregated drop-offs for one funnel stage across all rejections."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    total_dropped: int
    percentage_of_rejections: float
    top_reasons: list[str]


def analyze_barriers(results: dict | list) -> list[BarrierDistribution]:
    """Analyze where personas drop off and why."""
    if not results:
        return []

    iterable = results.values() if isinstance(results, dict) else results
    total_personas = len(iterable)

    if total_personas == 0:
        return []

    counts: dict[tuple[str, str], int] = {}
    for row in iterable:
        stage = row.get("rejection_stage")
        reason = row.get("rejection_reason")

        if stage and reason:
            key = (str(stage), str(reason))
            counts[key] = counts.get(key, 0) + 1

    distributions = []
    for (stage, reason), count in counts.items():
        distributions.append(
            BarrierDistribution(
                stage=stage, barrier=reason, count=count, percentage=float(count) / total_personas
            )
        )

    distributions.sort(key=lambda x: (-x.count, x.stage, x.barrier))
    return distributions


def summarize_barrier_stages(results: dict[str, dict[str, Any]]) -> list[StageSummary]:
    """
    Summarize rejection volume and mix by funnel stage.

    Uses :func:`analyze_barriers` on ``results``, then groups counts by
    ``rejection_stage``. ``percentage_of_rejections`` is each stage's share of
    **total rejection events** (sum of per-reason counts), not population size.

    Args:
        results: ``persona_id`` → result row with optional ``rejection_stage`` /
            ``rejection_reason``.

    Returns:
        :class:`StageSummary` rows sorted by ``total_dropped`` descending, then
        ``stage``.
    """

    log = structlog.get_logger(__name__)

    if not results:
        return []

    distributions = analyze_barriers(results)
    if not distributions:
        return []

    total_rejections = sum(d.count for d in distributions)
    if total_rejections <= 0:
        return []

    stage_totals: dict[str, int] = defaultdict(int)
    stage_reason_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for dist in distributions:
        stage_totals[dist.stage] += dist.count
        stage_reason_counts[dist.stage][dist.barrier] += dist.count

    summaries: list[StageSummary] = []
    for stage, total_dropped in stage_totals.items():
        pct = (float(total_dropped) / float(total_rejections)) * 100.0
        reason_items = sorted(
            stage_reason_counts[stage].items(),
            key=lambda kv: (-kv[1], kv[0]),
        )
        top_reasons = [reason for reason, _ in reason_items[:ANALYSIS_STAGE_SUMMARY_TOP_REASONS]]
        summaries.append(
            StageSummary(
                stage=stage,
                total_dropped=total_dropped,
                percentage_of_rejections=pct,
                top_reasons=top_reasons,
            )
        )

    summaries.sort(key=lambda s: (-s.total_dropped, s.stage))
    log.debug(
        "barrier_stages_summarized",
        stages=len(summaries),
        total_rejection_events=total_rejections,
    )
    return summaries
