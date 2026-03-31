"""System Voice component — narration callouts rendered before dashboards."""

from __future__ import annotations

import streamlit as st


def render_system_voice(text: str, icon: str = "🤖") -> None:
    """Blue-bordered system narration callout.

    Renders the platform's interpretive voice before raw data is shown.
    Always call this BEFORE displaying charts or tables.
    """
    st.markdown(
        f"""
        <div style="
            border-left: 5px solid #2E86C1;
            background: #EBF5FB;
            padding: 14px 18px;
            margin: 10px 0 16px 0;
            border-radius: 0 6px 6px 0;
            font-family: sans-serif;
        ">
            <span style="color:#1A5276; font-weight:700; font-size:0.95rem;">{icon} System</span>
            <span style="color:#555; font-size:0.9rem; margin-left:6px;">analysis</span>
            <div style="margin-top:6px; color:#1C1C1C; font-size:0.97rem; line-height:1.55;">
                {text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_magic_moment(label: str, text: str) -> None:
    """Green-bordered callout for demo magic moments (used in documentation/demo mode)."""
    st.markdown(
        f"""
        <div style="
            border-left: 5px solid #27AE60;
            background: #EAFAF1;
            padding: 14px 18px;
            margin: 10px 0 16px 0;
            border-radius: 0 6px 6px 0;
            font-family: sans-serif;
        ">
            <span style="color:#1E8449; font-weight:700; font-size:0.95rem;">✨ {label}</span>
            <div style="margin-top:6px; color:#1C1C1C; font-size:0.97rem; line-height:1.55;">
                {text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_core_finding(text: str) -> None:
    """Orange-bordered full-width Core Finding callout — the analytical climax."""
    st.markdown(
        f"""
        <div style="
            border-left: 6px solid #E67E22;
            border-top: 1px solid #E67E22;
            border-bottom: 1px solid #E67E22;
            border-right: 1px solid #E67E22;
            background: #FDEBD0;
            padding: 18px 22px;
            margin: 16px 0;
            border-radius: 4px;
            font-family: sans-serif;
        ">
            <div style="color:#E67E22; font-weight:700; font-size:1.0rem; margin-bottom:8px;">
                🔍 Core Finding
            </div>
            <div style="color:#1C1C1C; font-size:1.05rem; line-height:1.65; font-style:italic;">
                {text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
