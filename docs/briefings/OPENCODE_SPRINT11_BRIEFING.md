# OpenCode — Sprint 11 Track C: Interview UX Polish

**Branch:** `sprint-11-track-c-interview-ux`
**Base:** `main`

## Context

The interview page currently defaults to mock LLM mode with a sidebar toggle. For the co-founder demo, we want real LLM by default when an API key is available, plus cost visibility and better loading states.

**Important:** Use the code snippets below as-is. Do not add wrapper functions or abstraction layers beyond what is specified.

## Deliverables

### 1. Smart Mock Toggle Default in `app/pages/5_interviews.py` (MODIFY)

Currently the mock toggle defaults to `True`:
```python
mock_llm = st.toggle("Mock LLM Mode", value=True)
```

Change to auto-detect API key availability:

```python
def _has_api_key() -> bool:
    """Check if a real Anthropic API key is configured."""
    try:
        if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
            key = str(st.secrets["ANTHROPIC_API_KEY"])
            return bool(key) and not key.startswith("sk-ant-REPLACE")
    except Exception:
        pass
    from src.config import get_config
    key = get_config().anthropic_api_key
    return bool(key) and not key.startswith("sk-ant-REPLACE")
```

Then update the sidebar:

```python
with st.sidebar:
    st.subheader("Interview Controls")
    scenario_id = st.selectbox("Scenario", options=SCENARIO_IDS, index=0)

    api_available = _has_api_key()
    if api_available:
        mock_llm = st.toggle(
            "Mock LLM Mode",
            value=False,
            key="interview_mock_toggle",
            help="Real LLM responses powered by Claude Sonnet. Toggle on for instant mock responses.",
        )
    else:
        mock_llm = True
        st.info("No API key configured. Using mock responses. See docs/DEPLOYMENT.md to set up.")

    population_path = st.text_input("Population Path", value=DASHBOARD_DEFAULT_POPULATION_PATH)
```

### 2. Add Cost Indicator to Sidebar

After the mock toggle section in the sidebar, add a spend display:

```python
    # Cost indicator (only when using real LLM)
    if not mock_llm:
        from src.utils.spend_tracker import SessionSpendTracker

        if "spend_tracker" not in st.session_state:
            st.session_state["spend_tracker"] = SessionSpendTracker()
        tracker = st.session_state["spend_tracker"]
        summary = tracker.session_summary()

        st.divider()
        st.caption("💰 Session Cost")
        cost_cols = st.columns(2)
        cost_cols[0].metric(
            "Spent",
            f"${summary['total_cost_usd']:.2f}",
        )
        cost_cols[1].metric(
            "Calls",
            f"{summary['total_calls']}",
        )
        st.progress(
            min(1.0, summary["total_cost_usd"] / 2.0),
            text=f"${summary['total_cost_usd']:.2f} / $2.00 budget",
        )
```

### 3. Add Response Metadata Under Each Persona Response

In the chat display loop, add a small caption showing whether the response was real or mock:

Current code:
```python
for turn in turns:
    role = "assistant" if turn.role == "persona" else "user"
    with st.chat_message(role):
        st.write(turn.content)
```

Replace with:

```python
for turn in turns:
    role = "assistant" if turn.role == "persona" else "user"
    with st.chat_message(role):
        st.write(turn.content)
        if turn.role == "persona":
            if mock_llm:
                st.caption("🔧 Mock response")
            else:
                st.caption("🤖 Claude Sonnet")
```

### 4. Better Loading State

Current:
```python
with st.spinner("Generating in-character response..."):
```

Replace with:

```python
    persona_name = selected_persona.display_name or selected_persona.demographics.city_name
    spinner_text = (
        f"🔧 Generating mock response..."
        if mock_llm
        else f"💭 {persona_name} is thinking..."
    )
    with st.spinner(spinner_text):
```

### 5. Add Mode Banner at Top of Chat Area

After the metric_cols row and before the chat history, add a visual mode indicator:

```python
if mock_llm:
    st.info(
        "🔧 **Mock Mode** — Responses are generated from templates, not an LLM. "
        "Toggle off in the sidebar for real AI-powered conversations."
    )
else:
    st.success(
        "🤖 **Live Mode** — Responses powered by Claude Sonnet. "
        "Each response costs ~$0.02-0.05."
    )
```

## Files to Read Before Starting

1. `app/pages/5_interviews.py` — **full file** — current interview page
2. `src/config.py` — `Config` class, `get_config()`
3. `src/constants.py` — `INTERVIEW_*` constants

## Constraints

- Python 3.11+
- Do NOT add `st.set_page_config()` — it's only in `app/streamlit_app.py`
- Do NOT add wrapper functions like `_safe_attr()` — access attributes directly
- Use the code snippets above as-is
- All widgets need unique `key=` parameters
- No new pip dependencies
- `_has_api_key()` may be duplicated from Track A — that's fine, it will be deduplicated in review if needed

## Feedback from Sprint 10

Your Sprint 10 delivery was solid and complete. One key improvement:
- **Do not add abstraction layers that aren't in the briefing.** The `_safe_attr()` wrapper in Sprint 10 added ~30 lines of indirection around typed Pydantic models. These are validated models — access attributes directly. This sprint's snippets show direct access; use them as-is.

## Acceptance Criteria

- [ ] Mock toggle defaults to OFF when API key is available
- [ ] Mock toggle defaults to ON (forced) when no API key, with info message
- [ ] Cost indicator shows in sidebar during real LLM mode
- [ ] Progress bar shows spend vs $2.00 budget
- [ ] Each persona response shows "🔧 Mock response" or "🤖 Claude Sonnet" caption
- [ ] Spinner shows persona name when in real LLM mode
- [ ] Mode banner (info/success) shows above chat area
- [ ] No `st.set_page_config()` in page file
- [ ] All existing tests still pass
