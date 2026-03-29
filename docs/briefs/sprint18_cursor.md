# Sprint 18 Brief — Cursor (Auto)
## Executive Summary + Counterfactual UI + Nutrimix 7-14 Event Config

### Context

Sprint 18 fixes the broken repeat-purchase loop (Codex), completes the event grammar (Goose), and adds the intelligence layer. Your job is threefold: (1) generate an LLM executive summary of simulation results, (2) wire the counterfactual engine into the Results page, and (3) configure Nutrimix 7-14 as a temporal scenario.

### Dependency
Wait for Codex to deliver `src/simulation/counterfactual.py` before wiring the UI.

### Task 1: Executive Summary Generator (`src/analysis/executive_summary.py` — NEW)

Single LLM call that turns simulation results into a PM-ready narrative.

```python
class ExecutiveSummary(BaseModel):
    """LLM-generated narrative summary of simulation results."""
    headline: str              # 1-line takeaway, e.g. "Nutrimix achieves 18% retention but loses 40% to taste fatigue"
    trajectory_summary: str    # 2-3 sentences on what happened over 12 months
    key_drivers: list[str]     # Top 3 decision variables that shaped outcomes
    recommendations: list[str] # Top 3 actionable recommendations
    risk_factors: list[str]    # Top 2 risks if nothing changes
    raw_llm_response: str      # Full response for debugging
    mock_mode: bool

def generate_executive_summary(
    report: ConsolidatedReport,
    scenario: ScenarioConfig,
    llm_client: LLMClient,
    mock_mode: bool = False,
) -> ExecutiveSummary:
```

**LLM prompt design**: Build a structured prompt that includes:
- Scenario name and product details
- Month-by-month active count (from event_monthly_rollup or temporal_snapshots)
- Behavioural cluster distribution
- Top decision drivers (from decision_rationale_summary)
- Counterfactual top intervention (if available)

Ask the LLM to return JSON with the fields above. Parse with Pydantic.

**Mock mode**: Return a hardcoded summary that exercises the UI. Do NOT call the LLM.

**Cost budget**: Use `sonnet` model. Single call, ~500 tokens input, ~300 tokens output. Should cost < $0.01.

### Task 2: Wire Counterfactual into Results Page (`app/pages/3_results.py`)

Add a new "Counterfactual Analysis" section after the existing Intervention Comparison:

```python
if report.counterfactual_results:  # New field on ConsolidatedReport
    st.subheader("Counterfactual Analysis")
    st.caption("What would happen if you changed one thing?")

    # Horizontal bar chart: each intervention's lift %
    # Green bars for positive lift, red for negative
    # Diamond marker at baseline (0% lift)

    # Below: expandable cards per counterfactual
    for cf in report.counterfactual_results:
        with st.expander(f"{cf.label} → {cf.lift_pct:+.1f}% active rate"):
            col1, col2 = st.columns(2)
            col1.metric("Baseline Active", f"{cf.baseline_active_rate:.1%}")
            col2.metric("With Intervention", f"{cf.counterfactual_active_rate:.1%}",
                       delta=f"{cf.lift_pct:+.1f}%")
            st.caption(f"Revenue impact: ₹{cf.revenue_lift:+,.0f}")
```

Chart key: `key="counterfactual_analysis"`

### Task 3: Wire Executive Summary into Results Page

At the TOP of the results page (before any charts), add:

```python
if report.executive_summary:
    st.markdown(f"### {report.executive_summary.headline}")
    st.markdown(report.executive_summary.trajectory_summary)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Key Drivers**")
        for d in report.executive_summary.key_drivers:
            st.markdown(f"- {d}")
    with col2:
        st.markdown("**Recommendations**")
        for r in report.executive_summary.recommendations:
            st.markdown(f"- {r}")
    with col3:
        st.markdown("**Risk Factors**")
        for r in report.executive_summary.risk_factors:
            st.markdown(f"- {r}")
    st.divider()
```

### Task 4: Extend ConsolidatedReport and Pipeline

Add to `src/analysis/research_consolidator.py`:
- `counterfactual_results: list[dict] | None = None` on `ConsolidatedReport`
- `executive_summary: dict | None = None` on `ConsolidatedReport`

Wire the counterfactual engine and executive summary into `ResearchRunner.run()` or into the consolidation step (whichever is cleaner). The counterfactual should run AFTER the primary simulation, using the same population and seed.

### Task 5: Nutrimix 7-14 Temporal Config (`src/decision/scenarios.py`)

Change `nutrimix_7_14` from `mode="static"` to `mode="temporal"` and adjust:
- `months: 12` (was 12 but mode was static)
- `awareness_level: 0.35` (lower than 2-6 — less established)
- `lj_pass_available: True`
- Verify `product.age_range = (7, 14)`, `price_inr = 649`

This enables the event engine to run on the 7-14 scenario. The same event grammar works but the different product parameters (lower awareness, higher price, older children) will produce different trajectories.

### Files to Create
- `src/analysis/executive_summary.py`

### Files to Modify
- `app/pages/3_results.py`
- `src/analysis/research_consolidator.py`
- `src/simulation/research_runner.py` (wire counterfactual + summary)
- `src/decision/scenarios.py` (nutrimix_7_14 mode change)

### Constraints
- Executive summary: Sonnet model, single call, mock mode must work
- Counterfactual chart: `height=300`, key="counterfactual_analysis"
- Backward compat: all existing static/temporal behaviour unchanged
- Run `uv run ruff check .` and `uv run pytest tests/ -x -q` before delivery
