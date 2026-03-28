"""
LittleJoys Persona Simulation Engine — Streamlit Dashboard.

Main entry point for the interactive presentation layer.
Full implementation in PRD-011 (Sprint 4).
"""

import streamlit as st

st.set_page_config(
    page_title="LittleJoys Persona Engine",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("LittleJoys Persona Simulation Engine")
st.markdown("---")
st.info("Dashboard under construction. Sprint 4 will implement all pages.")

st.sidebar.header("Navigation")
st.sidebar.markdown("""
- Population Explorer
- Scenario Configurator
- Results Dashboard
- Counterfactual Analysis
- Persona Interviews
- Report Generator
""")
