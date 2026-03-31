# ruff: noqa: N999
"""Cross-Scenario Comparison.

Compare findings, cohort splits, and top interventions across two business problems.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from app.utils.phase_state import render_phase_sidebar
from src.analysis.cohort_classifier import classify_population
from src.constants import SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.simulation.static import run_static_simulation

st.set_page_config(page_title="Compare Scenarios", page_icon="⚖️", layout="wide")
render_phase_sidebar()
st.header("Cross-Scenario Comparison")
st.caption("Compare findings across two business problems side by side.")


def _problem_label(scenario_id: str) -> str:
    mapping = {
        "nutrimix_2_6": "Nutrimix 2-6",
        "nutrimix_7_14": "Nutrimix 7-14",
        "magnesium_gummies": "Magnesium Gummies",
        "protein_mix": "Protein Mix",
    }
    return f"{mapping.get(scenario_id, scenario_id)} ({scenario_id})"


# ── Guard: need population ─────────────────────────────────────────────────
if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()

pop = st.session_state.population


col_a, col_b = st.columns(2)
with col_a:
    scenario_a = st.selectbox(
        "Scenario A",
        options=SCENARIO_IDS,
        format_func=_problem_label,
        key="compare_scenario_a",
    )
with col_b:
    scenario_b = st.selectbox(
        "Scenario B",
        options=SCENARIO_IDS,
        format_func=_problem_label,
        key="compare_scenario_b",
    )

if scenario_a == scenario_b:
    st.warning("Select two different scenarios to compare.")
    st.stop()


def _ensure_static_results_for(scenario_id: str) -> None:
    if "scenario_results" not in st.session_state:
        st.session_state.scenario_results = {}
    if scenario_id not in st.session_state.scenario_results:
        with st.spinner("Running baseline simulation for selected scenario…"):
            st.session_state.scenario_results[scenario_id] = run_static_simulation(
                pop,
                get_scenario(scenario_id),
            )


def _ensure_classified_cohorts(scenario_id: str) -> Any:
    cache_key = f"compare_cohorts_{scenario_id}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    scenario_obj = get_scenario(scenario_id)
    _ensure_static_results_for(scenario_id)

    with st.spinner(f"Classifying cohorts for {scenario_obj.name}…"):
        cohorts = classify_population(pop, scenario_obj, seed=42)
    st.session_state[cache_key] = cohorts
    return cohorts


cohorts_a = _ensure_classified_cohorts(scenario_a)
cohorts_b = _ensure_classified_cohorts(scenario_b)


def _cohort_tiles(cohorts: Any) -> None:
    cohort_display = {
        "never_aware": ("Never Aware", "🔇", "Never engaged with the product"),
        "aware_not_tried": (
            "Aware, Not Tried",
            "👁️",
            "Became aware but never purchased",
        ),
        "first_time_buyer": (
            "First-Time Buyer",
            "🛒",
            "Bought once, did not repeat",
        ),
        "current_user": ("Current User", "⭐", "Active repeat buyer"),
        "lapsed_user": ("Lapsed User", "💤", "Was active, has stopped"),
    }

    total = sum(cohorts.summary.values()) or 1
    cols = st.columns(len(cohort_display))
    for i, (cid, (label, icon, desc)) in enumerate(cohort_display.items()):
        count = cohorts.summary.get(cid, 0)
        pct = round(count / total * 100)
        with cols[i]:
            st.metric(f"{icon} {label}", f"{count}", f"{pct}% of population")
            st.caption(desc)


def _funnel_fig(cohorts: Any) -> go.Figure:
    _total = sum(cohorts.summary.values()) or 1
    _aware = _total - cohorts.summary.get("never_aware", 0)
    _tried = (
        cohorts.summary.get("first_time_buyer", 0)
        + cohorts.summary.get("current_user", 0)
        + cohorts.summary.get("lapsed_user", 0)
    )
    _repeated = cohorts.summary.get("current_user", 0) + cohorts.summary.get("lapsed_user", 0)
    _active = cohorts.summary.get("current_user", 0)

    fig = go.Figure(
        go.Funnel(
            y=["Became Aware", "Tried Product", "Repeated Purchase", "Still Active"],
            x=[_aware, _tried, _repeated, _active],
            textinfo="value+percent initial",
            marker_color=["#3498DB", "#2ECC71", "#27AE60", "#1A8A50"],
        )
    )
    fig.update_layout(
        title="Purchase Journey Funnel",
        margin=dict(l=10, r=10, t=40, b=10),
        height=300,
    )
    return fig


scenario_obj_a = get_scenario(scenario_a)
scenario_obj_b = get_scenario(scenario_b)

st.markdown("---")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader(f"A: {scenario_obj_a.name}")
    st.caption(f"Cohort split for {scenario_a}")
    _cohort_tiles(cohorts_a)

with col_right:
    st.subheader(f"B: {scenario_obj_b.name}")
    st.caption(f"Cohort split for {scenario_b}")
    _cohort_tiles(cohorts_b)

st.markdown("---")

col_funnel_a, col_funnel_b = st.columns(2)
with col_funnel_a:
    st.subheader("Adoption Funnel")
    st.plotly_chart(_funnel_fig(cohorts_a), use_container_width=True)

with col_funnel_b:
    st.subheader("Adoption Funnel")
    st.plotly_chart(_funnel_fig(cohorts_b), use_container_width=True)

st.markdown("---")


def _render_core_finding_block(scenario_id: str) -> None:
    key = f"core_finding_{scenario_id}"
    core_finding = st.session_state.get(key)
    # Fall back to the main pipeline's core_finding if it belongs to this scenario
    if not core_finding:
        _cf = st.session_state.get("core_finding", {})
        if _cf.get("scenario_id") == scenario_id:
            core_finding = _cf
    if not core_finding:
        st.info("Run Phase 3 for this scenario to see its core finding.")
        return

    dominant = core_finding.get("dominant_hypothesis_title") or core_finding.get(
        "dominant_hypothesis"
    )
    confidence = float(core_finding.get("overall_confidence", 0.0))
    if dominant:
        st.markdown(
            f'<div style="border-left: 4px solid #E67E22; background:#FEF9E7; padding:16px 20px; border-radius:4px; margin:8px 0;">'
            f'<strong style="font-size:1.05rem;">{dominant}</strong>'
            f'<br><span style="color:#666; font-size:0.85rem;">Overall confidence: {confidence:.0%}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )


def _infer_complexity(iv: Any) -> str:
    if iv.scope == "cohort_specific" and iv.temporality == "temporal":
        return "High"
    if iv.temporality == "temporal":
        return "Medium"
    return "Low"


def _top_intervention_block(scenario_id: str) -> None:
    key = f"intervention_run_{scenario_id}"
    run = st.session_state.get(key)
    # Fall back to main pipeline's intervention_run if it belongs to this scenario
    if not run:
        _ir = st.session_state.get("intervention_run", {})
        if _ir.get("scenario_id") == scenario_a or _ir.get("scenario_id") == scenario_b:
            if _ir.get("scenario_id") == scenario_id:
                run = _ir
    if not run:
        st.info("Run Phase 4 for this scenario to see its top intervention.")
        return

    all_results = run.get("all_results") or []
    if not all_results:
        st.info("Run Phase 4 for this scenario to see its top intervention.")
        return

    sorted_results = sorted(all_results, key=lambda x: x["result"].absolute_lift, reverse=True)
    top = sorted_results[0]
    iv = top["intervention"]
    r = top["result"]
    cx = _infer_complexity(iv)
    sign = "+" if r.absolute_lift >= 0 else ""

    st.success(
        f"Top intervention: {iv.name} ({sign}{r.absolute_lift:.1%} adoption lift) · Complexity: {cx}",
    )


col_core_a, col_core_b = st.columns(2)
with col_core_a:
    st.subheader("Core Finding")
    _render_core_finding_block(scenario_a)

with col_core_b:
    st.subheader("Core Finding")
    _render_core_finding_block(scenario_b)

col_iv_a, col_iv_b = st.columns(2)
with col_iv_a:
    st.subheader("Top Intervention per Scenario")
    _top_intervention_block(scenario_a)

with col_iv_b:
    st.subheader("Top Intervention per Scenario")
    _top_intervention_block(scenario_b)
