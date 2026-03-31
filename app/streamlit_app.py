"""
LittleJoys Persona Simulation Engine — Streamlit Dashboard.

Main entry point for the interactive presentation layer.
"""

import sys
from pathlib import Path

# Ensure repo root is on sys.path so src.* and app.* packages are importable
# regardless of how Streamlit or the cloud runner sets the working directory.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st  # noqa: E402

from src.constants import DEFAULT_SEED, SCENARIO_IDS  # noqa: E402
from src.decision.scenarios import get_scenario  # noqa: E402
from src.generation.population import Population  # noqa: E402
from src.simulation.static import run_static_simulation  # noqa: E402

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

pop_path = Path("data/population")

if "population" not in st.session_state:
    if pop_path.exists():
        with st.status("Initialising engine...", expanded=True) as status:
            st.write("Loading 200 synthetic household profiles...")
            st.session_state.population = Population.load(pop_path)
            st.write("Running baseline decision simulations across 4 scenarios...")
            st.session_state.scenario_results = {}
            for sid in SCENARIO_IDS:
                st.write(f"  · {get_scenario(sid).name}")
                st.session_state.scenario_results[sid] = run_static_simulation(
                    st.session_state.population,
                    get_scenario(sid),
                )
            status.update(label="Engine ready.", state="complete", expanded=False)
        st.rerun()
    else:
        st.info("No population data found. Generate a synthetic baseline population to begin.")
        if st.button("Generate Population", type="primary"):
            from src.generation.population import PopulationGenerator

            with st.spinner("Generating population..."):
                pop = PopulationGenerator().generate(seed=DEFAULT_SEED)
                pop.save(pop_path)
                st.session_state.population = pop
            st.toast("Population generated successfully!", icon="✅")
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
    _with_narratives = sum(1 for p in pop.personas if p.narrative)
    # Only show "With Narratives" if more than 0, otherwise show a neutral label.
    if _with_narratives > 0:
        c2.metric("With Narratives", _with_narratives)
    else:
        c2.metric(
            "Persona Depth",
            "Deep Profiles",
            help="All personas have full demographic and behavioral profiles.",
        )
    c3.metric(
        "Business Problems",
        4,
        help="4 pre-configured business problems available to investigate.",
    )

    st.markdown("---")
    st.subheader("Getting Started")
    st.markdown(
        "1. **Browse personas** — Explore your synthetic population\n"
        "2. **Define your problem** — Pick a business question; the engine runs a 12-month simulation\n"
        "3. **Investigate** — Review hypotheses, run the probing tree, see evidence accumulate\n"
        "4. **Core Finding** — One synthesised insight with evidence chain\n"
        "5. **Interventions** — Compare solutions on effort, cost, and projected lift\n"
        "6. **Deep-dive interviews** — Read smart-sampled persona conversations"
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.page_link("pages/1_personas.py", label="🔍 Explore Population", icon="👥")
    with col2:
        st.page_link("pages/2_problem.py", label="💡 State a Problem", icon="🎯")
    with col3:
        st.page_link("pages/4_finding.py", label="📊 View Core Finding", icon="📋")
    with col4:
        st.page_link("pages/9_compare.py", label="⚖️ Compare Scenarios", icon="⚖️")
