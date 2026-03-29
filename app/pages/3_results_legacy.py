# Streamlit multipage: numeric module name (``3_…``) is required for sidebar order.
# ruff: noqa: N999
"""
Results Dashboard — KPIs, decision pathway, segments, barriers, causal insights, what-if.

Legacy snapshot (Sprint 14). Prefer the hybrid Research Results flow on ``3_results.py``.
"""

from __future__ import annotations

import streamlit as st

from src.analysis.barriers import analyze_barriers, summarize_barrier_stages
from src.analysis.causal import compute_variable_importance, generate_causal_statements
from src.analysis.segments import analyze_segments
from src.analysis.waterfall import compute_funnel_waterfall
from src.constants import (
    DASHBOARD_WHATIF_POPULATION_SIZE,
    DEFAULT_SIMULATION_MONTHS,
    SCENARIO_IDS,
)
from src.decision.scenarios import get_scenario
from src.simulation.static import StaticSimulationResult, run_static_simulation
from src.simulation.temporal import run_temporal_simulation
from src.utils.dashboard_data import adoption_heatmap_matrix, tier1_dataframe_with_results
from src.utils.viz import (
    create_barrier_chart,
    create_funnel_chart,
    create_importance_bar,
    create_segment_heatmap,
    create_temporal_chart,
)

st.title("Results Dashboard")
st.caption(
    "Static decision-pathway outcomes, segment heatmaps, barriers, drivers, and quick what-if runs."
)

if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()

pop = st.session_state.population


def _coerce_static(entry: object) -> StaticSimulationResult | None:
    if isinstance(entry, StaticSimulationResult):
        return entry
    if isinstance(entry, dict) and "results_by_persona" in entry:
        try:
            return StaticSimulationResult.model_validate(entry)
        except Exception:
            return None
    return None


scenario_id = st.selectbox(
    "Scenario",
    list(SCENARIO_IDS),
    key="selected_scenario",
)

raw_entry = (st.session_state.get("scenario_results") or {}).get(scenario_id)
static = _coerce_static(raw_entry)

if static is None:
    st.info("No static simulation results for this scenario. Open the home page to pre-compute runs.")
    st.stop()

results: dict[str, dict] = dict(static.results_by_persona)
scenario = get_scenario(scenario_id)

merged_results: dict[str, dict] = {}
for pid, row in results.items():
    try:
        merged_results[pid] = {**pop.get_persona(pid).to_flat_dict(), **row}
    except KeyError:
        merged_results[pid] = dict(row)

n = len(results)
adopt_n = static.adoption_count
reject_n = max(0, n - adopt_n)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Population (Tier 1)", f"{n:,}")
k2.metric("Positive response rate", f"{static.adoption_rate:.1%}")
k3.metric("Positive response", f"{adopt_n:,}")
k4.metric("No / not now", f"{reject_n:,}")

st.subheader("Decision pathway waterfall")
waterfall = compute_funnel_waterfall(results)
st.plotly_chart(create_funnel_chart(waterfall), use_container_width=True)

st.subheader("Segment response heatmap")
df_seg = tier1_dataframe_with_results(pop, results)
mat, row_lbl, col_lbl = adoption_heatmap_matrix(df_seg, "city_tier", "income_bracket")
if mat and row_lbl and col_lbl:
    st.plotly_chart(
        create_segment_heatmap(
            [],
            "city_tier vs income_bracket",
            matrix=mat,
            row_labels=row_lbl,
            col_labels=col_lbl,
        ),
        use_container_width=True,
    )
else:
    segs = analyze_segments(merged_results, group_by="city_tier")
    st.plotly_chart(create_segment_heatmap(segs, "city_tier"), use_container_width=True)

st.subheader("Barrier distribution")
barriers = analyze_barriers(results)
st.plotly_chart(create_barrier_chart(barriers), use_container_width=True)
with st.expander("Stage summaries", expanded=False):
    for summary in summarize_barrier_stages(results):
        reasons = ", ".join(summary.top_reasons) if summary.top_reasons else "—"
        st.markdown(
            f"**{summary.stage}** — {summary.total_dropped} drops "
            f"({summary.percentage_of_rejections:.1%} of rejection events); top reasons: {reasons}"
        )

