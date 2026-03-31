# ruff: noqa: N999
"""Phase 2 — Decomposition & Probing.

Presents simulation-grounded hypotheses for the selected problem, lets the user
enable/disable individual branches, then runs the full probing tree and renders
results using the existing tree visualization components.
"""

from __future__ import annotations

import os
import re

import streamlit as st

from app.components.system_voice import render_system_voice
from app.utils.phase_state import render_phase_sidebar
from src.analysis.contradiction_detector import detect_contradictions
from src.probing.models import Hypothesis

# ---------------------------------------------------------------------------
# Scenario → problem-tree ID mapping
# ---------------------------------------------------------------------------

_SCENARIO_TO_TREE: dict[str, str] = {
    "nutrimix_2_6": "repeat_purchase_low",
    "nutrimix_7_14": "nutrimix_7_14_expansion",
    "magnesium_gummies": "magnesium_gummies_growth",
    "protein_mix": "protein_mix_launch",
}

# Human-readable labels for cohort keys used in the system voice callout
_COHORT_LABELS: dict[str, str] = {
    "never_aware": "never aware of the product",
    "aware_not_tried": "aware but haven't tried",
    "first_time_buyer": "first-time buyers",
    "current_user": "current users",
    "lapsed_user": "lapsed users",
}

# Verdict badge config -------------------------------------------------------

_VERDICT_BADGE: dict[str, dict[str, str]] = {
    "confirmed": {"icon": "✅", "color": "#2ECC71", "label": "Confirmed"},
    "partially_confirmed": {"icon": "⚠️", "color": "#F39C12", "label": "Partially Confirmed"},
    "rejected": {"icon": "❌", "color": "#E74C3C", "label": "Rejected"},
    "inconclusive": {"icon": "❔", "color": "#95A5A6", "label": "Inconclusive"},
}


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return value or "hypothesis"

# ---------------------------------------------------------------------------
# Page config & sidebar
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Phase 2 — Decomposition & Probing", layout="wide")
render_phase_sidebar()

st.header("Phase 2 — Decomposition & Probing")

# ---------------------------------------------------------------------------
# GUARD — Phase 1 must be complete
# ---------------------------------------------------------------------------

if "baseline_cohorts" not in st.session_state:
    st.warning(
        "No baseline simulation found. Complete Phase 1 (Problem & Simulation) first.",
        icon="🔒",
    )
    st.stop()

# ---------------------------------------------------------------------------
# Resolve tree problem ID from session scenario
# ---------------------------------------------------------------------------

scenario_id: str = st.session_state.get("baseline_scenario_id", "")
problem_id: str | None = _SCENARIO_TO_TREE.get(scenario_id)

if problem_id is None:
    st.error(
        f"Unknown scenario '{scenario_id}'. Cannot load a hypothesis tree. "
        "Go back to Phase 1 and re-run the baseline simulation."
    )
    st.stop()

# Load tree definitions once (cheap — pure Python, no I/O)
try:
    from src.probing.predefined_trees import get_problem_tree

    problem, all_hypotheses, all_probes = get_problem_tree(problem_id)
except Exception as exc:
    st.error(f"Failed to load problem tree for '{problem_id}': {exc}")
    st.stop()

# ---------------------------------------------------------------------------
# SYSTEM VOICE — orientation callout
# ---------------------------------------------------------------------------

cohorts = st.session_state["baseline_cohorts"]  # PopulationCohorts
summary: dict[str, int] = cohorts.summary

# Build a natural-language cohort snapshot
cohort_fragments: list[str] = []
for key in ("never_aware", "aware_not_tried", "first_time_buyer", "current_user", "lapsed_user"):
    count = summary.get(key, 0)
    if count:
        cohort_fragments.append(f"<strong>{count}</strong> {_COHORT_LABELS.get(key, key)}")

cohort_sentence = (
    "The simulated population breaks down as: " + ", ".join(cohort_fragments) + "."
    if cohort_fragments
    else "The population cohort breakdown is available in Phase 1."
)

raw_problem_id: str = st.session_state.get("baseline_problem_id", problem_id)

