"""Unit tests for cross-hypothesis contradiction detection."""

from __future__ import annotations

from src.analysis.contradiction_detector import detect_contradictions
from src.probing.models import (
    Hypothesis,
    HypothesisVerdict,
    Probe,
    ProbeResult,
    ProbeType,
    ResponseCluster,
)


def _hypothesis(hypothesis_id: str, attrs: list[str]) -> Hypothesis:
    return Hypothesis(
        id=hypothesis_id,
        problem_id="repeat_purchase_low",
        title=f"Hypothesis {hypothesis_id}",
        rationale="Test rationale",
        indicator_attributes=attrs,
        enabled=True,
        order=1,
    )


def _verdict(hypothesis_id: str, *, status: str, confidence: float) -> HypothesisVerdict:
    return HypothesisVerdict(
        hypothesis_id=hypothesis_id,
        confidence=confidence,
        status=status,
        evidence_summary="Evidence summary",
        key_persona_segments=[],
        recommended_actions=[],
        consistency_score=0.6,
    )


def test_detect_contradictions_confidence_conflict() -> None:
    hypotheses = [
        _hypothesis("h1", ["price", "trust"]),
        _hypothesis("h2", ["price", "habit_strength"]),
    ]
    verdicts = {
        "h1": _verdict("h1", status="confirmed", confidence=0.82),
        "h2": _verdict("h2", status="rejected", confidence=0.21),
    }

    warnings = detect_contradictions(hypotheses=hypotheses, verdicts=verdicts, probes=[])

    assert any(
        warning.contradiction_type == "confidence_conflict" and warning.severity == "high"
        for warning in warnings
    )


def test_detect_contradictions_mechanism_overlap() -> None:
    hypotheses = [
        _hypothesis("h1", ["habit_strength"]),
        _hypothesis("h2", ["trust"]),
    ]
    verdicts = {
        "h1": _verdict("h1", status="confirmed", confidence=0.72),
        "h2": _verdict("h2", status="rejected", confidence=0.25),
    }
    probes = [
        Probe(
            id="p1",
            hypothesis_id="h1",
            probe_type=ProbeType.INTERVIEW,
            order=1,
            question_template="Why did they lapse?",
            result=ProbeResult(
                probe_id="p1",
                confidence=0.8,
                evidence_summary="Interview signals",
                sample_size=8,
                response_clusters=[
                    ResponseCluster(
                        theme="Forgetfulness",
                        description="Users forgot to reorder",
                        persona_count=5,
                        percentage=0.62,
                        representative_quotes=[],
                        dominant_attributes={},
                    )
                ],
            ),
        ),
        Probe(
            id="p2",
            hypothesis_id="h2",
            probe_type=ProbeType.INTERVIEW,
            order=1,
            question_template="Why did they not reorder?",
            result=ProbeResult(
                probe_id="p2",
                confidence=0.74,
                evidence_summary="Interview signals",
                sample_size=8,
                response_clusters=[
                    ResponseCluster(
                        theme="Forgetfulness",
                        description="Same theme surfaced",
                        persona_count=4,
                        percentage=0.50,
                        representative_quotes=[],
                        dominant_attributes={},
                    )
                ],
            ),
        ),
    ]

    warnings = detect_contradictions(hypotheses=hypotheses, verdicts=verdicts, probes=probes)

    assert any(
        warning.contradiction_type == "mechanism_overlap" and warning.severity == "medium"
        for warning in warnings
    )


def test_detect_contradictions_simulation_divergence() -> None:
    hypotheses = [_hypothesis("h1", ["price"])]
    verdicts = {"h1": _verdict("h1", status="inconclusive", confidence=0.45)}
    probes = [
        Probe(
            id="p3",
            hypothesis_id="h1",
            probe_type=ProbeType.SIMULATION,
            order=2,
            comparison_metric="adoption_rate",
            result=ProbeResult(
                probe_id="p3",
                confidence=0.7,
                evidence_summary="Simulation lift exists",
                sample_size=200,
                lift=0.05,
            ),
        )
    ]

    warnings = detect_contradictions(hypotheses=hypotheses, verdicts=verdicts, probes=probes)

    assert any(
        warning.contradiction_type == "simulation_divergence" and warning.severity == "low"
        for warning in warnings
    )
