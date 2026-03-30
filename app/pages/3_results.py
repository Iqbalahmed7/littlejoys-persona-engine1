# Streamlit multipage: numeric module name (``3_…``) is required for sidebar order.
# ruff: noqa: N999
"""
Research Results — consolidated hybrid pipeline report (Sprint 14).
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from src.analysis.barriers import analyze_barriers, summarize_barrier_stages
from src.analysis.causal import compute_variable_importance, generate_causal_statements
from src.analysis.research_consolidator import ConsolidatedReport, consolidate_research
from src.analysis.segments import analyze_segments
from src.analysis.waterfall import compute_funnel_waterfall
from src.constants import (
    DASHBOARD_WHATIF_POPULATION_SIZE,
    DEFAULT_SIMULATION_MONTHS,
    SCENARIO_IDS,
)
from src.decision.scenarios import get_scenario
from src.simulation.research_runner import ResearchResult
from src.simulation.static import StaticSimulationResult, run_static_simulation
from src.simulation.temporal import run_temporal_simulation
from src.utils.dashboard_data import adoption_heatmap_matrix, tier1_dataframe_with_results
from src.utils.display import display_name
from src.utils.viz import (
    create_barrier_chart,
    create_funnel_chart,
    create_importance_bar,
    create_segment_heatmap,
    create_temporal_chart,
)

_CHART_HEIGHT = 300
_CHART_MARGINS = dict(l=20, r=20, t=40, b=20)

_HUMAN_LABELS: dict[str, str] = {
    "price_salience": "Price Sensitivity",
    "brand_salience": "Brand Awareness",
    "child_acceptance": "Child Acceptance",
    "habit_strength": "Usage Habit",
    "effort_friction": "Effort / Friction",
    "perceived_value": "Perceived Value",
    "reorder_urgency": "Reorder Urgency",
    "discretionary_budget": "Budget Headroom",
    "trust": "Trust",
    "fatigue": "Fatigue",
}


def _label(key: str) -> str:
    """Convert internal variable keys into UI-friendly labels."""

    return _HUMAN_LABELS.get(key, key.replace("_", " ").title())


def _snap_val(row: dict[str, Any], *keys: str, default: Any = 0) -> Any:
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return default


def _cluster_bar_color(cluster_name: str) -> str:
    n = cluster_name.lower()
    if "loyal" in n and "repeat" in n:
        return "#2ca02c"
    if "churn" in n or "lapsed" in n:
        return "#d62728"
    if "never" in n:
        return "#7f7f7f"
    return "#aec7e8"


def _coerce_static(entry: object) -> StaticSimulationResult | None:
    """Normalize session ``scenario_results`` entries to :class:`StaticSimulationResult`."""

    if isinstance(entry, StaticSimulationResult):
        return entry
    if isinstance(entry, dict) and "results_by_persona" in entry:
        try:
            return StaticSimulationResult.model_validate(entry)
        except Exception:
            return None
    return None


def _render_legacy_dashboard() -> None:
    """Static results dashboard (home-page quick run or Scenario Configurator)."""

    pop = st.session_state.population

    st.subheader("Simulation summary (legacy)")
    st.caption(
        "Static decision-pathway outcomes, segment heatmaps, barriers, drivers, and quick what-if runs."
    )

    scenario_id = st.selectbox(
        "Scenario",
        list(SCENARIO_IDS),
        key="selected_scenario",
    )

    raw_entry = (st.session_state.get("scenario_results") or {}).get(scenario_id)
    static = _coerce_static(raw_entry)

    if static is None:
        st.info(
            "No static simulation results for this scenario. Open the home page to pre-compute runs."
        )
        return

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
            with st.expander(
                f"{stmt.statement[:100]}…" if len(stmt.statement) > 100 else stmt.statement
            ):
                st.write(stmt.statement)
                st.caption(
                    f"Evidence strength: {stmt.evidence_strength:.2f} · "
                    f"Variables: {', '.join(stmt.supporting_variables)}"
                    + (f" · Segment: {stmt.segment}" if stmt.segment else "")
                )
    else:
        st.caption("No causal statements (needs importances and segmentable numeric splits).")

    with st.expander("Temporal simulation (Mode B)", expanded=False):
        months = st.slider(
            "Months", 3, 24, min(DEFAULT_SIMULATION_MONTHS, 12), key="temporal_months"
        )
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


@st.cache_data(show_spinner="Preparing PDF…")
def _research_pdf_bytes(_report_json: str) -> bytes:
    """Cache PDF generation; keyed by consolidated report JSON."""

    from src.analysis.pdf_export import generate_pdf_report

    rpt = ConsolidatedReport.model_validate_json(_report_json)
    scenario = get_scenario(rpt.scenario_id)
    return generate_pdf_report(rpt, scenario)


@st.cache_data(show_spinner="Consolidating results...")
def _consolidate(_result_json: str, _population_id: str) -> dict[str, Any]:
    """Rebuild :class:`ConsolidatedReport` from cached JSON; uses live session population."""

    from src.config import Config
    from src.utils.api_keys import has_api_key, resolve_api_key
    from src.utils.llm import LLMClient

    r = ResearchResult.model_validate_json(_result_json)
    pop = st.session_state.population
    llm_client = None
    if not r.metadata.mock_mode and has_api_key():
        llm_client = LLMClient(
            Config(
                llm_mock_enabled=False,
                llm_cache_enabled=True,
                anthropic_api_key=resolve_api_key(),
            )
        )
    report = consolidate_research(r, pop, llm_client=llm_client)
    return report.model_dump(mode="json")


if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()

st.header("Research Results")
st.caption(
    "Quantitative findings, qualitative themes, and strategic alternatives from your research run."
)

if "research_result" in st.session_state:
    result = st.session_state["research_result"]
    pop = st.session_state.population

    report = ConsolidatedReport.model_validate(
        _consolidate(result.model_dump_json(), pop.id),
    )

    event_monthly_rows = report.event_monthly_rollup or []
    pop_n = max(report.funnel.population_size, 1)

    if event_monthly_rows:
        month1_trial_pct = (
            float(_snap_val(event_monthly_rows[0], "new_adopters", default=0)) / pop_n * 100.0
        )
        final_active_pct = (
            float(_snap_val(event_monthly_rows[-1], "total_active", "active", default=0))
            / pop_n
            * 100.0
        )
        total_repeat_purchases = int(
            sum(int(_snap_val(r, "repeat_purchasers", default=0)) for r in event_monthly_rows),
        )
    else:
        month1_trial_pct = None
        final_active_pct = None
        total_repeat_purchases = None

    peak_churn_month = report.peak_churn_month
    health_banner_rendered = False

    if report.executive_summary:
        st.markdown(f"### {report.executive_summary.headline}")
        st.markdown(report.executive_summary.trajectory_summary)

        col_es1, col_es2, col_es3 = st.columns(3)
        with col_es1:
            st.markdown("**Key Drivers**")
            for d in report.executive_summary.key_drivers:
                st.markdown(f"- {d}")
        with col_es2:
            st.markdown("**Recommendations**")
            for r_item in report.executive_summary.recommendations:
                st.markdown(f"- {r_item}")
        with col_es3:
            st.markdown("**Risk Factors**")
            for r_item in report.executive_summary.risk_factors:
                st.markdown(f"- {r_item}")
        st.divider()

        health_cols = st.columns(4)
        health_cols[0].metric(
            "Month-1 Trial %",
            f"{month1_trial_pct:.1f}%" if month1_trial_pct is not None else "—",
            help=("Percentage of the population that becomes new adopters in month 1"),
        )
        health_cols[1].metric(
            "Final Active %",
            f"{final_active_pct:.1f}%" if final_active_pct is not None else "—",
            help="Percentage of the population still actively using the product at the end of the simulation",
        )
        health_cols[2].metric(
            "Repeat Purchases",
            f"{total_repeat_purchases:,}" if total_repeat_purchases is not None else "—",
            help="Total number of repeat purchase actions across all months",
        )
        health_cols[3].metric(
            "Peak Churn Month",
            f"Month {peak_churn_month}" if peak_churn_month is not None else "—",
            help="Month when the simulation had the highest churn count",
        )
        health_banner_rendered = True

    st.subheader(f"{report.scenario_name}: {report.question_title}")
    st.caption(report.question_description)

    if report.mock_mode:
        st.info(
            "🧪 Mock mode: Insights reflect model structure. Run with an API key for LLM-powered qualitative depth.",
        )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Population", f"{report.funnel.population_size:,}")
    m2.metric(
        "Would Try", f"{report.funnel.adoption_count:,}", f"{report.funnel.adoption_rate:.1%}"
    )
    m3.metric("Interviews", f"{report.interview_count}")
    m4.metric(
        "Alternatives Tested",
        f"{len(report.top_alternatives) + len(report.worst_alternatives)}",
    )
    m5.metric("Duration", f"{report.duration_seconds:.1f}s")

    if not health_banner_rendered:
        health_cols = st.columns(4)
        health_cols[0].metric(
            "Month-1 Trial %",
            f"{month1_trial_pct:.1f}%" if month1_trial_pct is not None else "—",
            help=("Percentage of the population that becomes new adopters in month 1"),
        )
        health_cols[1].metric(
            "Final Active %",
            f"{final_active_pct:.1f}%" if final_active_pct is not None else "—",
            help="Percentage of the population still actively using the product at the end of the simulation",
        )
        health_cols[2].metric(
            "Repeat Purchases",
            f"{total_repeat_purchases:,}" if total_repeat_purchases is not None else "—",
            help="Total number of repeat purchase actions across all months",
        )
        health_cols[3].metric(
            "Peak Churn Month",
            f"Month {peak_churn_month}" if peak_churn_month is not None else "—",
            help="Month when the simulation had the highest churn count",
        )

    st.subheader("Decision Pathway")
    # ``report.funnel.waterfall_data`` is stage→passed counts only; chart needs full waterfall rows.
    wf = compute_funnel_waterfall(result.primary_funnel.results_by_persona)
    st.plotly_chart(create_funnel_chart(wf), use_container_width=True)

    if report.funnel.top_barriers:
        st.caption("Top barriers to trial:")
        for b in report.funnel.top_barriers[:5]:
            st.markdown(f"- **{b['stage']}** → {b['reason']} ({b['count']} personas)")

    monthly_rows = report.event_monthly_rollup or report.temporal_snapshots
    has_event_daily = bool(report.event_daily_rollups)

    if has_event_daily or monthly_rows:
        st.subheader("Repeat Purchase Trajectory")
        traj_key = "event_trajectory" if has_event_daily else "temporal_trajectory"

        resolution = "Show monthly"
        if has_event_daily:
            resolution = st.radio(
                "Resolution",
                ["Show daily", "Show monthly"],
                horizontal=True,
                key="traj_resolution_radio",
            )

        traj_fig = go.Figure()
        if resolution == "Show daily" and has_event_daily:
            daily = report.event_daily_rollups or []
            xs = [int(d["day"]) for d in daily]
            traj_fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=[int(d["total_active"]) for d in daily],
                    mode="lines+markers",
                    name="Total active",
                    line={"color": "#1f77b4", "width": 3},
                )
            )
            traj_fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=[int(d["new_adopters"]) for d in daily],
                    mode="lines+markers",
                    name="New adopters",
                    line={"color": "#2ca02c", "width": 2},
                )
            )
            traj_fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=[int(d["churned"]) for d in daily],
                    mode="lines+markers",
                    name="Churned",
                    line={"color": "#d62728", "width": 2},
                )
            )
            traj_fig.update_layout(
                height=_CHART_HEIGHT,
                margin=_CHART_MARGINS,
                xaxis_title="Day",
                yaxis_title="Personas",
                legend={
                    "orientation": "h",
                    "yanchor": "bottom",
                    "y": 1.02,
                    "xanchor": "right",
                    "x": 1,
                },
            )
        elif monthly_rows:
            months = [int(_snap_val(s, "month")) for s in monthly_rows]
            total_active = [float(_snap_val(s, "total_active", "active")) for s in monthly_rows]
            new_adopters = [float(_snap_val(s, "new_adopters")) for s in monthly_rows]
            churned_s = [float(_snap_val(s, "churned")) for s in monthly_rows]
            traj_fig.add_trace(
                go.Scatter(
                    x=months,
                    y=total_active,
                    mode="lines+markers",
                    name="Total active",
                    line={"color": "#1f77b4", "width": 3},
                )
            )
            traj_fig.add_trace(
                go.Scatter(
                    x=months,
                    y=new_adopters,
                    mode="lines+markers",
                    name="New adopters",
                    line={"color": "#2ca02c", "width": 2},
                )
            )
            traj_fig.add_trace(
                go.Scatter(
                    x=months,
                    y=churned_s,
                    mode="lines+markers",
                    name="Churned",
                    line={"color": "#d62728", "width": 2},
                )
            )
            traj_fig.update_layout(
                height=_CHART_HEIGHT,
                margin=_CHART_MARGINS,
                xaxis_title="Month",
                yaxis_title="Personas",
                legend={
                    "orientation": "h",
                    "yanchor": "bottom",
                    "y": 1.02,
                    "xanchor": "right",
                    "x": 1,
                },
            )

        st.plotly_chart(traj_fig, use_container_width=True, key=traj_key)
        st.caption(f"Month-by-month customer dynamics for {report.scenario_name}")

        if event_monthly_rows:
            retention_months = [int(_snap_val(s, "month")) for s in event_monthly_rows]
            retention_pct: list[float] = []
            for s in event_monthly_rows:
                total_active = float(_snap_val(s, "total_active", "active", default=0))
                cumulative_adopters = float(_snap_val(s, "cumulative_adopters", default=0))
                retention = (
                    (total_active / cumulative_adopters * 100.0) if cumulative_adopters else 0.0
                )
                retention_pct.append(retention)

            retention_fig = go.Figure(
                go.Scatter(
                    x=retention_months,
                    y=retention_pct,
                    mode="lines",
                    fill="tozeroy",
                    fillcolor="rgba(46, 204, 113, 0.20)",
                    line={"color": "#2ECC71", "width": 3},
                )
            )
            retention_fig.update_layout(
                height=_CHART_HEIGHT,
                margin=_CHART_MARGINS,
                xaxis_title="Month",
                yaxis_title="Retention %",
            )
            retention_fig.update_yaxes(range=[0, 100])
            st.subheader("Retention Curve")
            st.plotly_chart(
                retention_fig,
                use_container_width=True,
                key="retention_curve",
            )

        st.markdown("**Key Temporal Metrics**")
        pop_n = max(report.funnel.population_size, 1)
        first_snap = monthly_rows[0]
        month1_adoption_rate = (
            float(_snap_val(first_snap, "cumulative_adopters", default=0)) / pop_n
        )
        m12_active = report.month_12_active_rate
        if m12_active is None and monthly_rows:
            last_snap = monthly_rows[-1]
            m12_active = float(_snap_val(last_snap, "total_active", "active")) / pop_n

        tm1, tm2, tm3, tm4 = st.columns(4)
        m12_delta = (
            f"{(m12_active - month1_adoption_rate):+.1%}"
            if m12_active is not None and pop_n
            else None
        )
        tm1.metric(
            "Month 12 Active Rate",
            f"{m12_active:.1%}" if m12_active is not None else "—",
            delta=m12_delta,
            help="Share still active by horizon vs. Month 1 cumulative adoption share.",
        )
        if report.peak_churn_day is not None:
            tm2.metric("Peak Churn Day", f"Day {report.peak_churn_day}")
        else:
            peak_m = report.peak_churn_month
            tm2.metric("Peak Churn Month", f"Month {peak_m}" if peak_m is not None else "—")
        revenue_inr = report.revenue_estimate
        revenue_l = revenue_inr / 100_000.0 if revenue_inr is not None else None
        tm3.metric(
            "Estimated Annual Revenue", f"₹{revenue_l:.1f}L" if revenue_l is not None else "—"
        )
        lj_last = int(_snap_val(monthly_rows[-1], "lj_pass_holders", default=0))
        tm4.metric("LJ Pass Holders", f"{lj_last:,}")

    clusters_src = report.event_clusters or report.behaviour_clusters
    if clusters_src:
        st.subheader("Behavioural Segments")
        clusters_sorted = sorted(
            clusters_src,
            key=lambda c: int(c.get("size", 0) or 0),
            reverse=True,
        )
        names = [str(c.get("cluster_name", "Cluster")) for c in clusters_sorted]
        sizes = [int(c.get("size", 0) or 0) for c in clusters_sorted]
        colors = [_cluster_bar_color(n) for n in names]
        beh_fig = go.Figure(
            go.Bar(
                y=names[::-1],
                x=sizes[::-1],
                orientation="h",
                marker_color=colors[::-1],
            )
        )
        beh_fig.update_layout(
            height=_CHART_HEIGHT,
            margin=_CHART_MARGINS,
            showlegend=False,
            xaxis_title="Cluster size",
        )
        st.plotly_chart(beh_fig, use_container_width=True, key="behaviour_clusters")

        for cl in clusters_sorted:
            cname = str(cl.get("cluster_name", "Cluster"))
            pct = float(cl.get("pct", 0) or 0)
            with st.expander(f"{cname} — {cl.get('size', 0)} personas ({pct:.0%})"):
                st.markdown(
                    f"**Cluster size:** {cl.get('size', 0)} · **Share of sample:** {pct:.1%}",
                )
                life = float(cl.get("avg_lifetime_months", cl.get("avg_lifetime", 0)) or 0)
                st.markdown(f"**Average lifetime (months):** {life:.1f}")
                sat = cl.get("avg_satisfaction")
                if sat is not None:
                    st.markdown(f"**Average satisfaction score:** {float(sat):.2f}")
                attrs: dict[str, Any] = cl.get("dominant_attributes") or cl.get("key_traits") or {}
                top3 = list(attrs.items())[:3]
                if top3:
                    st.markdown("**Top distinguishing persona attributes:**")
                    for k, v in top3:
                        st.markdown(f"- **{_label(str(k))}:** {float(v):.2f}")

    if result.event_result is not None and result.smart_sample.selections:
        st.subheader("Event Timeline")
        st.caption("Day-level events and decision points for one smart-sample persona.")
        sample_ids = [s.persona_id for s in result.smart_sample.selections]
        label_map = {sid: (pop.get_persona(sid).display_name or sid) for sid in sample_ids}
        selected_pid = st.selectbox(
            "Persona (smart sample)",
            options=sample_ids,
            format_func=lambda pid: f"{label_map.get(pid, pid)} ({pid})",
            key="event_timeline_persona",
        )
        persona_traj = next(
            (t for t in result.event_result.trajectories if t.persona_id == selected_pid),
            None,
        )
        if persona_traj is not None:
            evt_days: list[int] = []
            evt_types: list[str] = []
            evt_sizes: list[int] = []
            for snap in persona_traj.days:
                for et in snap.events_fired:
                    evt_days.append(snap.day)
                    evt_types.append(et)
                    evt_sizes.append(10)
            dec_days = [s.day for s in persona_traj.days if s.decision]
            dec_y = [str(s.decision) for s in persona_traj.days if s.decision]
            tline = go.Figure()
            if evt_days:
                tline.add_trace(
                    go.Scatter(
                        x=evt_days,
                        y=evt_types,
                        mode="markers",
                        name="Events",
                        marker={"size": evt_sizes, "opacity": 0.75},
                    )
                )
            if dec_days:
                tline.add_trace(
                    go.Scatter(
                        x=dec_days,
                        y=dec_y,
                        mode="markers",
                        name="Decisions",
                        marker={"symbol": "diamond", "size": 14, "color": "#7b1fa2"},
                    )
                )
            tline.update_layout(
                height=_CHART_HEIGHT,
                margin=_CHART_MARGINS,
                xaxis_title="Day",
                yaxis_title="Event / decision",
                legend={"orientation": "h", "y": 1.12},
            )
            st.plotly_chart(tline, use_container_width=True, key="event_timeline")

    if report.decision_rationale_summary:
        st.subheader("Decision Drivers")
        st.caption(
            "State variables most often dominant in churn/switch decisions (event model).",
        )
        summ = sorted(
            report.decision_rationale_summary,
            key=lambda x: float(x.get("fraction", 0)),
            reverse=True,
        )[:10]
        drv_labels = [display_name(str(item["variable"])) for item in summ]
        drv_x = [float(item["fraction"]) for item in summ]
        drv_fig = go.Figure(
            go.Bar(
                x=drv_x,
                y=drv_labels[::-1],
                orientation="h",
                marker_color="#9467bd",
            )
        )
        drv_fig.update_layout(
            height=_CHART_HEIGHT,
            margin=_CHART_MARGINS,
            xaxis_title="Share of churn/switch decisions",
            showlegend=False,
        )
        st.plotly_chart(drv_fig, use_container_width=True, key="decision_drivers")
        for item in summ[:5]:
            frac = float(item.get("fraction", 0))
            st.caption(
                f"**{display_name(str(item['variable']))}** was the dominant factor in "
                f"{frac:.0%} of churn/switch decisions."
            )

    st.subheader("Segment Analysis")
    tab_tier, tab_income = st.tabs(["By City Tier", "By Income Bracket"])

    with tab_tier:
        if report.segments_by_tier:
            for seg in report.segments_by_tier:
                delta_str = (
                    f"+{seg.delta_vs_population:.1%}"
                    if seg.delta_vs_population > 0
                    else f"{seg.delta_vs_population:.1%}"
                )
                st.metric(
                    f"{seg.segment_value}",
                    f"{seg.adoption_rate:.1%}",
                    delta=delta_str,
                    help=f"{seg.persona_count} personas",
                )

    with tab_income:
        if report.segments_by_income:
            for seg in report.segments_by_income:
                delta_str = (
                    f"+{seg.delta_vs_population:.1%}"
                    if seg.delta_vs_population > 0
                    else f"{seg.delta_vs_population:.1%}"
                )
                st.metric(
                    f"{seg.segment_value}",
                    f"{seg.adoption_rate:.1%}",
                    delta=delta_str,
                    help=f"{seg.persona_count} personas",
                )

    st.subheader("Key Decision Variables")
    st.caption(
        "These variables had the strongest influence on adoption outcomes in the simulation model.",
    )

    if report.causal_drivers:
        for driver in report.causal_drivers[:8]:
            direction = "↑" if driver["direction"] == "positive" else "↓"
            name = _label(str(driver["variable"]))
            imp = float(driver["importance"])
            st.markdown(f"- {direction} **{name}** — importance: {imp:.3f}")

    has_temporal_snapshots = bool(report.temporal_snapshots)
    has_event_rollups = bool(report.event_daily_rollups or report.event_monthly_rollup)
    event_compare = [a for a in result.alternative_runs if a.event_active_rate is not None]
    temporal_compare = [a for a in result.alternative_runs if a.temporal_active_rate is not None]

    if has_event_rollups and event_compare and result.event_result is not None:
        st.subheader("Intervention Comparison")
        st.caption(
            "Static trial vs event-model active rate for top interventions "
            "(high trial can mask weak retention)."
        )
        ranked_alt = sorted(
            event_compare,
            key=lambda a: a.event_active_rate if a.event_active_rate is not None else 0.0,
            reverse=True,
        )[:5]
        labels = [
            (a.variant_id[:28] + "…") if len(a.variant_id) > 28 else a.variant_id
            for a in ranked_alt
        ]
        comp_fig = go.Figure()
        comp_fig.add_trace(
            go.Bar(
                name="Static adoption rate",
                x=labels,
                y=[a.adoption_rate for a in ranked_alt],
                marker_color="#1f77b4",
            )
        )
        comp_fig.add_trace(
            go.Bar(
                name="Event model active rate",
                x=labels,
                y=[float(a.event_active_rate) for a in ranked_alt],
                marker_color="#ff7f0e",
            )
        )
        comp_fig.update_layout(
            barmode="group",
            height=_CHART_HEIGHT,
            margin=_CHART_MARGINS,
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.08, "x": 0},
        )
        st.plotly_chart(comp_fig, use_container_width=True, key="intervention_comparison")
    elif has_temporal_snapshots and temporal_compare:
        st.subheader("Intervention Comparison")
        st.caption(
            "Top interventions by month-12 active rate: static trial vs retention "
            "(high trial can mask weak ongoing engagement)."
        )
        ranked_alt = sorted(
            temporal_compare,
            key=lambda a: a.temporal_active_rate if a.temporal_active_rate is not None else 0.0,
            reverse=True,
        )[:5]
        labels = [
            (a.variant_id[:28] + "…") if len(a.variant_id) > 28 else a.variant_id
            for a in ranked_alt
        ]
        comp_fig = go.Figure()
        comp_fig.add_trace(
            go.Bar(
                name="Static adoption rate",
                x=labels,
                y=[a.adoption_rate for a in ranked_alt],
                marker_color="#1f77b4",
            )
        )
        comp_fig.add_trace(
            go.Bar(
                name="Month-12 active rate",
                x=labels,
                y=[float(a.temporal_active_rate) for a in ranked_alt],
                marker_color="#ff7f0e",
            )
        )
        comp_fig.update_layout(
            barmode="group",
            height=_CHART_HEIGHT,
            margin=_CHART_MARGINS,
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.08, "x": 0},
        )
        st.plotly_chart(comp_fig, use_container_width=True, key="intervention_comparison")
    else:
        st.subheader("Strategic Alternatives")
        st.caption(
            "Top-performing and worst-performing scenario variants ranked by impact on trial rate."
        )

        col_top, col_worst = st.columns([2, 1])

        with col_top:
            st.markdown("**Best alternatives:**")
            for alt in report.top_alternatives[:10]:
                delta_str = (
                    f"+{alt.delta_vs_primary:.1%}"
                    if alt.delta_vs_primary > 0
                    else f"{alt.delta_vs_primary:.1%}"
                )
                with st.expander(f"#{alt.rank} {alt.variant_id} ({delta_str})"):
                    st.markdown(alt.business_rationale)
                    st.caption(f"Adoption rate: {alt.adoption_rate:.1%}")

        with col_worst:
            st.markdown("**Worst alternatives:**")
            for alt in report.worst_alternatives:
                delta_str = f"{alt.delta_vs_primary:.1%}"
                st.markdown(f"- {alt.variant_id}: {delta_str}")

    if report.counterfactual_results:
        st.subheader("Counterfactual Analysis")
        st.caption("What would happen if you changed one thing?")

        cf_rows = sorted(
            report.counterfactual_results,
            key=lambda c: float(c.lift_pct) if c.lift_pct is not None else 0.0,
        )
        cf_labels = [
            (c.label or c.counterfactual_name or c.scenario_id or "?")[:42] for c in cf_rows
        ]
        cf_lifts = [float(c.lift_pct) if c.lift_pct is not None else 0.0 for c in cf_rows]
        cf_colors = ["#2ca02c" if lift >= 0 else "#d62728" for lift in cf_lifts]

        cf_fig = go.Figure()
        cf_fig.add_trace(
            go.Bar(
                x=cf_lifts,
                y=cf_labels,
                orientation="h",
                marker_color=cf_colors,
                showlegend=False,
            )
        )
        cf_fig.add_vline(x=0, line_dash="dash", line_color="#333333")
        cf_fig.add_trace(
            go.Scatter(
                x=[0] * len(cf_labels),
                y=cf_labels,
                mode="markers",
                marker={"symbol": "diamond", "size": 14, "color": "#333333"},
                name="Baseline",
                showlegend=False,
            )
        )
        cf_fig.update_layout(
            height=300,
            margin=_CHART_MARGINS,
            xaxis_title="Lift vs baseline (% active rate)",
            yaxis_title="",
        )
        st.plotly_chart(cf_fig, use_container_width=True, key="counterfactual_analysis")

        for cf in cf_rows:
            lift = float(cf.lift_pct) if cf.lift_pct is not None else 0.0
            label = cf.label or cf.counterfactual_name or cf.scenario_id or "Intervention"
            base_rate = (
                float(cf.baseline_active_rate) if cf.baseline_active_rate is not None else 0.0
            )
            cf_rate = (
                float(cf.counterfactual_active_rate)
                if cf.counterfactual_active_rate is not None
                else 0.0
            )
            rev = float(cf.revenue_lift) if cf.revenue_lift is not None else 0.0
            with st.expander(f"{label} → {lift:+.1f}% active rate"):
                c1, c2 = st.columns(2)
                c1.metric("Baseline Active", f"{base_rate:.1%}")
                c2.metric(
                    "With Intervention",
                    f"{cf_rate:.1%}",
                    delta=f"{lift:+.1f}%",
                )
                st.caption(f"Revenue impact: ₹{rev:+,.0f}")

    st.subheader("Interview Themes")
    st.caption(f"Themes identified from {report.interview_count} deep interviews.")

    if report.clusters:
        for cluster in report.clusters:
            title = cluster.theme.replace("_", " ").title()
            with st.expander(
                f"{title} — {cluster.persona_count} personas ({cluster.percentage:.0%})"
            ):
                st.markdown(cluster.description)
                if cluster.representative_quotes:
                    st.markdown("**Sample responses:**")
                    for quote in cluster.representative_quotes[:2]:
                        st.markdown(f"> {quote[:300]}")
                if cluster.dominant_attributes:
                    st.caption(
                        "Dominant persona traits: "
                        + ", ".join(
                            f"{_label(str(k))}: {v:.2f}"
                            for k, v in list(cluster.dominant_attributes.items())[:5]
                        )
                    )
    else:
        st.caption("No interview themes available (mock mode or insufficient responses).")

    st.divider()
    export_cols = st.columns(2)
    with export_cols[0]:
        st.download_button(
            "Download Report (JSON)",
            data=report.model_dump_json(indent=2),
            file_name=f"{report.scenario_id}_research_report.json",
            mime="application/json",
        )
    with export_cols[1]:
        pdf_bytes = _research_pdf_bytes(report.model_dump_json())
        st.download_button(
            "Download Report (PDF)",
            data=pdf_bytes,
            file_name=f"{report.scenario_id}_research_report.pdf",
            mime="application/pdf",
        )

elif st.session_state.get("scenario_results"):
    st.info(
        "These results are from a quick simulation run. Run a full research pipeline from the "
        "Research Design page for the complete report."
    )
    _render_legacy_dashboard()

else:
    st.warning(
        "No research results available. Run a research pipeline from the Research Design page."
    )
    st.stop()
