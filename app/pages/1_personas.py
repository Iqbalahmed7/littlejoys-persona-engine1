# ruff: noqa: N999
"""Compact personas dashboard for browsing the synthetic population."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.persona_card import render_persona_card
from app.components.persona_spider import render_persona_spider
from app.utils.demo_mode import ensure_demo_data
from src.constants import SCENARIO_IDS
from src.utils.display import city_tier_label, display_name


def _income_bracket(flat: dict) -> str:
    income = flat.get("household_income_lpa", 0)
    if not isinstance(income, (int, float)):
        return "unknown"
    if income <= 8.0:
        return "low_income"
    if income <= 15.0:
        return "middle_income"
    return "high_income"


st.header("Personas")
st.caption("Browse your synthetic population. Use filters to explore segments.")

demo_mode = st.sidebar.toggle(
    "Demo Mode",
    value=st.session_state.get("demo_mode", False),
    key="demo_mode",
)
if demo_mode:
    st.sidebar.caption("🎯 Demo Mode Active")
st.sidebar.caption("1️⃣ Personas — Explore synthetic households")
st.sidebar.caption("2️⃣ Research — Run scenario research")
st.sidebar.caption("3️⃣ Results — View research results")
st.sidebar.caption("4️⃣ Diagnose — Phase A problem decomposition")
st.sidebar.caption("5️⃣ Simulate — Phase C intervention testing")
st.sidebar.caption("6️⃣ Interviews — Deep dive conversations")
st.sidebar.caption("7️⃣ Comparison — Compare two scenarios")

if demo_mode:
    ensure_demo_data()

if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()

pop = st.session_state.population

m1, m2, m3 = st.columns(3)
m1.metric("Personas", len(pop.personas))
if not demo_mode:
    m2.metric("With Narratives", sum(1 for p in pop.personas if p.narrative))
m3.metric("Scenarios Available", len(SCENARIO_IDS))

st.subheader("Population Overview")

df = pop.to_dataframe().copy()

c1, c2 = st.columns(2)
with c1:
    tier_counts = df["city_tier"].value_counts().reset_index()
    tier_counts.columns = ["City Tier", "Count"]
    tier_counts["City Tier"] = tier_counts["City Tier"].apply(city_tier_label)
    fig = px.bar(tier_counts, x="City Tier", y="Count", title="City Tier Distribution")
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    bins = [0, 5, 10, 20, 50, 100]
    labels = ["<5L", "5-10L", "10-20L", "20-50L", "50L+"]
    df["income_bracket"] = pd.cut(
        df["household_income_lpa"],
        bins=bins,
        labels=labels,
        right=False,
    )
    income_counts = df["income_bracket"].value_counts().sort_index().reset_index()
    income_counts.columns = ["Income Bracket", "Count"]
    fig = px.bar(income_counts, x="Income Bracket", y="Count", title="Income Distribution")
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    fam_counts = df["family_structure"].map(display_name).value_counts().reset_index()
    fam_counts.columns = ["Family Structure", "Count"]
    fig = px.bar(fam_counts, x="Family Structure", y="Count", title="Family Structure")
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

with c4:

    def age_group(age: object) -> str:
        if pd.isna(age):
            return "Unknown"
        age = float(age)
        if age <= 5:
            return "Toddler (2-5)"
        if age <= 10:
            return "School-age (6-10)"
        return "Pre-teen (11-14)"

    df["age_group"] = df["youngest_child_age"].apply(age_group)
    age_counts = df["age_group"].value_counts().reset_index()
    age_counts.columns = ["Age Group", "Count"]
    fig = px.bar(age_counts, x="Age Group", y="Count", title="Youngest Child Age")
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Explore Segments")
st.caption("Select filters to drill down. Empty = show all.")

f1, f2, f3, f4 = st.columns(4)
with f1:
    sel_tier = st.multiselect(
        "City Tier",
        sorted(df["city_tier"].dropna().unique()),
        default=[],
        placeholder="All tiers",
        key="personas_sel_tier",
    )
with f2:
    sel_sec = st.multiselect(
        "Socioeconomic Class",
        sorted(df["socioeconomic_class"].dropna().unique()),
        default=[],
        placeholder="All Socioeconomic Classes",
        key="personas_sel_sec",
    )
with f3:
    sel_diet = st.multiselect(
        "Diet Culture",
        sorted(df["dietary_culture"].dropna().unique()),
        default=[],
        placeholder="All diets",
        key="personas_sel_diet",
    )
with f4:
    sel_region = st.multiselect(
        "Region",
        sorted(df["cultural_region"].dropna().unique()),
        default=[],
        placeholder="All",
        key="personas_sel_region",
    )

filtered = df.copy()
if sel_tier:
    filtered = filtered[filtered["city_tier"].isin(sel_tier)]
if sel_sec:
    filtered = filtered[filtered["socioeconomic_class"].isin(sel_sec)]
if sel_diet:
    filtered = filtered[filtered["dietary_culture"].isin(sel_diet)]
if sel_region:
    filtered = filtered[filtered["cultural_region"].isin(sel_region)]

st.caption(f"Showing {len(filtered)} of {len(df)} personas")

if sel_tier or sel_sec or sel_diet or sel_region:
    c1, c2 = st.columns(2)
    with c1:
        tier_counts = filtered["city_tier"].value_counts().reset_index()
        tier_counts.columns = ["City Tier", "Count"]
        fig = px.bar(tier_counts, x="City Tier", y="Count", title="City Tier Distribution")
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True, key="filtered_tier")

    with c2:
        income_counts = filtered["income_bracket"].value_counts().sort_index().reset_index()
        income_counts.columns = ["Income Bracket", "Count"]
        fig = px.bar(income_counts, x="Income Bracket", y="Count", title="Income Distribution")
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True, key="filtered_income")

    c3, c4 = st.columns(2)
    with c3:
        fam_counts = filtered["family_structure"].map(display_name).value_counts().reset_index()
        fam_counts.columns = ["Family Structure", "Count"]
        fig = px.bar(fam_counts, x="Family Structure", y="Count", title="Family Structure")
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True, key="filtered_family")

    with c4:
        age_counts = filtered["age_group"].value_counts().reset_index()
        age_counts.columns = ["Age Group", "Count"]
        fig = px.bar(age_counts, x="Age Group", y="Count", title="Youngest Child Age")
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True, key="filtered_age")
else:
    st.caption("Apply filters above to see segmented views.")

st.subheader("Persona Browser")

persona_ids = [p.id for p in pop.personas]
persona_labels = {
    p.id: f"{p.demographics.city_name} · Age {p.demographics.parent_age} · {p.id}"
    for p in pop.personas
}

if sel_tier or sel_sec or sel_diet or sel_region:
    filtered_ids = set(filtered["id"].tolist())
    persona_ids = [pid for pid in persona_ids if pid in filtered_ids]

selected_id = None
if persona_ids:
    selected_id = st.selectbox(
        "Select persona",
        options=persona_ids,
        format_func=lambda pid: persona_labels.get(pid, pid),
        placeholder="Choose a persona...",
        index=None,
        key="personas_selected_id",
    )
else:
    st.info("No personas match the current filters.")

if selected_id:
    persona = pop.get_persona(selected_id)

    col_card, col_spider = st.columns([3, 2])
    with col_card:
        render_persona_card(persona)
    with col_spider:
        render_persona_spider(persona, key="browser")

    if persona.narrative:
        with st.expander("Full Narrative", expanded=False):
            st.markdown(persona.narrative)
