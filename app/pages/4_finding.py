"""Phase 3 — Core Finding.

The climactic reveal: synthesises the Phase 2 probe investigation into a single
dominant finding, a ranked evidence chain, and a strategic insight callout.
"""

from __future__ import annotations

import json

import streamlit as st

from app.components.system_voice import (
    render_core_finding,
    render_magic_moment,
    render_system_voice,
)
from app.utils.phase_state import render_phase_sidebar

# ---------------------------------------------------------------------------
# Verdict badge config (mirrors 3_decompose.py for visual consistency)
# ---------------------------------------------------------------------------

_VERDICT_BADGE: dict[str, dict[str, str]] = {
    "confirmed": {"icon": "✅", "color": "#2ECC71", "label": "Confirmed"},
    "partially_confirmed": {"icon": "⚠️", "color": "#F39C12", "label": "Partially Confirmed"},
    "rejected": {"icon": "❌", "color": "#E74C3C", "label": "Rejected"},
    "inconclusive": {"icon": "❔", "color": "#95A5A6", "label": "Inconclusive"},
    "insufficient": {"icon": "❔", "color": "#95A5A6", "label": "Insufficient"},
}

# ---------------------------------------------------------------------------
# Page config & sidebar
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Phase 3 — Core Finding", layout="wide")
render_phase_sidebar()

st.header("Phase 3 — Core Finding")

# ---------------------------------------------------------------------------
# PHASE GATE — probe_results must exist
# ---------------------------------------------------------------------------

if "probe_results" not in st.session_state:
    st.warning(
        "Complete Phase 2 (Decomposition & Probing) first.",
        icon="🔒",
    )
    st.stop()

# ---------------------------------------------------------------------------
# Extract data from session state
# ---------------------------------------------------------------------------

probe_results: dict = st.session_state["probe_results"]

# TreeSynthesis object — always present after Phase 2 completes
synthesis = probe_results.get("synthesis")

# OrchestrationResult — only present if the sequential orchestrator was used;
# the default Phase 2 path (ProbingTreeEngine.execute_tree) does NOT write this.
orchestration = probe_results.get("orchestration")

# Supporting collections written by 3_decompose.py
verdicts: dict = probe_results.get("verdicts", {})
hypotheses_list: list = probe_results.get("hypotheses", [])
probes_list: list = probe_results.get("probes", [])

# Population cohorts and scenario from earlier phases
cohorts = st.session_state.get("baseline_cohorts")
scenario_id: str = st.session_state.get("baseline_scenario_id", "unknown")

# ---------------------------------------------------------------------------
# Defensive attribute accessors for TreeSynthesis
# ---------------------------------------------------------------------------

hypotheses_tested: int = getattr(synthesis, "hypotheses_tested", 0) if synthesis else 0
hypotheses_confirmed: int = getattr(synthesis, "hypotheses_confirmed", 0) if synthesis else 0
dominant_hypothesis_id: str = getattr(synthesis, "dominant_hypothesis", "") if synthesis else ""
overall_confidence: float = getattr(synthesis, "overall_confidence", 0.0) if synthesis else 0.0
confidence_ranking: list = getattr(synthesis, "confidence_ranking", []) if synthesis else []
synthesis_narrative_text: str = getattr(synthesis, "synthesis_narrative", "") if synthesis else ""

# Resolve dominant hypothesis title from the hypotheses list in session state
_hyp_title_by_id: dict[str, str] = {h.id: h.title for h in hypotheses_list if hasattr(h, "id")}
dominant_hypothesis_title: str = _hyp_title_by_id.get(dominant_hypothesis_id, dominant_hypothesis_id)

# Probe count — use length of all probes that have a result attached,
# falling back to total probes defined if results are unavailable
probes_with_results = [p for p in probes_list if getattr(p, "result", None) is not None]
probe_count: int = len(probes_with_results) if probes_with_results else len(probes_list)

# ---------------------------------------------------------------------------
# 1. SYSTEM VOICE — investigation summary callout
# ---------------------------------------------------------------------------

render_system_voice(
    f"The investigation is complete. Across <strong>{hypotheses_tested} "
    f"hypothesis{'es' if hypotheses_tested != 1 else ''}</strong> and "
    f"<strong>{probe_count} probe{'s' if probe_count != 1 else ''}</strong>, "
    "a dominant pattern has emerged. Here is what the evidence says."
)

# ---------------------------------------------------------------------------
# 2. CORE FINDING — orange box (the analytical climax)
# ---------------------------------------------------------------------------

# Priority order: OrchestrationResult.core_finding_draft > synthesis.synthesis_narrative
# (TreeSynthesis has no dedicated .summary field — synthesis_narrative is the closest)
if orchestration is not None:
    core_finding_text: str = getattr(orchestration, "core_finding_draft", "") or ""
