"""Streamlit persona summary card — fields aligned with ``src.taxonomy.schema.Persona``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import streamlit as st

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


def render_persona_card(persona: Persona, decision_result: dict[str, Any] | None = None) -> None:
    """Render a bordered card with demographics, psychographics, and optional funnel outcome."""

    city = persona.demographics.city_name
    tier = persona.demographics.city_tier
    header = f"{persona.id} — {city} ({tier})"

    with st.container(border=True):
        st.subheader(header)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Demographics**")
            st.write(f"- Income: {persona.demographics.household_income_lpa} LPA")
            st.write(f"- Parent age: {persona.demographics.parent_age}")
            st.write(f"- Children: {persona.demographics.num_children}")
            st.write(f"- Region: {persona.demographics.region}")
        with c2:
            st.markdown("**Psychographics**")
            st.write(f"- Health consciousness: {persona.health.diet_consciousness:.2f}")
            st.write(f"- Brand loyalty: {persona.values.brand_loyalty_tendency:.2f}")
            st.write(f"- Social proof: {persona.psychology.social_proof_bias:.2f}")

        if decision_result is not None:
            st.divider()
            outcome = decision_result.get("outcome")
            if outcome == "adopt":
                st.success("Outcome: Adopted")
            else:
                stage = decision_result.get("rejection_stage") or "unknown"
                reason = decision_result.get("rejection_reason") or "unknown"
                st.error(f"Outcome: Rejected at {stage} ({reason})")
