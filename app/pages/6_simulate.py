# ruff: noqa: N999
"""Phase C — Simulate intervention quadrant UI.

UI-only page for running post-diagnosis intervention simulations and
visualizing lift results.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

import pandas as pd
import streamlit as st

from app.components.quadrant_grid import render_quadrant_grid
from src.analysis.intervention_engine import (
    InterventionInput,
    InterventionQuadrant,
    generate_intervention_quadrant,
    quadrant_key,
)
from src.analysis.quadrant_analysis import (
    InterventionLift,
    QuadrantAnalysis,
    analyze_quadrant_results,
    format_quadrant_table,
)
from src.constants import DEFAULT_SEED
from src.decision.scenarios import get_scenario
from src.simulation.quadrant_runner import (
    InterventionRunResult,
    QuadrantRunResult,
    run_intervention_quadrant,
)
from src.utils.display import cohort_label, scope_label, temporality_label

if TYPE_CHECKING:
    from src.generation.population import Population


if "population" not in st.session_state:
    st.warning("Load or generate a population first.")
    st.stop()

if "phase_a_insights" not in st.session_state:
    st.info("Run Phase A Diagnose first")
    st.stop()

demo_mode = False
st.sidebar.caption("1️⃣ Personas — Explore synthetic households")
st.sidebar.caption("2️⃣ Research — Run scenario research")
st.sidebar.caption("3️⃣ Results — View research results")
st.sidebar.caption("4️⃣ Diagnose — Phase A problem decomposition")
st.sidebar.caption("5️⃣ Simulate — Phase C intervention testing")
st.sidebar.caption("6️⃣ Interviews — Deep dive conversations")
st.sidebar.caption("7️⃣ Comparison — Compare two scenarios")

if demo_mode:
    # Keep consistent with other pages: deterministic demo.
    random.seed(DEFAULT_SEED)

st.header("Phase C — Simulate")

st.page_link(
    "pages/2_diagnose.py",
    label="← Back to Diagnose",
    icon="🔍",
)

pop: Population = st.session_state.population
phase_a_insights: dict[str, Any] = st.session_state["phase_a_insights"]
scenario_id = phase_a_insights["scenario_id"]
scenario = get_scenario(scenario_id)


def _quadrant_total(quadrant: InterventionQuadrant) -> int:
    return sum(len(v) for v in quadrant.quadrants.values())


def _make_demo_quadrant_run_and_analysis(
    quadrant: InterventionQuadrant,
    scenario_obj: Any,
) -> tuple[QuadrantRunResult, QuadrantAnalysis]:
    baseline_adoption_rate = 0.20
    baseline_active_rate = 0.13 if scenario_obj.mode == "temporal" else None

    interventions: list[tuple[str, Any, str]] = []
    for qkey, ints in quadrant.quadrants.items():
        for i in ints:
            interventions.append((qkey, i, i.id))

    if not interventions:
        # Minimal fallback quadrant.
        interventions = [("general_non_temporal", None, "demo_intervention")]

    adoption_spread = [0.02, 0.05, -0.01, 0.03, -0.02]
    adoption_rates: list[float] = []
    for idx in range(len(interventions)):
        drift = adoption_spread[idx % len(adoption_spread)]
        adoption_rates.append(max(0.0, baseline_adoption_rate + drift))

    results: list[InterventionRunResult] = []
    for idx, (_qkey, intervention, _id) in enumerate(interventions):
        if intervention is None:
            intervention_id = "demo_intervention"
            intervention_name = "Demo Intervention"
            scope = "general"
            temporality = "non_temporal"
            target_cohort_id = None
            # Expected mechanism is not used in demo result rows.
        else:
            intervention_id = intervention.id
            intervention_name = intervention.name
            scope = intervention.scope
            temporality = intervention.temporality
            target_cohort_id = intervention.target_cohort_id
            # Expected mechanism is not used in demo result rows.

        tested = max(1, len(pop.personas))
        adoption_rate = adoption_rates[idx]
        adoption_count = round(tested * adoption_rate)

        final_active_rate = None
        total_revenue = None
        if scenario_obj.mode == "temporal" and baseline_active_rate is not None:
            final_active_rate = max(
                0.0, baseline_active_rate + (adoption_rate - baseline_adoption_rate) / 2
            )
            total_revenue = tested * 1000.0 * adoption_rate

        results.append(
            InterventionRunResult(
                intervention_id=intervention_id,
                intervention_name=intervention_name,
                scope=scope,
                temporality=temporality,
                target_cohort_id=target_cohort_id,
                adoption_rate=adoption_rate,
                adoption_count=adoption_count,
                population_tested=tested,
                final_active_rate=final_active_rate,
                total_revenue=total_revenue,
                monthly_snapshots=None,
                rejection_distribution={},
            )
        )

    run_result = QuadrantRunResult(
        scenario_id=scenario_obj.id,
        baseline_adoption_rate=baseline_adoption_rate,
        baseline_active_rate=baseline_active_rate,
        baseline_revenue=None,
        results=results,
        duration_seconds=0.01,
        population_size=len(pop.personas),
        seed=DEFAULT_SEED,
    )

    ranked: list[InterventionLift] = []
    quadrant_summaries: dict[str, dict[str, Any]] = {
        "general_temporal": {"avg_lift": 0.0, "best": None, "count": 0},
        "general_non_temporal": {"avg_lift": 0.0, "best": None, "count": 0},
        "cohort_temporal": {"avg_lift": 0.0, "best": None, "count": 0},
        "cohort_non_temporal": {"avg_lift": 0.0, "best": None, "count": 0},
    }

    # Compute lifts and ranks.
    baseline = baseline_adoption_rate
    baseline_active = baseline_active_rate

    for idx, r in enumerate(results, start=1):
        lift_abs = r.adoption_rate - baseline
        lift_pct = (lift_abs / baseline * 100.0) if baseline else 0.0
        active_rate_lift_pct: float | None = None
        active_rate_lift_abs: float | None = None
        if baseline_active is not None and r.final_active_rate is not None:
            active_rate_lift_abs = r.final_active_rate - baseline_active
            active_rate_lift_pct = (
                active_rate_lift_abs / baseline_active * 100.0 if baseline_active else 0.0
            )

        qkey = quadrant_key(r.scope, r.temporality)

        ranked.append(
            InterventionLift(
                intervention_id=r.intervention_id,
                intervention_name=r.intervention_name,
                scope=r.scope,
                temporality=r.temporality,
                target_cohort_id=r.target_cohort_id,
                expected_mechanism="Demo mechanism",
                adoption_lift_abs=lift_abs,
                adoption_lift_pct=lift_pct,
                active_rate_lift_abs=active_rate_lift_abs,
                active_rate_lift_pct=active_rate_lift_pct,
                revenue_lift=None,
                rank=idx,
                quadrant_key=qkey,
            )
        )

    ranked.sort(key=lambda x: x.adoption_lift_pct, reverse=True)
    for idx, row in enumerate(ranked, start=1):
        row.rank = idx

    for qkey in quadrant_summaries:
        bucket = [x for x in ranked if x.quadrant_key == qkey]
        if not bucket:
            continue
        avg_lift = sum(x.adoption_lift_pct for x in bucket) / len(bucket)
        best = max(bucket, key=lambda x: x.adoption_lift_pct)
        quadrant_summaries[qkey] = {
            "avg_lift": avg_lift,
            "best": best.intervention_name,
            "count": len(bucket),
        }

    analysis = QuadrantAnalysis(
        scenario_id=scenario_obj.id,
        baseline_adoption_rate=baseline_adoption_rate,
        baseline_active_rate=baseline_active_rate,
        ranked_interventions=ranked,
        top_recommendation=ranked[0],
        quadrant_summaries=quadrant_summaries,
    )

    return run_result, analysis


# STEP 1 — Intervention quadrant
phase_a_quadrant: InterventionQuadrant | None = st.session_state.get("phase_a_quadrant")
if phase_a_quadrant is None:
    decomp = InterventionInput(problem_id=phase_a_insights["scenario_id"])
    phase_a_quadrant = generate_intervention_quadrant(decomp, scenario)

quadrant = phase_a_quadrant

render_quadrant_grid(quadrant)
st.caption(f"Total interventions: {_quadrant_total(quadrant)}")


# STEP 2 — Run simulation
scope_choice = st.selectbox(
    "Simulation scope",
    ["All interventions", "Selected quadrant only"],
    key="phase_c_scope",
)

selected_quadrant_key = None
if scope_choice == "Selected quadrant only":
    selected_quadrant_key = st.radio(
        "Which quadrant?",
        list(quadrant.quadrants.keys()),
        format_func=lambda x: x.replace("_", " ").title(),
        key="phase_c_quad_radio",
    )

run_clicked = st.button(
    "Run Simulation",
    type="primary",
    use_container_width=True,
    key="phase_c_run_btn",
)

if run_clicked:
    if demo_mode:
        mock_run, mock_analysis = _make_demo_quadrant_run_and_analysis(quadrant, scenario)
        st.session_state["phase_c_run_result"] = mock_run
        st.session_state["phase_c_analysis"] = mock_analysis
        st.rerun()
    else:
        with st.spinner("Running intervention simulations..."):
            q_to_run = quadrant
            if selected_quadrant_key is not None:
                q_to_run = InterventionQuadrant(
                    problem_id=quadrant.problem_id,
                    quadrants={
                        selected_quadrant_key: quadrant.quadrants.get(selected_quadrant_key, [])
                    },
                )
            run_result = run_intervention_quadrant(q_to_run, pop, scenario)
        st.session_state["phase_c_run_result"] = run_result
        st.rerun()


# STEP 3 — Results
if "phase_c_run_result" in st.session_state:
    run_result = st.session_state["phase_c_run_result"]

    if demo_mode and "phase_c_analysis" in st.session_state:
        analysis = st.session_state["phase_c_analysis"]
    else:
        analysis = analyze_quadrant_results(run_result, quadrant)

    st.success(
        "🏆 Top recommendation: "
        f"{analysis.top_recommendation.intervention_name} "
        f"(+{analysis.top_recommendation.adoption_lift_pct:.1f}% adoption lift)"
    )

    rows = format_quadrant_table(analysis)
    df = pd.DataFrame(rows)
    df["scope"] = df["scope"].apply(scope_label)
    df["temporality"] = df["temporality"].apply(temporality_label)
    df["cohort"] = df["cohort"].apply(cohort_label)
    df = df.rename(
        columns={
            "name": "Intervention",
            "scope": "Scope",
            "temporality": "Timing",
            "cohort": "Target Cohort",
            "baseline_adoption": "Baseline",
            "intervention_adoption": "With Intervention",
            "lift_pct": "Lift (%)",
            "rank": "Rank",
        }
    )
    st.dataframe(df, use_container_width=True)

    for qkey, summary in analysis.quadrant_summaries.items():
        with st.expander(qkey.replace("_", " ").title()):
            st.metric("Avg adoption lift", f"{summary['avg_lift']:.1f}%")
            st.caption(f"Best: {summary['best']}")

    st.caption(
        f"Simulation completed in {run_result.duration_seconds:.1f}s "
        f"across {len(run_result.results)} interventions"
    )

    st.divider()
    sim_export_cols = st.columns(2)
    with sim_export_cols[0]:
        sim_df = df
        st.download_button(
            "⬇️ Export Results (CSV)",
            data=sim_df.to_csv(index=False),
            file_name=f"{scenario_id}_phase_c_results.csv",
            mime="text/csv",
            key="phase_c_export_csv",
        )
    with sim_export_cols[1]:
        import json

        sim_json = json.dumps(
            {
                "scenario_id": analysis.scenario_id,
                "baseline_adoption_rate": analysis.baseline_adoption_rate,
                "baseline_active_rate": analysis.baseline_active_rate,
                "top_recommendation": {
                    "name": analysis.top_recommendation.intervention_name,
                    "adoption_lift_pct": analysis.top_recommendation.adoption_lift_pct,
                    "quadrant": analysis.top_recommendation.quadrant_key,
                },
                "quadrant_summaries": analysis.quadrant_summaries,
                "interventions": rows,
            },
            indent=2,
        )
        st.download_button(
            "⬇️ Export Results (JSON)",
            data=sim_json,
            file_name=f"{scenario_id}_phase_c_results.json",
            mime="application/json",
            key="phase_c_export_json",
        )

    st.divider()
    nav_cols = st.columns(3)
    with nav_cols[0]:
        st.page_link("pages/2_diagnose.py", label="← Diagnose", icon="🔍")
    with nav_cols[1]:
        st.page_link("pages/3_results.py", label="📊 Research Results")
    with nav_cols[2]:
        st.page_link("pages/1_personas.py", label="👥 Personas")
