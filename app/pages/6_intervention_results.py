# ruff: noqa: N999
\"\"\"Phase 4 — Intervention Comparison Dashboard.

Full comparison of ALL interventions run in parallel — ranked by adoption lift.
\"\"\"

from __future__ import annotations

import streamlit as st

from app.components.system_voice import render_system_voice
from app.utils.phase_state import render_phase_sidebar

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Phase 4 — Intervention Results", page_icon="📊", layout="wide")
render_phase_sidebar()
st.header("Phase 4 — Intervention Results")

# ── Phase gate ────────────────────────────────────────────────────────────────
if "intervention_run" not in st.session_state:
    st.warning("No simulation results yet. Go to Phase 4 — Interventions and click Run All Simulations.", icon="🔒")
    if st.button("← Back to Interventions"):
        st.switch_page("pages/5_intervention.py")
    st.stop()

_run = st.session_state["intervention_run"]
all_results: list[dict] = _run.get("all_results", [])
scenario_id: str = _run.get("scenario_id", "")
baseline_cohorts = _run.get("baseline_cohorts")

if not all_results:
    st.warning("No simulation results found. Please re-run the simulations.")
    if st.button("← Back to Interventions"):
        st.switch_page("pages/5_intervention.py")
    st.stop()

# Baseline adoption rate (same for all — from first result)
_baseline_rate = all_results[0]["result"].baseline_adoption_rate if all_results else 0.0

# System Voice
render_system_voice(
    f"I simulated all <strong>{len(all_results)} interventions</strong> against your baseline population. "
    f"Baseline adoption: <strong>{_baseline_rate:.1%}</strong>. "
    f"The table below ranks every intervention by adoption lift — and flags the best trade-off between impact and execution effort."
)

def _infer_complexity(iv) -> str:
    if iv.scope == "cohort_specific" and iv.temporality == "temporal":
        return "High"
    if iv.temporality == "temporal":
        return "Medium"
    return "Low"

def _infer_ttm(iv) -> str:
    if iv.scope == "cohort_specific" and iv.temporality == "temporal":
        return "3–4 months"
    if iv.temporality == "temporal":
        return "4–6 weeks"
    return "1–2 weeks"

def _infer_cost(iv) -> str:
    if iv.scope == "cohort_specific" and iv.temporality == "temporal":
        return "High"
    if iv.temporality == "temporal":
        return "Medium"
    return "Low"

_COMPLEXITY_COLOR = {"Low": "#2ECC71", "Medium": "#F39C12", "High": "#E74C3C"}

# Comparison table (sort by absolute_lift descending)
sorted_results = sorted(all_results, key=lambda x: x["result"].absolute_lift, reverse=True)

_HEADER_BG = "#1A5276"
_HEADER_FG = "#FFFFFF"
_TOP_BG = "#EBF5FB"
_DEFAULT_BG = "#FFFFFF"

_rows_html = ""
for _ri, _row in enumerate(sorted_results):
    _iv = _row["intervention"]
    _r = _row["result"]
    _lift = _r.absolute_lift
    _rel = _r.relative_lift_percent
    _sign = "+" if _lift >= 0 else ""
    _lift_color = "#27AE60" if _lift > 0.01 else ("#E74C3C" if _lift < 0 else "#7F8C8D")
    _row_bg = _TOP_BG if _ri == 0 else _DEFAULT_BG
    _top_badge = (
        ' <span style="background:#1A5276;color:#fff;border-radius:4px;padding:1px 5px;font-size:0.72rem;margin-left:6px;">★ Top</span>'
        if _ri == 0 else ""
    )
    _cx = _infer_complexity(_iv)
    _cx_color = _COMPLEXITY_COLOR.get(_cx, "#555")
    _scope_label = "General" if _iv.scope == "general" else "Cohort"
    _temp_label = "One-time" if _iv.temporality == "non_temporal" else "Sustained"

    _rows_html += (
        f'<tr style="background:{_row_bg}; border-bottom:1px solid #E8E8E8;">'
        f'<td style="padding:9px 12px; font-weight:600; min-width:180px;">{_iv.name}{_top_badge}</td>'
        f'<td style="padding:9px 12px; text-align:center;">{_scope_label} · {_temp_label}</td>'
        f'<td style="padding:9px 12px; text-align:right;">{_r.counterfactual_adoption_rate:.1%}</td>'
        f'<td style="padding:9px 12px; text-align:right; font-weight:700; color:{_lift_color};">{_sign}{_lift:.1%}</td>'
        f'<td style="padding:9px 12px; text-align:right; color:{_lift_color};">{_sign}{_rel:.1f}%</td>'
        f'<td style="padding:9px 12px; text-align:center; color:{_cx_color}; font-weight:600;">{_cx}</td>'
        f'<td style="padding:9px 12px; text-align:center; color:#555;">{_infer_ttm(_iv)}</td>'
        f'<td style="padding:9px 12px; text-align:center; color:#555;">{_infer_cost(_iv)}</td>'
        f'</tr>'
    )

