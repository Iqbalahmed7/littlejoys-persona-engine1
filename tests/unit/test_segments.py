from __future__ import annotations

import pytest

from src.analysis.segments import analyze_segments


def _base_row(
    *,
    outcome: str,
    city_tier: str | None = None,
    employment_status: str | None = None,
    need_score: float = 0.5,
    awareness_score: float = 0.5,
    consideration_score: float = 0.5,
    purchase_score: float = 0.5,
    rejection_reason: str | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "outcome": outcome,
        "need_score": need_score,
        "awareness_score": awareness_score,
        "consideration_score": consideration_score,
        "purchase_score": purchase_score,
        "rejection_reason": rejection_reason,
        "rejection_stage": None,
    }
    if city_tier is not None:
        row["city_tier"] = city_tier
    if employment_status is not None:
        row["employment_status"] = employment_status
    return row


def test_segment_by_city_tier_returns_three_groups() -> None:
    results = {
        "p1": _base_row(outcome="adopt", city_tier="Tier1"),
        "p2": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="price_too_high"),
        "p3": _base_row(outcome="adopt", city_tier="Tier2"),
        "p4": _base_row(outcome="reject", city_tier="Tier2", rejection_reason="no_trust"),
        "p5": _base_row(outcome="reject", city_tier="Tier3", rejection_reason="effort_too_high"),
    }

    segs = analyze_segments(results, group_by="city_tier")
    assert len(segs) == 3
    assert {s.segment_value for s in segs} == {"Tier1", "Tier2", "Tier3"}


def test_segment_adoption_rate_correct() -> None:
    # Tier1: 1 adopt out of 3 => 0.333...
    results = {
        "p1": _base_row(outcome="adopt", city_tier="Tier1"),
        "p2": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="price_too_high"),
        "p3": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="no_trust"),
        # Tier2: 2 adopts out of 2 => 1.0
        "p4": _base_row(outcome="adopt", city_tier="Tier2"),
        "p5": _base_row(outcome="adopt", city_tier="Tier2"),
    }

    segs = analyze_segments(results, group_by="city_tier")
    tier1 = next(s for s in segs if s.segment_value == "Tier1")
    assert tier1.count == 3
    assert tier1.adoption_rate == pytest.approx(1.0 / 3.0)


def test_segment_top_barriers_sorted_by_frequency() -> None:
    # Tier1 rejects: price_too_high(3), no_trust(2), effort_too_high(1)
    results = {
        "p1": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="price_too_high"),
        "p2": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="price_too_high"),
        "p3": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="price_too_high"),
        "p4": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="no_trust"),
        "p5": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="no_trust"),
        "p6": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="effort_too_high"),
    }

    segs = analyze_segments(results, group_by="city_tier")
    tier1 = segs[0]
    assert tier1.top_barriers == ["price_too_high", "no_trust", "effort_too_high"]


def test_segment_empty_results_returns_empty() -> None:
    assert analyze_segments({}, group_by="city_tier") == []


def test_segment_unknown_attribute_returns_empty() -> None:
    results = {
        "p1": _base_row(outcome="adopt", city_tier="Tier1"),
        "p2": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="price_too_high"),
    }

    assert analyze_segments(results, group_by="unknown_attribute") == []
