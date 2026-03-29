"""Integration tests for the full event-level research and consolidation pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.analysis.research_consolidator import consolidate_research
from src.config import Config
from src.constants import DASHBOARD_DEFAULT_POPULATION_PATH, DEFAULT_SEED
from src.decision.scenarios import get_scenario
from src.generation.population import Population, PopulationGenerator
from src.probing.question_bank import get_questions_for_scenario
from src.simulation.counterfactual import CounterfactualScenario
from src.simulation.research_runner import ResearchRunner
from src.utils.llm import LLMClient


def _few_counterfactuals(scenario):  # type: ignore[no-untyped-def]
    del scenario
    return [
        CounterfactualScenario(
            id="cf_a",
            label="Pediatrician endorsement",
            parameter_changes={"marketing.pediatrician_endorsement": True},
        ),
    ]


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
        alternative_count=2,
        sample_size=3,
        seed=42,
    )

    with patch(
        "src.simulation.research_runner.generate_default_counterfactuals",
        _few_counterfactuals,
    ):
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

    assert report.counterfactual_results is not None
    assert len(report.counterfactual_results) == 1
    assert report.executive_summary is not None
    assert "mock" in report.executive_summary.headline.lower()


def test_nutrimix_7_14_runs_temporal(population):
    """Verify that the Nutrimix 7-14 expansion scenario runs in temporal/event mode."""
    from src.config import Config
    from src.decision.scenarios import get_scenario
    from src.probing.question_bank import get_questions_for_scenario
    from src.simulation.research_runner import ResearchRunner
    from src.utils.llm import LLMClient

    scenario = get_scenario("nutrimix_7_14")
    assert scenario.mode == "temporal"

    question = get_questions_for_scenario("nutrimix_7_14")[0]
    llm = LLMClient(Config(llm_mock_enabled=True))

    runner = ResearchRunner(
        population=population,
        scenario=scenario,
        question=question,
        llm_client=llm,
        mock_mode=True
    )
    with patch("src.simulation.research_runner.generate_default_counterfactuals", return_value=_few_counterfactuals(None)):
        result = runner.run()

    assert result.event_result is not None
    assert result.event_result.duration_days == scenario.months * 30


def test_counterfactual_in_pipeline(population):
    """Explicitly verify that counterfactual results appear in the final ConsolidatedReport."""
    from src.analysis.research_consolidator import consolidate_research
    from src.config import Config
    from src.decision.scenarios import get_scenario
    from src.probing.question_bank import get_questions_for_scenario
    from src.simulation.research_runner import ResearchRunner
    from src.utils.llm import LLMClient

    scenario = get_scenario("nutrimix_2_6")
    question = get_questions_for_scenario("nutrimix_2_6")[0]
    llm = LLMClient(Config(llm_mock_enabled=True))

    runner = ResearchRunner(
        population=population,
        scenario=scenario,
        question=question,
        llm_client=llm,
        mock_mode=True
    )

    with patch("src.simulation.research_runner.generate_default_counterfactuals", return_value=_few_counterfactuals(None)):
        result = runner.run()

    report = consolidate_research(result, population)

    assert report.counterfactual_results is not None
    assert len(report.counterfactual_results) > 0
    # Check one specific field to ensure it's the new model
    assert hasattr(report.counterfactual_results[0], "lift_pct")

    assert report.peak_churn_day is not None
    assert report.decision_rationale_summary is not None


def test_backward_compat_static(population):
    """Verify that static scenarios still work and do NOT produce event results."""
    scenario = get_scenario("magnesium_gummies")
    questions = get_questions_for_scenario("magnesium_gummies")
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
    assert result.counterfactual_report is None
    assert result.primary_funnel is not None
