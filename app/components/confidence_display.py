"""components/confidence_display.py

Renders a persona's confidence score with noise band indicator.
Color-coded: green ≥ 70, amber 50–69, red < 50.
"""

from __future__ import annotations

import streamlit as st


def render_confidence(confidence: int | float, noise_applied: int | float | None = None) -> None:
    """Render confidence score with optional noise band."""

    if confidence >= 70:
        color = "#10B981"
        bg = "#D1FAE5"
    elif confidence >= 50:
        color = "#F59E0B"
        bg = "#FEF3C7"
    else:
        color = "#EF4444"
        bg = "#FEE2E2"

    if noise_applied is not None:
        score_text = f"{confidence} ± {noise_applied}"
    else:
        score_text = str(confidence)

    st.markdown(
        f"""
        <div style="font-family: sans-serif; margin: 6px 0 10px 0;">
            <span style="
                font-size: 0.78rem;
                font-weight: 600;
                color: #6B7280;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                display: block;
                margin-bottom: 4px;
            ">Confidence</span>
            <span style="
                display: inline-block;
                background: {bg};
                color: {color};
                border: 1.5px solid {color};
                border-radius: 20px;
                padding: 3px 14px;
                font-size: 1.05rem;
                font-weight: 700;
                letter-spacing: 0.02em;
            ">{score_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
