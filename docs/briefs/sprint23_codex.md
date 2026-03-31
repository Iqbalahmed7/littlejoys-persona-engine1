# Sprint 23 Brief — Codex
## S3-02: Interventions Page (`app/pages/5_intervention.py`)

> **Engineer**: Codex (GPT 5.3 medium → escalate to GPT 5.4 High if intervention engine integration is complex)
> **Sprint**: 23
> **Ticket**: S3-02
> **Estimated effort**: Medium-High (new page + intervention engine integration + multi-row comparison table)

---

### Context

Phase 4 is the **strategic output** layer. Having identified the root cause in Phase 3, the founder now needs to know: *what do I do about it?*

This page generates, compares, and recommends interventions — turning the research into an actionable playbook. The comparison table is a key demo asset: it shows trade-offs clearly across multiple dimensions so the founder can make a staged investment decision.

---

### Backend: Intervention Engine

The intervention engine already exists at:
- `src/analysis/intervention_engine.py` — `generate_intervention_quadrant(input, scenario) -> InterventionQuadrant`
- `InterventionInput(problem_id: str)`
- `InterventionQuadrant` — has a list of `Intervention` objects

Each `Intervention` has (verify exact fields in `intervention_engine.py`):
- `name`, `description`, `category`
- `estimated_lift` (float, 0–1), `confidence` (float, 0–1)
- `implementation_complexity` (`"low"` / `"medium"` / `"high"`)
- `time_to_market_weeks` (int)
- `estimated_cost_usd` (int or float)

If any of these fields don't exist on the model, derive them from the available fields or add them to the model — **do not fake data**. Read `src/analysis/intervention_engine.py` carefully before building the table.

---

### Design Spec

**System Voice callout (render_system_voice — blue border) #1 — Opening:**
> "Phase 3 identified {dominant_hypothesis} as the primary barrier. I've generated {N} targeted interventions mapped to this root cause. Here is how they compare."

**Intervention Comparison Table:**

Use `st.dataframe` or a custom HTML table rendered with `st.markdown(unsafe_allow_html=True)`.
Rows = individual interventions. Columns:

| Column | Source | Display |
|--------|--------|---------|
| Intervention | `i.name` | Bold text |
| Description | `i.description` | Caption (grey, italic) |
| Est. Lift | `i.estimated_lift` | `+{pct}%` green if ≥15%, amber if 8–15%, grey if <8% |
| Confidence | `i.confidence` | 🟢/🟡/🔴 + pct |
| Complexity | `i.implementation_complexity` | Colour-coded chip: green=low, amber=medium, red=high |
| Time to Market | `i.time_to_market_weeks` | `{N} wks` |
| Est. Cost | `i.estimated_cost_usd` | `$X,XXX` |

Highlight the recommended row (highest confidence × lift composite score) with a `#EBF5FB` background.

**System Voice callout #2 — Staged Execution Recommendation:**
> "Our recommendation: begin with the **{low_complexity_intervention}** to build momentum and validate assumptions at low cost. If results confirm the hypothesis, escalate to **{high_lift_intervention}** in the next cycle."

Build this dynamically: pick the lowest-complexity high-confidence intervention as "begin with", and the highest-lift intervention as "escalate to".

**System Voice callout #3 — Caveat:**
> "These projections are based on {N}-persona simulation data. Real-world results will vary — use this as a directional compass, not a guarantee."

**Per-intervention expanders:**

Below the table, for each intervention, render an `st.expander(intervention.name)` containing `intervention.description` in full plus any available sub-points.

**Export:**
JSON download of the full quadrant. Filename: `{scenario_id}_interventions.json`.

---

### Session State

**Reads:**
- `st.session_state["core_finding"]` — for `dominant_hypothesis` and `scenario_id`
- `st.session_state["baseline_scenario_id"]` — fallback for scenario ID
- `st.session_state["baseline_problem_id"]` — for `InterventionInput`

**Writes:**
- `st.session_state["intervention_results"]` — the full `InterventionQuadrant` (triggers phase gate unlock for Phase 4 completion)

---

### Phase Gate

```python
if "core_finding" not in st.session_state:
    st.warning("Complete Phase 3 (Core Finding) first.", icon="🔒")
    st.stop()
```

---

### Imports to use

```python
from app.components.system_voice import render_system_voice
from app.utils.phase_state import render_phase_sidebar
from src.analysis.intervention_engine import InterventionInput, generate_intervention_quadrant
```

---

### Files to Create/Modify

| File | Change |
|------|--------|
| `app/pages/5_intervention.py` | Create new page |

### Files NOT to modify

`src/analysis/intervention_engine.py` — read-only from this ticket. If you find bugs or missing fields, flag them in a comment but do not change the engine.

---

### Acceptance Criteria

- [ ] Phase gate blocks entry if `core_finding` not in session state
- [ ] Comparison table renders all required columns with correct colour coding
- [ ] Recommended row is highlighted
- [ ] Three system voice narrations present (opening, staged execution, caveat)
- [ ] Per-intervention expanders rendered below table
- [ ] `intervention_results` written to session state on page load (unlocks phase completion)
- [ ] JSON export download button present
- [ ] Import check passes: `python -c "import app.pages.5_intervention"`
- [ ] No raw `os.environ.get()` — all config through `Config` object
