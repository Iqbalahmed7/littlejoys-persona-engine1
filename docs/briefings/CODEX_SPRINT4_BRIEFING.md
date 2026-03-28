# Codex — Sprint 4 Briefing

> **Sprint**: 4 (Days 7-8)
> **Branch**: `feat/PRD-011-interview-report-pages` from `staging`
> **PRD**: PRD-011 (Streamlit Dashboard)

---

## Your Assignments

You own the LLM-powered interactive pages. These are the "wow factor" for the demo.

### Task 1: Persona Interview Chat Page (P0)

**File**: `app/pages/5_interviews.py`

1. **Persona selector**: Dropdown of Tier 2 personas showing ID + outcome (adopt/reject)
2. **Scenario selector**: Which scenario context
3. **Chat interface**: Use `st.chat_message("user")` and `st.chat_message("assistant")` blocks
4. **Input**: `st.chat_input("Ask the persona a question...")` at bottom
5. **Suggested questions**: Row of `st.button` quick-fire prompts:
   - "Why did you decide this?"
   - "What about the price?"
   - "Do you trust the brand?"
   - "Tell me about your morning routine"
6. **Persona card sidebar**: `st.sidebar` section showing demographics, top psychographic highlights, decision outcome + scores while chatting
7. **Quality indicator**: After each response, show green/yellow/red dot based on `check_interview_quality()`:
   - Green: all checks pass
   - Yellow: warnings but in_character=True
   - Red: in_character=False
8. **Session state**: `st.session_state.interview_history` preserves turns across rerenders
9. **Mock mode**: Must work with `LLMClient(mock_enabled=True)` for demos without API keys
10. `st.spinner("Persona is thinking...")` during LLM calls

### Task 2: ReportAgent Interactive Page (P0)

**File**: `app/pages/6_report.py`

1. **Scenario selector**: Dropdown
2. **Generate button**: `st.button("Generate Report")` triggers `ReportAgent.generate_report()` with `st.spinner`
3. **Report display**: Render `report.raw_markdown` with `st.markdown()`
4. **Section navigation**: `st.tabs` for each of the 6 report sections
5. **Supporting data**: `st.expander("View raw data")` inside each tab showing `section.supporting_data` as JSON
6. **Tool call log**: `st.expander("ReACT Tool Calls")` showing tool_calls_made count and which tools were used
7. **Download**: `st.download_button("Download Report", report.raw_markdown, file_name=f"{scenario_id}_report.md")`
8. **Grounding warnings**: If `validate_report_grounding()` returns warnings, show them in an expander with `st.warning`
9. Must work in mock LLM mode
10. Cache generated reports in `st.session_state.generated_reports[scenario_id]`

### Task 3: Pre-Compute Script (P1)

**File**: `scripts/precompute_results.py`

Build the data preparation script so the dashboard has instant-load data:
1. Generate population (300 Tier 1 + 30 Tier 2) if `data/population/` doesn't exist
2. Run static simulation for all 4 scenarios
3. Run all predefined counterfactuals
4. Save results as JSON to `data/results/{scenario_id}_static.json`
5. Save counterfactual results to `data/results/{scenario_id}_counterfactuals.json`
6. Log timing for each step
7. Idempotent: skip if result files already exist (force flag to override)

```python
def precompute_all(force: bool = False) -> None:
```

### Tests

```python
# tests/unit/test_precompute.py
test_precompute_creates_result_files()
test_precompute_idempotent()
```

---

## Standards

- Use `st.session_state` for all mutable state — no module-level globals
- `st.spinner` on every LLM/simulation call
- `@st.cache_data` / `@st.cache_resource` where appropriate
- structlog for backend logging (not `st.write` for debugging)
- Mock mode must produce realistic-looking output — the demo may run without API keys
- Use `DEFAULT_SEED` from constants for any seeded operations
- Run before submitting:
  ```
  uv run ruff check app/ scripts/
  uv run pytest tests/unit/test_precompute.py -v
  streamlit run app/streamlit_app.py  # manual smoke test
  ```

---

## Sprint 3 Feedback

Composite was **9.2** — highest on the team. Zero fixes needed. For Sprint 4: the interview page is the single most impressive demo element. Make the mock responses feel natural and varied. The persona card sidebar is what sells the "these are real people" narrative — make it visually rich.
