"""Reusable demographic filters for Streamlit dashboard pages (Sprint 8 Track A)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.utils.display import display_name, income_bracket_ui_label

_CITY_TIERS = ("Tier1", "Tier2", "Tier3")
_SEC_CLASSES = ("A1", "A2", "B1", "B2", "C1", "C2")
_REGIONS = ("North", "South", "East", "West", "NE")
_INCOME_CODES = ("low_income", "middle_income", "high_income")
_NUM_CHILDREN = (1, 2, 3, 4, 5)
_CHILD_AGE_GROUPS = ("Toddler (2-5)", "School-age (6-10)", "Pre-teen (11-14)")


def child_age_group_mask(series: pd.Series, selected_labels: list[str]) -> pd.Series:
    """
    True where ``youngest_child_age`` falls in ANY selected age band.

    Empty ``selected_labels`` means no restriction (all True).
    """

    if selected_labels is None or len(selected_labels) == 0:
        return pd.Series(True, index=series.index)

    mask = pd.Series(False, index=series.index)
    if "Toddler (2-5)" in selected_labels:
        mask |= series.between(2, 5, inclusive="both")
    if "School-age (6-10)" in selected_labels:
        mask |= series.between(6, 10, inclusive="both")
    if "Pre-teen (11-14)" in selected_labels:
        mask |= series.between(11, 14, inclusive="both")
    return mask


def render_demographic_filters(
    df: pd.DataFrame,
    key_prefix: str = "demo_filter",
) -> pd.DataFrame:
    """
    Render demographic filter widgets in a compact grid and return the filtered dataframe.

    Filters are multi-select; default is all options selected (full cohort).
    """

    filtered = df.copy()
    n_total = len(df)

    st.markdown("**Demographic filters**")
    st.caption("Narrow the psychographics scatter; demographics charts above still use the full cohort.")

    row1 = st.columns(3)
    row2 = st.columns(3)

    if "city_tier" in df.columns:
        opts = [o for o in _CITY_TIERS if o in set(df["city_tier"].astype(str).unique())]
        if not opts:
            opts = list(_CITY_TIERS)
        sel = row1[0].multiselect(
            display_name("city_tier"),
            options=opts,
            default=opts,
            key=f"{key_prefix}_city_tier",
        )
        if sel:
            filtered = filtered[filtered["city_tier"].astype(str).isin(sel)]

    if "socioeconomic_class" in df.columns:
        opts = [o for o in _SEC_CLASSES if o in set(df["socioeconomic_class"].astype(str).unique())]
        if not opts:
            opts = list(_SEC_CLASSES)
        sel = row1[1].multiselect(
            display_name("socioeconomic_class"),
            options=opts,
            default=opts,
            key=f"{key_prefix}_sec",
        )
        if sel:
            filtered = filtered[filtered["socioeconomic_class"].astype(str).isin(sel)]

    if "region" in df.columns:
        opts = [o for o in _REGIONS if o in set(df["region"].astype(str).unique())]
        if not opts:
            opts = list(_REGIONS)
        sel = row1[2].multiselect(
            display_name("region"),
            options=opts,
            default=opts,
            key=f"{key_prefix}_region",
        )
        if sel:
            filtered = filtered[filtered["region"].astype(str).isin(sel)]

    if "income_bracket" in df.columns:
        opts = [c for c in _INCOME_CODES if c in set(df["income_bracket"].astype(str).unique())]
        if not opts:
            opts = list(_INCOME_CODES)
        sel = row2[0].multiselect(
            display_name("income_bracket"),
            options=opts,
            format_func=income_bracket_ui_label,
            default=opts,
            key=f"{key_prefix}_income",
        )
        if sel:
            filtered = filtered[filtered["income_bracket"].astype(str).isin(sel)]

    if "num_children" in df.columns:
        nc = pd.to_numeric(df["num_children"], errors="coerce").fillna(0).astype(int)
        present = sorted({int(x) for x in nc.unique() if 1 <= int(x) <= 5})
        opts = present if present else list(_NUM_CHILDREN)
        sel = row2[1].multiselect(
            display_name("num_children"),
            options=opts,
            default=opts,
            key=f"{key_prefix}_num_children",
        )
        if sel:
            filtered = filtered[pd.to_numeric(filtered["num_children"], errors="coerce").isin(sel)]

    if "youngest_child_age" in df.columns:
        sel = row2[2].multiselect(
            display_name("child_age_group_filter"),
            options=list(_CHILD_AGE_GROUPS),
            default=list(_CHILD_AGE_GROUPS),
            help=(
                "Based on youngest child age. A persona matches if any selected band "
                "includes that age."
            ),
            key=f"{key_prefix}_child_age",
        )
        if sel:
            ages_f = pd.to_numeric(filtered["youngest_child_age"], errors="coerce")
            m = child_age_group_mask(ages_f, sel)
            filtered = filtered[m]

    st.caption(f"Showing **{len(filtered):,}** of **{n_total:,}** personas matching filters")
    return filtered
