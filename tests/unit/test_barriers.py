import pytest

from src.analysis.barriers import analyze_barriers, summarize_barrier_stages
from src.constants import ANALYSIS_STAGE_SUMMARY_TOP_REASONS


@pytest.fixture
def mock_results():
    return {
        "p1": {"rejection_stage": "awareness", "rejection_reason": "ignored_ad"},
        "p2": {"rejection_stage": "awareness", "rejection_reason": "ignored_ad"},
        "p3": {"rejection_stage": "consideration", "rejection_reason": "price_too_high"},
        "p4": {"rejection_stage": None, "rejection_reason": None},  # adopted
        "p5": {"rejection_stage": "intent", "rejection_reason": "no_trust"},
    }


def test_barrier_distribution_sums_to_rejections(mock_results):
    dists = analyze_barriers(mock_results)
    assert len(dists) == 3

    total_rejections = sum(d.count for d in dists)
    # 4 personas rejected, 1 adopted
    assert total_rejections == 4


def test_every_rejection_has_a_reason(mock_results):
    dists = analyze_barriers(mock_results)
    for d in dists:
        assert d.barrier is not None
        assert d.stage is not None
        assert d.count > 0

    # test invalid format where stage is missing
    bad_results = {"p1": {"rejection_reason": "missed"}, "p2": {"rejection_stage": "awareness"}}
    bad_dists = analyze_barriers(bad_results)
    assert len(bad_dists) == 0


def test_barrier_analysis_empty_results():
    assert len(analyze_barriers({})) == 0
    assert len(analyze_barriers([])) == 0


def test_stage_summary_percentages_sum_to_100(mock_results) -> None:
    """Stage shares are relative to total rejection events."""

    summaries = summarize_barrier_stages(mock_results)
    assert summaries
    total_pct = sum(s.percentage_of_rejections for s in summaries)
    assert total_pct == pytest.approx(100.0)


def test_stage_summary_sorted_by_drop_count() -> None:
    """Stages with more drop-offs appear first."""

    results = {
        "p1": {"rejection_stage": "awareness", "rejection_reason": "a"},
        "p2": {"rejection_stage": "awareness", "rejection_reason": "b"},
        "p3": {"rejection_stage": "purchase", "rejection_reason": "c"},
    }
    summaries = summarize_barrier_stages(results)
    assert [s.stage for s in summaries] == ["awareness", "purchase"]
    assert summaries[0].total_dropped == 2
    assert summaries[1].total_dropped == 1


def test_stage_summary_top_reasons_max_three() -> None:
    """At most ``ANALYSIS_STAGE_SUMMARY_TOP_REASONS`` reasons per stage."""

    results = {
        "p1": {"rejection_stage": "consideration", "rejection_reason": "r1"},
        "p2": {"rejection_stage": "consideration", "rejection_reason": "r2"},
        "p3": {"rejection_stage": "consideration", "rejection_reason": "r3"},
        "p4": {"rejection_stage": "consideration", "rejection_reason": "r4"},
        "p5": {"rejection_stage": "consideration", "rejection_reason": "r4"},
    }
    summaries = summarize_barrier_stages(results)
    assert len(summaries) == 1
    assert len(summaries[0].top_reasons) == ANALYSIS_STAGE_SUMMARY_TOP_REASONS
    assert summaries[0].top_reasons == ["r4", "r1", "r2"]


def test_barrier_percentage_relative_to_total_population() -> None:
    results = {
        "p1": {"rejection_stage": "awareness", "rejection_reason": "r1"},
        "p2": {"rejection_stage": "awareness", "rejection_reason": "r1"},
        "p3": {"rejection_stage": "consideration", "rejection_reason": "r2"},
        "p4": {"rejection_stage": None, "rejection_reason": None},  # adopted
    }

    dists = analyze_barriers(results)
    by_barrier = {d.barrier: d for d in dists}
    # Total personas = 4. r1 count=2 => 0.5
    assert by_barrier["r1"].percentage == pytest.approx(0.5)
    # r2 count=1 => 0.25
    assert by_barrier["r2"].percentage == pytest.approx(0.25)


def test_barrier_sorted_by_count_descending() -> None:
    results = {
        "p1": {"rejection_stage": "awareness", "rejection_reason": "a"},
        "p2": {"rejection_stage": "awareness", "rejection_reason": "a"},
        "p3": {"rejection_stage": "consideration", "rejection_reason": "b"},
        "p4": {"rejection_stage": "consideration", "rejection_reason": "c"},
        "p5": {"rejection_stage": None, "rejection_reason": None},
    }

    dists = analyze_barriers(results)
    # First entry should have highest count (2)
    assert dists[0].count == 2


def test_barrier_handles_missing_stage_key() -> None:
    bad_results = {
        "p1": {"rejection_reason": "missed"},  # missing rejection_stage
        "p2": {"rejection_stage": "awareness", "rejection_reason": "ok"},
    }
    dists = analyze_barriers(bad_results)
    assert len(dists) == 1
    assert dists[0].barrier == "ok"
