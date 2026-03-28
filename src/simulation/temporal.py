"""
Temporal simulation runner (Mode B) — month-by-month with repeat purchase and WOM.

Runs for N months, each month: awareness grows, new adopters enter, repeat purchases occur,
word-of-mouth spreads, churn happens.
See ARCHITECTURE.md §9.2.
Full implementation in PRD-006 (Cursor).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.decision.scenarios import ScenarioConfig
    from src.generation.population import Population


class MonthlySnapshot(BaseModel):
    """State of the simulation at a given month."""

    month: int
    new_adopters: int
    repeat_purchasers: int
    churned: int
    total_active: int
    cumulative_adopters: int
    awareness_level_mean: float
    lj_pass_holders: int


class TemporalSimulationResult(BaseModel):
    """Results from a temporal (multi-month) simulation."""

    scenario_id: str
    months: int
    population_size: int
    monthly_snapshots: list[MonthlySnapshot]
    final_adoption_rate: float
    final_active_rate: float
    total_revenue_estimate: float


def run_temporal_simulation(
    population: Population,
    scenario: ScenarioConfig,
    months: int = 12,
    seed: int = 42,
) -> TemporalSimulationResult:
    """Run a month-by-month simulation with repeat purchase and churn."""
    raise NotImplementedError("Full implementation in PRD-006")
