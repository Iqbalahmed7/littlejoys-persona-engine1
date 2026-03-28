"""
Static simulation runner (Mode A) — single-pass funnel for all personas.

Runs each persona through the purchase funnel once. No temporal dynamics.
See ARCHITECTURE.md §9.1.
Full implementation in PRD-006 (Cursor).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.decision.scenarios import ScenarioConfig
    from src.generation.population import Population


class StaticSimulationResult(BaseModel):
    """Results from a static simulation run."""

    scenario_id: str
    population_size: int
    adoption_count: int
    adoption_rate: float
    results_by_persona: dict[str, dict]  # persona_id → funnel scores + outcome
    rejection_distribution: dict[str, int]  # rejection_stage → count


def run_static_simulation(
    population: Population,
    scenario: ScenarioConfig,
    seed: int = 42,
) -> StaticSimulationResult:
    """Run all personas through the purchase funnel once (no temporal dynamics)."""
    raise NotImplementedError("Full implementation in PRD-006")
