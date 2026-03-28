import pandas as pd
import plotly.express as px

# ruff: noqa: N999
import streamlit as st

from src.constants import SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.simulation.counterfactual import (
    get_predefined_counterfactuals,
    run_counterfactual,
    run_predefined_counterfactual,
)

st.set_page_config(page_title="Counterfactual Analysis", page_icon="⚖️", layout="wide")
st.header("Counterfactual Analysis")
st.caption("Compare alternative scenarios and interventions against the baseline.")

if "population" not in st.session_state:
    st.info("No data loaded. Click Generate to create a population.")
    st.stop()

if "cf_history" not in st.session_state:
    st.session_state.cf_history = []  # List of CounterfactualResult objects

st.subheader("1. Baseline Scenario")
scenario_id = st.selectbox(
    "Select Baseline", SCENARIO_IDS, format_func=lambda sid: f"{get_scenario(sid).name} ({sid})"
)

predefined = get_predefined_counterfactuals(scenario_id)

st.subheader("2. Predefined Interventions")
if not predefined:
    st.write("No predefined counterfactuals available for this scenario.")
else:
    cols = st.columns(len(predefined))
    for i, (cf_name, mods) in enumerate(predefined.items()):
        with cols[i], st.container(border=True):
            st.markdown(f"**{cf_name.replace('_', ' ').title()}**")
            st.caption(f"Changes: {list(mods.keys())}")
            if st.button(f"Run {cf_name}", key=cf_name, use_container_width=True):
                with st.spinner(f"Running {cf_name}..."):
                    res = run_predefined_counterfactual(
                        st.session_state.population, scenario_id, cf_name
                    )
                    st.session_state.cf_history.append(res)
                    st.toast(f"Counterfactual {cf_name} completed!", icon="✅")

st.subheader("3. Custom What-If")
with st.expander("Configure Custom Intervention"):
    c1, c2 = st.columns(2)
    with c1:
        custom_price = st.number_input("Override Price (INR)", value=0.0, step=10.0)
    with c2:
        custom_budget = st.number_input("Override Awareness Budget", value=-1.0, step=0.1)

    if st.button("Run Custom Counterfactual", type="secondary"):
        mods = {}
        if custom_price > 0:
            mods["product.price_inr"] = custom_price
        if custom_budget >= 0.0:
            mods["marketing.awareness_budget"] = custom_budget

        if mods:
            with st.spinner("Running custom counterfactual..."):
                res = run_counterfactual(
                    st.session_state.population, get_scenario(scenario_id), mods, "Custom"
                )
                st.session_state.cf_history.append(res)
                st.toast("Custom counterfactual completed!", icon="✅")
        else:
            st.warning("No modifications applied. Adjust parameters before running.")

st.divider()

if not st.session_state.cf_history:
    st.info("Run a counterfactual to see comparison and lift results.")
    st.stop()

# Get the latest result
latest = st.session_state.cf_history[-1]

st.subheader("Latest Comparison: Baseline vs Counterfactual")
st.markdown(f"**Intervention: {latest.counterfactual_name}**")

c_base, c_cf, c_lift = st.columns(3)
with c_base:
    st.metric("Baseline Adoption Rate", f"{latest.baseline_adoption_rate:.2%}")
with c_cf:
    st.metric(
        "Counterfactual Adoption Rate",
        f"{latest.counterfactual_adoption_rate:.2%}",
        delta=f"{latest.absolute_lift:.2%}",
    )
with c_lift:
    st.metric("Absolute Lift", f"{latest.absolute_lift:.2%}")

st.subheader("Segment Impact")
if latest.most_affected_segments:
    # Build dataframe
    df = pd.DataFrame([s.model_dump() for s in latest.most_affected_segments])
    st.dataframe(df, use_container_width=True)
else:
    st.write("No segments heavily impacted in this run.")

st.subheader("Cumulative Lift Visualization")
# Build a chart of all history
history_df = pd.DataFrame(
    [
        {
            "Intervention": f"{i}. {r.counterfactual_name}",
            "Absolute Lift": r.absolute_lift,
            "Relative Lift %": r.relative_lift_percent,
        }
        for i, r in enumerate(st.session_state.cf_history, 1)
    ]
)

fig = px.bar(
    history_df,
    x="Intervention",
    y="Absolute Lift",
    title="Absolute Lift by Intervention Tracked History",
    text_auto=".2%",
)
st.plotly_chart(fig, use_container_width=True)
