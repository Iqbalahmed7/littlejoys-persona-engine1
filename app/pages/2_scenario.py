# ruff: noqa: N999
from __future__ import annotations

import copy

import streamlit as st
import structlog

from src.constants import SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.simulation.static import run_static_simulation
from src.utils.display import CHANNEL_HELP

log = structlog.get_logger(__name__)

st.set_page_config(page_title="Scenario Configurator", page_icon="🎛️", layout="wide")
st.header("Scenario Configurator")
st.caption(
    "Configure the market conditions for your product. These become the **baseline** "
    "that the Results and Counterfactual pages analyse. Adjust parameters to model "
    "different launch strategies."
)

if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()

if "scenario_results" not in st.session_state:
    st.session_state.scenario_results = {}

scenario_id = st.selectbox(
    "Select Base Scenario",
    SCENARIO_IDS,
    format_func=lambda sid: f"{get_scenario(sid).name} ({sid})",
    help="Choose which product story you are configuring. Each scenario has its own default "
    "price, audience, and marketing mix.",
)

base_scenario = get_scenario(scenario_id)
st.markdown(f"**Description**: {base_scenario.description}")

session_key = f"custom_scenario_{scenario_id}"
if session_key not in st.session_state:
    st.session_state[session_key] = copy.deepcopy(base_scenario)

if st.button(
    "Reset to Defaults",
    help="Restore all sliders and toggles to the built-in defaults for the selected scenario.",
):
    st.session_state[session_key] = copy.deepcopy(base_scenario)
    st.toast("Settings restored to defaults", icon="🔄")

custom_scenario = st.session_state[session_key]

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Product Parameters")
    custom_scenario.product.price_inr = st.slider(
        "Price (INR)",
        100.0,
        1500.0,
        float(custom_scenario.product.price_inr),
        step=50.0,
        help=(
            "Retail price of the product. Lower prices reduce the purchase barrier, "
            "especially for budget-conscious (SEC B2+) families. "
            "Reference: Nutrimix ₹599, Gummies ₹499, Protein Mix ₹699."
        ),
    )
    custom_scenario.product.taste_appeal = st.slider(
        "Taste Appeal",
        0.0,
        1.0,
        float(custom_scenario.product.taste_appeal),
        step=0.05,
        help=(
            "How likely children are to accept the taste and format. "
            "0.0 = most kids refuse, 1.0 = kids ask for it. "
            "Gummy formats score 0.8+, powders 0.4-0.6."
        ),
    )
    custom_scenario.product.effort_to_acquire = st.slider(
        "Effort to Acquire",
        0.0,
        1.0,
        float(custom_scenario.product.effort_to_acquire),
        step=0.05,
        help=(
            "Friction to obtain AND use the product. "
            "0.0 = buy and consume instantly (ready-to-drink), "
            "1.0 = requires multiple steps (cook into a recipe). "
            "High effort hurts busy parents most."
        ),
    )
    custom_scenario.product.clean_label_score = st.slider(
        "Clean Label Score",
        0.0,
        1.0,
        float(custom_scenario.product.clean_label_score),
        step=0.05,
        help=(
            "How 'natural' the ingredient list looks to a parent scanning the pack. "
            "0.0 = synthetic-looking (E-numbers, preservatives), "
            "1.0 = recognisable whole ingredients."
        ),
    )
    custom_scenario.product.health_relevance = st.slider(
        "Health Relevance",
        0.0,
        1.0,
        float(custom_scenario.product.health_relevance),
        step=0.05,
        help=(
            "How clearly this product solves a perceived health need. "
            "0.0 = nice-to-have wellness, "
            "1.0 = doctor-recommended for a specific condition."
        ),
    )
    custom_scenario.lj_pass_available = st.toggle(
        "LJ Pass Available",
        custom_scenario.lj_pass_available,
        help=(
            "Whether a subscription/loyalty pass is offered. "
            "Reduces repeat-purchase friction and increases retention for habit-forming products."
        ),
    )

