# ruff: noqa: N999
"""Interview Deep-Dive page.

Renders qualitative evidence from the Phase 2 probing tree interview probes.
Data source: st.session_state["probe_results"] set by 3_decompose.py.
"""

from __future__ import annotations

import streamlit as st

from app.components.system_voice import render_system_voice
from app.utils.phase_state import render_phase_sidebar
from src.probing.models import ProbeType

st.set_page_config(page_title="Interview Deep-Dive", page_icon="🎙️", layout="wide")
render_phase_sidebar()
st.header("Interview Deep-Dive")
st.caption("Qualitative evidence collected during Phase 2 investigation.")

# ── Phase gate ────────────────────────────────────────────────────────────────
if "probe_results" not in st.session_state:
    st.warning(
        "No investigation results yet. Complete Phase 2 (Decomposition & Probing) first.",
        icon="🔒",
    )
    st.stop()

# ── Extract data ──────────────────────────────────────────────────────────────
results = st.session_state["probe_results"]
probes = results.get("probes", [])
hypotheses = results.get("hypotheses", [])
problem = results.get("problem")
population = st.session_state.get("population")

# Build hypothesis id→title lookup
hyp_titles: dict[str, str] = {h.id: h.title for h in hypotheses}

# Collect all interview probes that completed successfully
interview_probes = [
    p for p in probes
    if p.probe_type == ProbeType.INTERVIEW and p.result is not None
]

if not interview_probes:
    st.info(
        "No interview probes were run during the investigation. "
        "Interview probes run automatically when hypotheses require qualitative evidence.",
        icon="ℹ️",
    )
    st.stop()

# Summary counts
total_responses = sum(len(p.result.interview_responses) for p in interview_probes)
total_clusters = sum(len(p.result.response_clusters) for p in interview_probes)

render_system_voice(
    f"Phase 2 gathered <strong>{total_responses} interview responses</strong> "
    f"across <strong>{len(interview_probes)} interview probes</strong>, "
    f"surfacing <strong>{total_clusters} response clusters</strong>. "
    f"Here is the qualitative evidence organised by hypothesis."
)

# ── Per-hypothesis interview evidence ─────────────────────────────────────────
# Group interview probes by hypothesis
from collections import defaultdict
hyp_to_probes: dict[str, list] = defaultdict(list)
for p in interview_probes:
    hyp_to_probes[p.hypothesis_id].append(p)

for hyp_id, hyp_probes in hyp_to_probes.items():
    hyp_title = hyp_titles.get(hyp_id, hyp_id)
    hyp_responses = [r for p in hyp_probes for r in p.result.interview_responses]
    hyp_clusters = [c for p in hyp_probes for c in p.result.response_clusters]

    st.subheader(f"📋 {hyp_title}")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Interview Probes", len(hyp_probes))
    col_b.metric("Responses", len(hyp_responses))
    col_c.metric("Themes Identified", len(hyp_clusters))

    # Response clusters / themes
    if hyp_clusters:
        st.markdown("**Response Themes**")
        for cluster in hyp_clusters:
            theme_label = cluster.theme.replace("_", " ").title()
            pct = f"{cluster.percentage:.0%}" if cluster.percentage <= 1.0 else f"{cluster.percentage:.0f}%"
            with st.expander(f"{theme_label} — {cluster.persona_count} personas ({pct})"):
                st.caption(cluster.description)
                if cluster.representative_quotes:
                    for quote in cluster.representative_quotes[:3]:
                        st.markdown(f"> *{quote[:300]}*")

    # Individual responses
    if hyp_responses:
        with st.expander(f"All {len(hyp_responses)} individual responses", expanded=False):
            for resp in hyp_responses:
                outcome_icon = "✅" if resp.outcome == "adopt" else "❌"
                st.markdown(
                    f"**{resp.persona_name}** {outcome_icon} _{resp.outcome.replace('_', ' ').title()}_"
                )
                st.markdown(f"> {resp.content[:400]}")
                st.divider()

    st.markdown("---")

# ── Cross-hypothesis theme summary ────────────────────────────────────────────
all_clusters_raw = [c for p in interview_probes for c in p.result.response_clusters]
if all_clusters_raw:
    st.subheader("Cross-Hypothesis Themes")
    st.caption("All response clusters across every interview probe, ranked by frequency.")

    # Deduplicate clusters by theme label, keeping the one with the highest persona_count
    # (Fix for duplicate theme entries in Phase 7)
    deduped: dict[str, Any] = {}
    for cluster in all_clusters_raw:
        label = cluster.theme.replace("_", " ").title()
        if label not in deduped or cluster.persona_count > deduped[label].persona_count:
            deduped[label] = cluster
    
    all_clusters = list(deduped.values())
    sorted_clusters = sorted(all_clusters, key=lambda c: c.persona_count, reverse=True)
    for cluster in sorted_clusters[:8]:
        theme_label = cluster.theme.replace("_", " ").title()
        pct = f"{cluster.percentage:.0%}" if cluster.percentage <= 1.0 else f"{cluster.percentage:.0f}%"
        st.markdown(f"**{theme_label}** — {cluster.persona_count} personas ({pct})")
        st.caption(cluster.description)
        if cluster.representative_quotes:
            st.markdown(f"> *{cluster.representative_quotes[0][:250]}*")
        st.divider()

