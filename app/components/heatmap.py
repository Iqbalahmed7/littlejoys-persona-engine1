import streamlit as st

from src.utils.viz import create_segment_heatmap


def render_heatmap(segment_impacts):
    if not segment_impacts:
        st.info("No segment impacts generated to render heatmap.")
        return
    fig = create_segment_heatmap(segment_impacts)
    st.plotly_chart(fig, use_container_width=True)
