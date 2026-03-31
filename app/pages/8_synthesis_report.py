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
scenario_id: str = core_finding.get("scenario_id") or st.session_state.get(
    "baseline_scenario_id", ""
)
dominant_hypothesis: str = core_finding.get("dominant_hypothesis_title", "") or core_finding.get("dominant_hypothesis", "")
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
_phases_complete = sum(
    [
        "baseline_cohorts" in st.session_state,
        "probe_results" in st.session_state,
        "core_finding" in st.session_state,
        "intervention_run" in st.session_state,
    ]
)
render_system_voice(
    f"Your investigation is <strong>{_phases_complete}/4 phases complete</strong>. "
    f"Below is the full synthesis — from population baseline through to intervention recommendations. "
    f"Download the brief to share with your team."
)

# ── Section 1: Business Problem ───────────────────────────────────────────────
st.subheader("1. Business Problem")
_problem_labels = {
    "nutrimix_2_6": "Why is repeat purchase low despite high NPS? (Nutrimix 2-6)",
    "nutrimix_7_14": "How do we expand Nutrimix from 2-6 to the 7-14 age group?",
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

# ── Section 3: Core Finding ─────────────────────────────────────────────────
st.subheader("3. Core Finding")
if dominant_hypothesis:
    st.markdown(
        f'<div style="border-left: 4px solid #E67E22; background:#FEF9E7; '
        f'padding:16px 20px; border-radius:4px; margin:8px 0;">'
        f'<strong style="font-size:1.05rem;">{dominant_hypothesis}</strong>'
        f'<br><span style="color:#666; font-size:0.85rem;">Overall confidence: {overall_confidence:.0%}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )

# Evidence chain summary
_confirmed = [
    h
    for h in hypotheses
    if verdicts.get(h.id) and verdicts[h.id].status in ("confirmed", "partially_confirmed")
]
if _confirmed:
    st.markdown("**Supporting evidence:**")
    for _hyp in _confirmed:
        _v = verdicts[_hyp.id]
        _status_icon = "✅" if _v.status == "confirmed" else "⚠️"
        st.markdown(
            f"{_status_icon} **{_hyp.title}** — {_v.confidence:.0%} confidence",
        )
        if _v.evidence_summary:
            st.caption(f"↳ {_v.evidence_summary[:200]}")

# ── Section 4: Interventions ─────────────────────────────────────────────────
st.subheader("4. Intervention Recommendations")
if all_iv_results:
    _sorted_iv = sorted(
        all_iv_results,
        key=lambda x: x["result"].absolute_lift,
        reverse=True,
    )
    _baseline_rate = _sorted_iv[0]["result"].baseline_adoption_rate

    st.caption(
        f"Baseline adoption: **{_baseline_rate:.1%}** · {len(_sorted_iv)} interventions tested",
    )

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
            {
                "title": h.title,
                "confidence": verdicts[h.id].confidence,
                "status": verdicts[h.id].status,
            }
            for h in _confirmed
        ]
        if _confirmed
        else [],
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
    "LITTLEJOYS PERSONA ENGINE — SYNTHESIS REPORT",
    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    f"Scenario: {scenario_id}",
    "=" * 60,
    "",
    "BUSINESS PROBLEM",
    f"{_problem_labels.get(scenario_id, scenario_id)}",
    "",
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
        _text_lines.append(
            f"  [{_v.status.replace('_', ' ').title()}] {_hyp.title} ({_v.confidence:.0%})",
        )

if all_iv_results:
    _sorted_for_text = sorted(
        all_iv_results,
        key=lambda x: x["result"].absolute_lift,
        reverse=True,
    )
    _text_lines += ["", "TOP INTERVENTIONS"]
    for _rank, _row in enumerate(_sorted_for_text[:5]):
        _iv = _row["intervention"]
        _r = _row["result"]
        _sign = "+" if _r.absolute_lift >= 0 else ""
        _text_lines.append(
            f"  {_rank + 1}. {_iv.name}: {_sign}{_r.absolute_lift:.1%} lift → {_r.counterfactual_adoption_rate:.1%} adoption",
        )

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
