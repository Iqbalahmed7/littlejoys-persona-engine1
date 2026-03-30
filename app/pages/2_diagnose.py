# ruff: noqa: N999
"""Phase A — Problem Diagnosis UI.

UI-only Streamlit page implementing Phase A diagnostic workflow:
1) Problem decomposition + cohort selection
2) Cohort deep dive + run diagnosis (interview pipeline on cohort sub-pop)
3) Insight display + persist to ``st.session_state['phase_a_insights']``
"""

from __future__ import annotations

import random
import re
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from app.components.persona_card import render_persona_card
from src.analysis.cohort_classifier import classify_population
from src.analysis.problem_decomposition import decompose_problem
from src.config import Config
from src.constants import SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.probing.models import ProbeType
from src.probing.question_bank import get_questions_for_scenario, get_tree_for_question
from src.simulation.research_runner import ResearchRunner
from src.utils.llm import LLMClient


def _sidebar_caption(text: str) -> None:
    if hasattr(st.sidebar, "caption"):
        st.sidebar.caption(text)
    else:
        st.caption(text)


def _sidebar_toggle(label: str, *, key: str, value: bool = False) -> bool:
    if hasattr(st.sidebar, "toggle"):
        return st.sidebar.toggle(label, key=key, value=value)
    return st.toggle(label, key=key, value=value)


def _parse_value(raw: str) -> Any:
    raw = raw.strip()
    if raw.lower() in {"true", "false"}:
        return raw.lower() == "true"
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


_COND_RE = re.compile(
    r"^(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)\s*(?P<op>>=|<=|!=|=|<|>)\s*(?P<val>.+)$",
)


def _match_cohort_expression(flat: dict[str, Any], expression: str) -> bool:
    """Best-effort cohort expression evaluator.

    Supports comma-separated AND conditions such as:
        trust > 0.6, ever_adopted = False, working_status = 'full_time'

    Unknown keys are ignored to keep cohorts usable.
    """

    parts = [p.strip() for p in expression.split(",") if p.strip()]
    for part in parts:
        m = _COND_RE.match(part)
        if not m:
            continue
        key = m.group("key")
        op = m.group("op")
        val = _parse_value(m.group("val"))

        if key not in flat:
            # Key missing in persona identity: ignore this constraint.
            continue
        actual = flat.get(key)

        try:
            if op == ">":
                if not (actual > val):
                    return False
            elif op == ">=":
                if not (actual >= val):
                    return False
            elif op == "<":
                if not (actual < val):
                    return False
            elif op == "<=":
                if not (actual <= val):
                    return False
            elif (op == "=" and actual != val) or (op == "!=" and actual == val):
                return False
        except TypeError:
            return False

    return True


def _sample_personas(personas: list[Any], n: int) -> list[Any]:
    if len(personas) <= n:
        return personas
    return random.sample(personas, n)


def _root_cause_keywords(sub_problem: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]+", sub_problem.lower())
    stop = {"the", "and", "or", "to", "of", "a", "an", "over", "with"}
    return [w for w in words if w not in stop and len(w) > 2][:10]


def _compute_root_causes(
    sub_problems: list[str],
    interview_texts: list[str],
) -> list[dict[str, Any]]:
    totals: dict[str, int] = {sp: 0 for sp in sub_problems}
    for text in interview_texts:
        tl = text.lower()
        for sp in sub_problems:
            kws = _root_cause_keywords(sp)
            if any(k in tl for k in kws):
                totals[sp] += 1

    total = sum(totals.values())
    if total == 0:
        return [
            {"root": sp, "pct": 100.0 / len(sub_problems), "count": 0} for sp in sub_problems[:5]
        ]

    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    out: list[dict[str, Any]] = []
    for root, c in ranked[:5]:
        out.append({"root": root, "pct": (c / total) * 100.0, "count": c})
    return out


def _top_quotes_for_root(root: str, interview_texts: list[str], k: int = 2) -> list[str]:
    kws = _root_cause_keywords(root)
    matches: list[str] = []
    for t in interview_texts:
        tl = t.lower()
        if any(kw in tl for kw in kws):
            matches.append(t)
    return matches[:k]


