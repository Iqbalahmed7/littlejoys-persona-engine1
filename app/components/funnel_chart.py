import streamlit as st

from src.utils.viz import create_funnel_chart


def render_funnel_chart(waterfall_data):
    if not waterfall_data:
        st.info("No waterfall data available to render funnel.")
        return
    fig = create_funnel_chart(waterfall_data)
    st.plotly_chart(fig, use_container_width=True)