else:
    core_finding_text = ""

if not core_finding_text and synthesis is not None:
    # synthesis_narrative is a multi-sentence cross-hypothesis description;
    # use the first sentence as a compact core finding if no dedicated draft exists
    full_narrative = synthesis_narrative_text.strip()
    if full_narrative:
        # Take up to the first sentence (split on ". " but keep at most 300 chars)
        first_sentence = full_narrative.split(". ")[0]
        core_finding_text = first_sentence if len(first_sentence) <= 300 else first_sentence[:297] + "…"

if not core_finding_text and dominant_hypothesis_title:
    core_finding_text = (
        f"The primary barrier identified is <strong>{dominant_hypothesis_title}</strong>, "
        f"supported by {probe_count} probe{'s' if probe_count != 1 else ''} "
        f"at {overall_confidence:.0%} overall confidence."
    )

if not core_finding_text:
    core_finding_text = "Insufficient evidence collected — re-run the Phase 2 investigation."

render_core_finding(core_finding_text)

# ---------------------------------------------------------------------------
# 3. EVIDENCE CHAIN — ranked hypothesis verdicts
# ---------------------------------------------------------------------------

st.subheader("Evidence Chain")

# Build display order: confidence_ranking from synthesis first (it's already sorted
# by descending confidence); fall back to iterating verdicts dict if ranking is empty
ordered_hyp_ids: list[str] = [hyp_id for hyp_id, _ in confidence_ranking] if confidence_ranking else list(verdicts.keys())

# Ensure any hypothesis ID in verdicts but absent from ranking is appended at the end
for hyp_id in verdicts:
    if hyp_id not in ordered_hyp_ids:
        ordered_hyp_ids.append(hyp_id)

evidence_chain_ids: list[str] = []

if not ordered_hyp_ids:
    st.info("No hypothesis verdicts found. Run the investigation in Phase 2 to generate results.")
else:
    for position, hyp_id in enumerate(ordered_hyp_ids, start=1):
        verdict_obj = verdicts.get(hyp_id)
        if verdict_obj is None:
            continue

        # Status and badge
        status: str = getattr(verdict_obj, "status", "inconclusive")
        badge = _VERDICT_BADGE.get(status, _VERDICT_BADGE["inconclusive"])

        # Hypothesis title — prefer session state list, fall back to verdict's own id
        hyp_title: str = _hyp_title_by_id.get(hyp_id, hyp_id)

        # Evidence snippet — truncate to 200 chars
        evidence_raw: str = getattr(verdict_obj, "evidence_summary", "")
        evidence_snippet = evidence_raw[:200] + "…" if len(evidence_raw) > 200 else evidence_raw

        # Confidence and consistency
        confidence: float = getattr(verdict_obj, "confidence", 0.0)
        consistency: float = getattr(verdict_obj, "consistency_score", 0.0)

        # Effect size — look up from the best probe result (highest confidence probe for this hyp)
        best_probe_result = None
        best_probe_confidence: float = -1.0
        for probe in probes_list:
            if getattr(probe, "hypothesis_id", None) == hyp_id:
                probe_result = getattr(probe, "result", None)
                if probe_result is not None:
                    pc = getattr(probe_result, "confidence", 0.0)
                    if pc > best_probe_confidence:
                        best_probe_confidence = pc
                        best_probe_result = probe_result

        # Build effect size / lift display string
        effect_parts: list[str] = []
        if best_probe_result is not None:
            lift = getattr(best_probe_result, "lift", None)
            attribute_splits = getattr(best_probe_result, "attribute_splits", [])
            if lift is not None:
                effect_parts.append(f"Lift: {lift:+.1%}")
            if attribute_splits:
                top_split = attribute_splits[0]
                d = getattr(top_split, "effect_size", None)
                attr_name = getattr(top_split, "attribute", "")
                if d is not None:
                    effect_parts.append(
                        f"{attr_name.replace('_', ' ')} effect size: d={d:.2f}"
                    )

        with st.container(border=True):
            col_num, col_body = st.columns([0.06, 0.94])
            with col_num:
                st.markdown(
                    f"<div style='font-size:1.4rem; font-weight:700; "
                    f"color:#888; text-align:center; padding-top:6px;'>{position}</div>",
                    unsafe_allow_html=True,
                )
            with col_body:
                # Title row with badge
                badge_html = (
                    f"<span style='background:{badge['color']}22; color:{badge['color']}; "
                    f"border:1px solid {badge['color']}; border-radius:10px; "
                    f"padding:1px 9px; font-size:0.82rem; font-weight:600; "
                    f"margin-left:8px; display:inline-block;'>"
                    f"{badge['icon']} {badge['label']}</span>"
                )
                st.markdown(
                    f"<strong>{hyp_title}</strong>{badge_html}",
                    unsafe_allow_html=True,
                )

                # Confidence bar
                st.progress(min(confidence, 1.0), text=f"Confidence {confidence:.0%}")

                # Evidence snippet (from verdict)
                if evidence_snippet:
                    st.caption(f"**Verdict:** {evidence_snippet}")

                # Task 1: Probe evidence rows (detailed grounding)
                _PROBE_TYPE_ICON = {
                    "ATTRIBUTE": "📊",
                    "INTERVIEW": "🎤",
                    "SIMULATION": "🔬",
                }
                
                hyp_probes = [p for p in probes_list if getattr(p, "hypothesis_id", None) == hyp_id and getattr(p, "result", None) is not None]
                if hyp_probes:
                    for probe in sorted(hyp_probes, key=lambda p: getattr(p, "order", 0)):
                        r = probe.result
                        ptype_str = str(getattr(probe, "probe_type", "PROBE")).upper()
                        # Extract enum value if possible
                        if "." in ptype_str:
                            ptype_str = ptype_str.split(".")[-1]
                        
                        icon = _PROBE_TYPE_ICON.get(ptype_str, "🔍")
                        conf = getattr(r, "confidence", 0.0)
                        conf_bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
                        
                        st.caption(
                            f"{icon} **{ptype_str.title()}** — {conf:.0%} confidence  "
                            f"`{conf_bar}`"
                        )
                        
                        ev_summary = getattr(r, "evidence_summary", "")
                        if ev_summary:
                            st.caption(f"↳ {ev_summary[:180]}")
                if effect_parts:
                    chips_html = " ".join(
                        f"<span style='background:#FEF9E7; color:#7D6608; "
                        f"border:1px solid #F9E79F; border-radius:10px; "
                        f"padding:2px 9px; font-size:0.8rem; display:inline-block; "
                        f"margin-right:4px;'>{part}</span>"
                        for part in effect_parts
                    )
                    st.markdown(
                        f"<div style='margin-top:4px;'>{chips_html}</div>",
                        unsafe_allow_html=True,
                    )

                # Consistency score — only show if meaningful
                if consistency > 0.0:
                    st.caption(f"Consistency: {consistency:.0%}")

        # Accumulate evidence chain for session state
        if status in ("confirmed", "partially_confirmed"):
            evidence_chain_ids.append(hyp_id)


