"""Tests for app/utils/probe_orchestrator.py helper functions."""
from __future__ import annotations

import dataclasses
import pytest

from app.utils.probe_orchestrator import (
    _effect_label,
    _confidence_label,
    ProbeChainResult,
    OrchestrationResult,
    _describe_probe_result,
)


# ---------------------------------------------------------------------------
# _effect_label — thresholds: weak(<0.3), weak-to-moderate(0.3-0.5), moderate(0.5-0.8), strong(>=0.8)
# ---------------------------------------------------------------------------

def test_effect_label_weak():
    assert _effect_label(0.2) == "weak"

def test_effect_label_weak_boundary():
    """Exactly at 0.3 should be weak-to-moderate."""
    assert _effect_label(0.3) == "weak-to-moderate"

def test_effect_label_weak_to_moderate():
    assert _effect_label(0.4) == "weak-to-moderate"

def test_effect_label_moderate():
    assert _effect_label(0.6) == "moderate"

def test_effect_label_moderate_boundary():
    """Exactly at 0.5 should be moderate."""
    assert _effect_label(0.5) == "moderate"

def test_effect_label_strong():
    assert _effect_label(0.9) == "strong"

def test_effect_label_strong_boundary():
    """Exactly at 0.8 should be strong."""
    assert _effect_label(0.8) == "strong"

def test_effect_label_negative_abs():
    """Negative effect sizes use absolute value."""
    assert _effect_label(-0.9) == "strong"
    assert _effect_label(-0.2) == "weak"


# ---------------------------------------------------------------------------
# _confidence_label — thresholds: weak(<0.45), moderate(0.45-0.70), strong(>=0.70)
# ---------------------------------------------------------------------------

def test_confidence_label_weak():
    assert _confidence_label(0.3) == "weak"

def test_confidence_label_weak_upper():
    """Just below 0.45 stays weak."""
    assert _confidence_label(0.44) == "weak"

def test_confidence_label_moderate():
    assert _confidence_label(0.5) == "moderate"

def test_confidence_label_moderate_boundary():
    """Exactly at 0.45 should be moderate."""
    assert _confidence_label(0.45) == "moderate"

def test_confidence_label_strong():
    assert _confidence_label(0.8) == "strong"

def test_confidence_label_strong_boundary():
    """Exactly at 0.70 should be strong."""
    assert _confidence_label(0.70) == "strong"


# ---------------------------------------------------------------------------
# ProbeChainResult dataclass — required fields
# ---------------------------------------------------------------------------

def test_probe_chain_result_has_required_fields():
    """ProbeChainResult dataclass instantiates with expected fields."""
    fields = {f.name for f in dataclasses.fields(ProbeChainResult)}
    assert "hypothesis_id" in fields
    assert "hypothesis_title" in fields
    assert "probes_run" in fields
    assert "final_verdict" in fields
    assert "stopped_early" in fields
    assert "narrative" in fields


def test_probe_chain_result_instantiates():
    """ProbeChainResult can be constructed with minimal valid values."""
    result = ProbeChainResult(
        hypothesis_id="h-001",
        hypothesis_title="Test Hypothesis",
        probes_run=[],
        final_verdict="insufficient",
        stopped_early=False,
        narrative="No probes run.",
    )
    assert result.hypothesis_id == "h-001"
    assert result.final_verdict == "insufficient"
    assert result.stopped_early is False


# ---------------------------------------------------------------------------
# OrchestrationResult dataclass — required fields
# ---------------------------------------------------------------------------

def test_orchestration_result_has_required_fields():
    """OrchestrationResult dataclass has the expected fields."""
    fields = {f.name for f in dataclasses.fields(OrchestrationResult)}
    assert "problem_id" in fields
    assert "chain_results" in fields
    assert "synthesis_narrative" in fields
    assert "core_finding_draft" in fields


def test_orchestration_result_instantiates():
    """OrchestrationResult can be constructed with minimal valid values."""
    result = OrchestrationResult(
        problem_id="p-001",
        chain_results=[],
        synthesis_narrative="No results.",
        core_finding_draft="No finding.",
    )
    assert result.problem_id == "p-001"
    assert result.chain_results == []


# ---------------------------------------------------------------------------
# _describe_probe_result — fallback path (no probe type)
# ---------------------------------------------------------------------------

def test_describe_probe_result_fallback_uses_evidence_summary():
    """When probe_type is None, falls back to result.evidence_summary."""
    from unittest.mock import MagicMock

    mock_result = MagicMock()
    mock_result.evidence_summary = "some evidence text"
    mock_result.response_clusters = []
    mock_result.attribute_splits = []
    mock_result.lift = None

    output = _describe_probe_result(mock_result, None)
    assert output == "some evidence text"
