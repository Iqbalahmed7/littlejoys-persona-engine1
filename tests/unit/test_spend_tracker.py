"""Unit tests for session spend tracker."""

from __future__ import annotations

from src.utils.spend_tracker import SessionSpendTracker


def test_initial_state_is_zero() -> None:
    """A fresh tracker should have zero calls, tokens, and cost."""
    tracker = SessionSpendTracker()
    assert tracker.total_calls == 0
    assert tracker.total_input_tokens == 0
    assert tracker.total_output_tokens == 0
    assert tracker.total_cost_usd == 0.0


def test_record_call_accumulates() -> None:
    """Recording multiple calls should sum tokens and cost."""
    tracker = SessionSpendTracker()
    tracker.record_call(input_tokens=1000, output_tokens=500, model="claude-sonnet-4-6")
    tracker.record_call(input_tokens=2000, output_tokens=1000, model="claude-sonnet-4-6")
    assert tracker.total_calls == 2
    assert tracker.total_input_tokens == 3000
    assert tracker.total_output_tokens == 1500
    assert tracker.total_cost_usd > 0


def test_can_proceed_under_limits() -> None:
    """Should allow calls when under both limits."""
    tracker = SessionSpendTracker()
    tracker.record_call(input_tokens=100, output_tokens=50)
    allowed, reason = tracker.can_proceed()
    assert allowed is True
    assert reason == ""


def test_can_proceed_blocked_by_call_limit() -> None:
    """Should block when call count exceeds MAX_CALLS_PER_SESSION."""
    from src.constants import INTERVIEW_MAX_CALLS_PER_SESSION

    tracker = SessionSpendTracker()
    for _ in range(INTERVIEW_MAX_CALLS_PER_SESSION):
        tracker.record_call(input_tokens=10, output_tokens=10)
    allowed, reason = tracker.can_proceed()
    assert allowed is False
    assert "limit" in reason.lower()


def test_can_proceed_blocked_by_cost_limit() -> None:
    """Should block when estimated cost exceeds MAX_COST_PER_SESSION."""
    tracker = SessionSpendTracker()
    # Send a huge call that will exceed the cost limit
    tracker.record_call(input_tokens=500_000, output_tokens=200_000)
    allowed, reason = tracker.can_proceed()
    assert allowed is False
    assert "cost" in reason.lower() or "limit" in reason.lower()


def test_reset_clears_all_counters() -> None:
    """Reset should zero out everything."""
    tracker = SessionSpendTracker()
    tracker.record_call(input_tokens=1000, output_tokens=500)
    tracker.reset()
    assert tracker.total_calls == 0
    assert tracker.total_cost_usd == 0.0
    summary = tracker.session_summary()
    assert summary["total_calls"] == 0


def test_session_summary_format() -> None:
    """Summary should include all expected keys."""
    tracker = SessionSpendTracker()
    tracker.record_call(input_tokens=1000, output_tokens=500)
    summary = tracker.session_summary()
    assert "total_calls" in summary
    assert "total_cost_usd" in summary
    assert "remaining_calls" in summary
    assert "remaining_budget_usd" in summary
    assert summary["total_calls"] == 1
    assert summary["remaining_calls"] >= 0
