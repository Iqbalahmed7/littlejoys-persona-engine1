"""
Static simulation runner (Mode A) — single-pass funnel for all personas.

Runs each persona through the purchase funnel once. No temporal dynamics.
See ARCHITECTURE.md §9.1.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import structlog
from pydantic import BaseModel, Field

from src.decision.funnel import DecisionResult, run_funnel

if TYPE_CHECKING:
    from src.decision.scenarios import ScenarioConfig
    from src.generation.population import Population

log = structlog.get_logger(__name__)


class StaticSimulationResult(BaseModel):
    """Results from a static simulation run."""

    scenario_id: str
    population_size: int
    adoption_count: int
    adoption_rate: float
    results_by_persona: dict[str, dict] = Field(default_factory=dict)
    rejection_distribution: dict[str, int] = Field(default_factory=dict)
    random_seed: int = 42


def run_static_simulation(
    population: Population,
    scenario: ScenarioConfig,
    thresholds: dict[str, float] | None = None,
    seed: int = 42,
) -> StaticSimulationResult:
    """
    Run all Tier 1 personas through the purchase funnel once.

    Args:
        population: Generated population.
        scenario: Scenario configuration.
        thresholds: Optional funnel threshold overrides.
        seed: Recorded for reproducibility (deterministic funnel given same inputs).

    Returns:
        Aggregated static simulation outcome.
    """

    log.info("static_simulation_started", scenario_id=scenario.id, seed=seed)
    results_by_persona: dict[str, dict] = {}
    rejection_counts: Counter[str] = Counter()
    adoption_count = 0

    personas = population.personas
    for persona in personas:
        decision: DecisionResult = run_funnel(persona, scenario, thresholds)
        results_by_persona[persona.id] = decision.to_dict()
        if decision.outcome == "adopt":
            adoption_count += 1
        elif decision.rejection_stage:
            rejection_counts[decision.rejection_stage] += 1

    n = len(personas)
    adoption_rate = adoption_count / n if n else 0.0

    log.info(
        "static_simulation_complete",
        adoption_count=adoption_count,
        adoption_rate=adoption_rate,
    )

    return StaticSimulationResult(
        scenario_id=scenario.id,
        population_size=n,
        adoption_count=adoption_count,
        adoption_rate=adoption_rate,
        results_by_persona=results_by_persona,
        rejection_distribution=dict(rejection_counts),
        random_seed=seed,
    )
