"""components/memory_state_viewer.py

Compact panel showing persona memory state after simulation.
"""

from __future__ import annotations

import streamlit as st


def render_memory_state(
    observations: int = 0,
    reflections: int = 0,
    last_reflection: str | None = None,
) -> None:
    """Render a compact memory state panel."""

    snippet_html = ""
    if last_reflection:
        truncated = last_reflection[:120] + "…" if len(last_reflection) > 120 else last_reflection
        snippet_html = f"""
            <div style="
                margin-top: 10px;
                padding: 8px 12px;
                background: #F8FAFC;
                border-left: 3px solid #94A3B8;
                border-radius: 0 4px 4px 0;
                font-size: 0.88rem;
                color: #475569;
                font-style: italic;
                line-height: 1.5;
            ">"{truncated}"</div>
        """

    st.markdown(
        f"""
        <div style="
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 14px 16px;
            margin: 8px 0 12px 0;
            font-family: sans-serif;
            background: #FFFFFF;
        ">
            <div style="
                font-size: 0.78rem;
                font-weight: 600;
                color: #6B7280;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-bottom: 10px;
            ">Memory State</div>
            <div style="display: flex; gap: 24px;">
                <div>
                    <div style="font-size: 1.35rem; font-weight: 700; color: #1E293B; line-height: 1.1;">
                        {observations}
                    </div>
                    <div style="font-size: 0.78rem; color: #64748B; margin-top: 2px;">Observations</div>
                </div>
                <div>
                    <div style="font-size: 1.35rem; font-weight: 700; color: #1E293B; line-height: 1.1;">
                        {reflections}
                    </div>
                    <div style="font-size: 0.78rem; color: #64748B; margin-top: 2px;">Reflections</div>
                </div>
            </div>
            {snippet_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