render_system_voice(
    f"Based on the baseline simulation for <strong>{problem.title}</strong>, "
    f"I have decomposed the problem into <strong>{len(all_hypotheses)} hypotheses</strong> "
    f"covering the most plausible explanations rooted in your population's attribute profile. "
    f"{cohort_sentence} "
    f"Review and enable the hypotheses you want investigated. "
    f"Each enabled branch will be tested with a mix of simulated interviews, "
    f"counterfactual simulations, and attribute analysis."
)

# ---------------------------------------------------------------------------
# HYPOTHESIS REVIEW TABLE
# ---------------------------------------------------------------------------

st.subheader("Hypothesis Review")
st.caption(
    "All hypotheses are enabled by default. Uncheck any you want to skip. "
    "Disabled branches are excluded from probe execution and synthesis."
)

# Initialise enabled state in session_state on first load
if "hypothesis_enabled" not in st.session_state:
    st.session_state["hypothesis_enabled"] = {h.id: h.enabled for h in all_hypotheses}

custom_key = f"custom_hypotheses_{problem_id}"
if custom_key not in st.session_state:
    st.session_state[custom_key] = []

custom_hypotheses = [Hypothesis.model_validate(h) for h in st.session_state[custom_key]]
all_hypotheses = all_hypotheses + custom_hypotheses
sorted_hypotheses = sorted(all_hypotheses, key=lambda h: (h.order, h.id))

