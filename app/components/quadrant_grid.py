"""Reusable 2x2 intervention quadrant grid component."""

import streamlit as st

from src.analysis.intervention_engine import InterventionQuadrant
from src.utils.display import cohort_label

_QUADRANT_LABELS = {
    "general_temporal": ("General", "Temporal"),
    "general_non_temporal": ("General", "Non-temporal"),
    "cohort_temporal": ("Cohort-specific", "Temporal"),
    "cohort_non_temporal": ("Cohort-specific", "Non-temporal"),
}


def render_quadrant_grid(quadrant: InterventionQuadrant) -> None:
    """Render a 2x2 grid of intervention cards in Streamlit."""
    # Row 1: Temporal
    st.markdown("### Temporal interventions")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**General**")
        for intervention in quadrant.quadrants.get("general_temporal", []):
            with st.container(border=True):
                st.markdown(f"**{intervention.name}**")
                st.caption(intervention.description)
                st.caption(f"Mechanism: {intervention.expected_mechanism}")
    with col2:
        st.markdown("**Cohort-specific**")
        for intervention in quadrant.quadrants.get("cohort_temporal", []):
            with st.container(border=True):
                st.markdown(f"**{intervention.name}**")
                st.caption(intervention.description)
                st.caption(f"Target: {cohort_label(intervention.target_cohort_id)}")
                st.caption(f"Mechanism: {intervention.expected_mechanism}")

    # Row 2: Non-temporal
    st.markdown("### Non-temporal interventions")
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**General**")
        for intervention in quadrant.quadrants.get("general_non_temporal", []):
            with st.container(border=True):
                st.markdown(f"**{intervention.name}**")
                st.caption(intervention.description)
                st.caption(f"Mechanism: {intervention.expected_mechanism}")
    with col4:
        st.markdown("**Cohort-specific**")
        for intervention in quadrant.quadrants.get("cohort_non_temporal", []):
            with st.container(border=True):
                st.markdown(f"**{intervention.name}**")
                st.caption(intervention.description)
                st.caption(f"Target: {cohort_label(intervention.target_cohort_id)}")
                st.caption(f"Mechanism: {intervention.expected_mechanism}")

    total = sum(len(v) for v in quadrant.quadrants.values())
    st.caption(f"{total} interventions across 4 quadrants")
