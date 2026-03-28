"""Streamlit page for interactive ReportAgent generation.

Like interviews, this page loads population from the sidebar path for report
evidence, not from ``st.session_state.population``.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, TypeVar

import streamlit as st

from src.analysis.report_agent import ReportAgent, ReportOutput, validate_report_grounding
from src.config import Config
from src.constants import DASHBOARD_DEFAULT_POPULATION_PATH, DEFAULT_SEED, SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.generation.population import Population, PopulationGenerator
from src.simulation.static import run_static_simulation
from src.utils.llm import LLMClient

_T = TypeVar("_T")

DEFAULT_PRECOMPUTE_DIR = "data/results/precomputed"


def _run_async(coro: Any) -> _T:
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


@st.cache_resource(show_spinner=False)
def _load_population(population_path: str) -> Population:
    path = Path(population_path)
    if (path / "population_meta.json").exists():
        return Population.load(path)

    generated = PopulationGenerator().generate(seed=DEFAULT_SEED)
    generated.save(path)
    return generated


@st.cache_resource(show_spinner=False)
def _build_llm_client(mock_llm: bool) -> LLMClient:
    return LLMClient(
        Config(
            llm_mock_enabled=mock_llm,
            llm_cache_enabled=False,
            anthropic_api_key="",
        )
    )


@st.cache_data(show_spinner=False)
def _load_precomputed_decision_rows(
    precompute_dir: str,
    scenario_id: str,
) -> dict[str, Any] | None:
    path = Path(precompute_dir) / f"{scenario_id}_decision_rows.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def _load_precomputed_report_markdown(
    precompute_dir: str,
    scenario_id: str,
) -> str | None:
    path = Path(precompute_dir) / "reports" / f"{scenario_id}_report.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


@st.cache_data(show_spinner=False)
def _compute_decision_rows(
    population_path: str,
    scenario_id: str,
    seed: int,
) -> dict[str, dict[str, Any]]:
    population = _load_population(population_path)
    scenario = get_scenario(scenario_id)
    static = run_static_simulation(population, scenario, seed=seed)
    return static.results_by_persona


st.title("Report Generator")
st.caption("Generate grounded strategy reports with the ReportAgent.")

with st.sidebar:
    st.subheader("Report Controls")
    scenario_id = st.selectbox("Scenario", options=SCENARIO_IDS, index=0)
    mock_llm = st.toggle("Mock LLM Mode", value=True)
    population_path = st.text_input("Population Path", value=DASHBOARD_DEFAULT_POPULATION_PATH)
    precompute_dir = st.text_input("Precompute Directory", value=DEFAULT_PRECOMPUTE_DIR)
    run_generation = st.button("Generate Report", use_container_width=True)

cache_key = f"{scenario_id}|{int(mock_llm)}"

precomputed_payload = _load_precomputed_decision_rows(precompute_dir, scenario_id)
if (
    precomputed_payload is not None
    and isinstance(precomputed_payload.get("results_by_persona"), dict)
    and precomputed_payload["results_by_persona"]
):
    decision_rows = precomputed_payload["results_by_persona"]
    st.info("Using precomputed scenario evidence.")
else:
    with st.spinner("Running static simulation for report evidence..."):
        decision_rows = _compute_decision_rows(population_path, scenario_id, DEFAULT_SEED)

if "report_outputs" not in st.session_state:
    st.session_state["report_outputs"] = {}
if "report_grounding_warnings" not in st.session_state:
    st.session_state["report_grounding_warnings"] = {}

if run_generation:
    with st.spinner("Generating report with ReportAgent..."):
        population = _load_population(population_path)
        agent = ReportAgent(_build_llm_client(mock_llm))
        generated = _run_async(
            agent.generate_report(
                scenario_id=scenario_id,
                results=decision_rows,
                population=population,
            )
        )
        st.session_state["report_outputs"][cache_key] = generated.model_dump(mode="json")

        schema_attributes = list(next(iter(decision_rows.values())).keys()) if decision_rows else []
        st.session_state["report_grounding_warnings"][cache_key] = validate_report_grounding(
            generated,
            schema_attributes,
        )
    st.rerun()

raw_report = st.session_state["report_outputs"].get(cache_key)
if isinstance(raw_report, dict):
    report = ReportOutput.model_validate(raw_report)
    scenario = get_scenario(scenario_id)

    header_cols = st.columns(3)
    header_cols[0].metric("Scenario", scenario.id)
    header_cols[1].metric("Tool Calls", report.tool_calls_made)
    header_cols[2].metric("Sections", len(report.sections))

    for section in report.sections:
        with st.expander(section.title, expanded=True):
            st.markdown(section.content)
            if section.supporting_data:
                st.json(section.supporting_data)

    grounding_warnings = st.session_state["report_grounding_warnings"].get(cache_key, [])
    if isinstance(grounding_warnings, list) and grounding_warnings:
        st.warning("Grounding warnings detected:")
        for warning in grounding_warnings[:12]:
            st.write(f"- {warning}")

    st.download_button(
        "Download Markdown",
        data=report.raw_markdown,
        file_name=f"{scenario_id}_report.md",
        mime="text/markdown",
    )
else:
    precomputed_markdown = _load_precomputed_report_markdown(precompute_dir, scenario_id)
    if precomputed_markdown:
        st.subheader("Precomputed Report")
        st.markdown(precomputed_markdown)
    else:
        st.info("Click 'Generate Report' to run the ReportAgent for this scenario.")
