"""
LittleJoys Persona Simulation Engine — Streamlit Dashboard.

Main entry point for the interactive presentation layer.
"""

from pathlib import Path

import streamlit as st

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
        with st.spinner("Pre-computing default scenario bounds..."):
            for sid in SCENARIO_IDS:
                st.session_state.scenario_results[sid] = run_static_simulation(
                    st.session_state.population, get_scenario(sid)
                )
            st.toast("Baseline configurations evaluated successfully.", icon="📈")

if "population" in st.session_state:
    pop = st.session_state.population
    c1, c2, c3 = st.columns(3)
    c1.metric("Tier 1 (Statistical) Personas", len(pop.tier1_personas))
    c2.metric("Tier 2 (Deep) Personas", len(pop.tier2_personas))
    c3.metric("Scenarios Evaluated", len(st.session_state.get("scenario_results", {})))
