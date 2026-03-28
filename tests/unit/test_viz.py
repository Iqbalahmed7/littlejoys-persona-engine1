"""Unit tests for Plotly dashboard chart builders."""

from __future__ import annotations

import plotly.graph_objects as go

from src.analysis.barriers import BarrierDistribution
from src.analysis.causal import VariableImportance
from src.analysis.segments import SegmentAnalysis
from src.analysis.waterfall import WaterfallStage
from src.simulation.counterfactual import CounterfactualResult
from src.simulation.temporal import MonthlySnapshot, TemporalSimulationResult
from src.utils.viz import (
    create_barrier_chart,
    create_counterfactual_comparison,
    create_funnel_chart,
    create_importance_bar,
    create_segment_heatmap,
    create_temporal_chart,
)


def _sample_waterfall() -> list[WaterfallStage]:
    return [
        WaterfallStage(
            stage="need_recognition",
            entered=100,
            passed=90,
            dropped=10,
            pass_rate=0.9,
            cumulative_pass_rate=0.4,
        ),
        WaterfallStage(
            stage="awareness",
            entered=90,
            passed=70,
            dropped=20,
            pass_rate=0.778,
            cumulative_pass_rate=0.35,
        ),
    ]


def test_funnel_chart_returns_figure() -> None:
    fig = create_funnel_chart(_sample_waterfall())
    assert isinstance(fig, go.Figure)


def test_segment_heatmap_returns_figure() -> None:
    segs = [
        SegmentAnalysis(
            segment_key="city_tier",
            segment_value="Tier1",
            count=10,
            adoption_rate=0.5,
            avg_funnel_scores={},
            top_barriers=[],
        )
    ]
    fig = create_segment_heatmap(segs, "city_tier")
    assert isinstance(fig, go.Figure)

    fig2 = create_segment_heatmap(
        [],
        "x",
        matrix=[[0.2, 0.8], [0.5, 0.5]],
        row_labels=["a", "b"],
        col_labels=["c", "d"],
    )
    assert isinstance(fig2, go.Figure)


def test_barrier_chart_returns_figure() -> None:
    barriers = [
        BarrierDistribution(stage="purchase", barrier="price_too_high", count=3, percentage=0.1)
    ]
    fig = create_barrier_chart(barriers)
    assert isinstance(fig, go.Figure)


def test_temporal_chart_returns_figure() -> None:
    result = TemporalSimulationResult(
        scenario_id="s",
        months=2,
        population_size=10,
        monthly_snapshots=[
            MonthlySnapshot(
                month=1,
                new_adopters=1,
                repeat_purchasers=0,
                churned=0,
                total_active=1,
                cumulative_adopters=1,
                awareness_level_mean=0.3,
                lj_pass_holders=0,
            ),
            MonthlySnapshot(
                month=2,
                new_adopters=0,
                repeat_purchasers=1,
                churned=0,
                total_active=2,
                cumulative_adopters=2,
                awareness_level_mean=0.35,
                lj_pass_holders=0,
            ),
        ],
        final_adoption_rate=0.2,
        final_active_rate=0.2,
        total_revenue_estimate=100.0,
    )
    fig = create_temporal_chart(result)
    assert isinstance(fig, go.Figure)


def test_importance_bar_returns_figure() -> None:
    imp = [
        VariableImportance(
            variable_name="health_anxiety",
            coefficient=0.5,
            shap_mean_abs=0.12,
            direction="positive",
            rank=1,
        )
    ]
    fig = create_importance_bar(imp)
    assert isinstance(fig, go.Figure)


def test_counterfactual_comparison_returns_figure() -> None:
    cf = CounterfactualResult(
        baseline_scenario_id="base",
        counterfactual_name="price_cut",
        parameter_changes={"product.price_inr": (100.0, 80.0)},
        baseline_adoption_rate=0.2,
        counterfactual_adoption_rate=0.35,
        absolute_lift=0.15,
        relative_lift_percent=75.0,
    )
    fig = create_counterfactual_comparison(cf)
    assert isinstance(fig, go.Figure)


def test_charts_handle_empty_data() -> None:
    assert isinstance(create_funnel_chart([]), go.Figure)
    assert isinstance(create_segment_heatmap([], "k"), go.Figure)
    assert isinstance(
        create_segment_heatmap([], "k", matrix=[], row_labels=[], col_labels=[]),
        go.Figure,
    )
    assert isinstance(create_barrier_chart([]), go.Figure)
    assert isinstance(create_temporal_chart(TemporalSimulationResult(
        scenario_id="s",
        months=0,
        population_size=0,
        monthly_snapshots=[],
        final_adoption_rate=0.0,
        final_active_rate=0.0,
        total_revenue_estimate=0.0,
    )), go.Figure)
    assert isinstance(create_importance_bar([]), go.Figure)
    assert isinstance(create_counterfactual_comparison([]), go.Figure)
