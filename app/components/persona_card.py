import streamlit as st


def render_persona_card(persona, decision_result=None):
    with st.container(border=True):
        st.subheader(f"{persona.demographics.name} ({persona.demographics.age})")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Demographics**")
            st.write(f"- Location: {persona.demographics.location.city.title()}")
            st.write(f"- Income (LPA): {persona.financials.household_income_lpa}")
            st.write(f"- Work: {persona.financials.work_environment.title()}")
        with c2:
            st.markdown("**Psychographics**")
            st.write(f"- Social Proof Bias: {persona.psychology.social_proof_bias:.2f}")
            st.write(f"- Time Scarcity: {persona.psychology.perceived_time_scarcity:.2f}")
            st.write(f"- Deal Seeking: {persona.financials.deal_seeking_behavior:.2f}")

        if decision_result:
            st.divider()
            if decision_result.outcome == "adopt":
                st.success("Outcome: Adopted")
            else:
                st.error(
                    f"Outcome: Rejected at {decision_result.rejection_stage} ({decision_result.rejection_reason})"
                )
