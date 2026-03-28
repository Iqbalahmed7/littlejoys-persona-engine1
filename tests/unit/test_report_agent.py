"""Unit tests for the LLM ReportAgent."""

from __future__ import annotations

import pytest

from src.analysis.report_agent import (
    ReportAgent,
    ReportOutput,
    ReportSection,
    validate_report_grounding,
)
from src.config import Config
from src.utils.llm import LLMClient


def _report_results() -> dict[str, dict[str, object]]:
    return {
        "p1": {
            "outcome": "adopt",
            "need_score": 0.82,
            "awareness_score": 0.76,
            "consideration_score": 0.68,
            "purchase_score": 0.61,
            "rejection_stage": None,
            "rejection_reason": None,
            "city_tier": "Tier1",
            "income_bracket": "high_income",
            "budget_consciousness": 0.22,
            "health_anxiety": 0.81,
        },
        "p2": {
            "outcome": "adopt",
            "need_score": 0.75,
            "awareness_score": 0.70,
            "consideration_score": 0.64,
            "purchase_score": 0.57,
            "rejection_stage": None,
            "rejection_reason": None,
            "city_tier": "Tier1",
            "income_bracket": "middle_income",
            "budget_consciousness": 0.33,
            "health_anxiety": 0.74,
        },
        "p3": {
            "outcome": "reject",
            "need_score": 0.61,
            "awareness_score": 0.42,
            "consideration_score": 0.25,
            "purchase_score": 0.10,
            "rejection_stage": "purchase",
            "rejection_reason": "price_too_high",
            "city_tier": "Tier3",
            "income_bracket": "low_income",
            "budget_consciousness": 0.91,
            "health_anxiety": 0.39,
        },
        "p4": {
            "outcome": "reject",
            "need_score": 0.54,
            "awareness_score": 0.35,
            "consideration_score": 0.20,
            "purchase_score": 0.08,
            "rejection_stage": "purchase",
            "rejection_reason": "price_too_high",
            "city_tier": "Tier3",
            "income_bracket": "low_income",
            "budget_consciousness": 0.88,
            "health_anxiety": 0.32,
        },
        "p5": {
            "outcome": "reject",
            "need_score": 0.49,
            "awareness_score": 0.22,
            "consideration_score": 0.11,
            "purchase_score": 0.04,
            "rejection_stage": "awareness",
            "rejection_reason": "low_awareness",
            "city_tier": "Tier2",
            "income_bracket": "middle_income",
            "budget_consciousness": 0.60,
            "health_anxiety": 0.44,
        },
        "p6": {
            "outcome": "adopt",
            "need_score": 0.68,
            "awareness_score": 0.63,
            "consideration_score": 0.51,
            "purchase_score": 0.49,
            "rejection_stage": None,
            "rejection_reason": None,
            "city_tier": "Tier2",
            "income_bracket": "middle_income",
            "budget_consciousness": 0.42,
            "health_anxiety": 0.66,
        },
    }


def _mock_agent() -> ReportAgent:
    client = LLMClient(Config(llm_mock_enabled=True, llm_cache_enabled=False, anthropic_api_key=""))
    return ReportAgent(client)


@pytest.mark.asyncio
async def test_report_agent_produces_all_required_sections() -> None:
    report = await _mock_agent().generate_report("nutrimix_2_6", _report_results())
    titles = [section.title for section in report.sections]

    assert len(titles) == 6
    assert titles == [
        "Executive Summary",
        "Funnel Analysis",
        "Segment Deep Dive",
        "Key Drivers",
        "Counterfactual Insights",
        "Recommendations",
    ]


@pytest.mark.asyncio
async def test_report_agent_calls_tools_during_generation() -> None:
    report = await _mock_agent().generate_report("nutrimix_2_6", _report_results())

    assert report.tool_calls_made >= 3


@pytest.mark.asyncio
async def test_report_agent_respects_max_iterations() -> None:
    agent = _mock_agent()
    agent.max_iterations = 2
    report = await agent.generate_report("nutrimix_2_6", _report_results())

    assert report.tool_calls_made == 2


@pytest.mark.asyncio
async def test_report_output_contains_scenario_metadata() -> None:
    report = await _mock_agent().generate_report("nutrimix_2_6", _report_results())

    assert report.scenario_id == "nutrimix_2_6"
    assert "Nutrimix" in report.scenario_name


@pytest.mark.asyncio
async def test_report_agent_handles_empty_results() -> None:
    report = await _mock_agent().generate_report("nutrimix_2_6", {})

    assert len(report.sections) == 6
    assert report.tool_calls_made == 0
    assert "0 personas" in report.raw_markdown or "0 ranked drivers" in report.raw_markdown


def test_report_grounding_validation_catches_generic_statements() -> None:
    report = ReportOutput(
        scenario_id="nutrimix_2_6",
        scenario_name="Nutrimix for 2-6 year olds",
        sections=[
            ReportSection(
                title="Executive Summary",
                content="Various factors influence adoption.",
            )
        ],
        tool_calls_made=0,
        raw_markdown="# Test",
    )

    warnings = validate_report_grounding(report, ["budget_consciousness", "health_anxiety"])

    assert warnings
