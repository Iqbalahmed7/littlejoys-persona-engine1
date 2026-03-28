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
    raise NotImplementedError("Full implementation in PRD-008")
