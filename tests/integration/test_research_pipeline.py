"""Integration smoke test for the full research pipeline (Sprint 15)."""

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
    return PopulationGenerator().generate(seed=DEFAULT_SEED)


@pytest.fixture(scope="module")
def research_result(population):
    """Run the full research pipeline in mock mode."""
    scenario = get_scenario("nutrimix_2_6")
    questions = get_questions_for_scenario("nutrimix_2_6")
    question = questions[0]

    llm = LLMClient(
        Config(
            llm_mock_enabled=True,
            llm_cache_enabled=False,
            anthropic_api_key="",
        )
    )

    runner = ResearchRunner(
        population=population,
        scenario=scenario,
        question=question,
        llm_client=llm,
        mock_mode=True,
        alternative_count=10,  # Fewer for speed
        sample_size=5,  # Fewer for speed
        seed=42,
    )

    with patch(
        "src.simulation.research_runner.generate_default_counterfactuals",
        _few_counterfactuals,
    ):
        return runner.run()


def test_pipeline_produces_result(research_result) -> None:
    """Pipeline returns a valid ResearchResult."""
    assert isinstance(research_result, ResearchResult)
    assert research_result.primary_funnel.population_size > 0
    assert len(research_result.smart_sample.selections) > 0
    assert len(research_result.interview_results) > 0
    assert len(research_result.alternative_runs) > 0


def test_consolidation_succeeds(research_result, population) -> None:
    """Consolidation transforms raw result into a report."""
    report = consolidate_research(research_result, population)
    assert isinstance(report, ConsolidatedReport)
    assert report.funnel.population_size > 0
    assert len(report.segments_by_tier) > 0
    assert report.interview_count > 0


def test_report_has_alternatives(research_result, population) -> None:
    """Consolidated report includes ranked alternatives."""
    report = consolidate_research(research_result, population)
    assert len(report.top_alternatives) > 0
    # Top alternatives should be ranked by delta descending
    deltas = [a.delta_vs_primary for a in report.top_alternatives]
    assert deltas == sorted(deltas, reverse=True)


def test_all_scenarios_run(population) -> None:
    """Quick check that pipeline can run for all 4 scenarios."""
    from src.constants import SCENARIO_IDS

    llm = LLMClient(
        Config(
            llm_mock_enabled=True,
            llm_cache_enabled=False,
            anthropic_api_key="",
        )
    )

    for sid in SCENARIO_IDS:
        scenario = get_scenario(sid)
        questions = get_questions_for_scenario(sid)
        runner = ResearchRunner(
            population=population,
            scenario=scenario,
            question=questions[0],
            llm_client=llm,
            mock_mode=True,
            alternative_count=5,
            sample_size=3,
            seed=42,
        )
        with patch(
            "src.simulation.research_runner.generate_default_counterfactuals",
            _few_counterfactuals,
        ):
            result = runner.run()
        assert result.primary_funnel.population_size > 0
        assert result.metadata.scenario_id == sid
        if scenario.mode == "temporal":
            assert result.counterfactual_report is not None
        else:
            assert result.counterfactual_report is None