# ---------------------------------------------------------------------------
# 3.1. QUOTE BANK — Qualitative voices
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Representative Voices")
st.caption(
    "Persona responses from the investigation, organized by theme. "
    "These are simulated conversations grounded in each persona's full profile and behavior trajectory."
)

from src.probing.models import ProbeType

interview_probes = [
    p for p in probes_list
    if getattr(p, "probe_type", None) == ProbeType.INTERVIEW and getattr(p, "result", None) is not None
]

all_clusters = [c for p in interview_probes for c in p.result.response_clusters]
all_responses = [r for p in interview_probes for r in p.result.interview_responses]

if all_clusters:
    # Sort by persona count (most common themes first)
    sorted_clusters = sorted(all_clusters, key=lambda c: getattr(c, "persona_count", 0), reverse=True)

    for cluster in sorted_clusters[:5]:  # Cap at 5 themes
        theme_label = cluster.theme.replace("_", " ").title()
        pct_val = getattr(cluster, "percentage", 0.0)
        pct = f"{pct_val:.0%}" if pct_val <= 1.0 else f"{pct_val:.0f}%"

        with st.expander(f"**{theme_label}** — {getattr(cluster, 'persona_count', 0)} personas ({pct})", expanded=False):
            st.caption(getattr(cluster, "description", ""))
            quotes = getattr(cluster, "representative_quotes", [])
            if quotes:
                for quote in quotes[:3]:
                    st.markdown(f"> *{quote[:280]}*")
                    st.caption("")

elif all_responses:
    st.caption("Individual persona responses from the investigation:")
    for resp in all_responses[:6]:
        outcome_icon = "✅" if getattr(resp, "outcome", "") == "adopt" else "❌"
        with st.container(border=True):
            st.caption(f"**{getattr(resp, 'persona_name', 'Persona')}** {outcome_icon}")
            st.markdown(f"> *{getattr(resp, 'content', '')[:300]}*")

else:
    st.info(
        "No interview probes were run during this investigation. "
        "Interview evidence appears when the probing tree includes interview-type probes.",
        icon="ℹ️",
    )

# ---------------------------------------------------------------------------
# 4. MAGIC MOMENT — green insight callout
# ---------------------------------------------------------------------------

