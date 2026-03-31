# ruff: noqa: N999
"""Phase 4 — Intervention Simulation Results.

Shows the outcome of running a selected intervention against the population:
- Primary adoption lift (baseline → intervention)
- Micro-perturbation counterfactual table (intervention + additional tweaks)
- Segment impacts
"""

from __future__ import annotations

import streamlit as st

from app.components.system_voice import render_system_voice
from app.utils.phase_state import render_phase_sidebar

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Phase 4 — Intervention Results",
    page_icon="📊",
    layout="wide",
)
render_phase_sidebar()
st.header("Phase 4 — Intervention Results")

# ── Phase gate ────────────────────────────────────────────────────────────────
if "intervention_run" not in st.session_state:
    st.warning(
        "No intervention simulation has been run yet. "
        "Go to **Phase 4 — Interventions**, select an intervention, and click Run.",
        icon="🔒",
    )
    if st.button("← Back to Interventions"):
        st.switch_page("pages/5_intervention.py")
    st.stop()

# ── Unpack session state ───────────────────────────────────────────────────────
_run = st.session_state["intervention_run"]
iv = _run["intervention"]
scenario_id: str = _run["scenario_id"]
sim_months: int = _run.get("sim_months", 12)
primary_result = _run["primary_result"]
micro_results: list[dict] = _run.get("micro_results", [])
baseline_cohorts = _run.get("baseline_cohorts")

# ── System Voice — opening ────────────────────────────────────────────────────
_abs_lift = primary_result.absolute_lift
_rel_lift = primary_result.relative_lift_percent
_direction = "increase" if _abs_lift >= 0 else "decrease"
_lift_sign = "+" if _abs_lift >= 0 else ""

render_system_voice(
    f"You simulated <strong>{iv.name}</strong> — a "
    f"{'general' if iv.scope == 'general' else 'cohort-specific'}, "
    f"{'one-time' if iv.temporality == 'non_temporal' else f'{sim_months}-month sustained'} intervention. "
    f"Adoption rate moved from <strong>{primary_result.baseline_adoption_rate:.1%}</strong> to "
    f"<strong>{primary_result.counterfactual_adoption_rate:.1%}</strong> "
    f"— a <strong>{_lift_sign}{_abs_lift:.1%}</strong> absolute {_direction} "
    f"({_lift_sign}{_rel_lift:.1f}% relative lift). "
    f"Scroll down to see how additional micro-perturbations compound on top of this intervention."
)

# ── Intervention summary card ─────────────────────────────────────────────────
st.subheader("Intervention Summary")

_scope_label = "General (all personas)" if iv.scope == "general" else "Cohort-specific"
_temp_label = (
    f"Sustained — {sim_months} months"
    if iv.temporality == "temporal"
    else "One-time (permanent policy change)"
)
_target_label = (
    iv.target_cohort_id.replace("_", " ").title() if iv.target_cohort_id else "All personas"
)

_card_cols = st.columns([2, 1])
with _card_cols[0]:
    st.markdown(f"**{iv.name}**")
    st.caption(iv.description)
    st.markdown(f"**Expected mechanism:** {iv.expected_mechanism}")
with _card_cols[1]:
    st.markdown(f"**Scope:** {_scope_label}")
    st.markdown(f"**Timing:** {_temp_label}")
    st.markdown(f"**Target:** {_target_label}")
    if iv.parameter_modifications:
        st.markdown("**Parameter changes:**")
        for _pk, _pv in iv.parameter_modifications.items():
            _fk = _pk.replace(".", " → ").replace("_", " ").title()
            if isinstance(_pv, bool):
                _pv_str = "Enabled" if _pv else "Disabled"
            elif isinstance(_pv, float) and _pv <= 1.0:
                _pv_str = f"{_pv:.0%}"
            else:
                _pv_str = str(_pv)
            st.markdown(f"- **{_fk}**: {_pv_str}")

# ── Primary adoption lift ─────────────────────────────────────────────────────
st.divider()
st.subheader("Primary Adoption Lift")
st.caption("Baseline scenario vs. intervention scenario — static funnel comparison across all personas.")

