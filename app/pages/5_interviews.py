"""Streamlit page for interactive deep persona interviews.

Population is loaded from the sidebar path (or generated there), not from
``st.session_state.population``; no home-page session guard is required.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import streamlit as st
from pydantic import ValidationError

from src.analysis.interview_guardrails import run_all_guardrails
from src.analysis.interviews import InterviewTurn, PersonaInterviewer, check_interview_quality
from src.config import Config, get_config
from src.constants import (
    DASHBOARD_DEFAULT_POPULATION_PATH,
    DEFAULT_SEED,
    INTERVIEW_MAX_TURNS,
    SCENARIO_IDS,
)
from src.decision.funnel import run_funnel
from src.decision.scenarios import get_scenario
from src.generation.population import Population, PopulationGenerator
from src.utils.llm import LLMClient
from src.utils.spend_tracker import SessionSpendTracker

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona

_T = TypeVar("_T")


def _run_async(coro: Any) -> _T:
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@st.cache_resource(show_spinner=False)
def _load_population(population_path: str) -> Population:
    path = Path(population_path)
    if (path / "population_meta.json").exists():
        return Population.load(path)

    generated = PopulationGenerator().generate(seed=DEFAULT_SEED)
    generated.save(path)
    return generated


def _resolve_api_key() -> str:
    """Read Anthropic API key from Streamlit secrets (cloud) or .env.local (local)."""
    try:
        if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
            return str(st.secrets["ANTHROPIC_API_KEY"]).strip()
    except Exception:
        pass
    key = get_config().anthropic_api_key.strip()
    if not key or key == "sk-ant-REPLACE_ME":
        return ""
    return key


def _has_api_key() -> bool:
    """Return True if a non-placeholder API key is available."""
    key = _resolve_api_key()
    return bool(key) and not key.startswith("sk-ant-REPLACE")


@st.cache_resource(show_spinner=False)
def _build_interviewer(mock_llm: bool) -> PersonaInterviewer:
    api_key = "" if mock_llm else _resolve_api_key()
    client = LLMClient(
        Config(
            llm_mock_enabled=mock_llm,
            llm_cache_enabled=not mock_llm,
            anthropic_api_key=api_key,
        )
    )
    return PersonaInterviewer(client)


def _persona_label(persona: Persona) -> str:
    name = persona.display_name or persona.demographics.city_name
    employment = persona.career.employment_status.replace("_", " ")
    return f"{persona.id} · {name} · {employment}"


def _decision_result_for_persona(persona: Persona, scenario_id: str) -> dict[str, Any]:
    scenario = get_scenario(scenario_id)
    decision = run_funnel(persona, scenario)
    return {
        **decision.to_dict(),
        "scenario_id": scenario_id,
        "product_name": scenario.product.name,
    }


def _coerce_turns(raw_turns: Any) -> list[InterviewTurn]:
    if not isinstance(raw_turns, list):
        return []

    turns: list[InterviewTurn] = []
    for item in raw_turns:
        if isinstance(item, InterviewTurn):
            turns.append(item)
            continue
        if isinstance(item, dict):
            try:
                turns.append(InterviewTurn.model_validate(item))
            except ValidationError:
                continue
    return turns


st.title("Persona Interviews")
st.caption(
    "Chat with deep personas in-character about why they adopted or rejected a scenario product."
)

with st.sidebar:
    st.subheader("Interview Controls")
    scenario_id = st.selectbox("Scenario", options=SCENARIO_IDS, index=0)

    def _has_api_key() -> bool:
        """Check if a real Anthropic API key is configured."""
        try:
            if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
                key = str(st.secrets["ANTHROPIC_API_KEY"])
                return bool(key) and not key.startswith("sk-ant-REPLACE")
        except Exception:
            pass
        from src.config import get_config

        key = get_config().anthropic_api_key
        return bool(key) and not key.startswith("sk-ant-REPLACE")

    api_available = _has_api_key()
    if api_available:
        mock_llm = st.toggle(
            "Mock LLM Mode",
            value=False,
            key="interview_mock_toggle",
            help="Real LLM responses powered by Claude Sonnet. Toggle on for instant mock responses.",
        )
    else:
        mock_llm = True
        st.info("No API key configured. Using mock responses. See docs/DEPLOYMENT.md to set up.")

    population_path = st.text_input(
        "Population Path",
        value=DASHBOARD_DEFAULT_POPULATION_PATH,
    )

    # Cost indicator (only when using real LLM)
    if not mock_llm:
        from src.utils.spend_tracker import SessionSpendTracker

        if "spend_tracker" not in st.session_state:
            st.session_state["spend_tracker"] = SessionSpendTracker()
        tracker = st.session_state["spend_tracker"]
        summary = tracker.session_summary()

        st.divider()
        st.caption("💰 Session Cost")
        cost_cols = st.columns(2)
        cost_cols[0].metric(
            "Spent",
            f"${summary['total_cost_usd']:.2f}",
        )
        cost_cols[1].metric(
            "Calls",
            f"{summary['total_calls']}",
        )
        st.progress(
            min(1.0, summary["total_cost_usd"] / 2.0),
            text=f"${summary['total_cost_usd']:.2f} / $2.00 budget",
        )

with st.spinner("Loading population..."):
    population = _load_population(population_path)

persona_pool = population.personas
if not persona_pool:
    st.warning("No personas available. Generate population data first.")
    st.stop()

# Pre-compute outcomes for filtering
_scenario_obj = get_scenario(scenario_id)
_outcomes: dict[str, str] = {}
for _p in persona_pool:
    _dr = run_funnel(_p, _scenario_obj)
    _outcomes[_p.id] = _dr.to_dict()["outcome"]

outcome_filter = st.radio(
    "Show personas who…",
    options=["All", "Adopted", "Rejected"],
    horizontal=True,
    key="interview_outcome_filter",
)
if outcome_filter == "Adopted":
    filtered_pool = [p for p in persona_pool if _outcomes.get(p.id) == "adopt"]
elif outcome_filter == "Rejected":
    filtered_pool = [p for p in persona_pool if _outcomes.get(p.id) == "reject"]
else:
    filtered_pool = list(persona_pool)

_adopt_count = sum(1 for v in _outcomes.values() if v == "adopt")
_reject_count = sum(1 for v in _outcomes.values() if v == "reject")
st.caption(f"{_adopt_count} adopted · {_reject_count} rejected in this scenario")

if not filtered_pool:
    st.info(f"No personas matched the '{outcome_filter}' filter for this scenario.")
    st.stop()

persona_lookup = {persona.id: persona for persona in filtered_pool}
selected_persona_id = st.selectbox(
    "Persona",
    options=list(persona_lookup.keys()),
    format_func=lambda persona_id: _persona_label(persona_lookup[persona_id]),
)
selected_persona = persona_lookup[selected_persona_id]
decision_result = _decision_result_for_persona(selected_persona, scenario_id)

session_key = f"{scenario_id}|{selected_persona_id}|{int(mock_llm)}"
if st.session_state.get("interview_session_key") != session_key:
    st.session_state["interview_session_key"] = session_key
    st.session_state["interview_turns"] = []
    st.session_state["interview_quality_warnings"] = []
    st.session_state["interview_guardrail_warnings"] = []

if st.button("Reset Conversation"):
    st.session_state["interview_turns"] = []
    st.session_state["interview_quality_warnings"] = []
    st.session_state["interview_guardrail_warnings"] = []
    st.rerun()

metric_cols = st.columns(5)
metric_cols[0].metric("Outcome", str(decision_result["outcome"]).upper())
metric_cols[1].metric("Need", f"{float(decision_result['need_score']):.2f}")
metric_cols[2].metric("Awareness", f"{float(decision_result['awareness_score']):.2f}")
metric_cols[3].metric("Consideration", f"{float(decision_result['consideration_score']):.2f}")
metric_cols[4].metric("Purchase", f"{float(decision_result['purchase_score']):.2f}")

if mock_llm:
    st.info(
        "🔧 **Mock Mode** — Responses are generated from templates, not an LLM. "
        "Toggle off in the sidebar for real AI-powered conversations."
    )
else:
    st.success(
        "🤖 **Live Mode** — Responses powered by Claude Sonnet. Each response costs ~$0.02-0.05."
    )

turns = _coerce_turns(st.session_state.get("interview_turns", []))
st.session_state["interview_turns"] = turns

for turn in turns:
    role = "assistant" if turn.role == "persona" else "user"
    with st.chat_message(role):
        st.write(turn.content)
        if turn.role == "persona":
            if mock_llm:
                st.caption("🔧 Mock response")
            else:
                st.caption("🤖 Claude Sonnet")

question = st.chat_input("Ask this persona about price, trust, routine, or barriers...")
if question:
    if len(turns) >= INTERVIEW_MAX_TURNS:
        st.warning(f"Maximum interview turns reached ({INTERVIEW_MAX_TURNS}). Reset to continue.")
        st.stop()

    # Spend guard — block if session limits exceeded
    if not mock_llm:
        if "spend_tracker" not in st.session_state:
            st.session_state["spend_tracker"] = SessionSpendTracker()
        tracker = st.session_state["spend_tracker"]
        allowed, reason = tracker.can_proceed()
        if not allowed:
            st.error(reason)
            st.stop()

    history = list(turns)
    turns.append(InterviewTurn(role="user", content=question, timestamp=_iso_now()))

    persona_name = selected_persona.display_name or selected_persona.demographics.city_name
    spinner_text = (
        "🔧 Generating mock response..." if mock_llm else f"💭 {persona_name} is thinking..."
    )
    with st.spinner(spinner_text):
        interviewer = _build_interviewer(mock_llm)
        reply = _run_async(
            interviewer.interview(
                persona=selected_persona,
                question=question,
                scenario_id=scenario_id,
                decision_result=decision_result,
                conversation_history=history,
            )
        )

    turns.append(reply)
    quality = check_interview_quality(reply.content, selected_persona, decision_result)
    guardrail_warnings = run_all_guardrails(
        response=reply.content,
        question=question,
        persona=selected_persona,
        decision_result=decision_result,
        previous_turns=history,
    )

    st.session_state["interview_turns"] = turns
    st.session_state["interview_quality_warnings"] = quality.warnings
    st.session_state["interview_guardrail_warnings"] = guardrail_warnings
    st.rerun()

warnings = st.session_state.get("interview_quality_warnings", [])
if isinstance(warnings, list) and warnings:
    st.warning("Quality checks: " + ", ".join(str(item) for item in warnings))

guardrail_warnings = st.session_state.get("interview_guardrail_warnings", [])
if isinstance(guardrail_warnings, list) and guardrail_warnings:
    scope_violations = [warning for warning in guardrail_warnings if "scope" in warning]
    sec_issues = [warning for warning in guardrail_warnings if "sec" in warning]
    reframing = [warning for warning in guardrail_warnings if "reframing" in warning]
    consistency = [
        warning
        for warning in guardrail_warnings
        if "flip" in warning or "contradiction" in warning or "inconsistency" in warning
    ]

    if scope_violations:
        st.warning("Response may have ventured outside the study scope.")
    if sec_issues:
        st.warning("Some references may not match this persona's socioeconomic profile.")
    if reframing:
        st.warning("Persona may have agreed too readily with a leading question.")
    if consistency:
        st.warning("Response may contradict something said earlier in this conversation.")
