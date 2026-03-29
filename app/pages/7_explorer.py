# ruff: noqa: N999
"""Scenario Explorer — auto-generate and compare hundreds of scenario variations."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.constants import DASHBOARD_BRAND_COLORS, SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.utils.display import display_name

st.title("Scenario Explorer")
st.caption(
    "Run hundreds of scenario variations to find the optimal configuration for your population. "
    "Zero LLM cost — pure simulation."
)


def _format_variant_mods(mods: Any, limit: int = 3) -> str:
    if not mods or not isinstance(mods, dict):
        return "—"
    parts: list[str] = []
    for k, v in list(mods.items())[:limit]:
        key = str(k).split(".")[-1]
        parts.append(f"{key}: {v}")
    return ", ".join(parts) if parts else "—"


scenario_id = st.selectbox(
    "Base Scenario",
    SCENARIO_IDS,
    format_func=lambda sid: get_scenario(sid).name,
    key="explorer_scenario",
)

strategy_options = {
    "smart": "🧠 Smart — Target rejection reasons",
    "sweep": "📊 Sweep — One parameter at a time",
    "grid": "🔢 Grid — Parameter combinations",
    "random": "🎲 Random — Monte Carlo sampling",
}

strategy = st.radio(
    "Exploration Strategy",
    options=list(strategy_options.keys()),
    format_func=lambda s: strategy_options[s],
    horizontal=True,
    key="explorer_strategy",
)

n_variants = 100
if strategy == "random":
    n_variants = st.slider(
        "Number of variants",
        min_value=50,
        max_value=1000,
        value=100,
        step=50,
        key="explorer_n_variants",
        help=(
            "More variants = better coverage but longer runtime. 100 variants takes ~30 seconds."
        ),
    )


run_clicked = st.button(
    "🚀 Explore Variations",
    type="primary",
    use_container_width=True,
    key="explorer_run",
)


# Clear results when scenario changes
if st.session_state.get("explorer_scenario_id") != scenario_id:
    st.session_state.pop("explorer_report", None)
    st.session_state.pop("explorer_scenario_id", None)


if run_clicked:
    if "population" not in st.session_state:
        st.error("No population found. Generate one from the Home page first.")
        st.stop()

    pop = st.session_state.population
    base_scenario = get_scenario(scenario_id)

    try:
        from src.simulation.batch import BatchSimulationRunner
        from src.simulation.consolidation import ExplorationConsolidator
        from src.simulation.explorer import VariantStrategy, generate_variants
        from src.simulation.static import run_static_simulation
    except ImportError:
        st.error("Exploration modules not yet available. Waiting for Sprint 10 Tracks A & B.")
        st.stop()

    base_result = None
    if strategy == "smart":
        with st.spinner("Running baseline scenario..."):
            base_result = run_static_simulation(pop, base_scenario)

    with st.spinner("Generating scenario variants..."):
        variants = generate_variants(
            base=base_scenario,
            strategy=VariantStrategy(strategy),
            n_variants=n_variants,
            base_result=base_result,
        )

    st.caption(f"Generated {len(variants)} variants (including baseline)")

    progress_bar = st.progress(0.0)
    status_text = st.empty()

    def on_progress(done: int, total: int) -> None:
        if total:
            progress_bar.progress(done / total)
        status_text.caption(f"Running variant {done}/{total}...")

    runner = BatchSimulationRunner(pop)
    results = runner.run_batch(variants, progress_callback=on_progress)

    progress_bar.progress(1.0)
    status_text.caption("✅ All variants complete")

    consolidator = ExplorationConsolidator()
    report = consolidator.consolidate(
        base_scenario_id=scenario_id,
        base_scenario=base_scenario,
        all_results=results,
        execution_time=0.0,
        strategy=strategy,
    )

    st.session_state["explorer_report"] = report
    st.session_state["explorer_scenario_id"] = scenario_id
    st.rerun()


if "explorer_report" in st.session_state:
    report = st.session_state["explorer_report"]

    st.divider()
    st.subheader("Exploration Results")

    base_result = report.baseline_result
    best_result = report.best_result
    worst_result = report.worst_result
    median_adoption_rate = report.median_adoption_rate

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Your Scenario", f"{base_result.adoption_rate:.0%}")
    m2.metric(
        "Best Variant",
        f"{best_result.adoption_rate:.0%}",
        delta=f"{best_result.adoption_rate - base_result.adoption_rate:+.0%}",
    )
    m3.metric(
        "Worst Variant",
        f"{worst_result.adoption_rate:.0%}",
        delta=f"{worst_result.adoption_rate - base_result.adoption_rate:+.0%}",
    )
    m4.metric("Median Adoption", f"{median_adoption_rate:.0%}")

    missed_insights = report.missed_insights
    if missed_insights:
        st.subheader("⚡ You Missed This")
        for insight in missed_insights[:5]:
            with st.container(border=True):
                cols = st.columns([0.7, 0.3])
                with cols[0]:
                    st.markdown(f"**{insight.variant_name}**")
                    st.write(insight.explanation)
                    for diff in insight.key_differences[:20]:
                        st.markdown(f"- {diff}")
                with cols[1]:
                    insight_rate = float(insight.adoption_rate)
                    lift = float(insight.lift_over_baseline)
                    st.metric(
                        "Adoption Rate",
                        f"{insight_rate:.0%}",
                        delta=f"+{lift:.0%} vs yours",
                    )

    parameter_sensitivities = report.parameter_sensitivities
    if parameter_sensitivities:
        st.subheader("Parameter Sensitivity")
        st.caption("Which parameters move the needle most?")

        sens_df = pd.DataFrame(
            [
                {
                    "Parameter": s.parameter_display_name,
                    "Impact": s.sensitivity_score,
                    "Best Value": s.max_value,
                    "Worst Value": s.min_value,
                }
                for s in parameter_sensitivities[:10]
            ]
        )

        fig = px.bar(
            sens_df,
            x="Impact",
            y="Parameter",
            orientation="h",
            title="Adoption rate swing by parameter",
            color="Impact",
            color_continuous_scale="RdYlGn",
        )
        fig.update_layout(
            height=400,
            showlegend=False,
            yaxis={"autorange": "reversed"},
        )
        fig.update_xaxes(title="Adoption Rate Range (max - min)", tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Adoption Distribution")
    all_results = report.all_results
    rates = [float(r.adoption_rate) for r in all_results]
    rates_df = pd.DataFrame({"adoption_rate": rates})
    baseline_rate = float(base_result.adoption_rate)

    fig_hist = px.histogram(
        rates_df,
        x="adoption_rate",
        nbins=30,
        title=f"Adoption rate distribution across {report.total_variants} variants",
        color_discrete_sequence=[DASHBOARD_BRAND_COLORS["primary"]],
    )
    fig_hist.add_vline(
        x=baseline_rate,
        line_dash="dash",
        line_color=DASHBOARD_BRAND_COLORS["accent"],
        annotation_text="Your scenario",
    )
    fig_hist.update_xaxes(title="Adoption Rate", tickformat=".0%")
    fig_hist.update_yaxes(title="Number of Variants")
    fig_hist.update_layout(height=400)
    st.plotly_chart(fig_hist, use_container_width=True)

    st.subheader("All Variants")
    table_data: list[dict[str, Any]] = []
    for r in all_results:
        mods_summary = _format_variant_mods(r.modifications, limit=3)
        table_data.append(
            {
                "Rank": r.rank,
                "Variant": r.variant_name,
                "Adoption": f"{float(r.adoption_rate):.1%}",
                "Count": r.adoption_count,
                "Key Changes": mods_summary,
            }
        )

    st.dataframe(
        pd.DataFrame(table_data),
        use_container_width=True,
        hide_index=True,
    )

    recommended_mods = report.recommended_modifications
    if recommended_mods:
        st.subheader("Recommended Configuration")
        st.caption("Based on the best-performing variant")

        rec_cols = st.columns(2)
        items = list(recommended_mods.items())
        for i, (path, value) in enumerate(items):
            col = rec_cols[i % 2]
            field = display_name(str(path).split(".")[-1])
            if isinstance(value, float) and "price" not in str(path):
                col.metric(field, f"{value:.0%}")
            elif isinstance(value, bool):
                col.metric(field, "Enabled" if value else "Disabled")
            else:
                col.metric(field, str(value))