_lift_cols = st.columns(4)
_lift_cols[0].metric(
    "Baseline Adoption",
    f"{primary_result.baseline_adoption_rate:.1%}",
    help="Adoption rate under the unmodified baseline scenario.",
)
_lift_cols[1].metric(
    "Intervention Adoption",
    f"{primary_result.counterfactual_adoption_rate:.1%}",
    delta=f"{_lift_sign}{_abs_lift:.1%}",
    delta_color="normal",
    help="Adoption rate with the intervention applied.",
)
_lift_cols[2].metric(
    "Absolute Lift",
    f"{_lift_sign}{_abs_lift:.1%}",
    help="Percentage point change in adoption rate.",
)
_lift_cols[3].metric(
    "Relative Lift",
    f"{_lift_sign}{_rel_lift:.1f}%",
    help="Lift relative to the baseline adoption rate.",
)

# Pre-simulation population mix
if baseline_cohorts is not None:
    st.markdown("**Population mix at time of simulation** *(Phase 1 baseline cohorts)*")
    _cs = (
        baseline_cohorts.summary
        if hasattr(baseline_cohorts, "summary")
        else baseline_cohorts.get("summary", {})
    )
    _cohort_disp = {
        "never_aware":      ("Never Aware",      "🔇"),
        "aware_not_tried":  ("Aware, Not Tried",  "👁️"),
        "first_time_buyer": ("First-Time Buyer",  "🛒"),
        "current_user":     ("Current User",      "⭐"),
        "lapsed_user":      ("Lapsed User",       "💤"),
    }
    _total_c = sum(_cs.values()) or 1
    _c_cols = st.columns(len(_cohort_disp))
    for _ci, (_cid, (_clabel, _cicon)) in enumerate(_cohort_disp.items()):
        _cnt = _cs.get(_cid, 0)
        with _c_cols[_ci]:
            st.metric(f"{_cicon} {_clabel}", _cnt, f"{round(_cnt / _total_c * 100)}%")

# ── Segment impacts ───────────────────────────────────────────────────────────
if primary_result.most_affected_segments:
    st.divider()
    st.subheader("Most Affected Segments")
    st.caption(
        "Population sub-groups ranked by how much this intervention shifted their adoption. "
        "Positive lift = intervention helped; negative = intervention hurt this segment."
    )
    for _seg in primary_result.most_affected_segments[:6]:
        _seg_label = (
            f"{_seg.segment_attribute.replace('_', ' ').title()}: "
            f"{_seg.segment_value.replace('_', ' ').title()}"
        )
        _seg_lift = _seg.counterfactual_adoption_rate - _seg.baseline_adoption_rate
        _seg_sign = "+" if _seg_lift >= 0 else ""
        _bar_cols = st.columns([3, 1, 1, 1])
        _bar_cols[0].markdown(f"**{_seg_label}**")
        _bar_cols[1].metric("Baseline", f"{_seg.baseline_adoption_rate:.1%}")
        _bar_cols[2].metric("With Intervention", f"{_seg.counterfactual_adoption_rate:.1%}")
        _bar_cols[3].metric("Lift", f"{_seg_sign}{_seg_lift:.1%}")

# ── Counterfactual micro-perturbation analysis ────────────────────────────────
st.divider()
st.subheader("Counterfactual Micro-Perturbation Analysis")
st.caption(
    "Each row shows what happens when you add one more lever ON TOP of the selected intervention. "
    "The baseline here is the intervention scenario — so all lifts are compounding gains."
)

render_system_voice(
    f"Using <strong>{iv.name}</strong> as your new baseline, I tested "
    f"<strong>{len(micro_results)} additional levers</strong> — pricing, distribution, messaging, "
    f"and product tweaks. The table below shows which combinations deliver the greatest "
    f"incremental gain on top of the intervention."
)

