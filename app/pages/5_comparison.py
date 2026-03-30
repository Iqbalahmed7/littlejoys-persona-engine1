# ruff: noqa: N999
"""Scenario comparison UI.

UI-only front-end for :func:`src.analysis.scenario_comparison.compare_scenarios`.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analysis.scenario_comparison import compare_scenarios
from src.decision.scenarios import get_all_scenarios
from src.simulation.event_engine import run_event_simulation

_CHART_HEIGHT = 300
_CHART_MARGINS = dict(l=20, r=20, t=40, b=20)


def _retention_curve_from_monthly(
    monthly_rows: list[dict[str, int | float]],
) -> tuple[list[int], list[float]]:
    """Build retention curve from monthly event rollups."""

    months: list[int] = []
    retention_pct: list[float] = []
    for i, snap in enumerate(monthly_rows):
        month = int(snap.get("month", i + 1) or (i + 1))
        total_active = float(snap.get("total_active", 0) or 0)
        cumulative_adopters = float(snap.get("cumulative_adopters", 0) or 0)
        retention = (total_active / cumulative_adopters * 100.0) if cumulative_adopters else 0.0
        months.append(month)
        retention_pct.append(retention)
    return months, retention_pct


def _format_pct(rate: float | None) -> str:
    if rate is None:
        return "—"
    return f"{rate:.1%}"


def _format_revenue_l(revenue: float | None) -> str:
    if revenue is None:
        return "—"
    return f"₹{(float(revenue) / 100_000.0):.1f}L"


st.header("Scenario Comparison")
st.caption("Compare two business scenarios side by side.")

if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()

pop = st.session_state.population

scenarios = get_all_scenarios()
scenario_names = {s.id: s.name for s in scenarios}

col_a, col_b = st.columns(2)
with col_a:
    scenario_a_id = st.selectbox(
        "Scenario A",
        list(scenario_names.keys()),
        format_func=lambda sid: scenario_names[sid],
        key="cmp_a",
    )
with col_b:
    scenario_b_id = st.selectbox(
        "Scenario B",
        list(scenario_names.keys()),
        format_func=lambda sid: scenario_names[sid],
        index=1 if len(scenario_names) > 1 else 0,
        key="cmp_b",
    )

scenario_a = next(s for s in scenarios if s.id == scenario_a_id)
scenario_b = next(s for s in scenarios if s.id == scenario_b_id)

run_clicked = st.button("Compare", type="primary", use_container_width=True, key="cmp_run")

if run_clicked:
    with st.spinner("Running scenario comparison..."):
        comp = compare_scenarios(
            population=pop,
            scenario_a=scenario_a,
            scenario_b=scenario_b,
        )

    st.subheader("Metric Delta")
    m_a = comp.adoption_rate_a
    m_b = comp.adoption_rate_b
    active_a = comp.active_rate_a
    active_b = comp.active_rate_b

    active_delta = (
        (active_b - active_a) if (active_a is not None and active_b is not None) else None
    )
    revenue_delta = (
        (comp.revenue_delta)
        if (comp.revenue_a is not None and comp.revenue_b is not None)
        else None
    )

    adopt_delta_pp = (m_b - m_a) * 100.0
    active_delta_pp = active_delta * 100.0 if active_delta is not None else None

    adoption_row = f"{m_a * 100:.1f}%"
    metric_table = [
        ("Adoption Rate", m_a, m_b, f"{adopt_delta_pp:+.1f}pp"),
        (
            "Active Rate (M12)",
            active_a,
            active_b,
            f"{active_delta_pp:+.1f}pp" if active_delta_pp is not None else "—",
        ),
        (
            "Est. Revenue (₹)",
            comp.revenue_a,
            comp.revenue_b,
            (f"{comp.revenue_delta:+,.0f}" if revenue_delta is not None else "—"),
        ),
    ]

    st.markdown(
        "| Metric | Scenario A | Scenario B | Delta |"
        "\n|---|---:|---:|---:|"
        + "\n".join(
            [
                "| "
                + f"{metric}"
                + "| "
                + (
                    _format_revenue_l(a)
                    if metric == "Est. Revenue (₹)"
                    else (f"{a:.1%}" if isinstance(a, float) else "—")
                )
                + "| "
                + (
                    _format_revenue_l(b)
                    if metric == "Est. Revenue (₹)"
                    else (f"{b:.1%}" if isinstance(b, float) else "—")
                )
                + "| "
                + f"{delta}"
                + " |"
                for metric, a, b, delta in [
                    ("Adoption Rate", m_a, m_b, f"{adopt_delta_pp:+.1f}pp"),
                    (
                        "Active Rate (M12)",
                        active_a,
                        active_b,
                        (f"{active_delta_pp:+.1f}pp" if active_delta_pp is not None else "—"),
                    ),
                    (
                        "Est. Revenue (₹)",
                        comp.revenue_a,
                        comp.revenue_b,
                        (
                            f"{comp.revenue_delta:+,.0f}"
                            if comp.revenue_a is not None and comp.revenue_b is not None
                            else "—"
                        ),
                    ),
                ]
            ]
        )
    )

    st.subheader("Retention Curves (Event model)")
    if scenario_a.mode == "temporal" and scenario_b.mode == "temporal":
        months_a, retention_a = _retention_curve_from_monthly(
            run_event_simulation(
                population=pop,
                scenario=scenario_a,
                duration_days=int(scenario_a.months * 30),
            ).aggregate_monthly,
        )
        months_b, retention_b = _retention_curve_from_monthly(
            run_event_simulation(
                population=pop,
                scenario=scenario_b,
                duration_days=int(scenario_b.months * 30),
            ).aggregate_monthly,
        )
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=months_a,
                y=retention_a,
                mode="lines+markers",
                name="Scenario A",
                line={"color": "#1f77b4", "width": 3},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=months_b,
                y=retention_b,
                mode="lines+markers",
                name="Scenario B",
                line={"color": "#ff7f0e", "width": 3},
            )
        )
        fig.update_layout(
            height=_CHART_HEIGHT,
            margin=_CHART_MARGINS,
            xaxis_title="Month",
            yaxis_title="Retention %",
            yaxis={"range": [0, 100]},
            legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Retention curves require temporal (event) scenarios.")

    st.subheader("Barrier Comparison")
    barrier_rows: list[dict[str, Any]] = [
        {
            "Stage": row.stage,
            "Barrier": row.barrier,
            "Count A": row.count_a,
            "Count B": row.count_b,
            "Delta": row.delta,
        }
        for row in comp.barrier_comparison
    ]
    df_bar = pd.DataFrame(barrier_rows)
    if not df_bar.empty:
        styler = df_bar.style.apply(
            lambda r: ["background-color: #ffe5e5" if r["Delta"] > 5 else "" for _ in r],
            axis=1,
        )
        st.dataframe(styler, use_container_width=True, hide_index=True)
    else:
        st.caption("No barrier data available.")
