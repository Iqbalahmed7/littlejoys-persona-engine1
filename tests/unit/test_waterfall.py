from __future__ import annotations

from src.analysis.waterfall import compute_funnel_waterfall


def test_waterfall_empty_input():
    assert compute_funnel_waterfall({}) == []


def test_waterfall_stages_in_funnel_order():
    results = {
        "p1": {"rejection_stage": "awareness"},
        "p2": {"rejection_stage": None},
    }
    waterfall = compute_funnel_waterfall(results)
    stages = [w.stage for w in waterfall]
    assert stages == ["need_recognition", "awareness", "consideration", "purchase"]


def test_waterfall_entered_decreases_monotonically():
    results = {
        "p1": {"rejection_stage": "need_recognition"},
        "p2": {"rejection_stage": "awareness"},
        "p3": {"rejection_stage": "consideration"},
        "p4": {"rejection_stage": "purchase"},
        "p5": {"rejection_stage": None},
    }
    waterfall = compute_funnel_waterfall(results)
    prev_entered = waterfall[0].entered

    for stage in waterfall[1:]:
        assert stage.entered <= prev_entered
        prev_entered = stage.entered


def test_waterfall_all_adopt_shows_zero_drops():
    results = {
        "p1": {"rejection_stage": None},
        "p2": {"rejection_stage": None},
        "p3": {"rejection_stage": None},
    }
    waterfall = compute_funnel_waterfall(results)

    for stage in waterfall:
        assert stage.dropped == 0
        assert stage.entered == 3
        assert stage.passed == 3
        assert stage.pass_rate == 1.0
        assert stage.cumulative_pass_rate == 1.0


def test_waterfall_all_reject_shows_full_drop_at_first_stage():
    results = {
        "p1": {"rejection_stage": "need_recognition"},
        "p2": {"rejection_stage": "need_recognition"},
        "p3": {"rejection_stage": "need_recognition"},
    }
    waterfall = compute_funnel_waterfall(results)

    # Stage 0 (need_recognition)
    stage0 = waterfall[0]
    assert stage0.entered == 3
    assert stage0.dropped == 3
    assert stage0.passed == 0
    assert stage0.pass_rate == 0.0
    assert stage0.cumulative_pass_rate == 0.0

    # Subsequent stages should have 0 entered
    for stage in waterfall[1:]:
        assert stage.entered == 0
        assert stage.passed == 0
        assert stage.pass_rate == 0.0


def test_waterfall_cumulative_rate_matches_adoption():
    results = {
        "p1": {"rejection_stage": "awareness"},
        "p2": {"rejection_stage": "awareness"},
        "p3": {"rejection_stage": None},
        "p4": {"rejection_stage": None},
    }
    waterfall = compute_funnel_waterfall(results)

    for stage in waterfall:
        # 2 out of 4 adopted -> cumulative rate should be 0.5 everywhere
        assert stage.cumulative_pass_rate == 0.5
