from __future__ import annotations

import pytest


@pytest.mark.skip(reason="awaiting viz implementation")
def test_funnel_chart_single_stage() -> None:
    from src.utils.viz import create_funnel_chart

    data = {"stages": [{"stage": "need_recognition", "entered": 1, "passed": 1}]}
    create_funnel_chart(data)


@pytest.mark.skip(reason="awaiting viz implementation")
def test_segment_heatmap_single_segment() -> None:
    from src.utils.viz import create_segment_heatmap

    data = {"segments": [{"segment_value": "Tier1", "adoption_rate": 0.5}]}
    create_segment_heatmap(data)


@pytest.mark.skip(reason="awaiting viz implementation")
def test_barrier_chart_single_barrier() -> None:
    from src.utils.viz import create_barrier_chart

    data = {"barriers": [{"barrier": "price_too_high", "count": 1, "percentage": 1.0}]}
    create_barrier_chart(data)


@pytest.mark.skip(reason="awaiting viz implementation")
def test_importance_bar_single_variable() -> None:
    from src.utils.viz import create_importance_bar

    data = {"importances": [{"variable_name": "feature1", "shap_mean_abs": 0.4}]}
    create_importance_bar(data)
