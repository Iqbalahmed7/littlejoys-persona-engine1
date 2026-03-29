# ruff: noqa: N999
"""Probing Tree — hypothesis-driven investigation UI (PRD-014b)."""

from __future__ import annotations

import streamlit as st

from app.components.probing_tree_helpers import (
    load_population_for_probing,
    probe_icon,
    probe_label,
    render_attribute_detail,
    render_interview_detail,
    render_simulation_detail,
    verdict_status_display,
)
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
            "Indicator attributes: "
            + ", ".join(display_name(a) for a in hyp.indicator_attributes)
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
    st.markdown(f"**Latest run:** {problem_r.title}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Confidence", f"{synthesis.overall_confidence:.0%}")
    c2.metric("Hypotheses Tested", synthesis.hypotheses_tested)
    c3.metric("Confirmed", synthesis.hypotheses_confirmed)
    c4.metric("Estimated Cost", f"${synthesis.total_cost_estimate:.2f}")

    if synthesis.dominant_hypothesis:
        dominant_title = next(
            (h.title for h in hypotheses_r if h.id == synthesis.dominant_hypothesis),
            synthesis.dominant_hypothesis,
        )
        st.info(
            f"**Dominant finding:** {dominant_title} "
            f"({synthesis.overall_confidence:.0%} confidence)"
        )

    st.subheader("Hypothesis Results")

    for hyp_id, _confidence in synthesis.confidence_ranking:
        verdict = verdicts.get(hyp_id)
        hyp = next((h for h in hypotheses_r if h.id == hyp_id), None)
        if not verdict or not hyp:
            continue

        col_title, col_bar = st.columns([0.55, 0.45])
        with col_title:
            status_icon = {
                "confirmed": "✅",
                "partially_confirmed": "⚠️",
                "rejected": "❌",
                "inconclusive": "❔",
            }.get(verdict.status, "")
            st.markdown(
                f"**{status_icon} {hyp.title}** — {verdict_status_display(verdict.status)}"
            )
        with col_bar:
            st.progress(min(verdict.confidence, 1.0))
            st.caption(
                f"Confidence: {verdict.confidence:.0%} · "
                f"Consistency: {verdict.consistency_score:.0%}"
            )

        hyp_probes = [p for p in probes_r if p.hypothesis_id == hyp_id and p.result]
        with st.expander(f"View {len(hyp_probes)} probe results", expanded=False):
            for probe in sorted(hyp_probes, key=lambda p: p.order):
                result = probe.result
                if result is None:
                    continue
                icon = probe_icon(probe.probe_type)

                sample_info = ""
                if result.population_size and result.population_size > result.sample_size:
                    sample_info = f" · {result.sample_size}/{result.population_size} sampled"
                if result.clustering_method:
                    sample_info += f" · {result.clustering_method} clustering"

                st.markdown(f"{icon} **{probe_label(probe)}**")
                st.caption(f"Confidence: {result.confidence:.0%}{sample_info}")
                st.write(result.evidence_summary)

                if probe.probe_type == ProbeType.INTERVIEW and result.response_clusters:
                    render_interview_detail(result)
                elif probe.probe_type == ProbeType.SIMULATION and result.lift is not None:
                    render_simulation_detail(result)
                elif probe.probe_type == ProbeType.ATTRIBUTE and result.attribute_splits:
                    render_attribute_detail(result)

                st.markdown("---")

        st.caption(verdict.evidence_summary)

    disabled = [h for h in hypotheses_r if not h.enabled]
    if disabled:
        st.subheader("Skipped Hypotheses")
        for hyp in disabled:
            st.markdown(f"~~{hyp.title}~~")
        if synthesis.confidence_impact_of_disabled > 0:
            st.warning(
                f"Skipping {len(disabled)} hypothesis(es) may reduce confidence "
                f"by up to {synthesis.confidence_impact_of_disabled:.0%}."
            )

    st.subheader("Synthesis")
    st.write(synthesis.synthesis_narrative)

    if synthesis.recommended_actions:
        st.subheader("Recommended Actions")
        for i, action in enumerate(synthesis.recommended_actions, 1):
            st.markdown(f"{i}. {action}")

    st.divider()
    st.caption(
        "🎤 = Interview probe (sampled, 30 personas) · "
        "🔬 = Simulation probe (full population, no LLM) · "
        "📊 = Attribute analysis (full population, no LLM)"
    )
