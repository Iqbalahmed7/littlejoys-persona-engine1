"""
Visualization helpers — shared chart builders used by the Streamlit dashboard.

PRD-011 / Sprint 4. All builders return Plotly ``go.Figure`` instances.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import plotly.graph_objects as go

from src.constants import (
    DASHBOARD_BRAND_COLORS,
    DASHBOARD_CHART_HEIGHT,
    DASHBOARD_HEATMAP_COLORSCALE,
    DASHBOARD_IMPORTANCE_TOP_N,
    DASHBOARD_SCATTER_MARKER_SIZE,
)


def _brand_primary() -> str:
    return str(DASHBOARD_BRAND_COLORS["primary"])


def _brand_secondary() -> str:
    return str(DASHBOARD_BRAND_COLORS["secondary"])


def _brand_adopt() -> str:
    return str(DASHBOARD_BRAND_COLORS["adopt"])


def _brand_reject() -> str:
    return str(DASHBOARD_BRAND_COLORS["reject"])


def _brand_neutral() -> str:
    return str(DASHBOARD_BRAND_COLORS["neutral"])


def _empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        height=DASHBOARD_CHART_HEIGHT,
        annotations=[
            {
                "text": "No data",
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 16, "color": _brand_neutral()},
            }
        ],
    )
    return fig


def create_funnel_chart(waterfall: list[Any]) -> go.Figure:
    """Waterfall-style funnel from :class:`~src.analysis.waterfall.WaterfallStage` rows."""

    if not waterfall:
        return _empty_figure("Funnel")

    stages = [w.stage for w in waterfall]
    entered = [w.entered for w in waterfall]
    dropped = [w.dropped for w in waterfall]
    passed = [w.passed for w in waterfall]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Still in funnel",
            x=stages,
            y=passed,
            marker_color=_brand_secondary(),
        )
    )
    fig.add_trace(
        go.Bar(
            name="Dropped",
            x=stages,
            y=dropped,
            marker_color=_brand_reject(),
        )
    )
    fig.add_trace(
        go.Scatter(
            name="Entered stage",
            x=stages,
            y=entered,
            mode="lines+markers",
            line={"color": _brand_primary()},
            marker={"size": DASHBOARD_SCATTER_MARKER_SIZE},
        )
    )
    fig.update_layout(
        barmode="stack",
        title="Funnel retention by stage",
        height=DASHBOARD_CHART_HEIGHT,
        legend_orientation="h",
        yaxis_title="Personas",
    )
    return fig


def create_segment_heatmap(
    segments: list[Any],
    group_by: str,
    *,
    matrix: list[list[float]] | None = None,
    row_labels: list[str] | None = None,
    col_labels: list[str] | None = None,
) -> go.Figure:
    """
    Heatmap of adoption rates.

    If ``matrix`` and labels are provided, builds a 2D heatmap (e.g. city tier × income).
    Otherwise uses ``segments`` (:class:`~src.analysis.segments.SegmentAnalysis`) as a
    single-row heatmap for ``group_by``.
    """

    if matrix is not None and row_labels is not None and col_labels is not None:
        if not matrix or not row_labels or not col_labels:
            return _empty_figure(f"Segments ({group_by})")
        fig = go.Figure(
            data=go.Heatmap(
                z=matrix,
                x=col_labels,
                y=row_labels,
                colorscale=DASHBOARD_HEATMAP_COLORSCALE,
                zmin=0.0,
                zmax=1.0,
                colorbar={"title": "Adoption rate"},
            )
        )
        fig.update_layout(
            title=f"Adoption rate by {group_by}",
            height=DASHBOARD_CHART_HEIGHT,
            xaxis_title=col_labels and "Column" or "",
            yaxis_title=row_labels and "Row" or "",
        )
        return fig

    if not segments:
        return _empty_figure(f"Segments ({group_by})")

    values = [float(s.adoption_rate) for s in segments]
    labels = [str(s.segment_value) for s in segments]
    fig = go.Figure(
        data=go.Heatmap(
            z=[values],
            x=labels,
            y=[group_by],
            colorscale=DASHBOARD_HEATMAP_COLORSCALE,
            zmin=0.0,
            zmax=1.0,
            colorbar={"title": "Adoption rate"},
        )
    )
    fig.update_layout(
        title=f"Adoption rate by {group_by}",
        height=DASHBOARD_CHART_HEIGHT,
    )
    return fig


def create_barrier_chart(barriers: list[Any]) -> go.Figure:
    """Horizontal bar chart from :class:`~src.analysis.barriers.BarrierDistribution` rows."""

    if not barriers:
        return _empty_figure("Barriers")

    labels = [f"{b.stage}: {b.barrier}" for b in barriers]
    counts = [b.count for b in barriers]
    fig = go.Figure(
        go.Bar(
            x=counts,
            y=labels,
            orientation="h",
            marker_color=_brand_primary(),
        )
    )
    fig.update_layout(
        title="Rejection reasons by stage",
        height=DASHBOARD_CHART_HEIGHT,
        xaxis_title="Count",
        yaxis_title="",
    )
    return fig


def create_temporal_chart(result: Any) -> go.Figure:
    """Time series from :class:`~src.simulation.temporal.TemporalSimulationResult`."""

    snaps = getattr(result, "monthly_snapshots", None) or []
    if not snaps:
        return _empty_figure("Temporal simulation")

    months = [s.month for s in snaps]
    cumulative = [s.cumulative_adopters for s in snaps]
    awareness = [s.awareness_level_mean for s in snaps]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=cumulative,
            name="Cumulative adopters",
            mode="lines+markers",
            line={"color": _brand_adopt()},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=months,
            y=awareness,
            name="Mean awareness",
            mode="lines+markers",
            yaxis="y2",
            line={"color": _brand_secondary()},
        )
    )
    fig.update_layout(
        title=f"Temporal dynamics — {getattr(result, 'scenario_id', '')}",
        height=DASHBOARD_CHART_HEIGHT,
        xaxis_title="Month",
        yaxis_title="Cumulative adopters",
        yaxis2={
            "title": "Awareness (mean)",
            "overlaying": "y",
            "side": "right",
        },
        legend_orientation="h",
    )
    return fig


def create_importance_bar(importances: list[Any]) -> go.Figure:
    """Horizontal bar chart of top SHAP-driven importances."""

    if not importances:
        return _empty_figure("Variable importance")

    ranked = sorted(importances, key=lambda v: v.rank)[:DASHBOARD_IMPORTANCE_TOP_N]
    names = [v.variable_name for v in ranked]
    values = [float(v.shap_mean_abs) for v in ranked]
    colors = [_brand_adopt() if v.direction == "positive" else _brand_reject() for v in ranked]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker_color=colors,
        )
    )
    fig.update_layout(
        title="Variable importance (mean |SHAP|)",
        height=DASHBOARD_CHART_HEIGHT,
        xaxis_title="Mean |SHAP|",
    )
    return fig


def create_counterfactual_comparison(results: Any) -> go.Figure:
    """
    Grouped-style bar comparing baseline vs counterfactual adoption.

    Accepts a single :class:`~src.simulation.counterfactual.CounterfactualResult` or a list.
    """

    if results is None:
        return _empty_figure("Counterfactual")

    if not isinstance(results, list):
        results = [results]

    if not results:
        return _empty_figure("Counterfactual")

    names: list[str] = []
    baseline_rates: list[float] = []
    cf_rates: list[float] = []

    for r in results:
        label = getattr(r, "counterfactual_name", None) or getattr(
            r, "baseline_scenario_id", "scenario"
        )
        names.append(str(label))
        baseline_rates.append(float(getattr(r, "baseline_adoption_rate", 0.0)))
        cf_rates.append(float(getattr(r, "counterfactual_adoption_rate", 0.0)))

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Baseline",
            x=names,
            y=baseline_rates,
            marker_color=_brand_neutral(),
        )
    )
    fig.add_trace(
        go.Bar(
            name="Counterfactual",
            x=names,
            y=cf_rates,
            marker_color=_brand_secondary(),
        )
    )
    fig.update_layout(
        barmode="group",
        title="Adoption rate: baseline vs counterfactual",
        height=DASHBOARD_CHART_HEIGHT,
        yaxis_title="Adoption rate",
        yaxis_range=[0, 1],
        legend_orientation="h",
    )
    return fig