def _cohort_size(pop: Any, expression: str) -> list[Any]:
    personas = []
    for persona in pop.personas:
        if _match_cohort_expression(persona.to_flat_dict(), expression):
            personas.append(persona)
    return personas


st.header("Phase A — Diagnose")
st.caption("Problem decomposition, cohort deep dive, and interview-based root-cause ranking.")

demo_mode = False

_sidebar_caption("1️⃣ Personas — Explore synthetic households")
_sidebar_caption("2️⃣ Research — Run scenario research")
_sidebar_caption("3️⃣ Results — View research results")
_sidebar_caption("4️⃣ Diagnose — Phase A problem decomposition")
_sidebar_caption("5️⃣ Simulate — Phase C intervention testing")
_sidebar_caption("6️⃣ Interviews — Deep dive conversations")
_sidebar_caption("7️⃣ Comparison — Compare two scenarios")

if demo_mode:
    from app.utils.demo_mode import ensure_demo_data

    ensure_demo_data()

if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()

pop: Any = st.session_state.population

scenario_id = st.selectbox(
    "Scenario",
    list(SCENARIO_IDS),
    format_func=lambda sid: f"{get_scenario(sid).name} ({sid})",
    key="phase_a_scenario",
)
scenario = get_scenario(scenario_id)

questions = get_questions_for_scenario(scenario_id)
selected_question = questions[0]

# Run baseline simulation to classify personas into cohorts (cached per scenario)
_cohort_key = f"phase_a_cohorts_{scenario_id}"
if _cohort_key not in st.session_state:
    with st.spinner("Classifying personas into cohorts (baseline simulation)..."):
        st.session_state[_cohort_key] = classify_population(pop, scenario)
pop_cohorts = st.session_state[_cohort_key]

decomp = decompose_problem(scenario, selected_question, pop, pop_cohorts)

st.subheader("Step 1 — Problem Decomposition Display")
st.caption(decomp.problem_title)

st.markdown("**Sub-problems**")
for sp in decomp.sub_problems:
    with st.expander(sp.title, expanded=False):
        st.caption(sp.description)
        st.caption(f"Probe focus: {sp.probe_focus}")

st.markdown("**Cohorts**")
st.caption("Select a cohort to start diagnosis.")

selected_cohort_name = st.session_state.get("phase_a_selected_cohort")
cohort_personas_by_name: dict[str, list[Any]] = {}
for cohort in decomp.cohorts:
    personas = pop.filter_by_cohort(cohort.id).personas
    cohort_personas_by_name[cohort.name] = personas
    size = len(personas)

    cols = st.columns([3, 1, 3, 1])
    cols[0].markdown(f"**{cohort.name}**")
    cols[1].metric("Size", size)
    cols[2].caption(cohort.research_objective)
    button_label = "Selected" if selected_cohort_name == cohort.name else "Select"
    if cols[3].button(button_label, key=f"cohort_select_{cohort.name}"):
        st.session_state["phase_a_selected_cohort"] = cohort.name
        st.rerun()

st.divider()
st.subheader("Step 2 — Cohort Deep Dive")

selected_cohort = None
for c in decomp.cohorts:
    if c.name == st.session_state.get("phase_a_selected_cohort"):
        selected_cohort = c
        break

if selected_cohort is None:
    st.info("Select a cohort to begin diagnosis.")
    st.stop()

cohort_personas = cohort_personas_by_name.get(selected_cohort.name, [])
st.caption(
    f"Cohort: {selected_cohort.name} · {len(cohort_personas)} personas · Objective: {selected_cohort.research_objective}"
)

tree = get_tree_for_question(selected_question.id)
interview_probes = [
    p for p in tree.probes if p.probe_type == ProbeType.INTERVIEW and p.question_template
]

st.markdown("**Probe Questions (filtered to cohort)**")
for p in sorted(interview_probes, key=lambda x: x.order)[:6]:
    st.markdown(f"- {p.question_template}")

st.markdown("**Persona Sample (preview)**")
sample = _sample_personas(cohort_personas, n=5)
for persona in sample:
    with st.container(border=True):
        render_persona_card(persona)

run_clicked = st.button("Run Diagnosis", type="primary", key="phase_a_run")

