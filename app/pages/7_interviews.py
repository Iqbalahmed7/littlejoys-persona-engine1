# ruff: noqa: N999
"""Interview Deep-Dive page.

This page renders qualitative evidence from deep persona interviews.
It is driven by ``research_result`` stored in ``st.session_state``.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import streamlit as st

from app.components.persona_spider import render_persona_spider
from app.utils.demo_mode import ensure_demo_data
from src.probing.clustering import cluster_responses_mock
from src.utils.display import city_tier_label, interview_reason_label, persona_display_name

st.header("Interview Deep-Dive")
st.caption("Explore the qualitative evidence from deep persona interviews.")

demo_mode = False

if demo_mode:
    ensure_demo_data()

if "research_result" not in st.session_state:
    st.warning(
        "No research results available. Run a research pipeline from the Research Design page."
    )
    st.page_link("pages/2_research.py", label="Go to Research Design →")
    st.stop()

result = st.session_state["research_result"]
pop = st.session_state.population


st.subheader("Smart Sample")
st.caption(f"{len(result.smart_sample.selections)} personas selected for deep interviews.")

reason_counts = Counter(s.selection_reason for s in result.smart_sample.selections)
if reason_counts:
    reason_cols = st.columns(len(reason_counts))
    for i, (reason, count) in enumerate(reason_counts.most_common()):
        label = reason.replace("_", " ").title()
        reason_cols[i].metric(label, count)


st.subheader("Interview Responses")
for ir in result.interview_results:
    persona = pop.get_persona(ir.persona_id)
    decision = result.primary_funnel.results_by_persona.get(ir.persona_id, {})
    outcome = decision.get("outcome", "unknown")
    outcome_label = "Would try" if outcome == "adopt" else "Wouldn't try"

    with st.expander(
        f"{persona_display_name(persona)} · {outcome_label} · Reason: {interview_reason_label(ir.selection_reason)}",
        expanded=False,
    ):
        p1, p2, p3 = st.columns(3)
        p1.caption(f"City: {city_tier_label(persona.demographics.city_tier)}")
        p2.caption(f"Income: ₹{persona.demographics.household_income_lpa:.1f}L")
        p3.caption(f"Child age: {persona.demographics.youngest_child_age}")

        for qa in ir.responses:
            st.markdown(f"**Q:** {qa['question']}")
            st.markdown(f"**A:** {qa['answer']}")
            st.divider()


st.subheader("Response Themes")
st.caption("Keyword-based clustering of all interview responses.")

responses: list[tuple[Any, str]] = []
for ir in result.interview_results:
    persona = pop.get_persona(ir.persona_id)
    combined_text = " ".join(r["answer"] for r in ir.responses)
    responses.append((persona, combined_text))

clusters = cluster_responses_mock(responses)  # type: ignore[arg-type]

if clusters:
    for cluster in clusters:
        theme_label = cluster.theme.replace("_", " ").title()
        st.markdown(
            f"**{theme_label}** — {cluster.persona_count} personas ({cluster.percentage:.0%})"
        )
        st.caption(cluster.description)
        if cluster.representative_quotes:
            for quote in cluster.representative_quotes[:2]:
                st.markdown(f"> {quote[:250]}")
        st.divider()
else:
    st.caption("Not enough interview data for clustering.")


if len(result.interview_results) >= 2:
    st.subheader("Compare Personas")
    st.caption("Select 2 personas to compare their psychographic profiles side-by-side.")

    interviewed_ids = [ir.persona_id for ir in result.interview_results]
    interviewed_labels = {
        pid: persona_display_name(pop.get_persona(pid)) for pid in interviewed_ids
    }

    compare_cols = st.columns(2)
    with compare_cols[0]:
        left_id = st.selectbox(
            "Persona A",
            interviewed_ids,
            format_func=lambda x: interviewed_labels[x],
            index=0,
            key="compare_left",
        )
    with compare_cols[1]:
        right_id = st.selectbox(
            "Persona B",
            interviewed_ids,
            format_func=lambda x: interviewed_labels[x],
            index=min(1, len(interviewed_ids) - 1),
            key="compare_right",
        )

    if left_id and right_id:
        spider_cols = st.columns(2)
        with spider_cols[0]:
            render_persona_spider(pop.get_persona(left_id), key="compare_a")
        with spider_cols[1]:
            render_persona_spider(pop.get_persona(right_id), key="compare_b")
