"""Demo mode preloading helpers for Streamlit.

This module is UI-only: it pre-populates Streamlit ``st.session_state`` so
pages can render instantly in demo mode.
"""

from __future__ import annotations

import streamlit as st

from src.config import Config
from src.decision.scenarios import get_scenario
from src.generation.population import PopulationGenerator
from src.probing.question_bank import get_questions_for_scenario
from src.simulation.research_runner import ResearchRunner
from src.utils.llm import LLMClient

DEMO_SCENARIO_ID = "nutrimix_2_6"
DEMO_SEED = 42
DEMO_POPULATION_SIZE = 50


def ensure_demo_data() -> None:
    """Ensure demo data is preloaded into ``st.session_state``.

    Preloads:
    - ``population`` (size=50, seed=42)
    - ``scenario_results`` for ``nutrimix_2_6``
    - ``research_result`` for the consolidated results page
    """

    if st.session_state.get("demo_preloaded") is True:
        return

    # If an API key exists, the app may attempt real LLM calls elsewhere.
    # Demo mode is designed to be instant; we force mock mode here.
    mock_mode = True

    llm_client = LLMClient(
        Config(
            llm_mock_enabled=True,
            llm_cache_enabled=False,
            anthropic_api_key="",
        )
    )

    with st.spinner("Preparing demo data..."):
        pop = PopulationGenerator().generate(
            size=DEMO_POPULATION_SIZE,
            seed=DEMO_SEED,
            deep_persona_count=0,
            llm_client=llm_client,
        )
        st.session_state.population = pop

        scenario = get_scenario(DEMO_SCENARIO_ID)
        questions = get_questions_for_scenario(DEMO_SCENARIO_ID)
        question = questions[0] if questions else None

        st.session_state.scenario_results = {
            DEMO_SCENARIO_ID: None,
        }

        if question is not None:
            runner = ResearchRunner(
                population=pop,
                scenario=scenario,
                question=question,
                llm_client=llm_client,
                mock_mode=mock_mode,
                alternative_count=50,
                sample_size=18,
            )
            result = runner.run()
            st.session_state["research_result"] = result
            st.session_state.scenario_results[DEMO_SCENARIO_ID] = result.primary_funnel

        # Phase A/C demo data
        if question is not None:
            from src.analysis.cohort_classifier import classify_population
            from src.analysis.intervention_engine import (
                InterventionInput,
                generate_intervention_quadrant,
            )
            from src.analysis.problem_decomposition import decompose_problem
            from src.analysis.quadrant_analysis import analyze_quadrant_results
            from src.simulation.quadrant_runner import run_intervention_quadrant

            # Phase A
            cohorts = classify_population(pop, scenario, seed=DEMO_SEED)
            decomp = decompose_problem(scenario, question, pop, cohorts)

            st.session_state["phase_a_insights"] = {
                "scenario_id": DEMO_SCENARIO_ID,
                "cohort": decomp.cohorts[0].name if decomp.cohorts else "Current User",
                "sub_problems": [sp.title for sp in decomp.sub_problems],
                "root_causes": [
                    {"root": sp.title, "pct": 100.0 / max(1, len(decomp.sub_problems)), "count": 5}
                    for sp in decomp.sub_problems[:3]
                ],
                "summary": "\n".join(
                    f"- {sp.title}: {100.0 / max(1, len(decomp.sub_problems)):.0f}%"
                    for sp in decomp.sub_problems[:3]
                ),
            }

            # Phase A quadrant
            decomp_input = InterventionInput(problem_id=question.id)
            quadrant = generate_intervention_quadrant(decomp_input, scenario)
            st.session_state["phase_a_quadrant"] = quadrant

            # Phase C — run the quadrant
            run_result = run_intervention_quadrant(quadrant, pop, scenario, seed=DEMO_SEED)
            analysis = analyze_quadrant_results(run_result, quadrant)
            st.session_state["phase_c_run_result"] = run_result
            st.session_state["phase_c_analysis"] = analysis

            # Cohort classification cache
            _cohort_key = f"phase_a_cohorts_{DEMO_SCENARIO_ID}"
            st.session_state[_cohort_key] = cohorts

    st.session_state.demo_preloaded = True
