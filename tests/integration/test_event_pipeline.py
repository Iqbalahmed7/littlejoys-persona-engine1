"""Integration tests for the full event-level research and consolidation pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.analysis.research_consolidator import consolidate_research
from src.config import Config
from src.constants import DASHBOARD_DEFAULT_POPULATION_PATH, DEFAULT_SEED
from src.decision.scenarios import get_scenario
from src.generation.population import Population, PopulationGenerator
from src.probing.question_bank import get_questions_for_scenario
from src.simulation.research_runner import ResearchRunner
from src.utils.llm import LLMClient


@pytest.fixture(scope="module")
def population():
    """Load or generate population once for all tests in this module."""
    path = Path(DASHBOARD_DEFAULT_POPULATION_PATH)
    if (path / "population_meta.json").exists():
        return Population.load(path)
    return PopulationGenerator().generate(seed=DEFAULT_SEED, size=10)


@pytest.fixture(scope="module")
def event_research_result(population):
    """Run the event-level pipeline in mock mode."""
    # nutrimix_2_6 is temporal mode, 6 months -> 180 days.
    scenario = get_scenario("nutrimix_2_6")
    questions = get_questions_for_scenario("nutrimix_2_6")
    question = questions[0]

    llm = LLMClient(Config(
        llm_mock_enabled=True,
        llm_cache_enabled=False,
        anthropic_api_key="",
    ))

    runner = ResearchRunner(
        population=population,
        scenario=scenario,
        question=question,
        llm_client=llm,
        mock_mode=True,
        alternative_count=2, # Small count for speed
        sample_size=3,       # Small sample for speed
        seed=42,
    )

    return runner.run()


def test_event_research_pipeline(event_research_result):
    """Verify that ResearchRunner.run() produces event_result when appropriate."""
    assert event_research_result.event_result is not None
    assert event_research_result.event_result.final_active_rate > 0.0


def test_consolidation_includes_event_data(event_research_result, population):
    """Verify that ConsolidatedReport surfaces event-specific fields."""
    report = consolidate_research(event_research_result, population)

    assert report.event_monthly_rollup is not None
    assert len(report.event_monthly_rollup) > 0

    assert report.event_daily_rollups is not None
    assert len(report.event_daily_rollups) > 0

    assert report.event_clusters is not None
    assert len(report.event_clusters) > 0

    assert report.peak_churn_day is not None
    assert report.decision_rationale_summary is not None


def test_backward_compat_static(population):
    """Verify that static scenarios still work and do NOT produce event results."""
    # nutrimix_7_14 is static mode.
    scenario = get_scenario("nutrimix_7_14")
    questions = get_questions_for_scenario("nutrimix_7_14")
    question = questions[0]

    llm = LLMClient(Config(
        llm_mock_enabled=True,
        llm_cache_enabled=False,
        anthropic_api_key="",
    ))

    runner = ResearchRunner(
        population=population,
        scenario=scenario,
        question=question,
        llm_client=llm,
        mock_mode=True,
        alternative_count=0,
        sample_size=0,
        seed=42,
    )

    result = runner.run()
    assert result.event_result is None
    assert result.temporal_result is None
    assert result.primary_funnel is not None
