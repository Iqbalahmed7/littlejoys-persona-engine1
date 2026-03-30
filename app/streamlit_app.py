"""
LittleJoys Persona Simulation Engine — Streamlit Dashboard.

Main entry point for the interactive presentation layer.
"""

from pathlib import Path

import streamlit as st

from app.utils.demo_mode import ensure_demo_data
from src.constants import DEFAULT_SEED, SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.generation.population import Population
from src.simulation.static import run_static_simulation

st.set_page_config(
    page_title="LittleJoys Persona Engine",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("LittleJoys Persona Simulation Engine")
st.caption("Synthetic persona engine for kids nutrition D2C in India.")
st.markdown("---")

demo_mode = False
st.sidebar.caption("1️⃣ Personas — Explore synthetic households")
st.sidebar.caption("2️⃣ Research — Run scenario research")
st.sidebar.caption("3️⃣ Results — View research results")
st.sidebar.caption("4️⃣ Diagnose — Phase A problem decomposition")
st.sidebar.caption("5️⃣ Simulate — Phase C intervention testing")
st.sidebar.caption("6️⃣ Interviews — Deep dive conversations")
st.sidebar.caption("7️⃣ Comparison — Compare two scenarios")

if demo_mode:
    ensure_demo_data()

pop_path = Path("data/population")

if "population" not in st.session_state:
    if pop_path.exists():
        with st.spinner("Pre-loading cached demographic schemas..."):
            st.session_state.population = Population.load(pop_path)
            st.toast("Population loaded from disk.", icon="💾")
    else:
        st.info("No population data found. Generate a synthetic baseline population to begin.")
        if st.button("Generate Population", type="primary"):
            from src.generation.population import PopulationGenerator

            with st.spinner("Generating population..."):
                pop = PopulationGenerator().generate(seed=DEFAULT_SEED)
                pop.save(pop_path)
                st.session_state.population = pop
            st.toast("Population explicitly generated successfully!", icon="✅")
            st.rerun()

if "scenario_results" not in st.session_state:
    st.session_state.scenario_results = {}
    if "population" in st.session_state:
        for sid in SCENARIO_IDS:
            st.session_state.scenario_results[sid] = run_static_simulation(
                st.session_state.population,
                get_scenario(sid),
            )

if "population" in st.session_state:
    pop = st.session_state.population

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Personas", len(pop.personas))
    c2.metric("With Narratives", sum(1 for p in pop.personas if p.narrative))
    c3.metric("Scenarios Available", len(SCENARIO_IDS))

    st.markdown("---")
    st.subheader("Getting Started")
    st.markdown(
        "1. **Browse personas** — Explore your synthetic population\n"
        "2. **Design research** — Pick a scenario, choose a business question, run the hybrid pipeline\n"
        "3. **View results** — Quantitative findings, qualitative themes, strategic alternatives\n"
        "4. **Diagnose** — Phase A problem decomposition: identify root barriers by cohort\n"
        "5. **Simulate** — Phase C intervention testing: measure lift across the quadrant\n"
        "6. **Deep-dive interviews** — Read the smart-sampled persona conversations"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.page_link("pages/1_personas.py", label="Browse Personas →", icon="👥")
    with col2:
        st.page_link("pages/2_research.py", label="Design Research →", icon="🔬")
    with col3:
        st.page_link("pages/2_diagnose.py", label="Diagnose →", icon="🔍")
