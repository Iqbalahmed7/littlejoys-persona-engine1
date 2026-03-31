"""Unit tests for custom hypothesis fallback probe generation."""

from __future__ import annotations

from src.probing.models import Hypothesis, ProbeType
from src.probing.predefined_trees import generate_fallback_probes_for_custom_hypotheses


def _custom_hypothesis(*, with_attrs: bool) -> Hypothesis:
    return Hypothesis(
        id="custom_packaging",
        problem_id="repeat_purchase_low",
        title="Packaging looks cheap at shelf",
        rationale="Retail feedback suggests low quality impression.",
        signals=[],
        indicator_attributes=["budget_consciousness", "brand_loyalty_tendency"] if with_attrs else [],
        counterfactual_modifications=None,
        is_custom=True,
        enabled=True,
        order=999,
    )


def test_custom_hypothesis_empty_attributes_gets_two_interview_probes_only() -> None:
    hypotheses = [_custom_hypothesis(with_attrs=False)]
    probes = generate_fallback_probes_for_custom_hypotheses(hypotheses, [])

    assert len(probes) == 2
    assert all(probe.probe_type == ProbeType.INTERVIEW for probe in probes)


def test_custom_hypothesis_with_attributes_gets_interview_plus_attribute_probe() -> None:
    hypotheses = [_custom_hypothesis(with_attrs=True)]
    probes = generate_fallback_probes_for_custom_hypotheses(hypotheses, [])

    interview_count = sum(1 for probe in probes if probe.probe_type == ProbeType.INTERVIEW)
    attribute_count = sum(1 for probe in probes if probe.probe_type == ProbeType.ATTRIBUTE)
    simulation_count = sum(1 for probe in probes if probe.probe_type == ProbeType.SIMULATION)

    assert interview_count == 2
    assert attribute_count == 1
    assert simulation_count == 0
