# Cursor — Sprint 8 Track A: Demographic Filters + Smart Scatter Insights

**Branch:** `sprint-8-track-a-scatter-filters`
**Base:** `main`

## Context

The Population Explorer page (`app/pages/1_population.py`) has a psychographics scatter plot that shows all 200 personas at once with no way to slice by demographics. The scatter insights are also generic ("Parents with low X and high Y would buy at 48%") without product context.

This track adds a reusable demographic filter component and product-aware scatter insights.

## Deliverables

### 1. Shared Demographic Filter Component

**File:** `app/components/demographic_filters.py` (NEW)

Create a reusable filter function that other pages can import:

```python
def render_demographic_filters(
    df: pd.DataFrame,
    key_prefix: str = "demo_filter",
) -> pd.DataFrame:
    """
    Render demographic filter widgets in a compact row and return the filtered dataframe.

    Filters (all multi-select, default = all selected):
    - City Tier: ["Tier1", "Tier2", "Tier3"]
    - SEC Class: ["A1", "A2", "B1", "B2", "C1", "C2"]
    - Region: ["North", "South", "East", "West", "NE"]
    - Income Bracket: ["low_income", "middle_income", "high_income"]
    - Number of Children: [1, 2, 3, 4, 5]
    - Child Age Group: ["Toddler (2-5)", "School-age (6-10)", "Pre-teen (11-14)"]

    Layout: 3 columns × 2 rows of filters.
    Show a caption below: "Showing X of Y personas matching filters"
    """
```

**Child Age Group filter logic:**
- The dataframe has `youngest_child_age` column (int, 2-14)
- "Toddler (2-5)": youngest_child_age between 2-5
- "School-age (6-10)": youngest_child_age between 6-10
- "Pre-teen (11-14)": youngest_child_age between 11-14
- A persona can match if ANY selected group covers their youngest child's age

**Important:** Use `key_prefix` parameter to avoid Streamlit duplicate widget key errors when the same filter component is used on multiple pages.

Display names: use `display_name()` from `src.utils.display` for filter labels. For income bracket values, map: `"low_income"` → `"Under ₹8L"`, `"middle_income"` → `"₹8L–15L"`, `"high_income"` → `"Above ₹15L"`.

### 2. Integrate Filters into Scatter Plot

**File:** `app/pages/1_population.py` (MODIFY)

- Import `render_demographic_filters` from the new component
- Add the filter bar **above** the scatter plot section (after the Demographics section, before "Psychographics — scatter")
- Apply filters to the dataframe before plotting
- The scatter title, insights, and quadrant analysis should all use the **filtered** dataframe
- Keep the full `df` for the demographics section (those have their own charts)

### 3. Product-Aware Scatter Insights

**File:** `app/pages/1_population.py` (MODIFY the insight generation, lines 179-227)

Replace the current generic insight with product-contextual language. The current scenario being viewed determines the product name.

Add to `src/utils/display.py`:

```python
SCENARIO_PRODUCT_NAMES: dict[str, str] = {
    "nutrimix_2_6": "NutriMix (ages 2-6)",
    "nutrimix_7_14": "NutriMix (ages 7-14)",
    "magnesium_gummies": "Magnesium Gummies",
    "protein_mix": "Protein Mix",
}

QUADRANT_INTERPRETATIONS: dict[tuple[str, str], str] = {
    # (high_attr, low_attr) → "so what" interpretation
    # These are keyed by the attribute that is HIGH in the best-performing quadrant
}
```

**New insight format:**

Instead of:
> "Parents with low Fitness Engagement and high Dietary Awareness would buy at 48%, compared with 42% across everyone in this simulation."

Generate:
> "Among the **X parents** matching your filters, those with high Dietary Awareness and low Fitness Engagement are **14% more likely** to purchase NutriMix (ages 2-6) — 48% vs 42% baseline. This suggests convenience-oriented health consciousness drives purchase intent in this segment."

Logic:
1. Get the current scenario product name from `SCENARIO_PRODUCT_NAMES` (use first scenario in `SCENARIO_IDS` if multiple)
2. Compute the lift as percentage points above baseline: `(quad_rate - overall_rate)`
3. Compute the relative lift: `(quad_rate - overall_rate) / overall_rate * 100`
4. Frame insights around the product name
5. Show filtered population size in the insight

**Quadrant insight boxes:** Replace the single `st.info()` with individual quadrant cards:

```python
for quad_name, quad_df in quadrants.items():
    quad_rate = ...
    if abs(quad_rate - overall_rate) / overall_rate > 0.15:  # >15% relative difference
        delta = quad_rate - overall_rate
        icon = "🟢" if delta > 0 else "🔴"
        st.metric(
            label=f"{quad_name} ({len(quad_df)} parents)",
            value=f"{quad_rate:.0%}",
            delta=f"{delta:+.0%} vs baseline",
        )
```

## Files to Read Before Starting

1. `app/pages/1_population.py` — current scatter implementation (full file)
2. `src/utils/display.py` — display helpers, ATTRIBUTE_CATEGORIES
3. `src/utils/dashboard_data.py` — `tier1_dataframe_with_results()`, `income_bracket_label()`
4. `src/constants.py` — SCENARIO_IDS, DASHBOARD_BRAND_COLORS, income bracket thresholds
5. `app/components/persona_card.py` — existing component pattern

## Constraints

- Python 3.11+, Pydantic v2
- Do NOT add `st.set_page_config()` — it's in the main `app/streamlit_app.py` only
- Use `display_name()` for ALL user-facing field labels
- Use `use_container_width=True` for all `st.plotly_chart()` calls (will migrate to `width='stretch'` in a future sprint)
- Use `key=` parameter on ALL Streamlit widgets to avoid duplicate key errors
- All filter defaults should show ALL data (no filter = full population)
- Import only from `src.*` and `app.components.*` — no new dependencies

## Acceptance Criteria

- [ ] `render_demographic_filters()` is importable and works standalone
- [ ] Scatter plot updates live when filters change
- [ ] Insights reference the product name from the active scenario
- [ ] Insights show filtered population count
- [ ] Quadrant metrics show lift vs baseline with delta indicators
- [ ] No `st.set_page_config()` in page files
- [ ] All widgets have unique `key=` parameters
