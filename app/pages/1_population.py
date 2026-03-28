# Streamlit multipage: numeric module name (``1_…``) is required for sidebar order.
# ruff: noqa: N999, TC002
"""
Population Explorer — Tier 1 overview, demographics, psychographics, Tier 2 narratives.
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
from src.taxonomy.schema import list_psychographic_continuous_attributes
from src.utils.dashboard_data import tier1_dataframe_with_results

st.title("Population Explorer")
st.caption("Synthetic Tier 1 cohort, demographics, and deep (Tier 2) persona narratives.")

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
n2 = len(pop.tier2_personas)
c1, c2, c3 = (
    DASHBOARD_BRAND_COLORS["primary"],
    DASHBOARD_BRAND_COLORS["secondary"],
    DASHBOARD_BRAND_COLORS["accent"],
)
m1, m2, m3 = st.columns(3)
m1.metric("Tier 1 (statistical)", f"{n1:,}")
m2.metric("Tier 2 (deep)", f"{n2:,}")
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
            choice = st.selectbox("Distribution (categorical)", cat, key="pop_demo_cat")
            vc = df[choice].astype(str).value_counts().reset_index()
            vc.columns = [choice, "count"]
            fig = px.bar(
                vc,
                x=choice,
                y="count",
                color_discrete_sequence=[c1],
                title=f"Count by {choice}",
            )
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    with h2:
        if "household_income_lpa" in df.columns:
            fig_h = px.histogram(
                df,
                x="household_income_lpa",
                nbins=24,
                color_discrete_sequence=[c2],
                title="Household income (LPA)",
            )
            fig_h.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_h, use_container_width=True)
else:
    st.info("No demographic columns found in Tier 1 frame.")

st.subheader("Psychographics — scatter")
psy_attrs = [a for a in list_psychographic_continuous_attributes() if a in df.columns]
if len(psy_attrs) >= 2:
    cxa, cxb = st.columns(2)
    with cxa:
        x_attr = st.selectbox("X axis", psy_attrs, index=0, key="pop_scatter_x")
    with cxb:
        y_choices = [a for a in psy_attrs if a != x_attr]
        y_attr = st.selectbox("Y axis", y_choices, index=0, key="pop_scatter_y")
    color_col = "outcome" if "outcome" in df.columns else None
    fig_s = px.scatter(
        df,
        x=x_attr,
        y=y_attr,
        color=color_col,
        color_discrete_map={
            "adopt": DASHBOARD_BRAND_COLORS["adopt"],
            "reject": DASHBOARD_BRAND_COLORS["reject"],
        }
        if color_col
        else None,
        opacity=0.65,
        title=f"{x_attr} vs {y_attr}"
        + (" (colored by simulation outcome)" if color_col else ""),
    )
    fig_s.update_traces(marker={"size": 8})
    fig_s.update_layout(height=DASHBOARD_CHART_HEIGHT)
    st.plotly_chart(fig_s, use_container_width=True)
    if color_col is None:
        st.caption("Run simulations on the home page to merge outcomes and color this chart.")
else:
    st.info("Not enough continuous psychographic columns in the current frame.")

st.subheader("Persona lookup")
lookup_id = st.text_input("Persona ID", placeholder="e.g. abc-t1-00042", key="pop_lookup_id")
if lookup_id.strip():
    try:
        persona = pop.get_persona(lookup_id.strip())
        st.success(f"Found: **{persona.id}** (`{persona.tier}`)")
        with st.expander("Flattened identity attributes", expanded=False):
            st.json(persona.to_flat_dict())
        if persona.narrative:
            st.markdown("**Narrative**")
            st.write(persona.narrative)
        else:
            st.caption("No Tier 2 narrative stored for this persona.")
    except KeyError:
        st.error("No persona matches that ID.")

st.subheader("Tier 2 deep narratives")
cap = min(DASHBOARD_MAX_TIER2_DISPLAY, len(pop.tier2_personas))
if cap == 0:
    st.caption("No Tier 2 personas in this population.")
else:
    st.caption(f"Showing up to {cap} of {len(pop.tier2_personas)} deep personas.")
    for persona in pop.tier2_personas[:cap]:
        title = f"{persona.id} — {persona.demographics.city_tier}"
        with st.expander(title, expanded=False):
            body = persona.narrative or "_No narrative text (statistical enrichment pending)._"
            st.markdown(body)
