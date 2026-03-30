"""Streamlit persona summary card — fields aligned with ``src.taxonomy.schema.Persona``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import streamlit as st

from src.utils.display import (
    city_tier_label,
    display_name,
    outcome_label,
    persona_display_name,
    qualitative_level,
    rejection_reason_label,
    stage_label,
)

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


def render_persona_card(persona: Persona, decision_result: dict[str, Any] | None = None) -> None:
    """Render a bordered card with demographics, psychographics, and optional funnel outcome."""

    city = persona.demographics.city_name
    tier = city_tier_label(persona.demographics.city_tier)
    header = f"{persona_display_name(persona)} · {persona.id} — {city} ({tier})"

    with st.container(border=True):
        st.subheader(header)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Demographics**")
            st.write(
                f"- {display_name('household_income_lpa')}: ₹{persona.demographics.household_income_lpa:.1f}L",
            )
            st.write(f"- {display_name('parent_age')}: {persona.demographics.parent_age}")
            st.write(f"- {display_name('num_children')}: {persona.demographics.num_children}")
            st.write(f"- {display_name('region')}: {persona.demographics.region}")
        with c2:
            st.markdown("**Psychographics**")
            st.write(
                f"- {display_name('diet_consciousness')}: "
                f"{qualitative_level(persona.health.diet_consciousness)}",
            )
            st.write(
                f"- {display_name('brand_loyalty_tendency')}: "
                f"{qualitative_level(persona.values.brand_loyalty_tendency)}",
            )
            st.write(
                f"- {display_name('social_proof_bias')}: "
                f"{qualitative_level(persona.psychology.social_proof_bias)}",
            )

        if decision_result is not None:
            st.divider()
            outcome = decision_result.get("outcome")
            if outcome == "adopt":
                st.success(f"{display_name('outcome')}: {outcome_label('adopt')}")
            else:
                stage = decision_result.get("rejection_stage") or "unknown"
                reason = decision_result.get("rejection_reason") or "unknown"
                st.error(
                    f"{display_name('outcome')}: {outcome_label(str(outcome))} — "
                    f"{display_name('rejection_stage')}: {stage_label(str(stage))}; "
                    f"{display_name('rejection_reason')}: {rejection_reason_label(str(reason))}",
                )
