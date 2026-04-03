# ruff: noqa: N999
"""Compact personas dashboard for browsing the synthetic population."""

from __future__ import annotations

import statistics
from collections import Counter

import plotly.graph_objects as go
import streamlit as st

from app.components.persona_card import render_persona_card
from app.components.persona_spider import render_persona_spider
from app.components.system_voice import render_system_voice
from app.utils.demo_mode import ensure_demo_data
from src.constants import SCENARIO_IDS
from src.utils.display import city_tier_label, display_name, qualitative_level


def _health_consciousness_score(persona: object) -> float:
    # Proxy score using available health-oriented identity attributes.
    return (
        float(persona.health.diet_consciousness)
        + float(persona.health.child_health_proactivity)
        + float(persona.health.nutrition_gap_awareness)
    ) / 3.0


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
with st.expander("Population Distribution", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        incomes = [p.demographics.household_income_lpa for p in pop.personas]
        fig = go.Figure(
            go.Histogram(
                x=incomes,
                nbinsx=10,
                marker_color="#4ECDC4",
                opacity=0.8,
            )
        )
        fig.update_layout(
            title="Household Income Distribution",
            xaxis_title="Annual Income (₹ Lakhs)",
            yaxis_title="Number of Personas",
            plot_bgcolor="#FAFAFA",
            paper_bgcolor="#FFFFFF",
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        tier_counts = Counter(p.demographics.city_tier for p in pop.personas)
        fig = go.Figure(
            go.Pie(
                labels=[city_tier_label(k) for k in tier_counts],
                values=list(tier_counts.values()),
                hole=0.4,
                marker_colors=["#FF6B6B", "#4ECDC4", "#45B7D1", "#95A5A6"],
            )
        )
        fig.update_layout(title="City Distribution")
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        age_bins = {"0-2": 0, "3-5": 0, "6-8": 0, "9-12": 0, "13+": 0}
        for persona in pop.personas:
            for age in persona.demographics.child_ages:
                if age <= 2:
                    age_bins["0-2"] += 1
                elif age <= 5:
                    age_bins["3-5"] += 1
                elif age <= 8:
                    age_bins["6-8"] += 1
                elif age <= 12:
                    age_bins["9-12"] += 1
                else:
                    age_bins["13+"] += 1
        fig = go.Figure(
            go.Bar(
                x=list(age_bins.keys()),
                y=list(age_bins.values()),
                marker_color="#45B7D1",
            )
        )
        fig.update_layout(
            title="Child Age Distribution",
            xaxis_title="Age Band",
            yaxis_title="Number of Children",
            plot_bgcolor="#FAFAFA",
            paper_bgcolor="#FFFFFF",
        )
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        hc_bins = {"Low": 0, "Medium": 0, "High": 0}
        for persona in pop.personas:
            score = _health_consciousness_score(persona)
            if score < 0.4:
                hc_bins["Low"] += 1
            elif score < 0.7:
                hc_bins["Medium"] += 1
            else:
                hc_bins["High"] += 1
        fig = go.Figure(
            go.Bar(
                x=list(hc_bins.keys()),
                y=list(hc_bins.values()),
                marker_color=["#E74C3C", "#F39C12", "#2ECC71"],
            )
        )
        fig.update_layout(
            title="Health Consciousness",
            xaxis_title="Consciousness Band",
            yaxis_title="Number of Personas",
            plot_bgcolor="#FAFAFA",
            paper_bgcolor="#FFFFFF",
        )
        st.plotly_chart(fig, use_container_width=True)

tier2_3_count = sum(1 for p in pop.personas if p.demographics.city_tier in ("Tier2", "Tier3"))
tier2_3_pct = round((tier2_3_count / max(len(pop.personas), 1)) * 100)
render_system_voice(
    f"<strong>{tier2_3_pct}%</strong> of your population lives in Tier-2 or Tier-3 cities - "
    f"the fastest-growing consumption segment for kids' nutrition in India."
)

multi_child = [p for p in pop.personas if p.demographics.num_children >= 2]
single_child = [p for p in pop.personas if p.demographics.num_children == 1]
if multi_child and single_child:
    mc_price = sum(float(p.daily_routine.budget_consciousness) for p in multi_child) / len(multi_child)
    sc_price = sum(float(p.daily_routine.budget_consciousness) for p in single_child) / len(single_child)
    ratio = round(mc_price / sc_price, 1) if sc_price > 0 else 1.0
    render_system_voice(
        f"Personas with 2+ children show <strong>{ratio}x</strong> higher price sensitivity "
        f"than single-child households - discount triggers matter more than brand signals."
    )

age_bands: dict[str, list[float]] = {"25-30": [], "31-35": [], "36-40": [], "40+": []}
for p in pop.personas:
    age = p.demographics.parent_age
    score = _health_consciousness_score(p)
    if age <= 30:
        age_bands["25-30"].append(score)
    elif age <= 35:
        age_bands["31-35"].append(score)
    elif age <= 40:
        age_bands["36-40"].append(score)
    else:
        age_bands["40+"].append(score)
peak_band = max(age_bands, key=lambda b: statistics.mean(age_bands[b]) if age_bands[b] else 0.0)
render_system_voice(
    f"Health consciousness peaks in the <strong>{peak_band}</strong> age band - "
    f"your highest-receptivity window for nutrition messaging."
)

st.subheader("Explore Segments")
st.caption("Select filters to drill down. Empty = show all.")

f1, f2, f3, f4 = st.columns(4)
with f1:
    sel_tier = st.multiselect(
        "City Tier",
        sorted({p.demographics.city_tier for p in pop.personas}),
        default=[],
        placeholder="All tiers",
        key="personas_sel_tier",
    )
with f2:
    sel_sec = st.multiselect(
        "Socioeconomic Class",
        sorted({p.demographics.socioeconomic_class for p in pop.personas}),
        default=[],
        placeholder="All Socioeconomic Classes",
        key="personas_sel_sec",
    )
with f3:
    sel_diet = st.multiselect(
        "Diet Culture",
        sorted({p.cultural.dietary_culture for p in pop.personas}),
        default=[],
        placeholder="All diets",
        key="personas_sel_diet",
    )
with f4:
    sel_region = st.multiselect(
        "Region",
        sorted({p.cultural.cultural_region for p in pop.personas}),
        default=[],
        placeholder="All",
        key="personas_sel_region",
    )
narrative_search = st.text_input(
    "Search in persona stories",
    placeholder="e.g. 'working mother', 'organic food', 'Tier-2 city'",
    key="narrative_search",
)

filtered_personas = list(pop.personas)
if sel_tier:
    filtered_personas = [p for p in filtered_personas if p.demographics.city_tier in sel_tier]
if sel_sec:
    filtered_personas = [p for p in filtered_personas if p.demographics.socioeconomic_class in sel_sec]
if sel_diet:
    filtered_personas = [p for p in filtered_personas if p.cultural.dietary_culture in sel_diet]
if sel_region:
    filtered_personas = [p for p in filtered_personas if p.cultural.cultural_region in sel_region]
if narrative_search:
    search_lower = narrative_search.lower()
    filtered_personas = [p for p in filtered_personas if search_lower in (p.narrative or "").lower()]

st.caption(f"Showing {len(filtered_personas)} of {len(pop.personas)} personas")

st.subheader("Persona Browser")

persona_ids = [p.id for p in filtered_personas]
persona_labels = {
    p.id: f"{p.demographics.city_name} · {display_name('parent_age')} {p.demographics.parent_age} · {p.id}"
    for p in filtered_personas
}

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

    with st.expander("Children", expanded=False):
        child_ages = list(persona.demographics.child_ages)
        if child_ages:
            child_cols = st.columns(min(len(child_ages), 3))
            for ci, age in enumerate(child_ages):
                with child_cols[ci % 3], st.container(border=True):
                    st.markdown(f"**Child {ci + 1}**, {age} yrs")
                    st.caption(
                        f"{display_name('child_nutrition_concerns')}: "
                        + (
                            ", ".join(persona.health.child_nutrition_concerns)
                            if persona.health.child_nutrition_concerns
                            else "None"
                        )
                    )
                    st.caption(
                        f"{display_name('child_dietary_restrictions')}: "
                        + (
                            ", ".join(persona.health.child_dietary_restrictions)
                            if persona.health.child_dietary_restrictions
                            else "Not specified"
                        )
                    )
        else:
            st.caption("No child details available for this persona.")

    with st.expander("Memory & Anchors", expanded=False):
        if persona.episodic_memory or persona.semantic_memory or persona.brand_memories:
            if persona.episodic_memory:
                st.markdown("**Episodic Memories**")
                for mem in persona.episodic_memory[:3]:
                    st.caption(f"- {mem.content}")
            if persona.semantic_memory:
                st.markdown("**Beliefs & Values**")
                for key, value in list(persona.semantic_memory.items())[:3]:
                    st.caption(f"- {display_name(str(key))}: {value}")
            if persona.brand_memories:
                st.markdown("**Brand Associations**")
                for brand, memory in list(persona.brand_memories.items())[:3]:
                    st.caption(f"- {brand}: {memory.trust_level:.2f} trust")
        else:
            st.caption("No memory layer available for this persona.")

    with st.expander("Full Attribute Profile", expanded=False):
        flat = persona.to_flat_dict()
        sections = {
            "Demographics": [
                "city_tier",
                "city_name",
                "region",
                "household_income_lpa",
                "parent_age",
                "education_level",
                "employment_status",
                "num_children",
                "child_ages",
                "family_structure",
            ],
            "Health": [
                "diet_consciousness",
                "medical_authority_trust",
                "immunity_concern",
                "growth_concern",
                "nutrition_gap_awareness",
                "child_health_proactivity",
            ],
            "Psychology": [
                "health_anxiety",
                "risk_tolerance",
                "social_proof_bias",
                "authority_bias",
                "loss_aversion",
                "simplicity_preference",
                "decision_fatigue_level",
            ],
            "Cultural": [
                "dietary_culture",
                "traditional_vs_modern_spectrum",
                "ayurveda_affinity",
                "western_brand_trust",
                "community_orientation",
            ],
            "Relationships": [
                "peer_influence_strength",
                "influencer_trust",
                "elder_advice_weight",
                "pediatrician_influence",
                "child_pester_power",
                "child_taste_veto",
            ],
            "Career": [
                "employment_status",
                "work_hours_per_week",
                "perceived_time_scarcity",
                "cooking_time_available",
            ],
            "Education & Learning": [
                "science_literacy",
                "nutrition_knowledge",
                "label_reading_habit",
                "research_before_purchase",
                "ingredient_awareness",
            ],
            "Lifestyle": [
                "cooking_enthusiasm",
                "wellness_trend_follower",
                "clean_label_importance",
                "superfood_awareness",
            ],
            "Daily Routine": [
                "online_vs_offline_preference",
                "primary_shopping_platform",
                "subscription_comfort",
                "deal_seeking_intensity",
                "budget_consciousness",
                "milk_supplement_current",
            ],
            "Values": [
                "supplement_necessity_belief",
                "food_first_belief",
                "brand_loyalty_tendency",
                "indie_brand_openness",
                "best_for_my_child_intensity",
            ],
            "Emotional": [
                "emotional_persuasion_susceptibility",
                "fear_appeal_responsiveness",
                "testimonial_impact",
                "buyer_remorse_tendency",
            ],
            "Media": [
                "primary_social_platform",
                "daily_social_media_hours",
                "ad_receptivity",
                "digital_payment_comfort",
            ],
        }
        for section_name, fields in sections.items():
            with st.expander(section_name, expanded=False):
                for field in fields:
                    if field not in flat:
                        continue
                    val = flat[field]
                    label = display_name(field)
                    if isinstance(val, float):
                        st.caption(f"{label}: {qualitative_level(val)} ({val:.2f})")
                    else:
                        st.caption(f"{label}: {val}")
