"""Session-level LLM spend tracker for interview cost control."""

from __future__ import annotations

import structlog

from src.constants import (
    INTERVIEW_COST_PER_1K_INPUT_USD,
    INTERVIEW_COST_PER_1K_OUTPUT_USD,
    INTERVIEW_MAX_CALLS_PER_SESSION,
    INTERVIEW_MAX_COST_PER_SESSION_USD,
)

logger = structlog.get_logger(__name__)

_ACTIVE_TRACKER: SessionSpendTracker | None = None


class SessionSpendTracker:
    """Track LLM spend within a single Streamlit session.

    Stored in ``st.session_state`` to persist across reruns.
    """

    def __init__(self) -> None:
        self.total_calls: int = 0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_cost_usd: float = 0.0

        global _ACTIVE_TRACKER
        _ACTIVE_TRACKER = self

    def record_call(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "",
    ) -> None:
        """Record one LLM call's token usage."""
        self.total_calls += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        cost = (
            input_tokens / 1000 * INTERVIEW_COST_PER_1K_INPUT_USD
            + output_tokens / 1000 * INTERVIEW_COST_PER_1K_OUTPUT_USD
        )
        self.total_cost_usd += cost
        logger.debug(
            "spend_tracker_record",
            calls=self.total_calls,
            cost_usd=round(self.total_cost_usd, 4),
            model=model,
        )

    def can_proceed(self) -> tuple[bool, str]:
        """Return whether another LLM call is allowed and a blocking reason if not."""
        if self.total_calls >= INTERVIEW_MAX_CALLS_PER_SESSION:
            return False, (
                f"Session limit reached ({INTERVIEW_MAX_CALLS_PER_SESSION} calls). "
                "Reset the conversation or start a new session."
            )
        if self.total_cost_usd >= INTERVIEW_MAX_COST_PER_SESSION_USD:
            return False, (
                f"Session cost limit reached (${INTERVIEW_MAX_COST_PER_SESSION_USD:.2f}). "
                "Reset the conversation or start a new session."
            )
        return True, ""

    def session_summary(self) -> dict[str, object]:
        """Return a summary dict for display."""
        return {
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "remaining_calls": max(0, INTERVIEW_MAX_CALLS_PER_SESSION - self.total_calls),
            "remaining_budget_usd": round(
                max(0.0, INTERVIEW_MAX_COST_PER_SESSION_USD - self.total_cost_usd), 4
            ),
        }

    def reset(self) -> None:
        """Reset all counters (e.g. on conversation reset)."""
        self.total_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0


def record_llm_response(response: object) -> None:
    """Record an LLM response into the active session spend tracker."""

    if _ACTIVE_TRACKER is None:
        return

    inp = int(getattr(response, "input_tokens", 0) or 0)
    out = int(getattr(response, "output_tokens", 0) or 0)
    cached = bool(getattr(response, "cached", False))
    duration_ms = float(getattr(response, "duration_ms", 0.0) or 0.0)

    _ACTIVE_TRACKER.total_calls += 1
    _ACTIVE_TRACKER.total_input_tokens += inp
    _ACTIVE_TRACKER.total_output_tokens += out

    is_free = cached or duration_ms <= 0.0
    if not is_free:
        cost = (
            inp / 1000 * INTERVIEW_COST_PER_1K_INPUT_USD
            + out / 1000 * INTERVIEW_COST_PER_1K_OUTPUT_USD
        )
        _ACTIVE_TRACKER.total_cost_usd += cost
