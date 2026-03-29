# Cursor — Sprint 11 Track A: LLM Wiring + Spend Controls

**Branch:** `sprint-11-track-a-llm-wiring`
**Base:** `main`

## Context

The interview system already has a complete LLM pipeline (`LLMClient` with Anthropic API, retries, caching, mock mode). However, the Streamlit interview page hardcodes `anthropic_api_key=""` when constructing the client, so real LLM calls never work. This track fixes the wiring and adds session-level spend controls so we don't burn money during demos.

## Deliverables

### 1. Fix API Key Resolution in `app/pages/5_interviews.py` (MODIFY)

The current `_build_interviewer()` is broken for real LLM:

```python
# CURRENT (broken)
@st.cache_resource(show_spinner=False)
def _build_interviewer(mock_llm: bool) -> PersonaInterviewer:
    client = LLMClient(
        Config(
            llm_mock_enabled=mock_llm,
            llm_cache_enabled=False,
            anthropic_api_key="",  # ← never works for real LLM
        )
    )
    return PersonaInterviewer(client)
```

Replace with:

```python
def _resolve_api_key() -> str:
    """Read Anthropic API key from Streamlit secrets (cloud) or .env.local (local)."""
    # Streamlit Cloud secrets take priority
    try:
        if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
            return str(st.secrets["ANTHROPIC_API_KEY"])
    except Exception:
        pass
    # Fall back to env/config
    from src.config import get_config
    key = get_config().anthropic_api_key
    return key if key and key != "sk-ant-REPLACE_ME" else ""


def _has_api_key() -> bool:
    """Check if a real API key is available."""
    key = _resolve_api_key()
    return bool(key) and not key.startswith("sk-ant-REPLACE")


@st.cache_resource(show_spinner=False)
def _build_interviewer(mock_llm: bool) -> PersonaInterviewer:
    api_key = "" if mock_llm else _resolve_api_key()
    client = LLMClient(
        Config(
            llm_mock_enabled=mock_llm,
            llm_cache_enabled=not mock_llm,  # Cache real LLM responses
            anthropic_api_key=api_key,
        )
    )
    return PersonaInterviewer(client)
```

### 2. Create `src/utils/spend_tracker.py` (NEW)

```python
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


class SessionSpendTracker:
    """Track LLM spend within a single Streamlit session.

    Stored in st.session_state to persist across reruns.
    """

    def __init__(self) -> None:
        self.total_calls: int = 0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_cost_usd: float = 0.0

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
        """Check if another LLM call is allowed.

        Returns:
            (allowed, reason) — reason is empty string if allowed.
        """
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
            "remaining_calls": max(
                0, INTERVIEW_MAX_CALLS_PER_SESSION - self.total_calls
            ),
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
```

### 3. Integrate Spend Tracker into Interview Page

In `app/pages/5_interviews.py`, add spend tracking:

```python
from src.utils.spend_tracker import SessionSpendTracker

# After session key initialization block, add:
if "spend_tracker" not in st.session_state:
    st.session_state["spend_tracker"] = SessionSpendTracker()
tracker: SessionSpendTracker = st.session_state["spend_tracker"]

# When "Reset Conversation" is clicked, also reset tracker:
if st.button("Reset Conversation"):
    st.session_state["interview_turns"] = []
    st.session_state["interview_quality_warnings"] = []
    st.session_state["interview_guardrail_warnings"] = []
    tracker.reset()
    st.rerun()
```

Before sending a question to the LLM (inside the `if question:` block), check spend:

```python
if question:
    if not mock_llm:
        allowed, reason = tracker.can_proceed()
        if not allowed:
            st.error(reason)
            st.stop()
    # ... existing question handling ...
```

After getting the reply, record the spend:

```python
    # After reply = _run_async(...)
    if not mock_llm and hasattr(reply, 'content'):
        # Estimate tokens from response length
        input_tokens = max(1, len(question) // 4)
        output_tokens = max(1, len(reply.content) // 4)
        tracker.record_call(input_tokens, output_tokens, "claude-sonnet-4-6")
```

**Better approach:** Modify `PersonaInterviewer.interview()` to return token usage alongside the turn. Add an optional `last_usage` attribute:

```python
# In interviews.py, after the LLM call in the else branch:
    else:
        response = await self.llm.generate(...)
        response_text = response.text.strip()
        # Expose usage for spend tracking
        self._last_input_tokens = response.input_tokens
        self._last_output_tokens = response.output_tokens
```

Then in the page:
```python
    if not mock_llm:
        tracker.record_call(
            getattr(interviewer, '_last_input_tokens', 0),
            getattr(interviewer, '_last_output_tokens', 0),
            "claude-sonnet-4-6",
        )
```

### 4. Add Constants to `src/constants.py`

```python
# --- Interview LLM Spend Controls (Sprint 11) ---
INTERVIEW_MAX_CALLS_PER_SESSION = 50
INTERVIEW_MAX_COST_PER_SESSION_USD = 2.00
INTERVIEW_COST_PER_1K_INPUT_USD = 0.003   # Claude Sonnet input
INTERVIEW_COST_PER_1K_OUTPUT_USD = 0.015  # Claude Sonnet output
```

## Files to Read Before Starting

1. `app/pages/5_interviews.py` — **full file** — current interview page with mock toggle
2. `src/analysis/interviews.py` — **lines 434-498** — `PersonaInterviewer.interview()` method
3. `src/utils/llm.py` — **full file** — `LLMClient`, `LLMResponse` with token tracking
4. `src/config.py` — **full file** — `Config` class with env loading
5. `src/constants.py` — existing `INTERVIEW_*` constants
6. `.env.example` — current env var documentation

## Constraints

- Python 3.11+
- Do NOT change `LLMClient` internals — it already works with real Anthropic API
- Do NOT add `st.set_page_config()` — it's only in `app/streamlit_app.py`
- API key must work from both `.env.local` (local dev) and `st.secrets` (Streamlit Cloud)
- `_build_interviewer` must remain `@st.cache_resource` but the cache key changes with `mock_llm`
- Spend tracker must be serializable in `st.session_state`
- No new pip dependencies

## Feedback from Sprint 10

Your Sprint 10 delivery was the strongest on the team. Keep it up. Two things to improve:
1. Add brief docstrings to private helpers.
2. Include file paths, line counts, and a simple file listing in your delivery report. Example: "3 files changed, +480/-0: src/simulation/explorer.py (new, 479 lines), tests/unit/test_explorer.py (new, 111 lines)".

## Acceptance Criteria

- [ ] `_resolve_api_key()` reads from `st.secrets` first, then `.env.local`
- [ ] `_has_api_key()` returns True only for real keys (not placeholder)
- [ ] `_build_interviewer()` passes real API key when mock is off
- [ ] `SessionSpendTracker` tracks calls, tokens, and estimated cost
- [ ] `can_proceed()` blocks when call limit or cost limit exceeded
- [ ] Spend tracker integrated into interview page question flow
- [ ] Token usage recorded after each real LLM call
- [ ] Constants added to `src/constants.py`
- [ ] All existing tests still pass
