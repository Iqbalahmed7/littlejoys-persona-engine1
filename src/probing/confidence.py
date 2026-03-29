"""Confidence computation for probing tree results."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.probing.models import AttributeSplit, ResponseCluster


def compute_interview_confidence(clusters: list[ResponseCluster]) -> float:
    """Confidence = dominant cluster % x attribute coherence."""

    if not clusters:
        return 0.0

    dominant = max(clusters, key=lambda cluster: cluster.percentage)
    dominance = dominant.percentage
    coherence = _attribute_coherence(dominant)
    return dominance * 0.6 + coherence * 0.4


def _attribute_coherence(cluster: ResponseCluster) -> float:
    """How tightly the dominant cluster shares attribute patterns."""

    if not cluster.dominant_attributes:
        return 0.5

    values = list(cluster.dominant_attributes.values())
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return max(0.0, 1.0 - variance * 4)


def compute_simulation_confidence(
    baseline: float,
    modified: float,
    sample_size: int,
) -> float:
    """Confidence = lift magnitude x sample significance."""

    lift = abs(modified - baseline)
    significance = min(1.0, sample_size / 100)
    return min(1.0, lift * 3.0) * significance


def compute_attribute_confidence(splits: list[AttributeSplit]) -> float:
    """Confidence = effect size coverage x mean effect magnitude."""

    if not splits:
        return 0.0

    significant_splits = [split for split in splits if split.significant]
    coverage = len(significant_splits) / len(splits)
    mean_effect = (
        sum(abs(split.effect_size) for split in significant_splits) / len(significant_splits)
        if significant_splits
        else 0.0
    )
    return coverage * 0.5 + min(1.0, mean_effect) * 0.5


def compute_hypothesis_confidence(probe_confidences: list[float]) -> tuple[float, float]:
    """Return ``(final_confidence, consistency_score)``."""

    if not probe_confidences:
        return 0.0, 0.0

    mean_confidence = sum(probe_confidences) / len(probe_confidences)
    variance = sum(
        (confidence - mean_confidence) ** 2 for confidence in probe_confidences
    ) / len(probe_confidences)
    consistency = max(0.0, 1.0 - variance * 4)
    final_confidence = mean_confidence * 0.8 + consistency * 0.2
    return final_confidence, consistency


def classify_hypothesis(confidence: float) -> str:
    """Map confidence to a verdict status."""

    if confidence >= 0.70:
        return "confirmed"
    if confidence >= 0.50:
        return "partially_confirmed"
    if confidence >= 0.30:
        return "inconclusive"
    return "rejected"