with col2:
    st.subheader("Marketing Parameters")
    custom_scenario.marketing.awareness_budget = st.slider(
        "Awareness Budget",
        0.0,
        1.0,
        float(custom_scenario.marketing.awareness_budget),
        help=(
            "Marketing spend reaching target parents. "
            "0.0 = no marketing, 1.0 = saturated coverage. "
            "New products typically start at 0.2-0.3."
        ),
    )
    custom_scenario.marketing.awareness_level = st.slider(
        "Awareness Level",
        0.0,
        1.0,
        float(custom_scenario.marketing.awareness_level),
        help=(
            "What fraction of target parents have heard of this product. "
            "Distinct from budget — a viral moment can create high awareness at low budget."
        ),
    )
    custom_scenario.marketing.trust_signal = st.slider(
        "Trust Signal",
        0.0,
        1.0,
        float(custom_scenario.marketing.trust_signal),
        help=(
            "Overall brand credibility. Combines packaging quality, brand story, "
            "certifications, and social proof. New D2C brands start around 0.3-0.4."
        ),
    )
    custom_scenario.marketing.social_proof = st.slider(
        "Social Proof",
        0.0,
        1.0,
        float(custom_scenario.marketing.social_proof),
        help=(
            "Visible evidence that other parents use this product. "
            "Reviews, ratings, 'X mothers trust us' claims. "
            "Strongly influences community-oriented parents."
        ),
    )
    custom_scenario.marketing.expert_endorsement = st.slider(
        "Expert Endorsement",
        0.0,
        1.0,
        float(custom_scenario.marketing.expert_endorsement),
        help=(
            "Professional credibility signals — doctor recommendations, clinical studies "
            "cited on packaging, dietitian partnerships."
        ),
    )
    custom_scenario.marketing.discount_available = float(
        st.slider(
            "Discount Available",
            0.0,
            0.5,
            float(custom_scenario.marketing.discount_available),
            help=(
                "Active promotional discount (0.0 = full price, 0.5 = 50% off). "
                "Temporary discounts boost trial but may not sustain repeat purchase."
            ),
        )
    )

st.divider()

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
            help=CHANNEL_HELP.get(ch, ""),
        )
        custom_scenario.marketing.channel_mix[ch] = val
        mix_sum += val

if mix_sum > 1.05 or mix_sum < 0.95:
    st.error(f"Invalid mix sum ({mix_sum:.2f}). Please adjust sliders to sum to ~1.0.")

st.subheader("Campaign Toggles")
t1, t2, t3 = st.columns(3)
with t1:
    custom_scenario.marketing.school_partnership = st.toggle(
        "School Partnership",
        custom_scenario.marketing.school_partnership,
        help=(
            "Product distributed or endorsed through schools. "
            "High-trust channel that bypasses digital ad skepticism. "
            "Especially effective for 7-14 age group."
        ),
    )
with t2:
    custom_scenario.marketing.pediatrician_endorsement = st.toggle(
        "Pediatrician Endorsement",
        custom_scenario.marketing.pediatrician_endorsement,
        help=(
            "Formal endorsement from pediatricians. "
            "The single strongest trust signal for health-anxious parents."
        ),
    )
with t3:
    custom_scenario.marketing.influencer_campaign = st.toggle(
        "Influencer Campaign",
        custom_scenario.marketing.influencer_campaign,
        help=(
            "Parenting influencer partnerships on Instagram/YouTube. "
            "Effective for digitally-active Tier 1 parents, less impact in Tier 2-3."
        ),
    )

st.divider()

st.subheader("Scenario Comparison")
cmp1, cmp2 = st.columns(2)
with cmp1:
    st.markdown("**Original Defaults**")
    st.json(base_scenario.model_dump())
with cmp2:
    st.markdown("**Current Configuration**")
    st.json(custom_scenario.model_dump())

st.divider()

if st.button(
    "Run Simulation",
    type="primary",
    use_container_width=True,
    help="Run the static funnel on your loaded population and save results for Results and "
    "Population charts.",
):
    if mix_sum > 1.05 or mix_sum < 0.95:
        st.error("Cannot run simulation with unbalanced channel mix.")
    else:
        with st.spinner("Running simulation on population..."):
            res = run_static_simulation(st.session_state.population, custom_scenario)
            st.session_state.scenario_results[scenario_id] = res
            st.toast("Simulation complete and cached in session_state!", icon="✅")
            st.success(
                f"Results recorded! Adoption: {res.adoption_count} / {res.population_size} "
                f"({res.adoption_rate:.1%})"
            )
