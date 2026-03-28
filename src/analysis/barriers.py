"""
Barrier distribution analyzer — where and why personas drop off the funnel.

Full implementation in PRD-008 (Cursor).
"""

from __future__ import annotations

from pydantic import BaseModel


class BarrierDistribution(BaseModel):
    """Distribution of rejection reasons across the funnel."""

    stage: str
    barrier: str
    count: int
    percentage: float


def analyze_barriers(results: dict) -> list[BarrierDistribution]:
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
