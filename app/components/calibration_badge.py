"""components/calibration_badge.py

Colored badge showing cohort calibration status.
"""

from __future__ import annotations

import streamlit as st


def render_calibration_badge(status: str | None) -> None:
    """Render a calibration status badge.

    status values: "benchmark_calibrated", "client_calibrated", "uncalibrated",
                   "calibration_failed", None
    """

    if status in ("benchmark_calibrated", "client_calibrated"):
        color = "#10B981"
        bg = "#D1FAE5"
        label = "Calibrated ✓"
    elif status == "calibration_failed":
        color = "#EF4444"
        bg = "#FEE2E2"
        label = "Calibration Failed"
    else:
        # "uncalibrated" or None
        color = "#F59E0B"
        bg = "#FEF3C7"
        label = "Uncalibrated"

    st.markdown(
        f"""
        <div style="font-family: sans-serif; margin: 6px 0 10px 0;">
            <span style="
                display: inline-block;
                background: {bg};
                color: {color};
                border: 1.5px solid {color};
                border-radius: 20px;
                padding: 3px 14px;
                font-size: 0.88rem;
                font-weight: 600;
                letter-spacing: 0.01em;
            ">{label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
