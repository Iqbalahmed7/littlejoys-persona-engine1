# OpenCode — Sprint 8 Track C: Income Filters + Filtered Persona Browser

**Branch:** `sprint-8-track-c-persona-browser`
**Base:** `main`

## Context

The Population Explorer page (`app/pages/1_population.py`) currently:
1. Shows a household income histogram with no demographic filtering
2. Displays 30 persona narratives in a wall of expanders with no filtering

This track adds demographic filters to the income chart and replaces the persona wall with a searchable, filterable persona browser.

## Deliverables

### 1. Income Histogram with Demographic Filters

**File:** `app/pages/1_population.py` (MODIFY)

The income histogram is currently in the Demographics section (lines 137-149). Add filter controls above it.

**Implementation:** Import `render_demographic_filters` from `app/components/demographic_filters.py` (being built by Cursor in Track A). If that import fails (not yet merged), implement a minimal inline version with just city_tier and SEC multi-selects.

**Fallback inline filters** (in case Track A isn't merged yet):

```python
# Inline income filter — will be replaced by shared component post-merge
inc_filter_cols = st.columns(3)
with inc_filter_cols[0]:
    inc_tier_filter = st.multiselect(
        "City Tier",
        options=sorted(df["city_tier"].unique()),
        default=sorted(df["city_tier"].unique()),
        key="inc_tier_filter",
    )
with inc_filter_cols[1]:
    inc_sec_filter = st.multiselect(
        "SEC Class",
        options=sorted(df["socioeconomic_class"].unique()),
        default=sorted(df["socioeconomic_class"].unique()),
        key="inc_sec_filter",
    )
with inc_filter_cols[2]:
    inc_region_filter = st.multiselect(
        "Region",
        options=sorted(df["region"].unique()),
        default=sorted(df["region"].unique()),
        key="inc_region_filter",
    )
inc_filtered = df[
    df["city_tier"].isin(inc_tier_filter)
    & df["socioeconomic_class"].isin(inc_sec_filter)
    & df["region"].isin(inc_region_filter)
]
```

Use `inc_filtered` for the histogram. Show caption: `"Showing income distribution for {len(inc_filtered)} of {len(df)} personas"`

### 2. Filtered Persona Browser (Replace Persona Stories Section)

**File:** `app/pages/1_population.py` (MODIFY lines 278-310)

Replace the current "Persona stories" section (which shows 30 expanders in a wall) with a proper filterable browser.

**Section title:** `st.subheader("Persona Browser")`

**Filter bar** (compact row above the results):

```python
pb_cols = st.columns(5)
with pb_cols[0]:
    pb_tier = st.multiselect("City Tier", sorted(df["city_tier"].unique()),
                              default=sorted(df["city_tier"].unique()), key="pb_tier")
with pb_cols[1]:
    pb_sec = st.multiselect("SEC Class", sorted(df["socioeconomic_class"].unique()),
                             default=sorted(df["socioeconomic_class"].unique()), key="pb_sec")
with pb_cols[2]:
    pb_children = st.multiselect("Children", sorted(df["num_children"].unique()),
                                  default=sorted(df["num_children"].unique()), key="pb_children")
with pb_cols[3]:
    income_min, income_max = float(df["household_income_lpa"].min()), float(df["household_income_lpa"].max())
    pb_income = st.slider("Income (₹ LPA)", income_min, income_max,
                           (income_min, income_max), key="pb_income")
with pb_cols[4]:
    pb_outcome = st.multiselect("Outcome", ["adopt", "reject"],
                                 default=["adopt", "reject"], key="pb_outcome")
```

**Apply filters:**
```python
browser_df = df[
    df["city_tier"].isin(pb_tier)
    & df["socioeconomic_class"].isin(pb_sec)
    & df["num_children"].isin(pb_children)
    & df["household_income_lpa"].between(*pb_income)
]
if "outcome" in df.columns:
    browser_df = browser_df[browser_df["outcome"].isin(pb_outcome)]
```

**Sort control:**
```python
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
```

**Results display:**

```python
st.caption(f"Showing {len(browser_df)} of {len(df)} personas matching your filters")
```

**Pagination:**
```python
PAGE_SIZE = 10
total_pages = max(1, (len(browser_df) + PAGE_SIZE - 1) // PAGE_SIZE)
page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, key="pb_page")
start = (page - 1) * PAGE_SIZE
page_df = browser_df.iloc[start:start + PAGE_SIZE]
```

**For each persona on the page**, render using a modified version of `render_persona_card()` from `app/components/persona_card.py`. Import and use it:

```python
from app.components.persona_card import render_persona_card

for _, row in page_df.iterrows():
    persona = pop.get_persona(row["id"])
    result = results_by_persona.get(persona.id) if results_by_persona else None
    render_persona_card(persona, result)
    if persona.narrative:
        with st.expander("Read narrative", expanded=False):
            st.markdown(persona.narrative)
```

**Also keep the Persona Lookup** (text input search by ID) — move it above the browser as a quick-access tool.

### 3. Summary Stats Bar

Above the persona browser results, show key stats for the filtered set:

```python
stat_cols = st.columns(4)
stat_cols[0].metric("Matching Personas", len(browser_df))
if "outcome" in browser_df.columns:
    adopt_rate = (browser_df["outcome"] == "adopt").mean()
    stat_cols[1].metric("Adoption Rate", f"{adopt_rate:.0%}")
stat_cols[2].metric("Avg Income", f"₹{browser_df['household_income_lpa'].mean():.1f}L")
stat_cols[3].metric("Avg Children", f"{browser_df['num_children'].mean():.1f}")
```

## Files to Read Before Starting

1. `app/pages/1_population.py` — full file (you're modifying this)
2. `app/components/persona_card.py` — `render_persona_card()` to reuse
3. `src/utils/display.py` — `display_name()`, `persona_display_name()`
4. `src/utils/dashboard_data.py` — `tier1_dataframe_with_results()`
5. `src/constants.py` — `DASHBOARD_MAX_TIER2_DISPLAY`, `DASHBOARD_BRAND_COLORS`

## Constraints

- Python 3.11+
- Do NOT add `st.set_page_config()` — it's only in `app/streamlit_app.py`
- Use `display_name()` for filter labels where applicable
- Use `key=` parameter on ALL Streamlit widgets (avoid duplicate key errors)
- Use `use_container_width=True` for plotly charts
- The persona browser must handle the case where no simulation results exist (no `outcome` column)
- Pagination is required — do NOT render all 200 personas at once
- No new pip dependencies
- If `render_demographic_filters` from Track A is not available, use inline filters (as shown above)

## Acceptance Criteria

- [ ] Income histogram can be filtered by city tier, SEC, region
- [ ] Persona browser has 5 filter dimensions (tier, SEC, children, income, outcome)
- [ ] Browser shows paginated results (10 per page)
- [ ] Sort control works (by ID, income, age, purchase score)
- [ ] Summary stats update with filters
- [ ] Persona cards display correctly with demographics + psychographics + outcome
- [ ] Narrative expander shows for personas with narratives
- [ ] Persona lookup (text input) still works
- [ ] Handles missing simulation results gracefully
- [ ] No `st.set_page_config()` in page files