_table_html = (
    '<div style="overflow-x:auto; margin:12px 0;">'
    '<table style="border-collapse:collapse; width:100%; font-family:sans-serif; font-size:0.88rem;">'
    f'<thead><tr style="background:{_HEADER_BG}; color:{_HEADER_FG};">'
    '<th style="padding:10px 12px; text-align:left;">Intervention</th>'
    '<th style="padding:10px 12px; text-align:center;">Type</th>'
    '<th style="padding:10px 12px; text-align:right;">Adoption Rate</th>'
    '<th style="padding:10px 12px; text-align:right;">Lift (pp)</th>'
    '<th style="padding:10px 12px; text-align:right;">Relative Lift</th>'
    '<th style="padding:10px 12px; text-align:center;">Complexity</th>'
    '<th style="padding:10px 12px; text-align:center;">Time to Market</th>'
    '<th style="padding:10px 12px; text-align:center;">Est. Cost</th>'
    '</tr></thead>'
    f'<tbody>{_rows_html}</tbody>'
    '</table></div>'
)

st.subheader("Intervention Comparison")
st.caption(f"Baseline adoption: **{_baseline_rate:.1%}** · All interventions ranked by adoption lift.")
st.markdown(_table_html, unsafe_allow_html=True)

if sorted_results:
    _top = sorted_results[0]
    _top_iv = _top["intervention"]
    _top_r = _top["result"]
    _top_cx = _infer_complexity(_top_iv)
    _top_ttm = _infer_ttm(_top_iv)

    # Find best low-complexity option
    _low_cx = next(
        (x for x in sorted_results if _infer_complexity(x["intervention"]) == "Low"),
        sorted_results[-1],
    )

    _same_as_top = _low_cx["intervention"].id == _top_iv.id
    if _same_as_top:
        render_system_voice(
            f"The highest-lift option is <strong>{_top_iv.name}</strong> "
            f"(+{_top_r.absolute_lift:.1%} adoption lift) and it also has <strong>Low</strong> complexity "
            f"with a <strong>{_top_ttm}</strong> time to market — an ideal starting point. "
            f"No trade-off needed: this intervention delivers both impact and speed."
        )
    else:
        render_system_voice(
            f"The highest-lift option is <strong>{_top_iv.name}</strong> (+{_top_r.absolute_lift:.1%} adoption), "
            f"but it carries <strong>{_top_cx}</strong> complexity and a <strong>{_top_ttm}</strong> time to market. "
            f"For a faster path to impact, start with <strong>{_low_cx['intervention'].name}</strong> "
            f"(+{_low_cx['result'].absolute_lift:.1%} lift, Low complexity) to validate assumptions "
            f"before committing to the larger programme."
        )

st.divider()
_nav = st.columns([1, 1])
with _nav[0]:
    if st.button("← Re-run Simulations", use_container_width=True):
        st.switch_page("pages/5_intervention.py")
with _nav[1]:
    if st.button("→ Interview Deep-Dive", use_container_width=True):
        st.switch_page("pages/7_interviews.py")
