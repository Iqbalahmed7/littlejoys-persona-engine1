# ruff: noqa: N999
import copy

import streamlit as st
import structlog

from src.constants import SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.simulation.static import run_static_simulation

log = structlog.get_logger(__name__)

st.set_page_config(page_title="Scenario Configurator", page_icon="🎛️", layout="wide")
st.header("Scenario Configurator")
st.caption("Adjust scenario variables and run simulations manually.")

if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()

if "scenario_results" not in st.session_state:
    st.session_state.scenario_results = {}

# 1. Scenario selector
scenario_id = st.selectbox(
    "Select Base Scenario",
    SCENARIO_IDS,
    format_func=lambda sid: f"{get_scenario(sid).name} ({sid})",
)

base_scenario = get_scenario(scenario_id)
st.markdown(f"**Description**: {base_scenario.description}")

# Maintain a localized custom copy in session state to handle resets
session_key = f"custom_scenario_{scenario_id}"
if session_key not in st.session_state:
    st.session_state[session_key] = copy.deepcopy(base_scenario)

# 8. Reset button
if st.button("Reset to Defaults"):
    st.session_state[session_key] = copy.deepcopy(base_scenario)
    st.toast("Settings restored to defaults", icon="🔄")

custom_scenario = st.session_state[session_key]

st.divider()

col1, col2 = st.columns(2)

# 2. Product parameters
with col1:
    st.subheader("Product Parameters")
    custom_scenario.product.price_inr = st.slider(
        "Price (INR)", 100.0, 1500.0, float(custom_scenario.product.price_inr), step=50.0
    )
    custom_scenario.product.taste_appeal = st.slider(
        "Taste Appeal", 0.0, 1.0, float(custom_scenario.product.taste_appeal), step=0.05
    )
    custom_scenario.product.effort_to_acquire = st.slider(
        "Effort to Acquire", 0.0, 1.0, float(custom_scenario.product.effort_to_acquire), step=0.05
    )
    custom_scenario.product.clean_label_score = st.slider(
        "Clean Label Score", 0.0, 1.0, float(custom_scenario.product.clean_label_score), step=0.05
    )
    custom_scenario.product.health_relevance = st.slider(
        "Health Relevance", 0.0, 1.0, float(custom_scenario.product.health_relevance), step=0.05
    )
    custom_scenario.lj_pass_available = st.toggle(
        "LJ Pass Available", custom_scenario.lj_pass_available
    )

# 3. Marketing parameters
with col2:
    st.subheader("Marketing Parameters")
    custom_scenario.marketing.awareness_budget = st.slider(
        "Awareness Budget", 0.0, 1.0, float(custom_scenario.marketing.awareness_budget)
    )
    custom_scenario.marketing.awareness_level = st.slider(
        "Awareness Level", 0.0, 1.0, float(custom_scenario.marketing.awareness_level)
    )
    custom_scenario.marketing.trust_signal = st.slider(
        "Trust Signal", 0.0, 1.0, float(custom_scenario.marketing.trust_signal)
    )
    custom_scenario.marketing.social_proof = st.slider(
        "Social Proof", 0.0, 1.0, float(custom_scenario.marketing.social_proof)
    )
    custom_scenario.marketing.expert_endorsement = st.slider(
        "Expert Endorsement", 0.0, 1.0, float(custom_scenario.marketing.expert_endorsement)
    )
    custom_scenario.marketing.discount_available = float(
        st.slider(
            "Discount Available", 0.0, 0.5, float(custom_scenario.marketing.discount_available)
        )
    )

st.divider()

# 4. Channel mix
st.subheader("Channel Mix")
st.caption("Sum must equal 1.0")
channels = ["instagram", "youtube", "whatsapp"]
mix_cols = st.columns(3)
mix_sum = 0.0

for i, ch in enumerate(channels):
    with mix_cols[i]:
        val = st.slider(
            ch.title(),
            0.0,
            1.0,
            float(custom_scenario.marketing.channel_mix.get(ch, 0.0)),
            step=0.05,
            key=f"slider_{ch}",
        )
        custom_scenario.marketing.channel_mix[ch] = val
        mix_sum += val

if mix_sum > 1.05 or mix_sum < 0.95:
    st.error(f"Invalid mix sum ({mix_sum:.2f}). Please adjust sliders to sum to ~1.0.")

# 5. Toggles
st.subheader("Campaign Toggles")
t1, t2, t3 = st.columns(3)
with t1:
    custom_scenario.marketing.school_partnership = st.toggle(
        "School Partnership", custom_scenario.marketing.school_partnership
    )
with t2:
    custom_scenario.marketing.pediatrician_endorsement = st.toggle(
        "Pediatrician Endorsement", custom_scenario.marketing.pediatrician_endorsement
    )
with t3:
    custom_scenario.marketing.influencer_campaign = st.toggle(
        "Influencer Campaign", custom_scenario.marketing.influencer_campaign
    )

st.divider()

# 6. Side-by-side comparison
st.subheader("Scenario Comparison")
cmp1, cmp2 = st.columns(2)
with cmp1:
    st.markdown("**Original Defaults**")
    st.json(base_scenario.model_dump())
with cmp2:
    st.markdown("**Current Configuration**")
    st.json(custom_scenario.model_dump())

st.divider()

# 7. Run button
if st.button("Run Simulation", type="primary", use_container_width=True):
    if mix_sum > 1.05 or mix_sum < 0.95:
        st.error("Cannot run simulation with unbalanced channel mix.")
    else:
        with st.spinner("Running simulation on population..."):
            res = run_static_simulation(st.session_state.population, custom_scenario)
            st.session_state.scenario_results[scenario_id] = res
            st.toast("Simulation complete and cached in session_state!", icon="✅")
            st.success(
                f"Results recorded! Adoption: {res.adoption_count} / {res.population_size} ({res.adoption_rate:.1%})"
            )
