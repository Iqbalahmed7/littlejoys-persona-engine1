"""McKinsey-style visualization for the Probing Tree page."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app.components.probing_tree_helpers import (
    probe_icon,
    probe_label,
    render_attribute_detail,
    render_interview_detail,
    render_simulation_detail,
    verdict_status_display,
)
from src.probing import (
    Hypothesis,
    HypothesisVerdict,
    Probe,
    ProbeResult,
    ProbeType,
    ProblemStatement,
    TreeSynthesis,
)

VERDICT_STYLES: dict[str, dict[str, str]] = {
    "confirmed": {
        "icon": "✅",
        "color": "#2ECC71",
        "label": "Confirmed",
    },
    "partially_confirmed": {
        "icon": "⚠️",
        "color": "#F39C12",
        "label": "Partially Confirmed",
    },
    "rejected": {
        "icon": "❌",
        "color": "#E74C3C",
        "label": "Rejected",
    },
    "inconclusive": {
        "icon": "❔",
        "color": "#95A5A6",
        "label": "Inconclusive",
    },
}

PROBE_TYPE_CONFIG: dict[str, dict[str, str]] = {
    "interview": {"icon": "🎤", "label": "Interview", "color": "#8E44AD"},
    "simulation": {"icon": "🔬", "label": "Simulation", "color": "#2980B9"},
    "attribute": {"icon": "📊", "label": "Attribute", "color": "#27AE60"},
}


def _status_for_confidence(overall_confidence: float) -> str:
    """Convert overall confidence into a status caption."""

    if overall_confidence >= 0.70:
        return "Strong evidence gathered"
    if overall_confidence >= 0.50:
        return "Partial evidence — more investigation recommended"
    return "Inconclusive — consider additional hypotheses"


def _clamp_confidence(conf: float) -> float:
    return float(conf)


def _traffic_light_for_confidence(conf: float) -> str:
    """Return a traffic-light emoji based on confidence."""

    c = _clamp_confidence(conf)
    if c >= 0.70:
        return "🟢"
    if c >= 0.50:
        return "🟡"
    if c >= 0.30:
        return "🟠"
    return "🔴"


def _truncate(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _hypothesis_title(hypotheses: list[Hypothesis], hypothesis_id: str) -> str | None:
    return next((h.title for h in hypotheses if h.id == hypothesis_id), None)


def render_tree_root(
    problem: ProblemStatement,
    synthesis: TreeSynthesis,
    hypotheses: list[Hypothesis],
) -> None:
    """Render the McKinsey-style root card."""

    with st.container(border=True):
        st.markdown(f"### 🌳 {problem.title}")
        st.caption(problem.context)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Confidence", f"{synthesis.overall_confidence:.0%}")
    c2.metric("Hypotheses Tested", synthesis.hypotheses_tested)
    c3.metric("Confirmed", synthesis.hypotheses_confirmed)
    c4.metric("Est. Cost", f"${synthesis.total_cost_estimate:.2f}")

    if synthesis.dominant_hypothesis:
        dominant_title = _hypothesis_title(hypotheses, synthesis.dominant_hypothesis)
        dominant_label = dominant_title or synthesis.dominant_hypothesis
        st.success(f"Dominant finding: {dominant_label}")

    st.caption(_status_for_confidence(synthesis.overall_confidence))


def render_hypothesis_card(
    hyp: Hypothesis,
    verdict: HypothesisVerdict,
    probes: list[Probe],
) -> None:
    """Render a hypothesis branch card (Tier 1)."""

    style = VERDICT_STYLES.get(verdict.status, {})
    icon = style.get("icon", "")
    label = style.get("label", verdict_status_display(verdict.status))

    st.markdown(
        """
        <div style="display:flex; justify-content:center; margin-bottom:6px; color: #8E8E8E;">
          <div style="font-size:22px;">│</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(f"#### {icon} {hyp.title}")
        st.caption(label)
        st.progress(min(verdict.confidence, 1.0))
        st.caption(
            f"Confidence: {verdict.confidence:.0%} · Consistency: {verdict.consistency_score:.0%}"
        )
        st.caption(_truncate(verdict.evidence_summary or "—"))

        st.divider()

        executed = [p for p in probes if p.result is not None]
        _render_probe_nodes(executed)

        with st.expander("Full evidence detail", expanded=False, key=f"probe_detail_{hyp.id}"):
            for p in sorted(executed, key=lambda x: x.order):
                _render_probe_detail(p)


