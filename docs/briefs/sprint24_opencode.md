# Sprint 24 Brief — OpenCode
## S4-05: Home Page Polish + New Page 8 (Synthesis Report)

> **Engineer**: OpenCode (GPT 5.4 Nano → escalate to GPT 5.4 Pro if report assembly is complex)
> **Sprint**: 24
> **Ticket**: S4-05
> **Estimated effort**: Low-Medium (two separate tasks)
> **Reference**: LittleJoys User Flow Document v2.0, Sections 6.3, 8.1, 8.2, 10.1

---

### Context

Two tasks for this sprint:

**Task A — Home page polish**: `streamlit_app.py` needs three updates aligned to the v2.0 spec:
- Metric label: "Scenarios Available" → "Business Problems Available"
- Sidebar captions: Update to 5-phase v2.0 language
- Demo mode: Fix "With Narratives: 0" display in demo mode

**Task B — New Page 8 (Synthesis Report)**: Create `app/pages/8_synthesis_report.py`. This is the terminal page of the pipeline — it assembles everything from the 5-phase investigation into a single downloadable brief. The user arrives here after Phase 4 is complete.

---

### Task A1: Fix Home Page Metrics

File: `app/streamlit_app.py`

Find the metric row (currently):
```python
c1.metric("Total Personas", len(pop.personas))
c2.metric("With Narratives", sum(1 for p in pop.personas if p.narrative))
c3.metric("Scenarios Available", len(SCENARIO_IDS))
```

Replace with:
```python
c1.metric("Total Personas", len(pop.personas))
_with_narratives = sum(1 for p in pop.personas if p.narrative)
# Only show "With Narratives" if more than 0, otherwise show a neutral label
if _with_narratives > 0:
    c2.metric("With Narratives", _with_narratives)
else:
    c2.metric("Persona Depth", "Deep Profiles", help="All personas have full demographic and behavioral profiles.")
c3.metric("Business Problems", 4, help="4 pre-configured business problems available to investigate.")
```

---

### Task A2: Update Sidebar Captions

File: `app/streamlit_app.py`

Find any `st.sidebar.caption(...)` calls. The current file may already have updated captions (check before making changes). The required captions are:

```python
st.sidebar.caption("0️⃣ Personas — Explore your synthetic population")
st.sidebar.caption("1️⃣ Problem — State a business problem & run baseline simulation")
st.sidebar.caption("2️⃣ Decompose — Investigate hypotheses with the probing tree")
st.sidebar.caption("3️⃣ Finding — Core insight with evidence chain")
st.sidebar.caption("4️⃣ Interventions — Test solutions & compare results")
st.sidebar.caption("5️⃣ Interviews — Deep-dive persona conversations")
st.sidebar.caption("6️⃣ Report — Synthesis brief & export")
```

**Important**: The sidebar phase nav is also rendered by `app/utils/phase_state.py`'s `render_phase_sidebar()`. Check if the captions are already there via `render_phase_sidebar()`. If they are, do NOT add duplicate captions in `streamlit_app.py`. If captions are currently hardcoded in `streamlit_app.py`, replace them with the above. If no captions exist in `streamlit_app.py` (because `render_phase_sidebar()` handles it), skip this task entirely.

---

### Task A3: Fix Getting Started Quick-Links

File: `app/streamlit_app.py`

Find the `col1, col2, col3 = st.columns(3)` quick-link section. Replace with:

```python
col1, col2, col3 = st.columns(3)
with col1:
    st.page_link("pages/1_personas.py", label="🔍 Explore Population", icon="👥")
with col2:
    st.page_link("pages/2_problem.py", label="💡 State a Problem", icon="🎯")
with col3:
    st.page_link("pages/4_finding.py", label="📊 View Core Finding", icon="📋")
```

Note: The third button links to `4_finding.py` (Core Finding) rather than `3_decompose.py` — this gives investors jumping into the demo a direct path to the most impressive output.

---

### Task B: Create Page 8 — Synthesis Report

File: `app/pages/8_synthesis_report.py` (new file — create from scratch)

This is the terminal page. It assembles content from all completed phases into a single dashboard and downloadable report.

**Full file content:**

