"""
Counterfactual engine — "what if" analysis by modifying scenario parameters.

Compares baseline vs. modified scenarios to quantify the impact of interventions.
See ARCHITECTURE.md §9.3.
Full implementation in PRD-007 (Codex).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.decision.scenarios import ScenarioConfig
    from src.generation.population import Population


class CounterfactualResult(BaseModel):
    """Comparison between baseline and counterfactual scenarios."""

    baseline_scenario_id: str
    counterfactual_name: str
    parameter_changes: dict[str, tuple]  # param → (old_value, new_value)
    baseline_adoption_rate: float
    counterfactual_adoption_rate: float
    absolute_lift: float
    relative_lift_percent: float
    most_affected_segments: list[dict]


def run_counterfactual(
    population: Population,
    baseline_scenario: ScenarioConfig,
    modifications: dict,
    counterfactual_name: str = "",
    seed: int = 42,
) -> CounterfactualResult:
    """Run baseline vs. modified scenario and compare results."""
    raise NotImplementedError("Full implementation in PRD-007")