def _render_probe_nodes(probes: list[Probe]) -> None:
    """Render probe chips (Tier 2) with traffic-light indicators."""

    if not probes:
        st.caption("No probes executed for this hypothesis.")
        return

    cols = st.columns(len(probes))
    for i, probe in enumerate(sorted(probes, key=lambda x: x.order)):
        result = probe.result
        conf = result.confidence if result else 0.0
        tl = _traffic_light_for_confidence(conf)
        ptype_key: str
        if probe.probe_type in (ProbeType.INTERVIEW,):
            ptype_key = "interview"
        elif probe.probe_type in (ProbeType.SIMULATION,):
            ptype_key = "simulation"
        else:
            ptype_key = "attribute"
        cfg = PROBE_TYPE_CONFIG.get(ptype_key, {})

        with cols[i]:
            st.write(cfg.get("icon", probe_icon(probe.probe_type)))
            st.caption(f"{tl} {conf:.0%}")
            st.caption(cfg.get("label", str(probe.probe_type)))


def _render_probe_detail(probe: Probe) -> None:
    """Render full probe evidence detail."""

    if probe.result is None:
        return

    result = probe.result
    icon = probe_icon(probe.probe_type)
    label = probe_label(probe)

    st.markdown(f"{icon} **{label}**")
    st.caption(f"Confidence: {result.confidence:.0%}")
    if result.evidence_summary:
        st.write(result.evidence_summary)

    if probe.probe_type == ProbeType.INTERVIEW and result.response_clusters:
        render_interview_detail(result)
    elif probe.probe_type == ProbeType.SIMULATION and result.lift is not None:
        render_simulation_detail(result)
    elif probe.probe_type == ProbeType.ATTRIBUTE and result.attribute_splits:
        render_attribute_detail(result)


def render_results_table(
    hypotheses: list[Hypothesis],
    verdicts: dict[str, HypothesisVerdict],
    probes: list[Probe],
) -> None:
    """Render compact table view of hypothesis verdicts."""

    rows: list[dict[str, Any]] = []
    for hyp in sorted(hypotheses, key=lambda h: h.order):
        verdict = verdicts.get(hyp.id)
        if verdict is None:
            continue

        hyp_probes = [p for p in probes if p.hypothesis_id == hyp.id and p.result is not None]
        by_type: dict[ProbeType, list[float]] = {
            ProbeType.INTERVIEW: [],
            ProbeType.SIMULATION: [],
            ProbeType.ATTRIBUTE: [],
        }
        for p in hyp_probes:
            by_type.setdefault(p.probe_type, []).append(p.result.confidence)

        def _avg_or_dash(values: list[float]) -> float | str:
            return sum(values) / len(values) if values else "—"

        icon = VERDICT_STYLES.get(verdict.status, {}).get("icon", "")
        verdict_label = verdict_status_display(verdict.status)
        rows.append(
            {
                "Status": f"{icon}",
                "Hypothesis": hyp.title,
                "🎤 Interview": _avg_or_dash(by_type.get(ProbeType.INTERVIEW, [])),
                "🔬 Simulation": _avg_or_dash(by_type.get(ProbeType.SIMULATION, [])),
                "📊 Attribute": _avg_or_dash(by_type.get(ProbeType.ATTRIBUTE, [])),
                "Overall": verdict.confidence,
                "Verdict": verdict_label,
            }
        )

    if not rows:
        st.caption("No hypothesis verdicts available.")
        return

    df = pd.DataFrame(rows)
    df["Overall"] = df["Overall"].map(lambda x: f"{x:.0%}" if isinstance(x, float) else x)
    st.dataframe(df, hide_index=True, use_container_width=True)


