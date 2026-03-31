# Sprint 23 Brief — Cursor
## S3-01: Core Finding Page (`app/pages/4_finding.py`)

> **Engineer**: Cursor (Auto)
> **Sprint**: 23
> **Ticket**: S3-01
> **Estimated effort**: Medium (new page, moderate complexity)
> **Correction from S2-01**: Always use the `Config` object to read configuration. Never call `os.environ.get()` directly for app-level flags — route through `Config` instead.

---

### Context

Phase 3 is the **climactic moment** of the demo. After the user has watched probes accumulate evidence across hypotheses, this page synthesises everything into **one clear finding** — the answer to the business question they posed in Phase 1.

This is the page that makes an investor or PM lean forward. It should feel like a reveal.

---

### Design Spec

**System Voice callout (render_system_voice — blue border):**
> "The investigation is complete. Across {N} hypotheses and {P} probes, a dominant pattern has emerged. Here is what the evidence says."

**Core Finding box (render_core_finding — orange all-borders):**
The synthesised one-sentence finding pulled from `OrchestrationResult.core_finding_draft` or `TreeSynthesis.summary`.

**Evidence Chain section:**
A numbered list linking each confirmed/partially-confirmed hypothesis to its strongest probe result. Show:
- Hypothesis title
- Verdict badge (reuse `_VERDICT_BADGE` from `3_decompose.py`)
- Best evidence snippet (strongest confidence probe's `evidence_summary`, truncated to 200 chars)
- Effect size or lift number where available

**Magic Moment callout (render_magic_moment — green border):**
> "This is your answer. The data points to {dominant_hypothesis_title} as the primary barrier — affecting {cohort_size} of your target households."

**Synthesis Narrative:**
Render `OrchestrationResult.synthesis_narrative` in full as a paragraph (this is the cross-hypothesis pattern text from the orchestrator). This may be long — wrap in `st.expander("Read full synthesis", expanded=False)`.

**Export button:**
JSON download of the finding + evidence chain. Filename: `{scenario_id}_core_finding.json`.

**Proceed button:**
`st.button("Proceed to Interventions →", type="primary")` → `st.switch_page("pages/5_intervention.py")`
Writes `st.session_state["core_finding"]` before switching.

---

### Session State

**Reads:**
- `st.session_state["probe_results"]` — dict with keys `"synthesis"` (TreeSynthesis) and `"orchestration"` (OrchestrationResult, optional)
- `st.session_state["baseline_cohorts"]` — for cohort size in Magic Moment
- `st.session_state["baseline_problem_id"]` — for context

**Writes:**
- `st.session_state["core_finding"]` — dict: `{finding_text, evidence_chain, scenario_id, dominant_hypothesis}`

---

### Phase Gate

```python
if "probe_results" not in st.session_state:
    st.warning("Complete Phase 2 (Decomposition & Probing) first.", icon="🔒")
    st.stop()
```

---

### Imports to use

```python
from app.components.system_voice import render_system_voice, render_magic_moment, render_core_finding
from app.utils.phase_state import render_phase_sidebar
```

---

### Files to Create/Modify

| File | Change |
|------|--------|
| `app/pages/4_finding.py` | Create new page |

### Files NOT to modify

`src/probing/`, `app/utils/probe_orchestrator.py`, `app/components/probing_tree_viz.py` — read-only from this page.

---

### Acceptance Criteria

- [ ] Phase gate blocks entry if `probe_results` not in session state
- [ ] `render_core_finding()` orange box rendered prominently
- [ ] Evidence chain is numbered and shows verdict badge + evidence snippet per hypothesis
- [ ] `render_magic_moment()` green box rendered after evidence chain
- [ ] Synthesis narrative wrapped in expander
- [ ] JSON export download button present
- [ ] "Proceed to Interventions →" button writes `core_finding` to session state and switches page
- [ ] Import check passes: `python -c "import app.pages.4_finding"`
- [ ] Uses `Config` object — no raw `os.environ.get()` calls