```python
# ruff: noqa: N999
"""Phase 5 — Synthesis Report.

Terminal page of the 5-phase pipeline. Assembles findings from all phases
into a single downloadable brief for stakeholder sharing.
"""

from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from app.components.system_voice import render_system_voice
from app.utils.phase_state import render_phase_sidebar

st.set_page_config(page_title="Synthesis Report", page_icon="📋", layout="wide")
render_phase_sidebar()
st.header("Synthesis Report")
st.caption("Everything the system found, assembled into a single shareable brief.")

# ── Phase gate ────────────────────────────────────────────────────────────────
if "core_finding" not in st.session_state:
    st.warning(
        "Complete at least Phase 3 (Core Finding) before generating a report.",
        icon="🔒",
    )
    st.stop()

# ── Unpack available session state ────────────────────────────────────────────
core_finding: dict = st.session_state["core_finding"]
scenario_id: str = core_finding.get("scenario_id") or st.session_state.get("baseline_scenario_id", "")
dominant_hypothesis: str = core_finding.get("dominant_hypothesis", "")
overall_confidence: float = float(core_finding.get("overall_confidence", 0.0))

probe_results = st.session_state.get("probe_results", {})
synthesis = probe_results.get("synthesis")
verdicts = probe_results.get("verdicts", {})
hypotheses = probe_results.get("hypotheses", [])
probes = probe_results.get("probes", [])

intervention_run = st.session_state.get("intervention_run", {})
all_iv_results: list[dict] = intervention_run.get("all_results", [])

baseline_cohorts = st.session_state.get("baseline_cohorts")
cohort_summary: dict = {}
if baseline_cohorts is not None:
    cohort_summary = (
        baseline_cohorts.summary
        if hasattr(baseline_cohorts, "summary")
        else baseline_cohorts.get("summary", {})
    )

# ── System Voice ──────────────────────────────────────────────────────────────
_phases_complete = sum([
    "baseline_cohorts" in st.session_state,
    "probe_results" in st.session_state,
    "core_finding" in st.session_state,
    "intervention_run" in st.session_state,
])
render_system_voice(
    f"Your investigation is <strong>{_phases_complete}/4 phases complete</strong>. "
    f"Below is the full synthesis — from population baseline through to intervention recommendations. "
    f"Download the brief to share with your team."
)

# ── Section 1: Business Problem ───────────────────────────────────────────────
st.subheader("1. Business Problem")
_problem_labels = {
    "nutrimix_2_6": "Why is repeat purchase low despite high NPS? (Nutrimix 2–6)",
    "nutrimix_7_14": "How do we expand Nutrimix from 2–6 to the 7–14 age group?",
    "magnesium_gummies": "How do we grow sales of a niche supplement? (Magnesium Gummies)",
    "protein_mix": "The product requires cooking — how do we overcome the effort barrier? (Protein Mix)",
}
st.markdown(f"**{_problem_labels.get(scenario_id, scenario_id)}**")

# ── Section 2: Population & Baseline ─────────────────────────────────────────
st.subheader("2. Population Baseline")
if cohort_summary:
    _total = sum(cohort_summary.values()) or 1
    _cohort_labels = {
        "never_aware": "Never Aware 🔇",
        "aware_not_tried": "Aware, Not Tried 👁️",
        "first_time_buyer": "First-Time Buyer 🛒",
        "current_user": "Current User ⭐",
        "lapsed_user": "Lapsed User 💤",
    }
    _cols = st.columns(5)
    for _i, (_cid, _clabel) in enumerate(_cohort_labels.items()):
        _cnt = cohort_summary.get(_cid, 0)
        with _cols[_i]:
            st.metric(_clabel, _cnt, f"{round(_cnt / _total * 100)}%")
else:
    st.info("Baseline simulation data not available.")

# ── Section 3: Core Finding ───────────────────────────────────────────────────
st.subheader("3. Core Finding")
if dominant_hypothesis:
    st.markdown(
        f'<div style="border-left: 4px solid #E67E22; background:#FEF9E7; '
        f'padding:16px 20px; border-radius:4px; margin:8px 0;">'
        f'<strong style="font-size:1.05rem;">{dominant_hypothesis}</strong>'
        f'<br><span style="color:#666; font-size:0.85rem;">Overall confidence: {overall_confidence:.0%}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# Evidence chain summary
_confirmed = [h for h in hypotheses if verdicts.get(h.id) and verdicts[h.id].status in ("confirmed", "partially_confirmed")]
if _confirmed:
    st.markdown("**Supporting evidence:**")
    for _hyp in _confirmed:
        _v = verdicts[_hyp.id]
        _status_icon = "✅" if _v.status == "confirmed" else "⚠️"
        st.markdown(f"{_status_icon} **{_hyp.title}** — {_v.confidence:.0%} confidence")
        if _v.evidence_summary:
            st.caption(f"↳ {_v.evidence_summary[:200]}")

# ── Section 4: Interventions ──────────────────────────────────────────────────
if all_iv_results:
    st.subheader("4. Intervention Recommendations")
    _sorted_iv = sorted(all_iv_results, key=lambda x: x["result"].absolute_lift, reverse=True)
    _baseline_rate = _sorted_iv[0]["result"].baseline_adoption_rate

    st.caption(f"Baseline adoption: **{_baseline_rate:.1%}** · {len(_sorted_iv)} interventions tested")

    for _rank, _row in enumerate(_sorted_iv[:5]):  # Show top 5
        _iv = _row["intervention"]
        _r = _row["result"]
        _lift = _r.absolute_lift
        _sign = "+" if _lift >= 0 else ""
        _lift_color = "green" if _lift > 0.01 else "red"
        st.markdown(
            f"**{_rank + 1}. {_iv.name}** — "
            f"<span style='color:{_lift_color};'>{_sign}{_lift:.1%} lift</span> → "
            f"{_r.counterfactual_adoption_rate:.1%} adoption",
            unsafe_allow_html=True,
        )
else:
    st.info("Run Phase 4 — Interventions to add simulation results to this report.", icon="💡")

# ── Export ────────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Export")

# Assemble JSON export
_export = {
    "generated_at": datetime.now().isoformat(),
    "scenario_id": scenario_id,
    "business_problem": _problem_labels.get(scenario_id, scenario_id),
    "population_baseline": cohort_summary,
    "core_finding": {
        "statement": dominant_hypothesis,
        "confidence": overall_confidence,
        "confirmed_hypotheses": [
            {"title": h.title, "confidence": verdicts[h.id].confidence, "status": verdicts[h.id].status}
            for h in _confirmed
        ] if _confirmed else [],
    },
    "intervention_results": [
        {
            "name": row["intervention"].name,
            "adoption_rate": row["result"].counterfactual_adoption_rate,
            "lift": row["result"].absolute_lift,
            "relative_lift_pct": row["result"].relative_lift_percent,
        }
        for row in (all_iv_results or [])
    ],
}

# Assemble text brief
_text_lines = [
    f"LITTLEJOYS PERSONA ENGINE — SYNTHESIS REPORT",
    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    f"Scenario: {scenario_id}",
    f"=" * 60,
    f"",
    f"BUSINESS PROBLEM",
    f"{_problem_labels.get(scenario_id, scenario_id)}",
    f"",
    f"POPULATION BASELINE ({sum(cohort_summary.values())} personas)",
]
for _cid, _cnt in cohort_summary.items():
    _pct = round(_cnt / max(sum(cohort_summary.values()), 1) * 100)
    _text_lines.append(f"  {_cid.replace('_', ' ').title()}: {_cnt} ({_pct}%)")

_text_lines += ["", "CORE FINDING", dominant_hypothesis or "Not yet synthesized.", ""]
if _confirmed:
    _text_lines.append("EVIDENCE")
    for _hyp in _confirmed:
        _v = verdicts[_hyp.id]
        _text_lines.append(f"  [{_v.status.replace('_', ' ').title()}] {_hyp.title} ({_v.confidence:.0%})")

if all_iv_results:
    _sorted_for_text = sorted(all_iv_results, key=lambda x: x["result"].absolute_lift, reverse=True)
    _text_lines += ["", "TOP INTERVENTIONS"]
    for _rank, _row in enumerate(_sorted_for_text[:5]):
        _iv = _row["intervention"]
        _r = _row["result"]
        _sign = "+" if _r.absolute_lift >= 0 else ""
        _text_lines.append(f"  {_rank + 1}. {_iv.name}: {_sign}{_r.absolute_lift:.1%} lift → {_r.counterfactual_adoption_rate:.1%} adoption")

_text_lines += ["", "=" * 60, "LittleJoys Persona Simulation Engine", "Simulatte Research Pvt Ltd"]

_dl_cols = st.columns(2)
with _dl_cols[0]:
    st.download_button(
        label="⬇️ Download Brief (.txt)",
        data="\n".join(_text_lines),
        file_name=f"{scenario_id}_synthesis_report.txt",
        mime="text/plain",
    )
with _dl_cols[1]:
    st.download_button(
        label="⬇️ Download Data (.json)",
        data=json.dumps(_export, indent=2, default=str),
        file_name=f"{scenario_id}_synthesis_report.json",
        mime="application/json",
    )

# ── Navigation ────────────────────────────────────────────────────────────────
st.divider()
if st.button("← Back to Interventions", use_container_width=False):
    st.switch_page("pages/5_intervention.py")
```

---

### Acceptance Criteria

**Task A:**
- [ ] "Scenarios Available" metric is gone; replaced with "Business Problems: 4"
- [ ] "With Narratives: 0" no longer shows in demo mode — replaced with "Persona Depth: Deep Profiles"
- [ ] Quick-link buttons point to `1_personas.py`, `2_problem.py`, `4_finding.py`
- [ ] No duplicate sidebar captions (check if `render_phase_sidebar()` already handles them)

**Task B:**
- [ ] `8_synthesis_report.py` loads without error
- [ ] Page gates gracefully when `core_finding` not in session state
- [ ] All 4 sections render: Problem, Population, Core Finding, Interventions
- [ ] Both download buttons work (txt and json)
- [ ] Intervention section shows "Run Phase 4" info card when no results exist
- [ ] Import check: `python -c "import app.pages._8_synthesis_report"` or equivalent passes

---

### Files to Modify / Create

| File | Change |
|------|--------|
| `app/streamlit_app.py` | Fix metric labels, quick-links |
| `app/pages/8_synthesis_report.py` | Create new terminal page |

### Files NOT to Modify

Any `src/` files, any existing pages other than `streamlit_app.py`.
