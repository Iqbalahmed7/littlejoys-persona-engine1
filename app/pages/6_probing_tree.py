# ruff: noqa: N999
"""Probing Tree — hypothesis-driven investigation UI (PRD-014b)."""

from __future__ import annotations

import streamlit as st

from app.components.probing_tree_helpers import (
    load_population_for_probing,
    probe_icon,
    probe_label,
)
from app.components.probing_tree_viz import render_probing_tree_visualization
from src.config import Config
from src.probing import (
    Hypothesis,
    Probe,
    ProbeType,
    ProbingTreeEngine,
    ProblemStatement,
    TreeSynthesis,
    get_problem_tree,
    list_problem_ids,
)
from src.probing.sampling import PROBE_SAMPLE_SIZE
from src.utils.display import display_name
from src.utils.llm import LLMClient

st.title("Probing Tree")
st.caption(
    "Decompose a business question into testable hypotheses. "
    "Each hypothesis is investigated with interview, simulation, and statistical probes "
    "across your persona population."
)

_PROBING_RESULT_KEYS = (
    "probing_synthesis",
    "probing_hypotheses",
    "probing_probes",
    "probing_verdicts",
    "probing_problem",
)

problem_ids = list_problem_ids()
problem_labels: dict[str, str] = {}
for pid in problem_ids:
    prob, _, _ = get_problem_tree(pid)
    problem_labels[pid] = prob.title

selected_id = st.selectbox(
    "Business problem",
    problem_ids,
    format_func=lambda pid: problem_labels.get(pid, pid),
    help="Each problem decomposes into 3-5 testable hypotheses with structured probes.",
)

if st.session_state.get("probing_ui_problem_id") != selected_id:
    for k in _PROBING_RESULT_KEYS:
        st.session_state.pop(k, None)
    st.session_state["probing_ui_problem_id"] = selected_id

problem, hypotheses, probes = get_problem_tree(selected_id)

st.markdown(f"**Context:** {problem.context}")
st.markdown(f"**Success metric:** {display_name(problem.success_metric)}")
st.divider()

st.subheader("Investigation Plan")

for hyp in sorted(hypotheses, key=lambda h: h.order):
    ck = f"hyp_en_{selected_id}_{hyp.id}"
    col_check, col_title = st.columns([0.05, 0.95])
    with col_check:
        enabled = st.checkbox(
            "Enable",
            value=hyp.enabled,
            key=ck,
            label_visibility="collapsed",
        )
    with col_title:
        if enabled:
            st.markdown(f"**{hyp.title}**")
        else:
            st.markdown(f"~~{hyp.title}~~ *(skipped)*")

    if enabled:
        hyp_probes = [p for p in probes if p.hypothesis_id == hyp.id]
        for probe in sorted(hyp_probes, key=lambda p: p.order):
            icon = probe_icon(probe.probe_type)
            label = probe_label(probe)
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} {label}")

    with st.expander("Why this hypothesis?", expanded=False, key=f"why_hyp_{selected_id}_{hyp.id}"):
        st.write(hyp.rationale)
        st.caption(
            "Indicator attributes: " + ", ".join(display_name(a) for a in hyp.indicator_attributes)
        )

for hyp in hypotheses:
    hyp.enabled = bool(st.session_state.get(f"hyp_en_{selected_id}_{hyp.id}", hyp.enabled))

enabled_hyps = [h for h in hypotheses if h.enabled]
enabled_probes = [p for p in probes if any(h.id == p.hypothesis_id for h in enabled_hyps)]
interview_count = sum(1 for p in enabled_probes if p.probe_type == ProbeType.INTERVIEW)

st.divider()
col_run, col_info = st.columns([0.3, 0.7])
with col_info:
    st.caption(
        f"{len(enabled_hyps)} hypotheses enabled · "
        f"{len(enabled_probes)} probes · "
        f"{interview_count} interviews ({PROBE_SAMPLE_SIZE} personas each)"
    )

with col_run:
    run_clicked = st.button(
        "Run Investigation",
        type="primary",
        disabled=len(enabled_hyps) == 0,
        use_container_width=True,
        help="Runs all enabled probes against your persona population. Mock mode: instant. "
        "Real LLM: roughly 30 seconds or more depending on probe count.",
    )

if run_clicked:
    pop = load_population_for_probing()
    if pop is None:
        st.error("No population found. Generate one from the Home page first.")
        st.stop()

    run_problem, run_hypotheses, run_probes = get_problem_tree(selected_id)
    for h in run_hypotheses:
        h.enabled = bool(st.session_state.get(f"hyp_en_{selected_id}_{h.id}", h.enabled))

    config = Config()
    llm_client = LLMClient(config)
    engine = ProbingTreeEngine(
        population=pop,
        scenario_id=run_problem.scenario_id,
        llm_client=llm_client,
    )

    with st.spinner("Running probing tree…"):
        progress = st.progress(0.0)
        synthesis = engine.execute_tree(run_problem, run_hypotheses, run_probes)
        progress.progress(1.0)

    st.session_state["probing_synthesis"] = synthesis
    st.session_state["probing_hypotheses"] = run_hypotheses
    st.session_state["probing_probes"] = run_probes
    st.session_state["probing_verdicts"] = engine.verdicts
    st.session_state["probing_problem"] = run_problem
    st.rerun()

if "probing_synthesis" in st.session_state:
    synthesis: TreeSynthesis = st.session_state["probing_synthesis"]
    verdicts: dict = st.session_state["probing_verdicts"]
    hypotheses_r: list[Hypothesis] = st.session_state["probing_hypotheses"]
    probes_r: list[Probe] = st.session_state["probing_probes"]
    problem_r: ProblemStatement = st.session_state["probing_problem"]

    st.divider()
    render_probing_tree_visualization(
        problem=problem_r,
        synthesis=synthesis,
        hypotheses=hypotheses_r,
        probes=probes_r,
        verdicts=verdicts,
    )
