from __future__ import annotations

from typing import Any

import streamlit as st

from src.utils.viz import create_segment_heatmap


def render_heatmap(
    segments: list[Any],
    group_by: str,
    *,
    matrix: list[list[float]] | None = None,
    row_labels: list[str] | None = None,
    col_labels: list[str] | None = None,
) -> None:
    """Render segment heatmap via :func:`src.utils.viz.create_segment_heatmap`."""

    if matrix is not None and row_labels is not None and col_labels is not None:
        if not matrix or not row_labels or not col_labels:
            st.info("No heatmap matrix data available to render.")
            return
    elif not segments:
        st.info("No segment impacts generated to render heatmap.")
        return

    fig = create_segment_heatmap(
        segments,
        group_by,
        matrix=matrix,
        row_labels=row_labels,
        col_labels=col_labels,
    )
    st.plotly_chart(fig, use_container_width=True)
