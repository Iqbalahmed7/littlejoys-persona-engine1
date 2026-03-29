# Streamlit multipage: numeric module name (``1_…``) is required for sidebar order.
# ruff: noqa: N999
"""
Population Explorer — cohort overview, demographics, psychographics, persona stories.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.demographic_filters import render_demographic_filters
from app.components.persona_card import render_persona_card
from src.constants import (
    DASHBOARD_BRAND_COLORS,
    DASHBOARD_CHART_HEIGHT,
    SCENARIO_IDS,
)
from src.simulation.static import StaticSimulationResult
from src.utils.dashboard_data import child_age_group_label, tier1_dataframe_with_results
from src.utils.display import (
    ATTRIBUTE_CATEGORIES,
    SEC_DESCRIPTIONS,
    display_name,
    persona_display_name,
    scatter_attribute_pair_interpretation,
    scatter_purchase_outcome_label,
    scenario_product_display_name,
)

st.title("Population Explorer")
st.caption("Synthetic statistical cohort, demographics, psychographics, and rich persona stories.")

if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()

pop = st.session_state.population


def _active_scenario_id() -> str:
    raw = st.session_state.get("scenario_results") or {}
    sid = next((s for s in SCENARIO_IDS if s in raw), None)
    return sid if sid is not None else SCENARIO_IDS[0]


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
            hist_cols = [
                c
                for c in (
                    "city_tier",
                    "socioeconomic_class",
                    "region",
                    "household_income_lpa",
                )
                if c in df.columns
            ]
            hist_input = df[hist_cols].copy()
            filtered_hist_input = render_demographic_filters(
                hist_input,
                key_prefix="income_hist",
            )
            inc_filtered = df.loc[filtered_hist_input.index]

            inc_label = display_name("household_income_lpa")
            fig_h = px.histogram(
                inc_filtered,
                x="household_income_lpa",
                nbins=24,
                color_discrete_sequence=[c2],
                title=f"Distribution — {inc_label}",
            )
            fig_h.update_xaxes(title=inc_label)
            fig_h.update_yaxes(title="Count")
            fig_h.update_layout(height=400, showlegend=False)
            st.caption(f"Showing income distribution for {len(inc_filtered)} of {len(df)} personas")
            st.plotly_chart(fig_h, use_container_width=True)
else:
    st.info("No demographic columns found in Tier 1 frame.")

st.subheader("City Distribution")
if {"city_name", "city_tier"} <= set(df.columns):
    city_tier_map = df.drop_duplicates("city_name").set_index("city_name")["city_tier"].to_dict()
    city_counts = df["city_name"].astype(str).value_counts()
    n_cities = int(df["city_name"].nunique())
    top_n_cities = 15
    if len(city_counts) > top_n_cities:
        top = city_counts.head(top_n_cities)
        other_count = int(city_counts.iloc[top_n_cities:].sum())
        city_counts = pd.concat([top, pd.Series({"Other cities": other_count})])

    city_chart_df = city_counts.rename_axis("city_name").reset_index(name="count")
    city_chart_df["city_tier"] = city_chart_df["city_name"].map(city_tier_map).fillna("Mixed")
    city_chart_df = city_chart_df.sort_values("count", ascending=False)

    fig_city = px.bar(
        city_chart_df,
        x="count",
        y="city_name",
        color="city_tier",
        orientation="h",
        title=f"Count by {display_name('city_name')}",
        color_discrete_map={
            "Tier1": c1,
            "Tier2": c2,
            "Tier3": c3,
            "Mixed": DASHBOARD_BRAND_COLORS["neutral"],
        },
    )
    fig_city.update_xaxes(title="Number of Personas")
    fig_city.update_yaxes(title=display_name("city_name"), autorange="reversed")
    fig_city.update_layout(
        height=DASHBOARD_CHART_HEIGHT, legend_title_text=display_name("city_tier")
    )
    st.plotly_chart(fig_city, use_container_width=True)
    st.caption(
        f"Distribution across {n_cities} cities. Tier 1 metros in red, Tier 2 in teal, "
        f"Tier 3 in blue."
    )
else:
    st.info("City-level demographics are not available in the current frame.")

st.subheader("Children & Family")
family_cols = {"num_children", "youngest_child_age", "family_structure"}
if family_cols <= set(df.columns):
    child_col_left, child_col_right = st.columns(2)
    with child_col_left:
        num_children_counts = (
            df["num_children"]
            .value_counts()
            .sort_index()
            .rename_axis("num_children")
            .reset_index(name="count")
        )
        fig_nc = px.bar(
            num_children_counts,
            x="num_children",
            y="count",
            color_discrete_sequence=[DASHBOARD_BRAND_COLORS["primary"]],
            title="How many children do our personas have?",
        )
        fig_nc.update_xaxes(title=display_name("num_children"), dtick=1)
        fig_nc.update_yaxes(title="Count")
        fig_nc.update_layout(height=DASHBOARD_CHART_HEIGHT, showlegend=False)
        st.plotly_chart(fig_nc, use_container_width=True)

    with child_col_right:
        fig_ca = px.histogram(
            df,
            x="youngest_child_age",
            nbins=13,
            color_discrete_sequence=[DASHBOARD_BRAND_COLORS["secondary"]],
            title="Age of youngest child across personas",
        )
        fig_ca.update_xaxes(title=display_name("youngest_child_age"), dtick=1)
        fig_ca.update_yaxes(title="Count")
        fig_ca.update_layout(height=DASHBOARD_CHART_HEIGHT, showlegend=False)
        st.plotly_chart(fig_ca, use_container_width=True)

    age_groups = (
        df["youngest_child_age"]
        .apply(child_age_group_label)
        .value_counts()
        .reindex(
            ["Toddler (2-5)", "School-age (6-10)", "Pre-teen (11-14)", "Unknown"],
            fill_value=0,
        )
    )
    metric_groups = age_groups[age_groups > 0]
    if not metric_groups.empty:
        metric_cols = st.columns(len(metric_groups))
        for column, (group, count) in zip(metric_cols, metric_groups.items(), strict=False):
            pct = count / len(df) * 100
            column.metric(group, f"{int(count)}", f"{pct:.0f}% of population")

    toddler_pct = (
        df["youngest_child_age"]
        .apply(lambda age: False if pd.isna(age) else float(age) <= 5)
        .mean()
        * 100
    )
    older_pct = (
        df["youngest_child_age"]
        .apply(lambda age: False if pd.isna(age) else float(age) >= 7)
        .mean()
        * 100
    )
    st.caption(
        f"LittleJoys NutriMix (ages 2-6) is most relevant for the {toddler_pct:.0f}% of "
        f"families with toddlers. The 7-14 range ({older_pct:.0f}%) maps to NutriMix 7-14 "
        f"and Protein Mix."
    )

    family_structure_counts = (
        df["family_structure"]
        .astype(str)
        .map(display_name)
        .value_counts()
        .rename_axis("family_structure")
        .reset_index(name="count")
    )
    fig_fs = px.pie(
        family_structure_counts,
        names="family_structure",
        values="count",
        title=display_name("family_structure"),
        color_discrete_sequence=[
            DASHBOARD_BRAND_COLORS["primary"],
            DASHBOARD_BRAND_COLORS["secondary"],
            DASHBOARD_BRAND_COLORS["accent"],
        ],
    )
    fig_fs.update_layout(height=DASHBOARD_CHART_HEIGHT)
    st.plotly_chart(fig_fs, use_container_width=True)
else:
    st.info("Children and family demographics are not available in the current frame.")

df_scatter = render_demographic_filters(df, key_prefix="pop_scatter_demo")

st.subheader("Psychographics — scatter")
category = st.selectbox(
    "Attribute category",
    list(ATTRIBUTE_CATEGORIES.keys()),
    key="pop_psy_category",
)
attrs_in_category = [a for a in ATTRIBUTE_CATEGORIES[category] if a in df_scatter.columns]
if len(df_scatter) == 0:
    st.warning("No personas match these filters. Widen your demographic selections above.")
elif len(attrs_in_category) >= 2:
    df_s = df_scatter
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
    color_col = "outcome" if "outcome" in df_s.columns else None
    plot_df = df_s
    quadrants: dict[str, pd.DataFrame] = {}
    overall_rate = 0.0
    median_x = 0.5
    median_y = 0.5

    if color_col:
        plot_df = df_s.assign(
            _outcome_display=df_s["outcome"].map(scatter_purchase_outcome_label),
        )
        color_key = "_outcome_display"
        outcome_legend = "Purchase intent"
        title_text = (
            f"Do parents with high {display_name(x_attr)} and {display_name(y_attr)} buy more?"
        )
        subtitle_text = f"{display_name(x_attr)} vs {display_name(y_attr)}"
        median_x = float(df_s[x_attr].median())
        median_y = float(df_s[y_attr].median())
        if pd.isna(median_x):
            median_x = 0.5
        if pd.isna(median_y):
            median_y = 0.5

        quadrants = {
            "High-High": df_s[(df_s[x_attr] >= median_x) & (df_s[y_attr] >= median_y)],
            "High-Low": df_s[(df_s[x_attr] >= median_x) & (df_s[y_attr] < median_y)],
            "Low-High": df_s[(df_s[x_attr] < median_x) & (df_s[y_attr] >= median_y)],
            "Low-Low": df_s[(df_s[x_attr] < median_x) & (df_s[y_attr] < median_y)],
        }

        overall_rate = float((df_s[color_col] == "adopt").mean())

        best_quad = max(
            quadrants.items(),
            key=lambda q: (q[1][color_col] == "adopt").mean() if len(q[1]) > 0 else 0,
        )
        best_quad_rate = float((best_quad[1][color_col] == "adopt").mean())
        x_dir = "high" if "High-" in best_quad[0] else "low"
        y_dir = "high" if "-High" in best_quad[0] else "low"
        delta_pp = (best_quad_rate - overall_rate) * 100.0
        rel_clause = ""
        if overall_rate > 0:
            rel_lift = (best_quad_rate - overall_rate) / overall_rate * 100.0
            rel_clause = f" ({rel_lift:+.0f}% relative to baseline)."
        interp = scatter_attribute_pair_interpretation(x_attr, y_attr)
        prod = scenario_product_display_name(_active_scenario_id())
        narrative = (
            f"Among the **{len(df_s):,} parents** matching your filters, those with **{x_dir}** "
            f"{display_name(x_attr)} and **{y_dir}** {display_name(y_attr)} are "
            f"**{delta_pp:+.0f} percentage points** versus baseline on purchase intent for "
            f"**{prod}** — **{best_quad_rate:.0%}** would buy vs **{overall_rate:.0%}** across "
            f"this filtered cohort{rel_clause} {interp}"
        )
    else:
        color_key = None
        outcome_legend = ""
        title_text = ""
        subtitle_text = f"{display_name(x_attr)} vs {display_name(y_attr)}"
        narrative = ""

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
        if overall_rate > 0:
            st.markdown("##### Quadrant lift vs baseline")
            qcols = st.columns(4)
            for i, (quad_name, quad_df) in enumerate(quadrants.items()):
                if len(quad_df) == 0:
                    continue
                quad_rate = float((quad_df[color_col] == "adopt").mean())
                rel_diff = abs(quad_rate - overall_rate) / overall_rate
                if rel_diff > 0.15:
                    delta = quad_rate - overall_rate
                    with qcols[i]:
                        st.metric(
                            label=f"{quad_name} ({len(quad_df)} parents)",
                            value=f"{quad_rate:.0%}",
                            delta=f"{delta:+.0%} vs baseline",
                        )
        if narrative:
            st.info(narrative)
        elif color_col:
            st.caption("No strong differences between quadrants for these two attributes.")
else:
    st.info(
        "Not enough attributes from this category appear in the current frame for a scatter plot "
        "(need at least two).",
    )

results_by_persona = _results_for_merge()

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

st.subheader("Persona Browser")

pb_cols = st.columns(5)
with pb_cols[0]:
    pb_tier = st.multiselect(
        display_name("city_tier"),
        options=sorted(df["city_tier"].dropna().unique().tolist()),
        default=sorted(df["city_tier"].dropna().unique().tolist()),
        key="pb_tier",
    )
with pb_cols[1]:
    pb_sec = st.multiselect(
        display_name("socioeconomic_class"),
        options=sorted(df["socioeconomic_class"].dropna().unique().tolist()),
        default=sorted(df["socioeconomic_class"].dropna().unique().tolist()),
        key="pb_sec",
    )
with pb_cols[2]:
    pb_children = st.multiselect(
        display_name("num_children"),
        options=sorted(df["num_children"].dropna().unique().tolist()),
        default=sorted(df["num_children"].dropna().unique().tolist()),
        key="pb_children",
    )
with pb_cols[3]:
    income_min, income_max = (
        float(df["household_income_lpa"].min()),
        float(df["household_income_lpa"].max()),
    )
    pb_income = st.slider(
        display_name("household_income_lpa"),
        min_value=income_min,
        max_value=income_max,
        value=(income_min, income_max),
        key="pb_income",
    )
with pb_cols[4]:
    if "outcome" in df.columns:
        pb_outcome = st.multiselect(
            display_name("outcome"),
            ["adopt", "reject"],
            default=["adopt", "reject"],
            key="pb_outcome",
        )
    else:
        pb_outcome = ["adopt", "reject"]

browser_df = df
browser_df = browser_df[browser_df["city_tier"].isin(pb_tier)]
browser_df = browser_df[browser_df["socioeconomic_class"].isin(pb_sec)]
browser_df = browser_df[browser_df["num_children"].isin(pb_children)]
browser_df = browser_df[browser_df["household_income_lpa"].between(*pb_income)]
if "outcome" in browser_df.columns:
    browser_df = browser_df[browser_df["outcome"].isin(pb_outcome)]

sort_options = {
    "Persona ID": "id",
    "Income (high to low)": "household_income_lpa",
    "Parent Age": "parent_age",
    "Purchase Score": "purchase_score",
}
sort_choice = st.selectbox("Sort by", list(sort_options.keys()), key="pb_sort")
sort_col = sort_options[sort_choice]
ascending = sort_choice != "Income (high to low)"
if sort_col in browser_df.columns:
    browser_df = browser_df.sort_values(sort_col, ascending=ascending)

st.caption(f"Showing {len(browser_df)} of {len(df)} personas matching your filters")

stat_cols = st.columns(4)
stat_cols[0].metric("Matching Personas", len(browser_df))
if "outcome" in browser_df.columns and len(browser_df) > 0:
    adopt_rate = float((browser_df["outcome"] == "adopt").mean())
    stat_cols[1].metric("Adoption Rate", f"{adopt_rate:.0%}")
else:
    stat_cols[1].metric("Adoption Rate", "—")
if len(browser_df) > 0:
    stat_cols[2].metric("Avg Income", f"₹{float(browser_df['household_income_lpa'].mean()):.1f}L")
    stat_cols[3].metric("Avg Children", f"{float(browser_df['num_children'].mean()):.1f}")
else:
    stat_cols[2].metric("Avg Income", "—")
    stat_cols[3].metric("Avg Children", "—")

PAGE_SIZE = 10
total_pages = max(1, (len(browser_df) + PAGE_SIZE - 1) // PAGE_SIZE)
page = st.number_input(
    "Page",
    min_value=1,
    max_value=total_pages,
    value=1,
    step=1,
    key="pb_page",
)
start = (int(page) - 1) * PAGE_SIZE
page_df = browser_df.iloc[start : start + PAGE_SIZE]

if page_df.empty:
    st.caption("No personas match your current filters.")
else:
    for _, row in page_df.iterrows():
        persona = pop.get_persona(str(row["id"]))
        result = results_by_persona.get(persona.id) if results_by_persona else None
        render_persona_card(persona, result)
        if persona.narrative:
            with st.expander(
                "Read narrative",
                expanded=False,
                key=f"narr_{persona.id}",
            ):
                st.markdown(persona.narrative)
