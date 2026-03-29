# Streamlit multipage: numeric module name (``1_…``) is required for sidebar order.
# ruff: noqa: N999, TC002
"""
Population Explorer — cohort overview, demographics, psychographics, persona stories.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.constants import (
    DASHBOARD_BRAND_COLORS,
    DASHBOARD_CHART_HEIGHT,
    DASHBOARD_MAX_TIER2_DISPLAY,
    SCENARIO_IDS,
)
from src.simulation.static import StaticSimulationResult
from src.utils.dashboard_data import tier1_dataframe_with_results
from src.utils.display import (
    ATTRIBUTE_CATEGORIES,
    SEC_DESCRIPTIONS,
    display_name,
    persona_display_name,
    scatter_purchase_outcome_label,
)

st.title("Population Explorer")
st.caption("Synthetic statistical cohort, demographics, psychographics, and rich persona stories.")

if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()

pop = st.session_state.population


def _results_for_merge() -> dict[str, dict] | None:
    raw = st.session_state.get("scenario_results") or {}
    if not raw:
        return None
    sid = next((s for s in SCENARIO_IDS if s in raw), next(iter(raw.keys()), None))
    if sid is None:
        return None
    entry = raw[sid]
    if isinstance(entry, StaticSimulationResult):
        return dict(entry.results_by_persona)
    if isinstance(entry, dict) and "results_by_persona" in entry:
        return dict(entry["results_by_persona"])
    return None


@st.cache_data(show_spinner=False)
def _tier1_dataframe(
    _population_id: str,
    tier1_ids_fingerprint: tuple[str, ...],
    _scenario_fingerprint: str,
) -> pd.DataFrame:
    """Cache Tier-1 frame; scenario fingerprint busts cache when sim outputs change."""

    _p = st.session_state.population
    res = _results_for_merge()
    return tier1_dataframe_with_results(_p, res)


tier1_ids = tuple(sorted(p.id for p in pop.tier1_personas))
scenario_fp = ""
raw_sr = st.session_state.get("scenario_results") or {}
if raw_sr:
    parts: list[str] = []
    for sid in SCENARIO_IDS:
        if sid not in raw_sr:
            continue
        e = raw_sr[sid]
        if isinstance(e, StaticSimulationResult):
            parts.append(f"{sid}:{e.adoption_count}:{e.population_size}")
        elif isinstance(e, dict) and "adoption_count" in e:
            parts.append(f"{sid}:{e.get('adoption_count')}:{e.get('population_size')}")
    scenario_fp = "|".join(parts)

df = _tier1_dataframe(pop.id, tier1_ids, scenario_fp)

n1 = len(pop.tier1_personas)
n2 = sum(1 for p in pop.tier1_personas if p.narrative)
c1, c2, c3 = (
    DASHBOARD_BRAND_COLORS["primary"],
    DASHBOARD_BRAND_COLORS["secondary"],
    DASHBOARD_BRAND_COLORS["accent"],
)
m1, m2, m3 = st.columns(3)
m1.metric("Population Size", f"{n1:,}")
m2.metric("Personas with Narratives", f"{n2:,}")
m3.metric("Total personas", f"{n1 + n2:,}")

st.subheader("Demographics")
demo_cols = [
    c
    for c in (
        "city_tier",
        "region",
        "socioeconomic_class",
        "household_income_lpa",
        "parent_age",
    )
    if c in df.columns
]
if demo_cols:
    h1, h2 = st.columns(2)
    with h1:
        cat = [c for c in demo_cols if c != "household_income_lpa"]
        if cat:
            choice = st.selectbox(
                "Distribution (categorical)",
                cat,
                format_func=display_name,
                key="pop_demo_cat",
            )
            vc = df[choice].astype(str).value_counts().reset_index()
            vc.columns = [choice, "count"]
            fig = px.bar(
                vc,
                x=choice,
                y="count",
                color_discrete_sequence=[c1],
                title=f"Count by {display_name(choice)}",
            )
            fig.update_xaxes(title=display_name(choice))
            fig.update_yaxes(title="Count")
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            if choice == "socioeconomic_class":
                with st.expander("What do SEC classes mean?"):
                    for cls, desc in SEC_DESCRIPTIONS.items():
                        st.markdown(f"**{cls}**: {desc}")
    with h2:
        if "household_income_lpa" in df.columns:
            inc_label = display_name("household_income_lpa")
            fig_h = px.histogram(
                df,
                x="household_income_lpa",
                nbins=24,
                color_discrete_sequence=[c2],
                title=f"Distribution — {inc_label}",
            )
            fig_h.update_xaxes(title=inc_label)
            fig_h.update_yaxes(title="Count")
            fig_h.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_h, use_container_width=True)
else:
    st.info("No demographic columns found in Tier 1 frame.")

st.subheader("Psychographics — scatter")
category = st.selectbox(
    "Attribute category",
    list(ATTRIBUTE_CATEGORIES.keys()),
    key="pop_psy_category",
)
attrs_in_category = [a for a in ATTRIBUTE_CATEGORIES[category] if a in df.columns]
if len(attrs_in_category) >= 2:
    cxa, cxb = st.columns(2)
    with cxa:
        x_attr = st.selectbox(
            "X axis",
            attrs_in_category,
            format_func=display_name,
            key="pop_scatter_x",
        )
    with cxb:
        y_choices = [a for a in attrs_in_category if a != x_attr]
        y_attr = st.selectbox(
            "Y axis",
            y_choices,
            format_func=display_name,
            key="pop_scatter_y",
        )
    color_col = "outcome" if "outcome" in df.columns else None
    plot_df = df
    insight_parts: list[str] = []
    headline: str | None = None
    quadrants: dict[str, pd.DataFrame] = {}
    overall_rate = 0.0

    if color_col:
        plot_df = df.assign(
            _outcome_display=df["outcome"].map(scatter_purchase_outcome_label),
        )
        color_key = "_outcome_display"
        outcome_legend = "Purchase intent"
        title_text = (
            f"Do parents with high {display_name(x_attr)} and {display_name(y_attr)} buy more?"
        )
        subtitle_text = f"{display_name(x_attr)} vs {display_name(y_attr)}"
        median_x = df[x_attr].median()
        median_y = df[y_attr].median()

        quadrants = {
            "High-High": df[(df[x_attr] >= median_x) & (df[y_attr] >= median_y)],
            "High-Low": df[(df[x_attr] >= median_x) & (df[y_attr] < median_y)],
            "Low-High": df[(df[x_attr] < median_x) & (df[y_attr] >= median_y)],
            "Low-Low": df[(df[x_attr] < median_x) & (df[y_attr] < median_y)],
        }

        overall_rate = (df[color_col] == "adopt").mean()

        for quad_name, quad_df in quadrants.items():
            if len(quad_df) > 0:
                quad_rate = (quad_df[color_col] == "adopt").mean()
                ratio = quad_rate / overall_rate if overall_rate > 0 else 0
                if ratio > 1.3 or ratio < 0.7:
                    insight_parts.append(
                        f"**{quad_name}** quadrant: {quad_rate:.0%} would buy "
                        f"({ratio:.1f}x average)"
                    )

        best_quad = max(
            quadrants.items(),
            key=lambda q: (q[1][color_col] == "adopt").mean() if len(q[1]) > 0 else 0,
        )
        best_quad_rate = (best_quad[1][color_col] == "adopt").mean()
        x_dir = "high" if "High-" in best_quad[0] else "low"
        y_dir = "high" if "-High" in best_quad[0] else "low"
        headline = (
            f"Parents with {x_dir} {display_name(x_attr)} and {y_dir} {display_name(y_attr)} "
            f"would buy at {best_quad_rate:.0%}, compared with {overall_rate:.0%} across "
            "everyone in this simulation."
        )
    else:
        color_key = None
        outcome_legend = ""
        title_text = ""
        subtitle_text = f"{display_name(x_attr)} vs {display_name(y_attr)}"

    fig_s = px.scatter(
        plot_df,
        x=x_attr,
        y=y_attr,
        color=color_key,
        opacity=0.65,
        title=title_text if color_col else subtitle_text,
        color_discrete_map={
            "Would buy": DASHBOARD_BRAND_COLORS["adopt"],
            "Wouldn't buy": DASHBOARD_BRAND_COLORS["reject"],
            "No simulation": DASHBOARD_BRAND_COLORS["neutral"],
        }
        if color_col
        else None,
    )
    if color_col:
        fig_s.update_layout(legend_title_text=outcome_legend)
        fig_s.add_hline(y=median_y, line_dash="dot", line_color="gray", opacity=0.5)
        fig_s.add_vline(x=median_x, line_dash="dot", line_color="gray", opacity=0.5)
    fig_s.update_xaxes(title=f"{display_name(x_attr)} (0 = low, 1 = high)")
    fig_s.update_yaxes(title=f"{display_name(y_attr)} (0 = low, 1 = high)")
    fig_s.update_traces(marker={"size": 8})
    fig_s.update_layout(height=DASHBOARD_CHART_HEIGHT)

    st.plotly_chart(fig_s, use_container_width=True)
    if color_col is None:
        st.info(
            "Run a scenario from the **Home** page first. Once you do, this chart will colour "
            "each persona by whether they **would buy** or **wouldn't buy** — revealing which "
            "attribute combinations predict purchase behaviour."
        )
    else:
        if headline:
            st.info(headline)
        if insight_parts:
            st.info(" · ".join(insight_parts))
        elif not insight_parts:
            st.caption("No strong differences between quadrants for these two attributes.")
else:
    st.info(
        "Not enough attributes from this category appear in the current frame for a scatter plot "
        "(need at least two).",
    )

st.subheader("Persona lookup")
lookup_id = st.text_input("Persona ID", placeholder="e.g. Priya-Mumbai-Mom-32", key="pop_lookup_id")
if lookup_id.strip():
    try:
        persona = pop.get_persona(lookup_id.strip())
        primary = persona_display_name(persona)
        st.success(f"**{primary}** · `{persona.id}`")
        with st.expander("Identity attributes (technical view)", expanded=False):
            labeled = {display_name(k): v for k, v in sorted(persona.to_flat_dict().items())}
            st.json(labeled)
        if persona.narrative:
            st.markdown("**Narrative**")
            st.write(persona.narrative)
        else:
            st.caption("No narrative text stored for this persona yet.")
    except KeyError:
        st.error("No persona matches that ID.")

st.subheader("Persona stories")
_narrative_personas = [p for p in pop.tier1_personas if p.narrative]
cap = min(DASHBOARD_MAX_TIER2_DISPLAY, len(_narrative_personas))
if cap == 0:
    st.caption("No personas with narratives in this population.")
else:
    st.caption(
        f"Showing up to {cap} of {len(_narrative_personas)} personas that include narrative text."
    )
    for persona in _narrative_personas[:cap]:
        title = f"{persona_display_name(persona)} · `{persona.id}`"
        with st.expander(title, expanded=False):
            body = persona.narrative or "_No narrative text yet._"
            st.markdown(body)