for hyp in sorted_hypotheses:
    with st.container(border=True):
        col_check, col_body = st.columns([0.07, 0.93])
        with col_check:
            enabled = st.checkbox(
                label="enabled",
                value=st.session_state["hypothesis_enabled"].get(hyp.id, True),
                key=f"hyp_check_{hyp.id}",
                label_visibility="collapsed",
            )
            st.session_state["hypothesis_enabled"][hyp.id] = enabled

        with col_body:
            title_style = "" if enabled else "color:#999; text-decoration:line-through;"
            if hyp.is_custom:
                st.markdown(
                    (
                        "<div style='"
                        "border-left:4px solid #9B59B6; background:#F6F0FA; "
                        "padding:8px 10px; border-radius:4px;'>"
                        f"<span style='{title_style}'><strong>🧑 {hyp.title}</strong></span>"
                        f"<div style='margin-top:4px; font-size:0.9rem;'>{hyp.rationale}</div>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<span style='{title_style}'><strong>H{hyp.order}. {hyp.title}</strong></span>",
                    unsafe_allow_html=True,
                )
                st.caption(hyp.rationale)

            # Indicator attribute chips
            if hyp.indicator_attributes:
                chips_html = " ".join(
                    f"<span style='"
                    f"background:#EBF5FB; color:#1A5276; border:1px solid #AED6F1; "
                    f"border-radius:12px; padding:2px 10px; font-size:0.8rem; "
                    f"margin-right:4px; display:inline-block;'>"
                    f"{attr.replace('_', ' ')}"
                    f"</span>"
                    for attr in hyp.indicator_attributes
                )
                st.markdown(
                    f"<div style='margin-top:4px;'>{chips_html}</div>",
                    unsafe_allow_html=True,
                )

if "baseline_cohorts" in st.session_state:
    with st.expander("Add your own hypothesis (optional)", expanded=False):
        custom_title = st.text_input(
            "Hypothesis title",
            placeholder="e.g. Packaging looks cheap at shelf",
            key="custom_hypothesis_title",
        )
        custom_rationale = st.text_area(
            "Why you believe this",
            placeholder="Describe the signal you're seeing...",
            key="custom_hypothesis_rationale",
        )
        if st.button("Add hypothesis", key="add_custom_hypothesis"):
            title = custom_title.strip()
            rationale = custom_rationale.strip()
            if not title or not rationale:
                st.warning("Please provide both title and rationale.")
            else:
                new_id = f"custom_{_slug(title)}"
                if any(h.id == new_id for h in all_hypotheses):
                    st.warning("A custom hypothesis with a similar title already exists.")
                else:
                    custom_h = Hypothesis(
                        id=new_id,
                        problem_id=problem.id,
                        title=title,
                        rationale=rationale,
                        signals=[],
                        indicator_attributes=[],
                        is_custom=True,
                        enabled=True,
                        order=999 + len(custom_hypotheses),
                    )
                    st.session_state[custom_key] = [
                        *st.session_state[custom_key],
                        custom_h.model_dump(mode="json"),
                    ]
                    st.session_state["hypothesis_enabled"][custom_h.id] = True
                    st.success(
                        "Hypothesis added — it will be included in the next investigation run."
                    )
                    st.rerun()

# Count enabled
enabled_count = sum(
    1 for hyp in sorted_hypotheses if st.session_state["hypothesis_enabled"].get(hyp.id, True)
)

if enabled_count == 0:
    st.warning("Enable at least one hypothesis to run the investigation.")

# ---------------------------------------------------------------------------
# RUN INVESTIGATION BUTTON
# ---------------------------------------------------------------------------

st.divider()

run_clicked = st.button(
    "Run Investigation",
    type="primary",
    use_container_width=True,
    disabled=(enabled_count == 0),
)

if run_clicked:
    # Apply enabled state to hypothesis objects
    for hyp in all_hypotheses:
        hyp.enabled = st.session_state["hypothesis_enabled"].get(hyp.id, True)

    # Build LLM client
    mock_env = os.environ.get("LLM_MOCK_ENABLED", "false").lower() == "true"

    try:
        from src.config import Config
        from src.probing.engine import ProbingTreeEngine
        from src.utils.api_keys import resolve_api_key

        config = Config()

        # Override mock flag if env var requests it
        if mock_env and not config.llm_mock_enabled:
            config = config.model_copy(update={"llm_mock_enabled": True})

        api_key = resolve_api_key()
        if api_key:
            config = config.model_copy(update={"anthropic_api_key": api_key})

        from src.utils.llm import LLMClient

        llm_client = LLMClient(config=config)

        population = st.session_state["population"]

        # Initialise partial results bucket for live tree rendering
        st.session_state["partial_probe_results"] = {}

        from app.components.probing_tree_viz import render_probing_tree_progress

        # Create a placeholder for the live-growing tree
        tree_placeholder = st.empty()

        def _on_probe(hypothesis_id: str, result) -> None:
            bucket = st.session_state["partial_probe_results"]
            bucket.setdefault(hypothesis_id, []).append(result)
            st.session_state["partial_probe_results"] = bucket
            # Update the placeholder in-place
            with tree_placeholder.container():
                render_probing_tree_progress(
                    problem,
                    all_hypotheses,
                    bucket,
                )

        # Initial render of placeholders
        with tree_placeholder.container():
            render_probing_tree_progress(
                problem,
                all_hypotheses,
                {},
            )

        with st.spinner(
            f"Running investigation across {enabled_count} hypothesis branch(es) — "
            "this may take a minute…"
        ):
            engine = ProbingTreeEngine(
                population=population,
                scenario_id=scenario_id,
                llm_client=llm_client,
                on_probe_complete=_on_probe,
            )
            synthesis = engine.execute_tree(
                problem=problem,
                hypotheses=all_hypotheses,
                probes=all_probes,
            )

        # Clear the placeholder before showing final results if needed,
        # but here we just proceed to set session_state and rerun to final view
        tree_placeholder.empty()

        st.session_state["probe_results"] = {
            "synthesis": synthesis,
            "verdicts": engine.verdicts,
            "probes": all_probes,
            "problem": problem,
            "hypotheses": all_hypotheses,
        }

    except Exception as exc:
        st.error(
            f"Investigation failed: {exc}\n\n"
            "Check that a population is loaded in Phase 0 and the baseline simulation "
            "completed successfully in Phase 1."
        )
        st.stop()

    st.rerun()

# ---------------------------------------------------------------------------
# RESULTS DISPLAY
# ---------------------------------------------------------------------------

if "probe_results" not in st.session_state:
    st.stop()

results = st.session_state["probe_results"]
synthesis = results["synthesis"]
verdicts = results["verdicts"]
probes_r = results.get("probes", all_probes)
problem_r = results.get("problem", problem)
hypotheses_r = results.get("hypotheses", all_hypotheses)

st.divider()
st.subheader("Investigation Results")

# --- Results system voice ---
confirmed_count = synthesis.hypotheses_confirmed
tested_count = synthesis.hypotheses_tested
dominant_id = synthesis.dominant_hypothesis
dominant_title = next(
    (h.title for h in hypotheses_r if h.id == dominant_id), dominant_id
)

render_system_voice(
    f"The investigation tested <strong>{tested_count} hypothesis branch(es)</strong> and "
    f"found <strong>{confirmed_count}</strong> confirmed or partially confirmed. "
    + (
        f"The strongest explanation is <strong>{dominant_title}</strong> "
        f"at <strong>{synthesis.overall_confidence:.0%}</strong> confidence. "
        if dominant_title
        else ""
    )
    + (
        "Scroll down for the full tree view and synthesis narrative."
        if tested_count > 1
        else "Review the hypothesis detail below."
    )
)

# --- Probing tree visualization ---
try:
    from app.components.probing_tree_viz import render_probing_tree_visualization

    render_probing_tree_visualization(
        problem=problem_r,
        synthesis=synthesis,
        hypotheses=hypotheses_r,
        probes=probes_r,
        verdicts=verdicts,
    )

except Exception as viz_exc:
    # Fallback: simple per-hypothesis expanders
    st.warning(f"Tree visualization unavailable ({viz_exc}). Showing summary view.")

    for hyp in sorted(hypotheses_r, key=lambda h: h.order):
        verdict = verdicts.get(hyp.id)
        if verdict is None:
            continue

        badge = _VERDICT_BADGE.get(verdict.status, {"icon": "❔", "label": verdict.status})
        with st.expander(
            f"{badge['icon']} H{hyp.order}. {hyp.title} — {badge['label']} "
            f"({verdict.confidence:.0%})",
            expanded=True,
        ):
            st.progress(min(verdict.confidence, 1.0))
            st.caption(
                f"Confidence: {verdict.confidence:.0%} · "
                f"Consistency: {verdict.consistency_score:.0%}"
            )
            st.write(verdict.evidence_summary)

            hyp_probes = [p for p in probes_r if p.hypothesis_id == hyp.id and p.result]
            for probe in sorted(hyp_probes, key=lambda p: p.order):
                r = probe.result
                if r is None:
                    continue
                ptype_label = probe.probe_type.value.title() if probe.probe_type else "Probe"
                st.markdown(f"**{ptype_label}:** {probe.question_template or probe.id}")
                st.caption(f"Confidence: {r.confidence:.0%} — {r.evidence_summary}")

# --- Cross-hypothesis synthesis ---
contradictions = detect_contradictions(
    hypotheses=hypotheses_r,
    verdicts=verdicts,
    probes=probes_r,
)
st.markdown("## ⚡ Cross-Hypothesis Conflicts")
if contradictions:
    severity_style = {
        "high": {"border": "#E74C3C", "icon": "🔴"},
        "medium": {"border": "#F1C40F", "icon": "🟡"},
        "low": {"border": "#95A5A6", "icon": "⚪"},
    }
    for warning in contradictions:
        style = severity_style.get(warning.severity, severity_style["low"])
        st.markdown(
            (
                "<div style='"
                f"border-left:4px solid {style['border']}; "
                "padding:10px 12px; margin:8px 0; background:#FAFAFA;'>"
                f"<div><strong>{style['icon']} {warning.hypothesis_a_id} vs {warning.hypothesis_b_id}</strong> "
                f"<span style='background:#F4F6F7; border:1px solid #D5D8DC; border-radius:8px; "
                "padding:1px 8px; font-size:0.8rem;'>"
                f"{warning.contradiction_type}</span></div>"
                f"<div style='margin-top:4px;'>{warning.description}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
else:
    st.caption("Cross-hypothesis consistency check")
    st.success("No cross-hypothesis conflicts detected.")

if synthesis.synthesis_narrative:
    st.subheader("Cross-Hypothesis Synthesis")
    st.write(synthesis.synthesis_narrative)

# --- Core finding callout (if attribute available) ---
core_finding = getattr(synthesis, "core_finding", None)
if core_finding:
    from app.components.system_voice import render_core_finding

    render_core_finding(core_finding)

# --- Phase complete banner ---
st.success(
    "Phase 2 complete — proceed to **Core Finding** (Phase 3) to generate the strategic narrative.",
    icon="✅",
)
