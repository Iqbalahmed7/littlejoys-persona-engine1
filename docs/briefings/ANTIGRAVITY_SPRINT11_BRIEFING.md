# Antigravity — Sprint 11 Track D: Spend Tracker + Config Tests

**Branch:** `sprint-11-track-d-tests`
**Base:** `main`

## Context

Sprint 11 adds a session spend tracker and API key resolution for real LLM interviews. This track adds unit tests for those components.

## Deliverables

### 1. Create `tests/unit/test_spend_tracker.py` (NEW)

Write exactly these 6 test functions. Copy the signatures and docstrings as-is. Fill in the assertions.

```python
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
```

### 2. Create `tests/unit/test_interview_config.py` (NEW)

```python
"""Unit tests for interview configuration and API key resolution."""

from __future__ import annotations

from src.config import Config


def test_config_defaults_to_mock_enabled() -> None:
    """Default config should have mock mode enabled."""
    config = Config()
    assert config.llm_mock_enabled is True


def test_config_accepts_empty_api_key() -> None:
    """Config should accept empty string as API key (for mock mode)."""
    config = Config(anthropic_api_key="", llm_mock_enabled=True)
    assert config.anthropic_api_key == ""
    assert config.llm_mock_enabled is True
```

That's it. 2 files, 9 test functions total.

## Files to Read Before Starting

1. `src/utils/spend_tracker.py` — the module you're testing (read after Track A creates it)
2. `src/config.py` — Config class
3. `src/constants.py` — `INTERVIEW_MAX_CALLS_PER_SESSION`, `INTERVIEW_MAX_COST_PER_SESSION_USD`

## Constraints

- Python 3.11+
- Do NOT use `try/except ImportError` guards — these modules will exist when you run
- Do NOT add integration tests that require a real API key
- Do NOT use population data fixtures — these are pure unit tests
- No new pip dependencies

## Feedback from Sprint 10

Three areas to improve:
1. **Reporting accuracy** — you reported 30 tests but delivered 24. Count your tests before reporting: `pytest tests/your_files -v | grep "PASSED\|FAILED" | wc -l`
2. **Keep reports concise** — use this format: "2 files, 9 tests, all pass. Files: tests/unit/test_spend_tracker.py (7 tests), tests/unit/test_interview_config.py (2 tests)."
3. **Test isolation** — all tests in this sprint are pure unit tests with no external dependencies. No filesystem, no population data, no API calls.

## Acceptance Criteria

- [ ] `tests/unit/test_spend_tracker.py` — 7 tests, all pass
- [ ] `tests/unit/test_interview_config.py` — 2 tests, all pass
- [ ] No external dependencies (no filesystem, no API, no population data)
- [ ] `uv run ruff check .` passes
- [ ] `uv run pytest tests/ -q` — all pass
- [ ] Delivery report uses format: file count, test count, pass/fail, file list
