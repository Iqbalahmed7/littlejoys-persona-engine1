"""
LittleJoys Persona Simulation Engine — Streamlit Dashboard.

Main entry point for the interactive presentation layer.
Full implementation in PRD-011 (Sprint 4).
"""

from pathlib import Path

import streamlit as st

from src.constants import SCENARIO_IDS
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
st.caption("Unified interface mapping synthetic baseline configurations and simulation dynamics.")
st.markdown("---")

if "population" not in st.session_state:
    pop_path = Path("data/population")
    if pop_path.exists():
        with st.spinner("Pre-loading cached demographic schemas..."):
            st.session_state.population = Population.load(pop_path)
            st.toast("Population loaded from disk.", icon="💾")
    else:
        st.info("No data loaded. Click Generate to create a population.")

if "scenario_results" not in st.session_state:
    st.session_state.scenario_results = {}
    if "population" in st.session_state:
        with st.spinner("Pre-computing default scenario bounds..."):
            for sid in SCENARIO_IDS:
                st.session_state.scenario_results[sid] = run_static_simulation(
                    st.session_state.population, get_scenario(sid)
                )
            st.toast("Baseline configurations evaluated successfully.", icon="📈")

st.sidebar.header("Navigation")
st.sidebar.markdown("""
- Population Explorer
- Scenario Configurator
- Results Dashboard
- Counterfactual Analysis
- Persona Interviews
- Report Generator
""")
