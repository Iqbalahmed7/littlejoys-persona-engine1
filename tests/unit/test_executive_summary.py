"""Unit tests for the LLM-generated executive summary logic."""

from __future__ import annotations

import pytest

from src.analysis.executive_summary import ExecutiveSummary, generate_executive_summary
from src.analysis.research_consolidator import ConsolidatedReport
from src.decision.scenarios import get_scenario


@pytest.fixture
def mock_report():
    """Create a minimal mock report for testing."""
    # We need a formal ConsolidatedReport instance to pass pydantic validation
    # But generate_executive_summary doesn't actually use most fields in mock_mode.
    return ConsolidatedReport.model_construct(
        scenario_id="nutrimix_2_6",
        scenario_name="Nutrimix",
        question_title="Growth?",
        question_description="Growth decr?",
        funnel=None,
        segments_by_tier=[],
        segments_by_income=[],
        causal_drivers=[],
        interview_count=0,
        clusters=[],
        top_alternatives=[],
        worst_alternatives=[],
        mock_mode=True,
        duration_seconds=0.1,
        llm_calls_made=0,
        estimated_cost_usd=0.0
    )


def test_executive_summary_mock_mode(mock_report):
    """Verify mock executive summary returns a valid object with hardcoded text."""
    scenario = get_scenario("nutrimix_2_6")
    summary = generate_executive_summary(
        report=mock_report,
        scenario=scenario,
        mock_mode=True
    )

    assert isinstance(summary, ExecutiveSummary)
    assert summary.mock_mode is True
    assert "mock" in summary.headline.lower()
    assert len(summary.key_drivers) == 3
    assert len(summary.recommendations) == 3
    assert len(summary.risk_factors) == 2


def test_executive_summary_structure(mock_report):
    """Verify all required fields are present and typed correctly."""
    scenario = get_scenario("nutrimix_2_6")
    summary = generate_executive_summary(mock_report, scenario, mock_mode=True)

    assert isinstance(summary.headline, str)
    assert isinstance(summary.trajectory_summary, str)
    assert isinstance(summary.key_drivers, list)
    assert isinstance(summary.recommendations, list)
    assert isinstance(summary.risk_factors, list)


def test_executive_summary_drivers_non_empty(mock_report):
    """Ensure the lists are actually populated with non-trivial strings."""
    scenario = get_scenario("nutrimix_2_6")
    summary = generate_executive_summary(mock_report, scenario, mock_mode=True)

    for item in summary.key_drivers + summary.recommendations + summary.risk_factors:
        assert len(item) > 10
        assert item != "null"


def test_executive_summary_requires_client_if_not_mock(mock_report):
    """Verify ValueError when llm_client is missing in non-mock mode."""
    scenario = get_scenario("nutrimix_2_6")
    with pytest.raises(ValueError, match="llm_client is required"):
        generate_executive_summary(mock_report, scenario, llm_client=None, mock_mode=False)
