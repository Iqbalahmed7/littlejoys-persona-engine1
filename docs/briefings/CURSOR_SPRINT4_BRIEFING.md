# Cursor — Sprint 4 Briefing

> **Sprint**: 4 (Days 7-8)
> **Branch**: `feat/PRD-011-dashboard` from `staging`
> **PRD**: PRD-011 (Streamlit Dashboard)

---

## Your Assignments

You own the core dashboard infrastructure and the data-heavy pages.

### Task 1: App Scaffolding + Navigation (P0)

**File**: `app/streamlit_app.py` — replace stub

1. Multi-page app using Streamlit `pages/` convention
2. Sidebar with branding and navigation links
3. Session state init: load population + results from `data/` on first run
4. `st.session_state` keys: `population`, `scenario_results`, `selected_scenario`
5. Graceful fallback if data files don't exist — show button to generate
6. Import and cache population with `@st.cache_resource`

### Task 2: Population Explorer (P0)

**File**: `app/pages/1_population.py`

1. Overview stats row: total personas, Tier 1/2 counts, attribute count (use `st.metric`)
2. Demographic distributions: Plotly histograms for parent_age, household_income_lpa, city_tier, education_level, family_structure
3. Attribute scatter: two dropdowns for X/Y axis (any continuous attribute), color = adoption outcome
4. Persona search: text input by ID, show full attribute card
5. Tier 2 narratives: `st.expander` cards for each Tier 2 persona
6. `@st.cache_data` for DataFrame conversions

### Task 3: Results Dashboard (P0)

**File**: `app/pages/3_results.py`

1. Scenario selector dropdown at top
2. KPI row: adoption rate, adopters, rejectors, avg purchase score as `st.metric`
3. Funnel waterfall: call `compute_funnel_waterfall()`, render with `create_funnel_chart()`
4. Segment heatmap: call `analyze_segments()` with city_tier + income_bracket, render heatmap
5. Barrier distribution: pie or horizontal bar chart from `analyze_barriers()`
6. Variable importance: horizontal bar chart of top 10 SHAP values
7. Causal statements: `st.expander` cards for each statement
8. All Plotly charts, consistent brand colors

### Task 4: Plotly Chart Helpers (P0)

**File**: `src/utils/viz.py` — replace stubs

Implement all 6 chart builders:
- `create_funnel_chart(waterfall)` — waterfall/funnel from WaterfallStage list
- `create_segment_heatmap(segments, group_by)` — heatmap from SegmentAnalysis list
- `create_barrier_chart(barriers)` — pie/bar from BarrierDistribution list
- `create_temporal_chart(result)` — time-series from TemporalSimulationResult
- `create_importance_bar(importances)` — horizontal bar from VariableImportance list
- `create_counterfactual_comparison(results)` — grouped bar for baseline vs counterfactual

All return `plotly.graph_objects.Figure`. Use brand colors from `DASHBOARD_BRAND_COLORS` in constants.

### Task 5: What-If Live Mode (P1)

**File**: `app/pages/3_results.py` — add section

Add an expandable "What-If" panel below the results:
1. Sliders for key scenario parameters (price, awareness_budget, taste_appeal)
2. "Run What-If" button that re-runs static simulation with modified params
3. Show delta metrics (old vs new adoption rate)
4. `st.spinner` during simulation

### Tests

```python
# tests/unit/test_viz.py
test_funnel_chart_returns_figure()
test_segment_heatmap_returns_figure()
test_barrier_chart_returns_figure()
test_temporal_chart_returns_figure()
test_importance_bar_returns_figure()
test_counterfactual_comparison_returns_figure()
test_charts_handle_empty_data()
```

---

## Standards

- All charts: Plotly `go.Figure`, consistent colors from `DASHBOARD_BRAND_COLORS`
- `@st.cache_data` / `@st.cache_resource` for expensive operations
- `st.spinner` on all simulation calls
- No bare `print` — use `structlog` if backend logging is needed
- No magic numbers in chart sizing — use `DASHBOARD_CHART_HEIGHT` from constants
- Run before submitting:
  ```
  uv run ruff check app/ src/utils/viz.py
  uv run pytest tests/unit/test_viz.py -v
  streamlit run app/streamlit_app.py  # manual smoke test
  ```

---

## Sprint 3 Feedback

Composite was **9.0** — great improvement. Proactively covered OpenCode's test gaps. For Sprint 4: keep the same quality bar. The dashboard is the client-facing layer — visual consistency and polish matter here.
