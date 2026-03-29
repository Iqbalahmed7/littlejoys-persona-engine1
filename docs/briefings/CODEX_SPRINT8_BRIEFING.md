# Codex — Sprint 8 Track B: City Distribution + Children Demographics

**Branch:** `sprint-8-track-b-city-children`
**Base:** `main`

## Context

The Population Explorer page (`app/pages/1_population.py`) is missing two critical demographic visualizations for a kids nutrition D2C product:
1. No city-level distribution — users can't see which cities their personas come from
2. No children-related demographics — `num_children`, `youngest_child_age`, `child_ages` are in the data model but never visualized

This track adds both.

## Deliverables

### 1. City Distribution Chart

**File:** `app/pages/1_population.py` (MODIFY)

Add a new section after the existing Demographics section (after line 151, before the Psychographics scatter).

**Section title:** `st.subheader("City Distribution")`

**Chart:** Horizontal bar chart showing persona count by city, sorted descending.

```python
# Group cities: show top 15 individually, rest as "Other cities"
city_counts = df["city_name"].value_counts()
TOP_N_CITIES = 15
if len(city_counts) > TOP_N_CITIES:
    top = city_counts.head(TOP_N_CITIES)
    other_count = city_counts.iloc[TOP_N_CITIES:].sum()
    city_counts = pd.concat([top, pd.Series({"Other cities": other_count})])

# Color by city tier
```

Implementation details:
- Horizontal bar chart via `px.bar(..., orientation='h')`
- Color bars by city tier (use the `city_tier` column — join city_name to city_tier from the dataframe)
- Color mapping: `{"Tier1": "#FF6B6B", "Tier2": "#4ECDC4", "Tier3": "#45B7D1"}` (from DASHBOARD_BRAND_COLORS: primary, secondary, accent)
- Sort by count descending (largest city at top)
- X-axis: "Number of Personas", Y-axis: city names
- Height: 500px
- Add a caption: "Distribution across {n_cities} cities. Tier 1 metros in red, Tier 2 in teal, Tier 3 in blue."

**City-tier mapping:** The dataframe already has both `city_name` and `city_tier` columns from the persona model. Create a lookup:
```python
city_tier_map = df.drop_duplicates("city_name").set_index("city_name")["city_tier"].to_dict()
```

### 2. Children & Family Demographics

**File:** `app/pages/1_population.py` (MODIFY)

Add a new section after City Distribution.

**Section title:** `st.subheader("Children & Family")`

**Layout:** Two columns.

**Left column — Number of Children:**
```python
fig_nc = px.bar(
    df["num_children"].value_counts().sort_index().reset_index(),
    x="num_children",
    y="count",
    color_discrete_sequence=[DASHBOARD_BRAND_COLORS["primary"]],
    title="How many children do our personas have?",
)
fig_nc.update_xaxes(title="Number of Children", dtick=1)
fig_nc.update_yaxes(title="Count")
```

**Right column — Youngest Child's Age:**
```python
fig_ca = px.histogram(
    df,
    x="youngest_child_age",
    nbins=13,  # ages 2-14
    color_discrete_sequence=[DASHBOARD_BRAND_COLORS["secondary"]],
    title="Age of youngest child across personas",
)
fig_ca.update_xaxes(title="Youngest Child's Age (years)", dtick=1)
fig_ca.update_yaxes(title="Count")
```

**Below the two columns — Child Age Group Breakdown:**

Add a derived column for age group analysis:
```python
def child_age_group(age: int | float | None) -> str:
    if age is None:
        return "Unknown"
    if age <= 5:
        return "Toddler (2-5)"
    if age <= 10:
        return "School-age (6-10)"
    return "Pre-teen (11-14)"
```

Add this helper to `src/utils/dashboard_data.py` as `child_age_group_label()`.

Show a horizontal stacked bar or metric tiles:
```python
age_groups = df["youngest_child_age"].apply(child_age_group).value_counts()
cols = st.columns(len(age_groups))
for col, (group, count) in zip(cols, age_groups.items()):
    pct = count / len(df) * 100
    col.metric(group, f"{count}", f"{pct:.0f}% of population")
```

**Additional insight caption:**
```python
st.caption(
    f"LittleJoys NutriMix (ages 2-6) is most relevant for the "
    f"{toddler_pct:.0f}% of families with toddlers. "
    f"The 7-14 range ({older_pct:.0f}%) maps to NutriMix 7-14 and Protein Mix."
)
```

### 3. Family Structure Pie Chart

In the same "Children & Family" section, add below the age group metrics:

```python
fig_fs = px.pie(
    df["family_structure"].value_counts().reset_index(),
    names="family_structure",
    values="count",
    title="Family Structure",
    color_discrete_sequence=[
        DASHBOARD_BRAND_COLORS["primary"],
        DASHBOARD_BRAND_COLORS["secondary"],
        DASHBOARD_BRAND_COLORS["accent"],
    ],
)
```

Use `display_name()` for the family_structure values in labels. Map: `"nuclear"` → `"Nuclear Family"`, `"joint"` → `"Joint Family"`, `"single_parent"` → `"Single Parent"`.

Add these to `ATTRIBUTE_DISPLAY_NAMES` in `src/utils/display.py`:
```python
"nuclear": "Nuclear Family",
"joint": "Joint Family",
"single_parent": "Single Parent",
```

## Files to Read Before Starting

1. `app/pages/1_population.py` — full file, understand current structure
2. `src/utils/display.py` — `display_name()`, `ATTRIBUTE_DISPLAY_NAMES`
3. `src/utils/dashboard_data.py` — `tier1_dataframe_with_results()` to see available columns
4. `src/constants.py` — `DASHBOARD_BRAND_COLORS`, `DASHBOARD_CHART_HEIGHT`
5. `src/taxonomy/schema.py` — DemographicAttributes class (lines 40-122) to see available fields

## Constraints

- Python 3.11+
- Do NOT add `st.set_page_config()` — it's only in `app/streamlit_app.py`
- Use `display_name()` for ALL user-facing field labels
- Use `use_container_width=True` for all plotly charts
- Charts height: use `DASHBOARD_CHART_HEIGHT` from constants (500px)
- No new pip dependencies
- Add `child_age_group_label()` to `src/utils/dashboard_data.py`, not inline in the page

## Column Availability

The dataframe (`df`) already contains these columns from `to_flat_dict()`:
- `city_name` (str) — e.g., "Mumbai", "Jaipur", "Mangalore"
- `city_tier` (str) — "Tier1", "Tier2", "Tier3"
- `num_children` (int) — 1-5
- `youngest_child_age` (int or None) — 2-14
- `oldest_child_age` (int or None) — 2-14
- `family_structure` (str) — "nuclear", "joint", "single_parent"
- `child_ages` (list[int]) — per-child ages
- `region` (str) — "North", "South", "East", "West", "NE"

## Acceptance Criteria

- [ ] City distribution chart shows top 15 cities with "Other cities" bucket
- [ ] City bars are colored by tier
- [ ] Number of children bar chart renders correctly
- [ ] Youngest child age histogram renders
- [ ] Age group metric tiles show count + percentage
- [ ] Product relevance caption references LittleJoys products
- [ ] Family structure pie chart renders
- [ ] `child_age_group_label()` is in `src/utils/dashboard_data.py` (reusable)
- [ ] No `st.set_page_config()` in page files