st.subheader("Variable importance")
importances = compute_variable_importance(merged_results)
if importances:
    st.plotly_chart(create_importance_bar(importances), use_container_width=True)
else:
    st.caption("Not enough numeric features in merged rows to fit the importance model.")

st.subheader("Causal statements")
statements = generate_causal_statements(importances, merged_results, scenario_id=scenario_id)
if statements:
    for stmt in statements:
        with st.expander(f"{stmt.statement[:100]}…" if len(stmt.statement) > 100 else stmt.statement):
            st.write(stmt.statement)
            st.caption(
                f"Evidence strength: {stmt.evidence_strength:.2f} · "
                f"Variables: {', '.join(stmt.supporting_variables)}"
                + (f" · Segment: {stmt.segment}" if stmt.segment else "")
            )
else:
    st.caption("No causal statements (needs importances and segmentable numeric splits).")

with st.expander("Temporal simulation (Mode B)", expanded=False):
    months = st.slider("Months", 3, 24, min(DEFAULT_SIMULATION_MONTHS, 12), key="temporal_months")
    if st.button("Run temporal", key="run_temporal"):
        with st.spinner("Running temporal simulation…"):
            temporal = run_temporal_simulation(pop, scenario, months=months)
        st.plotly_chart(create_temporal_chart(temporal), use_container_width=True)
        st.caption(
            f"Final positive response rate {temporal.final_adoption_rate:.1%} · "
            f"Active rate {temporal.final_active_rate:.1%}"
        )

st.subheader("What-if (static, subset)")
st.caption(
    f"Re-runs static simulation on the first {DASHBOARD_WHATIF_POPULATION_SIZE} Tier 1 personas "
    "with adjusted product and marketing levers (fast preview, not full cohort)."
)
base = scenario
w1, w2, w3 = st.columns(3)
with w1:
    price = st.slider(
        "Price (INR)",
        min_value=float(base.product.price_inr) * 0.5,
        max_value=float(base.product.price_inr) * 1.5,
        value=float(base.product.price_inr),
        step=1.0,
        key="whatif_price",
        help=(
            "Drag to test how price changes affect positive response. "
            "This runs a quick simulation on a subset of personas."
        ),
    )
with w2:
    taste = st.slider(
        "Taste appeal",
        0.0,
        1.0,
        float(base.product.taste_appeal),
        0.01,
        key="whatif_taste",
        help=(
            "How likely kids accept the taste. 0 = refuse, 1 = love it. "
            "Try 0.8+ for gummy formats."
        ),
    )
with w3:
    ab = st.slider(
        "Awareness budget",
        0.0,
        1.0,
        float(base.marketing.awareness_budget),
        0.01,
        key="whatif_ab",
        help=(
            "Marketing reach. 0 = no spend, 1 = saturated. "
            "See how awareness scaling changes positive response."
        ),
    )

if st.button("Run What-If", key="run_whatif"):
    n_what = min(DASHBOARD_WHATIF_POPULATION_SIZE, len(pop.personas))
    mini = pop.model_copy(
        update={
            "tier1_personas": pop.personas[:n_what],
            "tier2_personas": [],
        },
        deep=True,
    )
    mod = base.model_copy(
        update={
            "product": base.product.model_copy(
                update={"price_inr": price, "taste_appeal": taste}
            ),
            "marketing": base.marketing.model_copy(update={"awareness_budget": ab}),
        },
        deep=True,
    )
    with st.spinner("Running static what-if…"):
        baseline_mini = run_static_simulation(mini, base)
        cf_mini = run_static_simulation(mini, mod)
    d_adopt = cf_mini.adoption_rate - baseline_mini.adoption_rate
    st.metric(
        "Positive response rate delta (subset)",
        f"{d_adopt:+.2%}",
        help=f"Subset size {n_what}; baseline {baseline_mini.adoption_rate:.1%} → "
        f"counterfactual {cf_mini.adoption_rate:.1%}",
    )