# Build cohort size string from cohorts.summary total if available
cohort_size_str: str = ""
if cohorts is not None:
    summary_dict: dict = getattr(cohorts, "summary", {})
    total = sum(summary_dict.values()) if isinstance(summary_dict, dict) else 0
    if total:
        cohort_size_str = f"<strong>{total:,}</strong>"

magic_text = (
    f"The data points to <strong>{dominant_hypothesis_title}</strong> as the primary barrier"
    + (f" — affecting {cohort_size_str} of your target households." if cohort_size_str else ".")
)

render_magic_moment("Key Insight", magic_text)

# ---------------------------------------------------------------------------
# 5. SYNTHESIS NARRATIVE — full text in expander
# ---------------------------------------------------------------------------

with st.expander("Read full synthesis", expanded=False):
    if orchestration is not None:
        orch_narrative: str = getattr(orchestration, "synthesis_narrative", "")
        if orch_narrative:
            st.markdown(orch_narrative)
        else:
            st.markdown(synthesis_narrative_text or "_No synthesis narrative available._")
    elif synthesis_narrative_text:
        st.markdown(synthesis_narrative_text)
    else:
        st.markdown("_No synthesis narrative available._")

    # Recommended actions from TreeSynthesis (bonus — available if synthesis ran)
    recommended_actions: list[str] = (
        getattr(synthesis, "recommended_actions", []) if synthesis is not None else []
    )
    if recommended_actions:
        st.markdown("**Recommended actions:**")
        for action in recommended_actions:
            st.markdown(f"- {action}")

# ---------------------------------------------------------------------------
# 6. WRITE TO SESSION STATE
# ---------------------------------------------------------------------------

st.session_state["core_finding"] = {
    "finding_text": core_finding_text,
    "scenario_id": scenario_id,
    "dominant_hypothesis": str(dominant_hypothesis_id),
    "dominant_hypothesis_title": dominant_hypothesis_title,
    "evidence_chain": evidence_chain_ids,
    "overall_confidence": overall_confidence,
    "hypotheses_tested": hypotheses_tested,
    "hypotheses_confirmed": hypotheses_confirmed,
}

# ---------------------------------------------------------------------------
# 7. JSON EXPORT
# ---------------------------------------------------------------------------

st.divider()

st.download_button(
    label="Export Core Finding (JSON)",
    data=json.dumps(st.session_state["core_finding"], indent=2),
    file_name=f"{scenario_id}_core_finding.json",
    mime="application/json",
)

# ---------------------------------------------------------------------------
# 7.1. TEXT BRIEF EXPORT
# ---------------------------------------------------------------------------

# Re-sort hypotheses for export (confirmed first)
sorted_hyps_export = sorted(
    [h for h in hypotheses_list if verdicts.get(h.id)],
    key=lambda h: (
        0 if verdicts[h.id].status == "confirmed" else
        1 if verdicts[h.id].status == "partially_confirmed" else 2
    )
)

_evidence_lines = []
for hyp in sorted_hyps_export:
    v = verdicts.get(hyp.id)
    if v and v.status in ("confirmed", "partially_confirmed"):
        _evidence_lines.append(f"\n{hyp.title} ({v.status.replace('_', ' ').title()}, {v.confidence:.0%} confidence)")
        ev_summary = getattr(v, "evidence_summary", "")
        if ev_summary:
            _evidence_lines.append(f"  {ev_summary[:300]}")

_top_quotes = []
if all_clusters:
    for cluster in sorted(all_clusters, key=lambda c: getattr(c, "persona_count", 0), reverse=True)[:3]:
        quotes = getattr(cluster, "representative_quotes", [])
        if quotes:
            _top_quotes.append(f"\"{quotes[0][:200]}\"")
elif all_responses:
    for resp in all_responses[:3]:
        content = getattr(resp, "content", "")
        if content:
             _top_quotes.append(f"\"{content[:200]}\"")

brief_text = f"""CORE FINDING
{'-' * 60}
{core_finding_text}

EVIDENCE CHAIN
{'-' * 60}
{''.join(_evidence_lines) or 'No detailed evidence found.'}

REPRESENTATIVE VOICES
{'-' * 60}
{chr(10).join(_top_quotes) or 'No interview evidence available.'}

Generated by LittleJoys Persona Simulation Engine
Scenario: {scenario_id}
"""

st.download_button(
    label="⬇️ Download Finding Brief (.txt)",
    data=brief_text,
    file_name=f"{scenario_id}_core_finding.txt",
    mime="text/plain",
)

# ---------------------------------------------------------------------------
# 8. PROCEED BUTTON
# ---------------------------------------------------------------------------

st.divider()

if st.button("Proceed to Interventions →", type="primary", use_container_width=True):
    st.switch_page("pages/5_intervention.py")
