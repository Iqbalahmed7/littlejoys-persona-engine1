"""Edge case tests for hardening and QA."""

from __future__ import annotations

from datetime import UTC, datetime

from src.analysis.barriers import analyze_barriers
from src.analysis.waterfall import compute_funnel_waterfall
from src.constants import SCENARIO_IDS
from src.generation.population import GenerationParams, Population, PopulationMetadata
from src.simulation.static import run_static_simulation


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def test_empty_population_tier1() -> None:
    """Population with no tier1 personas has zero-length lists."""

    pop = Population(
        id="empty-pop",
        generation_params=GenerationParams(size=0, seed=0, deep_persona_count=0),
        tier1_personas=[],
        tier2_personas=[],
        validation_report=None,
        metadata=PopulationMetadata(
            generation_timestamp=_now_iso(),
            generation_duration_seconds=0.0,
            engine_version="test",
        ),
    )

    assert pop.tier1_personas == []
    assert pop.tier2_personas == []


def test_static_simulation_empty_population() -> None:
    """Static sim on empty population returns 0 adoption."""

    scenario = SCENARIO_IDS[0]
    from src.decision.scenarios import get_scenario

    pop = Population(
        id="empty-pop",
        generation_params=GenerationParams(size=0, seed=0, deep_persona_count=0),
        tier1_personas=[],
        tier2_personas=[],
        validation_report=None,
        metadata=PopulationMetadata(
            generation_timestamp=_now_iso(),
            generation_duration_seconds=0.0,
            engine_version="test",
        ),
    )

    result = run_static_simulation(pop, get_scenario(scenario))
    assert result.population_size == 0
    assert result.adoption_count == 0
    assert result.adoption_rate == 0.0
    assert result.results_by_persona == {}


def test_funnel_waterfall_empty() -> None:
    """Waterfall on empty results dict returns empty list."""

    assert compute_funnel_waterfall({}) == []


def test_analyze_barriers_empty() -> None:
    """Barriers on empty results returns empty list."""

    assert analyze_barriers({}) == []
