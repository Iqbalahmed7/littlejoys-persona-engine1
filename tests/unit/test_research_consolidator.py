"""Unit tests for research result consolidation (Sprint 14)."""

from __future__ import annotations

import pytest
from src.decision.scenarios import get_scenario
from src.generation.population import Population
from src.simulation.static import run_static_simulation
from src.probing.smart_sample import select_smart_sample
from src.probing.question_bank import get_question
from src.simulation.research_runner import (
    ResearchResult, ResearchMetadata, InterviewResult, AlternativeRunSummary,
)
from src.analysis.research_consolidator import consolidate_research, ConsolidatedReport


@pytest.fixture
def population():
    """Load or generate a small test population."""
    from src.constants import DASHBOARD_DEFAULT_POPULATION_PATH
    from pathlib import Path
    path = Path(DASHBOARD_DEFAULT_POPULATION_PATH)
    if (path / "population_meta.json").exists():
        return Population.load(path)
    from src.generation.population import PopulationGenerator
    return PopulationGenerator().generate(seed=42)


@pytest.fixture
def research_result(population):
    """Build a minimal but realistic ResearchResult."""
    scenario = get_scenario("nutrimix_2_6")
    primary = run_static_simulation(population, scenario, seed=42)
    sample = select_smart_sample(population.personas, primary.results_by_persona, target_size=5, seed=42)

    # Mock interview results with keyword themes
    interviews = [
        InterviewResult(
            persona_id=s.persona_id,
            persona_name=s.persona_id,
            selection_reason=s.selection_reason,
            responses=[
                {"question": "What do you think about the price?", "answer": "The price seems expensive for our budget. We already spend on other health products."},
                {"question": "Would you trust this product?", "answer": "I would trust it more if a pediatrician recommended it."},
            ],
        )
        for s in sample.selections[:5]
    ]

    alternatives = [
        AlternativeRunSummary(
            variant_id=f"test_{i}",
            parameter_changes={"product.price_inr": 500 - i * 50},
            business_rationale=f"Test variant {i}",
            adoption_count=primary.adoption_count + i * 5,
            adoption_rate=min(1.0, primary.adoption_rate + i * 0.05),
            delta_vs_primary=float(i * 0.05),
        )
        for i in range(10)
    ]

    metadata = ResearchMetadata(
        timestamp="2026-03-29T00:00:00Z",
        duration_seconds=5.0,
        scenario_id="nutrimix_2_6",
        question_id="q_nm26_repeat_purchase",
        population_size=len(population.personas),
        sample_size=5,
        alternative_count=10,
        llm_calls_made=0,
        estimated_cost_usd=0.0,
        mock_mode=True,
    )

    return ResearchResult(
        primary_funnel=primary,
        smart_sample=sample,
        interview_results=interviews,
        alternative_runs=alternatives,
        metadata=metadata,
    )

def test_consolidation_returns_valid_report(research_result, population) -> None:
    """consolidate_research() returns a ConsolidatedReport."""
    report = consolidate_research(research_result, population)
    assert isinstance(report, ConsolidatedReport)

def test_funnel_summary_matches_primary(research_result, population) -> None:
    """Funnel quantitative stats are correctly propagated."""
    report = consolidate_research(research_result, population)
    assert report.funnel.adoption_count == research_result.primary_funnel.adoption_count
    assert report.funnel.adoption_rate == pytest.approx(research_result.primary_funnel.adoption_rate)
    assert report.funnel.population_size == research_result.primary_funnel.population_size

def test_segments_present(research_result, population) -> None:
    """Segments by tier and income are populated with valid rates."""
    report = consolidate_research(research_result, population)
    assert len(report.segments_by_tier) > 0
    assert len(report.segments_by_income) > 0
    for seg in report.segments_by_tier + report.segments_by_income:
        assert 0.0 <= seg.adoption_rate <= 1.0
        assert seg.persona_count >= 0

def test_clusters_from_interviews(research_result, population) -> None:
    """Interview responses are clustered into themes."""
    report = consolidate_research(research_result, population)
    assert len(report.clusters) > 0
    # Search for price or trust theme in clusters
    themes = {c.theme for c in report.clusters}
    assert any(t in themes for t in ["price_sensitivity", "trust_concern"])

def test_alternatives_ranked(research_result, population) -> None:
    """Top alternatives are ranked by delta desc."""
    report = consolidate_research(research_result, population)
    assert len(report.top_alternatives) > 0
    deltas = [alt.delta_vs_primary for alt in report.top_alternatives]
    assert deltas == sorted(deltas, reverse=True)
    assert report.top_alternatives[0].rank == 1

def test_worst_alternatives_present(research_result, population) -> None:
    """Worst alternatives are capped at 3 entries."""
    report = consolidate_research(research_result, population)
    assert 0 <= len(report.worst_alternatives) <= 3
    if len(report.worst_alternatives) > 1:
        deltas = [alt.delta_vs_primary for alt in report.worst_alternatives]
        assert deltas == sorted(deltas)

def test_metadata_propagated(research_result, population) -> None:
    """Metadata fields are correctly mapped."""
    report = consolidate_research(research_result, population)
    assert report.scenario_id == "nutrimix_2_6"
    assert report.mock_mode is True
    assert report.duration_seconds == research_result.metadata.duration_seconds
    assert report.llm_calls_made == research_result.metadata.llm_calls_made

def test_question_context_populated(research_result, population) -> None:
    """Business question details are retrieved and populated."""
    report = consolidate_research(research_result, population)
    assert len(report.question_title) > 0
    assert len(report.question_description) > 0
    # Verify title matches real question bank
    from src.probing.question_bank import get_question
    q = get_question("q_nm26_repeat_purchase")
    assert report.question_title == q.title

def test_causal_drivers_present(research_result, population) -> None:
    """Causal importance drivers are identified."""
    report = consolidate_research(research_result, population)
    assert len(report.causal_drivers) > 0
    for driver in report.causal_drivers:
        assert "variable" in driver
        assert "importance" in driver
        assert "direction" in driver

def test_interview_count_matches(research_result, population) -> None:
    """Interview count matches input results."""
    report = consolidate_research(research_result, population)
    assert report.interview_count == len(research_result.interview_results)
