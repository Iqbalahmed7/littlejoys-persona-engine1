from __future__ import annotations

from typing import TYPE_CHECKING, Any

import plotly.graph_objects as go
import streamlit as st

from src.utils.display import ATTRIBUTE_CATEGORIES, display_name

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


def render_persona_spider(persona: Persona, *, key: str = "") -> None:
    """Render a compact radar chart of a persona's top 5 anchor traits.

    The chart shows the 5 most distinctive psychographic/behavioral traits for
    the persona, ranked by ``abs(value - 0.5)``.

    Args:
        persona: Persona to visualize.
        key: Streamlit widget key suffix for uniqueness.
    """

    flat: dict[str, Any] = persona.to_flat_dict()

    allowed_attrs: list[str] = []
    for attrs in ATTRIBUTE_CATEGORIES.values():
        allowed_attrs.extend(attrs)

    scored: list[tuple[str, float, float]] = []
    for attr in allowed_attrs:
        value = flat.get(attr)
        if not isinstance(value, float):
            continue
        if isinstance(value, bool):
            continue
        if not (0.0 <= value <= 1.0):
            continue

        distinctiveness = abs(value - 0.5)
        scored.append((attr, value, distinctiveness))

    scored.sort(key=lambda x: (-x[2], -x[1]))
    top_5 = scored[:5]

    labels = [display_name(attr) for attr, _v, _d in top_5]
    values = [v for _attr, v, _d in top_5]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            fillcolor="rgba(99, 102, 241, 0.15)",
            line=dict(color="#6366f1", width=2),
            marker=dict(size=6),
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickvals=[0.25, 0.50, 0.75],
                ticktext=["Low", "Mid", "High"],
                tickfont=dict(size=10),
            ),
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=20, b=20),
        height=280,
    )

    st.plotly_chart(fig, use_container_width=True, key=f"spider_{persona.id}_{key}")

    trait_summary = " · ".join(f"{display_name(attr)}: {value:.0%}" for attr, value, _d in top_5)
    st.caption(trait_summary)