if micro_results:
    # Sort by absolute lift descending
    sorted_micro = sorted(
        micro_results,
        key=lambda x: x["result"].absolute_lift,
        reverse=True,
    )

    # Build HTML table
    _HEADER_BG = "#1A5276"
    _HEADER_FG = "#FFFFFF"
    _ROW_BG_TOP = "#EBF5FB"
    _ROW_BG_DEFAULT = "#FFFFFF"
    _ROW_BG_NEGATIVE = "#FEF9E7"

    _micro_rows = ""
    for _mi, _mrow in enumerate(sorted_micro):
        _mr = _mrow["result"]
        _m_lift = _mr.absolute_lift
        _m_rel = _mr.relative_lift_percent
        _m_sign = "+" if _m_lift >= 0 else ""
        _m_color = "#27AE60" if _m_lift > 0.005 else ("#E74C3C" if _m_lift < -0.005 else "#7F8C8D")
        _row_bg = _ROW_BG_TOP if _mi == 0 else (_ROW_BG_NEGATIVE if _m_lift < 0 else _ROW_BG_DEFAULT)
        _top_badge = (
            ' <span style="background:#1A5276;color:#fff;border-radius:4px;padding:1px 5px;'
            'font-size:0.72rem;margin-left:6px;">★ Top</span>'
            if _mi == 0 else ""
        )
        _micro_rows += (
            f'<tr style="background:{_row_bg}; border-bottom:1px solid #E8E8E8;">'
            f'<td style="padding:9px 12px; font-weight:600;">{_mrow["label"]}{_top_badge}</td>'
            f'<td style="padding:9px 12px; text-align:right;">{_mr.baseline_adoption_rate:.1%}</td>'
            f'<td style="padding:9px 12px; text-align:right;">{_mr.counterfactual_adoption_rate:.1%}</td>'
            f'<td style="padding:9px 12px; text-align:right; font-weight:700; color:{_m_color};">'
            f'{_m_sign}{_m_lift:.1%}</td>'
            f'<td style="padding:9px 12px; text-align:right; color:{_m_color};">'
            f'{_m_sign}{_m_rel:.1f}%</td>'
            f'</tr>'
        )

    _micro_table_html = (
        '<div style="overflow-x:auto; margin: 12px 0;">'
        '<table style="border-collapse:collapse; width:100%; font-family:sans-serif; font-size:0.9rem;">'
        f'<thead><tr style="background:{_HEADER_BG}; color:{_HEADER_FG};">'
        '<th style="padding:10px 12px; text-align:left;">Additional Lever</th>'
        '<th style="padding:10px 12px; text-align:right;">Intervention Baseline</th>'
        '<th style="padding:10px 12px; text-align:right;">Combined Adoption</th>'
        '<th style="padding:10px 12px; text-align:right;">Incremental Lift (pp)</th>'
        '<th style="padding:10px 12px; text-align:right;">Relative Lift (%)</th>'
        f'</tr></thead>'
        f'<tbody>{_micro_rows}</tbody>'
        '</table></div>'
    )
    st.markdown(_micro_table_html, unsafe_allow_html=True)

    # Highlight top recommendation
    _top = sorted_micro[0]
    _top_lift = _top["result"].absolute_lift
    if _top_lift > 0:
        render_system_voice(
            f"The highest-impact combination is <strong>{iv.name}</strong> + "
            f"<strong>{_top['label']}</strong>, delivering an additional "
            f"<strong>+{_top_lift:.1%}</strong> adoption lift on top of the intervention. "
            f"Combined adoption rate: <strong>{_top['result'].counterfactual_adoption_rate:.1%}</strong>."
        )
    else:
        render_system_voice(
            f"None of the micro-perturbations produced meaningful incremental lift beyond "
            f"<strong>{iv.name}</strong> alone. The intervention is already capturing the "
            f"primary lever. Consider revisiting the product or audience definition."
        )
else:
    st.info("No micro-perturbation results available.")

# ── Navigation ────────────────────────────────────────────────────────────────
st.divider()
_nav_cols = st.columns([1, 1])
with _nav_cols[0]:
    if st.button("← Run Another Intervention", use_container_width=True):
        st.switch_page("pages/5_intervention.py")
with _nav_cols[1]:
    if st.button("→ Interview Deep-Dive", use_container_width=True):
        st.switch_page("pages/7_interviews.py")