# ── Persona comparison ────────────────────────────────────────────────────────
all_responses = [r for p in interview_probes for r in p.result.interview_responses]
if population is not None and len(all_responses) >= 2:
    st.subheader("Compare Personas")
    st.caption("Select two personas from the interviews to compare their responses side-by-side.")

    # Deduplicate persona IDs preserving order
    seen: set[str] = set()
    persona_ids: list[str] = []
    for r in all_responses:
        if r.persona_id not in seen:
            persona_ids.append(r.persona_id)
            seen.add(r.persona_id)

    persona_labels: dict[str, str] = {}
    for pid in persona_ids:
        try:
            p = population.get_persona(pid)
            persona_labels[pid] = f"{p.name} ({p.demographics.city_tier})"
        except Exception:  # noqa: BLE001
            persona_labels[pid] = pid

    cmp_cols = st.columns(2)
    with cmp_cols[0]:
        left_id = st.selectbox(
            "Persona A",
            persona_ids,
            format_func=lambda x: persona_labels[x],
            index=0,
            key="cmp_left",
        )
    with cmp_cols[1]:
        right_id = st.selectbox(
            "Persona B",
            persona_ids,
            format_func=lambda x: persona_labels[x],
            index=min(1, len(persona_ids) - 1),
            key="cmp_right",
        )

    if left_id and right_id:
        left_responses = [r for r in all_responses if r.persona_id == left_id]
        right_responses = [r for r in all_responses if r.persona_id == right_id]

        left_col, right_col = st.columns(2)
        with left_col:
            st.markdown(f"**{persona_labels[left_id]}**")
            for r in left_responses[:5]:
                st.markdown(f"> *{r.content[:300]}*")
        with right_col:
            st.markdown(f"**{persona_labels[right_id]}**")
            for r in right_responses[:5]:
                st.markdown(f"> *{r.content[:300]}*")

# ── Single Persona Deep-Dive ──────────────────────────────────────────────────
if population is not None and persona_ids:
    st.divider()
    st.subheader("🔍 Single Persona Deep-Dive")
    st.caption("Drill into one persona to see every response they gave across the investigation.")

    selected_pid = st.selectbox(
        "Select a persona to deep-dive",
        persona_ids,
        format_func=lambda x: persona_labels[x],
        key="deep_dive_persona",
    )

    if selected_pid:
        persona = population.get_persona(selected_pid)
        
        # Profile card
        with st.container(border=True):
            col_id, col_meta = st.columns([0.2, 0.8])
            with col_id:
                st.markdown(f"### {persona.name}")
                st.caption(f"ID: `{persona.id}`")
            with col_meta:
                # Resolve cohort if possible (look up in classification results)
                cohort_label = "Unclassified"
                cohorts_obj = st.session_state.get("baseline_cohorts")
                if cohorts_obj and hasattr(cohorts_obj, "memberships"):
                    cid = cohorts_obj.memberships.get(persona.id, "unclassified")
                    # Emoji mapping from Ph 1
                    emojis = {"never_aware": "🔇", "aware_not_tried": "👁️", "first_time_buyer": "🛒", "current_user": "⭐", "lapsed_user": "💤"}
                    cohort_label = f"{emojis.get(cid, '👤')} {cid.replace('_', ' ').title()}"

                st.markdown(
                    f"**{persona.demographics.city_name}** · "
                    f"{persona.demographics.household_income_lpa} LPA · "
                    f"**{cohort_label}**"
                )
                narrative = getattr(persona, "narrative", "No narrative available.")
                st.caption(narrative.split(".")[0][:150] + "...")

        # All responses grouped by hypothesis
        persona_responses = [r for r in all_responses if r.persona_id == selected_pid]
        
        # Find which probes these responses came from to get questions/hypotheses
        for hyp_id, hyp_probes in hyp_to_probes.items():
            hyp_title = hyp_titles.get(hyp_id, hyp_id)
            
            # Find responses for this persona in this hypothesis's probes
            matches = []
            for probe in hyp_probes:
                for resp in probe.result.interview_responses:
                    if resp.persona_id == selected_pid:
                        # Find theme clustering if available
                        theme = "Unknown Theme"
                        for cluster in probe.result.response_clusters:
                            # Heuristic: does the representative quote match?
                            # Improved: just show the cluster it belongs to if engine provided it
                            # Since ProbeResult doesn't map resp -> cluster, we use the theme_label
                            # from the response if present (future sprint) or skip
                            pass
                        matches.append((probe, resp))
            
            if matches:
                 with st.expander(f"Hypothesis: {hyp_title}", expanded=True):
                     for probe, resp in matches:
                         st.markdown(f"**Probe Q:** _{probe.question_template}_")
                         st.markdown(f"> {resp.content}")
                         st.caption(f"Outcome: {resp.outcome.replace('_', ' ').title()}")
                         st.divider()
