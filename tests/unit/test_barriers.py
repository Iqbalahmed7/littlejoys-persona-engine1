import pytest

from src.analysis.barriers import analyze_barriers


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
