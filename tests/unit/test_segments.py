from __future__ import annotations

import pytest

from src.analysis.segments import analyze_segments, compare_segments_across_scenarios


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


def test_cross_scenario_identifies_best_worst() -> None:
    """Best and worst scenario IDs match min/max adoption for the segment."""

    s_a = {
        "p1": _base_row(outcome="adopt", city_tier="Tier1"),
        "p2": _base_row(outcome="adopt", city_tier="Tier1"),
    }
    s_b = {
        "p3": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="low_awareness"),
        "p4": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="low_awareness"),
    }
    cross = compare_segments_across_scenarios(
        {"scenario_high": s_a, "scenario_low": s_b},
        group_by="city_tier",
    )
    assert len(cross) == 1
    row = cross[0]
    assert row.segment_value == "Tier1"
    assert row.best_scenario_id == "scenario_high"
    assert row.worst_scenario_id == "scenario_low"
    assert row.best_adoption_rate == pytest.approx(1.0)
    assert row.worst_adoption_rate == pytest.approx(0.0)
    assert row.adoption_rate_spread == pytest.approx(1.0)


def test_cross_scenario_sorts_by_spread() -> None:
    """Larger adoption spread appears before smaller spread."""

    # Tier1: 1.0 vs 0.0 => spread 1.0
    tier1_high = {"a1": _base_row(outcome="adopt", city_tier="Tier1")}
    tier1_low = {"b1": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="x")}
    # Tier2: 0.5 vs 0.5 => spread 0
    tier2_a = {
        "c1": _base_row(outcome="adopt", city_tier="Tier2"),
        "c2": _base_row(outcome="reject", city_tier="Tier2", rejection_reason="y"),
    }
    tier2_b = {
        "d1": _base_row(outcome="adopt", city_tier="Tier2"),
        "d2": _base_row(outcome="reject", city_tier="Tier2", rejection_reason="y"),
    }
    cross = compare_segments_across_scenarios(
        {"s1": tier1_high, "s2": tier1_low, "s3": tier2_a, "s4": tier2_b},
        group_by="city_tier",
    )
    assert [r.segment_value for r in cross] == ["Tier1", "Tier2"]
    assert cross[0].adoption_rate_spread == pytest.approx(1.0)
    assert cross[1].adoption_rate_spread == pytest.approx(0.0)


def test_cross_scenario_empty_input() -> None:
    assert compare_segments_across_scenarios({}, group_by="city_tier") == []


def test_segment_funnel_score_averaging_correct() -> None:
    # Tier1: need_score avg = (0.2 + 0.8) / 2 = 0.5
    # Tier1: awareness_score avg = (0.1 + 0.3) / 2 = 0.2
    # Tier1: consideration_score key omitted from one row => avg over existing keys only
    results = {
        "p1": _base_row(
            outcome="adopt",
            city_tier="Tier1",
            need_score=0.2,
            awareness_score=0.1,
            consideration_score=0.4,
            purchase_score=0.9,
        ),
        "p2": _base_row(
            outcome="reject",
            city_tier="Tier1",
            need_score=0.8,
            awareness_score=0.3,
            consideration_score=0.6,
            purchase_score=0.1,
        ),
        "p3": {
            **_base_row(outcome="adopt", city_tier="Tier2", need_score=1.0),
            # drop awareness_score + purchase_score fields to ensure skipping works
            "awareness_score": None,
            "purchase_score": None,
        },
    }

    segs = analyze_segments(results, group_by="city_tier")
    tier1 = next(s for s in segs if s.segment_value == "Tier1")
    assert tier1.avg_funnel_scores["need_score"] == pytest.approx(0.5)
    assert tier1.avg_funnel_scores["awareness_score"] == pytest.approx(0.2)
    assert tier1.avg_funnel_scores["consideration_score"] == pytest.approx(0.5)
    assert tier1.avg_funnel_scores["purchase_score"] == pytest.approx(0.5)

    tier2 = next(s for s in segs if s.segment_value == "Tier2")
    assert tier2.avg_funnel_scores["need_score"] == pytest.approx(1.0)
    # None values must not appear in averages
    assert "awareness_score" not in tier2.avg_funnel_scores
    assert "purchase_score" not in tier2.avg_funnel_scores


def test_segment_results_sorted_by_adoption_rate_descending() -> None:
    # Tier1: 1/2 = 0.5
    # Tier2: 2/2 = 1.0
    # Tier3: 0/2 = 0.0
    results = {
        "p1": _base_row(outcome="adopt", city_tier="Tier1"),
        "p2": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="no_trust"),
        "p3": _base_row(outcome="adopt", city_tier="Tier2"),
        "p4": _base_row(outcome="adopt", city_tier="Tier2"),
        "p5": _base_row(outcome="reject", city_tier="Tier3", rejection_reason="price_too_high"),
        "p6": _base_row(outcome="reject", city_tier="Tier3", rejection_reason="no_trust"),
    }

    segs = analyze_segments(results, group_by="city_tier")
    assert [s.segment_value for s in segs] == ["Tier2", "Tier1", "Tier3"]


def test_segment_top_barriers_max_three() -> None:
    results = {
        "p1": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="r1"),
        "p2": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="r1"),
        "p3": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="r2"),
        "p4": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="r2"),
        "p5": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="r3"),
        "p6": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="r4"),
    }

    segs = analyze_segments(results, group_by="city_tier")
    tier1 = segs[0]
    assert len(tier1.top_barriers) == 3
    assert tier1.top_barriers == ["r1", "r2", "r3"]


def test_segment_non_dict_rows_skipped() -> None:
    results = {
        "p1": _base_row(outcome="adopt", city_tier="Tier1"),
        "p2": 123,  # non-dict row should be ignored
        "p3": _base_row(outcome="reject", city_tier="Tier1", rejection_reason="no_trust"),
    }

    segs = analyze_segments(results, group_by="city_tier")
    assert len(segs) == 1
    assert segs[0].count == 2


def test_segment_none_group_value_skipped() -> None:
    results = {
        "p1": _base_row(outcome="adopt", city_tier=None),
        "p2": _base_row(outcome="reject", city_tier=None, rejection_reason="no_trust"),
    }
    assert analyze_segments(results, group_by="city_tier") == []