def _render_detail_view(
    synthesis: TreeSynthesis,
    verdicts: dict[str, HypothesisVerdict],
    hypotheses_r: list[Hypothesis],
    probes_r: list[Probe],
    problem_r: ProblemStatement,
) -> None:
    """Preserve the existing expander-based rendering (backward compatible)."""

    st.divider()
    st.markdown(f"**Latest run:** {problem_r.title}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Confidence", f"{synthesis.overall_confidence:.0%}")
    c2.metric("Hypotheses Tested", synthesis.hypotheses_tested)
    c3.metric("Confirmed", synthesis.hypotheses_confirmed)
    c4.metric("Estimated Cost", f"${synthesis.total_cost_estimate:.2f}")

    if synthesis.dominant_hypothesis:
        dominant_title = _hypothesis_title(hypotheses_r, synthesis.dominant_hypothesis)
        st.info(
            f"**Dominant finding:** {dominant_title or synthesis.dominant_hypothesis} "
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
            status_icon = VERDICT_STYLES.get(verdict.status, {}).get("icon", "")
            st.markdown(f"**{status_icon} {hyp.title}** — {verdict_status_display(verdict.status)}")
        with col_bar:
            st.progress(min(verdict.confidence, 1.0))
            st.caption(
                f"Confidence: {verdict.confidence:.0%} · Consistency: {verdict.consistency_score:.0%}"
            )

        hyp_probes = [p for p in probes_r if p.hypothesis_id == hyp_id and p.result]
        with st.expander(
            f"View {len(hyp_probes)} probe results", expanded=False, key=f"detail_{hyp_id}"
        ):
            for probe in sorted(hyp_probes, key=lambda p: p.order):
                result = probe.result
                if result is None:
                    continue
                sample_info = ""
                if result.population_size and result.population_size > result.sample_size:
                    sample_info = f" · {result.sample_size}/{result.population_size} sampled"
                if result.clustering_method:
                    sample_info += f" · {result.clustering_method} clustering"

                st.markdown(f"{probe_icon(probe.probe_type)} **{probe_label(probe)}**")
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


def render_probing_tree_visualization(
    problem: ProblemStatement,
    synthesis: TreeSynthesis,
    hypotheses: list[Hypothesis],
    probes: list[Probe],
    verdicts: dict[str, HypothesisVerdict],
) -> None:
    """Master orchestrator that renders tree/table/detail views."""

    view_mode = st.radio(
        "View",
        ["🌳 Tree", "📋 Table", "📝 Detail"],
        horizontal=True,
        key="probing_tree_view_mode",
    )

    if view_mode == "📝 Detail":
        _render_detail_view(
            synthesis=synthesis,
            verdicts=verdicts,
            hypotheses_r=hypotheses,
            probes_r=probes,
            problem_r=problem,
        )
        return

    st.divider()
    render_tree_root(problem=problem, synthesis=synthesis, hypotheses=hypotheses)

    if view_mode == "📋 Table":
        render_results_table(hypotheses=hypotheses, verdicts=verdicts, probes=probes)
        st.subheader("Synthesis")
        st.write(synthesis.synthesis_narrative)
        if synthesis.recommended_actions:
            st.subheader("Recommended Actions")
            for i, action in enumerate(synthesis.recommended_actions, 1):
                st.markdown(f"{i}. {action}")
        return

    # Tree view (default)
    st.subheader("Hypothesis Branches")

    executed_counts = {h.id: 0 for h in hypotheses}
    for p in probes:
        if p.result is not None:
            executed_counts[p.hypothesis_id] = executed_counts.get(p.hypothesis_id, 0) + 1

    tested_verdicts = [h for h in hypotheses if h.id in verdicts]
    tested_verdicts = sorted(tested_verdicts, key=lambda h: h.order)

    max_per_row = 4
    for start in range(0, len(tested_verdicts), max_per_row):
        row_hyps = tested_verdicts[start : start + max_per_row]
        cols = st.columns(len(row_hyps))
        for idx, hyp in enumerate(row_hyps):
            with cols[idx]:
                verdict = verdicts[hyp.id]
                hyp_probes = [
                    p for p in probes if p.hypothesis_id == hyp.id and p.result is not None
                ]
                render_hypothesis_card(hyp=hyp, verdict=verdict, probes=hyp_probes)

    if synthesis.disabled_hypotheses:
        skipped = [h for h in hypotheses if h.id in set(synthesis.disabled_hypotheses)]
        if skipped:
            with st.expander("Skipped hypotheses", expanded=False, key="skipped_hypotheses"):
                for hyp in skipped:
                    st.markdown(f"~~{hyp.title}~~")

    st.subheader("Dominant Narrative")
    st.write(synthesis.synthesis_narrative)

    if synthesis.recommended_actions:
        st.subheader("Recommended Actions")
        for i, action in enumerate(synthesis.recommended_actions, 1):
            st.markdown(f"{i}. {action}")

    st.divider()
    st.caption(
        "🎤 Interview · 🔬 Simulation · 📊 Attribute analysis · Traffic light chips show probe confidence"
    )

    with st.expander("Legend", expanded=False, key="probing_tree_legend"):
        for _, cfg in VERDICT_STYLES.items():
            st.caption(f"{cfg['icon']} {cfg['label']}")
        st.caption("Probe chips: traffic light reflects confidence thresholds.")


def render_probing_tree_progress(
    problem: ProblemStatement,
    hypotheses: list[Hypothesis],
    partial_results: dict[str, list[ProbeResult]],
) -> None:
    """
    Render a live-growing tree from partial probe results accumulated so far.
    Shows completed hypothesis cards; pending hypotheses show a pulsing spinner row.
    """
    # 1. Root card placeholder
    with st.container(border=True):
        st.markdown(f"### 🌳 {problem.title}")
        st.caption(f"🔍 Progressive Investigation in progress... ({sum(len(r) for r in partial_results.values())} probes executed)")

    st.subheader("Hypothesis Branches")

    sorted_hyps = sorted(hypotheses, key=lambda h: h.order)
    enabled_hyps = [h for h in sorted_hyps if h.enabled]

    max_per_row = 4
    for start in range(0, len(enabled_hyps), max_per_row):
        row_hyps = enabled_hyps[start : start + max_per_row]
        cols = st.columns(len(row_hyps))
        for idx, hyp in enumerate(row_hyps):
            with cols[idx]:
                results = partial_results.get(hyp.id, [])
                if results:
                    _render_hypothesis_card_progress(hyp, results)
                else:
                    _render_hypothesis_placeholder(hyp)

    st.divider()
    st.caption("🎤 Interview · 🔬 Simulation · 📊 Attribute analysis")


def _render_hypothesis_card_progress(hyp: Hypothesis, results: list[ProbeResult]) -> None:
    """Render a partial hypothesis card for 'growing' view."""
    avg_conf = sum(r.confidence for r in results) / len(results)
    
    st.markdown(
        """
        <div style="display:flex; justify-content:center; margin-bottom:6px; color: #8E8E8E;">
          <div style="font-size:22px;">│</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(f"#### 🟡 {hyp.title}")
        st.caption(f"Investigated ({len(results)} probes)")
        st.progress(min(avg_conf, 1.0))
        st.caption(f"Est. Confidence: {avg_conf:.0%}")
        
        # Show truncated snippet of last evidence
        evidence = results[-1].evidence_summary if results else "Preparing analysis..."
        st.caption(_truncate(evidence))


def _render_hypothesis_placeholder(hyp: Hypothesis) -> None:
    """Render a placeholder card for a hypothesis that hasn't finished any probes yet."""
    st.markdown(
        """
        <div style="display:flex; justify-content:center; margin-bottom:6px; color: #8E8E8E;">
          <div style="font-size:22px;">│</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(f"#### ⚪ {hyp.title}")
        st.caption("Investigating… ⏳")
        st.divider()
        st.caption("Awaiting initial probe data")