if run_clicked:
    sub_pop = pop.model_copy(
        update={"tier1_personas": cohort_personas, "tier2_personas": []},
        deep=True,
    )
    sample_size = min(5, len(cohort_personas))
    llm_config = Config(
        llm_mock_enabled=True,
        llm_cache_enabled=False,
        anthropic_api_key="",
    )
    llm_client = LLMClient(llm_config)

    with st.spinner("Running diagnosis (interview pipeline) ..."):
        runner = ResearchRunner(
            population=sub_pop,
            scenario=scenario,
            question=selected_question,
            llm_client=llm_client,
            mock_mode=True,
            alternative_count=0,
            sample_size=sample_size,
        )
        diagnosis = runner.run()
    st.session_state["phase_a_diagnosis"] = diagnosis
    st.rerun()

if "phase_a_diagnosis" in st.session_state:
    diagnosis = st.session_state["phase_a_diagnosis"]
    interview_texts: list[str] = []
    for ir in diagnosis.interview_results:
        for resp in ir.responses:
            interview_texts.append(str(resp.get("answer", "")))

    root_causes = _compute_root_causes([sp.title for sp in decomp.sub_problems], interview_texts)

    st.subheader("Step 3 — Insight Display")

    st.subheader("Root cause ranking")
    fig = go.Figure(
        go.Bar(
            x=[rc["pct"] for rc in root_causes],
            y=[rc["root"] for rc in root_causes],
            orientation="h",
            marker_color="#2ECC71",
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="%",
        yaxis_title="Root cause",
    )
    st.plotly_chart(fig, use_container_width=True, key="phase_a_root_causes")

    for rc in root_causes:
        root = rc["root"]
        top_quotes = _top_quotes_for_root(root, interview_texts, k=2)
        with st.expander(f"{root} ({rc['pct']:.0f}%)", expanded=False):
            for q in top_quotes:
                st.markdown(f"> {q[:400]}")

    st.subheader("Per-cohort insight summary")
    summary_lines = []
    for rc in root_causes[:3]:
        summary_lines.append(f"- {rc['root']}: {rc['pct']:.0f}%")
    summary = "\n".join(summary_lines)
    st.markdown(summary)

    st.divider()
    export_cols = st.columns(2)
    with export_cols[0]:
        import json

        insights_json = json.dumps(
            {
                "scenario_id": scenario_id,
                "cohort": selected_cohort.name,
                "problem_title": decomp.problem_title,
                "sub_problems": [
                    {
                        "title": sp.title,
                        "description": sp.description,
                        "probe_focus": sp.probe_focus,
                        "cohort_id": sp.cohort_id,
                    }
                    for sp in decomp.sub_problems
                ],
                "root_causes": root_causes,
                "summary": summary,
            },
            indent=2,
        )
        st.download_button(
            "⬇️ Export Diagnosis (JSON)",
            data=insights_json,
            file_name=f"{scenario_id}_phase_a_diagnosis.json",
            mime="application/json",
            key="phase_a_export_json",
        )
    with export_cols[1]:
        cohort_df_data = []
        for cohort in decomp.cohorts:
            cohort_df_data.append(
                {
                    "Cohort": cohort.name,
                    "Size": cohort.size,
                    "Objective": cohort.research_objective,
                }
            )
        import pandas as pd

        cohort_df = pd.DataFrame(cohort_df_data)
        st.download_button(
            "⬇️ Export Cohorts (CSV)",
            data=cohort_df.to_csv(index=False),
            file_name=f"{scenario_id}_cohorts.csv",
            mime="text/csv",
            key="phase_a_export_csv",
        )

    if st.button("Proceed to Interventions →", type="primary", key="phase_a_proceed"):
        from src.analysis.intervention_engine import (
            InterventionInput,
            generate_intervention_quadrant,
        )

        decomp_input = InterventionInput(problem_id=selected_question.id)
        quadrant = generate_intervention_quadrant(decomp_input, scenario)

        st.session_state["phase_a_insights"] = {
            "scenario_id": scenario_id,
            "cohort": selected_cohort.name,
            "sub_problems": [sp.title for sp in decomp.sub_problems],
            "root_causes": root_causes,
            "summary": summary,
        }
        st.session_state["phase_a_quadrant"] = quadrant
        st.success("Phase A insights + intervention quadrant saved.")
        st.switch_page("pages/6_simulate.py")
