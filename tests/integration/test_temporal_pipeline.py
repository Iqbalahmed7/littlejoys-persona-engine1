"""Integration smoke test for the full research pipeline in temporal mode."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.analysis.research_consolidator import ConsolidatedReport, consolidate_research
from src.config import Config
from src.constants import DASHBOARD_DEFAULT_POPULATION_PATH, DEFAULT_SEED
from src.decision.scenarios import get_scenario
from src.generation.population import Population, PopulationGenerator
from src.probing.question_bank import get_questions_for_scenario
from src.simulation.counterfactual import CounterfactualScenario
from src.simulation.research_runner import ResearchResult, ResearchRunner
from src.utils.llm import LLMClient


def _few_counterfactuals(scenario):  # type: ignore[no-untyped-def]
    """Limit event counterfactuals so integration stays fast."""
    del scenario
    return [
        CounterfactualScenario(
            id="cf_a",
            label="Pediatrician endorsement",
            parameter_changes={"marketing.pediatrician_endorsement": True},
        ),
        CounterfactualScenario(
            id="cf_b",
            label="School partnership",
            parameter_changes={"marketing.school_partnership": True},
        ),
    ]


@pytest.fixture(scope="module")
def population():
    """Load or generate population once for all tests in this module."""
    path = Path(DASHBOARD_DEFAULT_POPULATION_PATH)
    if (path / "population_meta.json").exists():
        return Population.load(path)
    return PopulationGenerator().generate(seed=DEFAULT_SEED, size=50)


@pytest.fixture(scope="module")
def temporal_research_result(population):
    """Run the temporal pipeline in mock mode."""
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
        alternative_count=10,
        sample_size=5,
        seed=42,
    )

    with patch(
        "src.simulation.research_runner.generate_default_counterfactuals",
        _few_counterfactuals,
    ):
        return runner.run()


def test_temporal_research_pipeline(temporal_research_result):
    """Ensure temporal_result comes out of the runner."""
    assert isinstance(temporal_research_result, ResearchResult)
    assert temporal_research_result.temporal_result is not None
    assert temporal_research_result.temporal_result.final_adoption_rate > 0.0
    assert temporal_research_result.counterfactual_report is not None


def test_temporal_snapshots_count(temporal_research_result):
    """Ensure temporal snapshot count equals 6."""
    assert len(temporal_research_result.temporal_result.monthly_snapshots) == 6


def test_consolidation_includes_temporal(temporal_research_result, population):
    """Consolidation merges the temporal results directly into the ConsolidatedReport."""
    report = consolidate_research(temporal_research_result, population)
    assert isinstance(report, ConsolidatedReport)

    assert report.temporal_snapshots is not None
    assert len(report.temporal_snapshots) == 6

    assert report.behaviour_clusters is not None
    assert len(report.behaviour_clusters) > 0


def test_alternatives_have_temporal_rate(temporal_research_result, population):
    """Pipeline should execute temporal sim on variants, storing active rates."""
    report = consolidate_research(temporal_research_result, population)

    assert any(
        alt.temporal_active_rate is not None
        for alt in report.top_alternatives + report.worst_alternatives
    )


def test_peak_churn_month_valid(temporal_research_result, population):
    """The report calculates the peak churn out of exactly 6 months."""
    report = consolidate_research(temporal_research_result, population)
    assert report.peak_churn_month is not None
    assert 1 <= report.peak_churn_month <= 6


def test_consolidation_includes_counterfactual_and_executive(
    temporal_research_result,
    population,
) -> None:
    report = consolidate_research(temporal_research_result, population)
    assert report.counterfactual_results is not None
    assert len(report.counterfactual_results) == 2
    assert report.executive_summary is not None
    assert report.executive_summary.mock_mode is True
