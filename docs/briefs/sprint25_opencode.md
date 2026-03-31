# Sprint 25 — OpenCode (S5-05)
**Engineer:** OpenCode (GPT-5.4 Nano)
**Theme:** Cross-Scenario Comparison Page

---

## Context

The engine supports 4 business problems (scenarios). After running an investigation on one scenario, users want to compare findings across two scenarios side by side — e.g. "How does the repeat-purchase barrier for Nutrimix 2–6 compare to the effort barrier for Protein Mix?" This sprint creates a new Page 9 that lets users load two scenario results and compare them.

---

## Task A — Create the Comparison Page

**New file:** `app/pages/9_compare.py`

```python
# ruff: noqa: N999
"""Cross-Scenario Comparison.

Compare findings, cohort splits, and top interventions across two business problems.
"""
```

Page config:
```python
st.set_page_config(page_title="Compare Scenarios", page_icon="⚖️", layout="wide")
render_phase_sidebar()
st.header("Cross-Scenario Comparison")
st.caption("Compare findings across two business problems side by side.")
```

---

## Task B — Scenario Selectors

At the top, two columns with scenario selectors:

```python
col_a, col_b = st.columns(2)
with col_a:
    scenario_a = st.selectbox("Scenario A", options=SCENARIO_IDS, format_func=_problem_label)
with col_b:
    scenario_b = st.selectbox("Scenario B", options=SCENARIO_IDS, format_func=_problem_label)
```

Where `_problem_label` maps scenario IDs to human-readable names (same mapping as in `8_synthesis_report.py`).

Add a guard: if `scenario_a == scenario_b`, show `st.warning("Select two different scenarios to compare.")` and `st.stop()`.

---

## Task C — Run Baseline for Each Selected Scenario

For each scenario, check if `scenario_results[scenario_id]` is already in session state (it should be — home page pre-loads all 4). If not, run `run_static_simulation()` on demand with a spinner.

Then run `classify_population()` for each scenario to get the cohort split. Cache these results in `st.session_state[f"compare_cohorts_{scenario_id}"]` to avoid re-running on re-render.

---

## Task D — Side-by-Side Comparison Sections

### Section 1: Population Baseline
Two columns, each showing the 5 cohort metrics for that scenario (same metric tiles as Phase 1).

### Section 2: Adoption Funnel
Two Plotly `go.Funnel` charts side by side (Became Aware → Tried → Repeated → Still Active).

### Section 3: Core Finding (if available)
Check `st.session_state.get(f"core_finding_{scenario_id}")` — if not available, show `st.info("Run Phase 3 for this scenario to see its core finding.")`.

If available, show the dominant hypothesis + confidence side by side using the orange bordered callout style from `8_synthesis_report.py`.

### Section 4: Top Intervention per Scenario
Check `st.session_state.get(f"intervention_run_{scenario_id}")` — if not available, show `st.info("Run Phase 4 for this scenario to see its top intervention.")`.

If available, show the #1 ranked intervention (by absolute_lift) for each scenario with its lift and complexity.

---

## Task E — Session State Key Convention

**Important:** The comparison page can't reuse the existing single-scenario session state keys (`baseline_cohorts`, `core_finding`, etc.) because those would overwrite the main pipeline state.

Use per-scenario keys for comparison data only:
- `compare_cohorts_{scenario_id}` — cohort data for comparison
- Never write to `baseline_cohorts`, `probe_results`, `core_finding`, or `intervention_run`

The page is **read-only** with respect to the main pipeline session state.

---

## Task F — Navigation

Add "⚖️ Compare Scenarios" to the phase sidebar by updating `app/utils/phase_state.py` — add it as an always-available link (no phase gate required).

Add a link to the home page quick-links:
```python
with col4:  # add a 4th column
    st.page_link("pages/9_compare.py", label="⚖️ Compare Scenarios", icon="⚖️")
```

---

## Acceptance Criteria

- [ ] Page loads at `/compare` without errors
- [ ] Two scenario selectors work; same-scenario guard shows warning
- [ ] Section 1: Cohort metrics show for both scenarios
- [ ] Section 2: Two funnel charts render side by side
- [ ] Section 3: Core finding shows if available, info message if not
- [ ] Section 4: Top intervention shows if available, info message if not
- [ ] Writing to compare_ keys never overwrites main pipeline session state
- [ ] Navigation link added to sidebar and home page
- [ ] All existing tests pass
