# PRD-011: Streamlit Dashboard — Presentation Layer

> **Sprint**: 4 (Days 7-8)
> **Priority**: P0 (Critical Path)
> **Assignees**: Cursor (scaffolding, population explorer, results dashboard, what-if mode), Codex (interview chat, ReportAgent page), Antigravity (scenario configurator, counterfactual page, visual polish)
> **Depends On**: All Sprint 1-3 modules
> **Status**: Ready for Development

---

## Objective

Build an interactive Streamlit dashboard that tells a compelling story for the client demo. Six pages covering the full simulation pipeline, from population exploration through scenario results to interactive persona interviews. Pre-computed results ensure instant loading; live "what-if" mode shows real-time scenario changes.

---

## Architecture Reference

See ARCHITECTURE.md §10 (Presentation Layer) and file structure at lines 1498-1510.

---

## File Structure

```
app/
├── streamlit_app.py              # Main entry point + nav
├── pages/
│   ├── 1_population.py           # Population explorer
│   ├── 2_scenario.py             # Scenario configurator
│   ├── 3_results.py              # Results dashboard
│   ├── 4_counterfactual.py       # Counterfactual comparison
│   ├── 5_interviews.py           # Persona interview chat
│   └── 6_report.py               # ReportAgent interactive
└── components/
    ├── persona_card.py            # Persona detail card component
    ├── funnel_chart.py            # Plotly funnel waterfall
    └── heatmap.py                 # Segment adoption heatmap

src/utils/viz.py                   # Plotly chart builder helpers
```

---

## Deliverables

### D1: App Scaffolding + Navigation (Cursor)

**File**: `app/streamlit_app.py` — replace stub

Requirements:
1. Multi-page app using Streamlit's native `pages/` directory convention
2. Sidebar navigation with page links and branding
3. Session state initialization: load pre-computed population and results from `data/` on first run
4. Global state management via `st.session_state`:
   - `population`: loaded Population object
   - `scenario_results`: dict of scenario_id -> simulation results
   - `selected_scenario`: currently selected scenario ID
5. Error handling: graceful fallback if data files don't exist (offer to generate)
6. LittleJoys branding in sidebar header

### D2: Population Explorer (Cursor)

**File**: `app/pages/1_population.py`

Requirements:
1. **Overview stats**: Total personas, Tier 1 count, Tier 2 count, attribute count
2. **Demographic distributions**: Plotly histograms for age, income, city tier, education, family structure
3. **Attribute scatter plot**: Select any two continuous attributes, plot scatter with adoption outcome as color
4. **Persona search**: Text input to find persona by ID, show full attribute card
5. **Tier 2 narratives**: Expandable cards for Tier 2 personas showing their narrative text
6. Use `@st.cache_data` for expensive computations (DataFrame conversions)

### D3: Scenario Configurator (Antigravity)

**File**: `app/pages/2_scenario.py`

Requirements:
1. **Scenario selector**: Dropdown with all 4 scenarios, shows description
2. **Product parameters**: Sliders for price_inr, taste_appeal, effort_to_acquire, clean_label_score, health_relevance
3. **Marketing parameters**: Sliders for awareness_budget, awareness_level, trust_signal, social_proof, expert_endorsement, discount_available
4. **Channel mix**: Multi-slider for channel weights (must sum to ~1.0, show validation)
5. **Toggle switches**: school_partnership, pediatrician_endorsement, influencer_campaign, lj_pass_available
6. **Run simulation button**: Runs static simulation with modified parameters, stores results in session state
7. **Side-by-side**: Show original vs modified scenario parameters in two columns

### D4: Results Dashboard (Cursor)

**File**: `app/pages/3_results.py`

Requirements:
1. **Scenario selector**: Pick which scenario's results to view
2. **KPI row**: Adoption rate, total adopters, total rejectors, avg purchase score — as `st.metric` cards
3. **Funnel waterfall chart**: Using `compute_funnel_waterfall()` data, Plotly waterfall/funnel chart
4. **Segment heatmap**: Adoption rate by segment (city_tier x income_bracket), Plotly heatmap
5. **Barrier distribution**: Pie/bar chart of rejection stages and reasons
6. **Variable importance**: Horizontal bar chart of top 10 SHAP values
7. **Causal statements**: Display generated causal statements in expander cards
8. All charts must be Plotly for interactivity (hover, zoom)

### D5: Counterfactual Comparison (Antigravity)

**File**: `app/pages/4_counterfactual.py`

Requirements:
1. **Scenario selector**: Pick baseline scenario
2. **Predefined counterfactuals**: Show available counterfactuals for selected scenario, run on click
3. **Custom counterfactual**: Sliders to modify any scenario parameter, run comparison
4. **Results comparison**: Side-by-side metrics (baseline vs counterfactual adoption rate)
5. **Lift visualization**: Bar chart showing absolute lift per counterfactual
6. **Segment impact table**: Which segments benefit most from the counterfactual
7. Loading spinners during simulation runs

### D6: Persona Interview Chat (Codex)

**File**: `app/pages/5_interviews.py`

Requirements:
1. **Persona selector**: Dropdown of Tier 2 personas with name/ID and outcome (adopt/reject)
2. **Scenario selector**: Which scenario context for the interview
3. **Chat interface**: `st.chat_message` blocks for user/persona turns
4. **Input box**: `st.chat_input` for user questions
5. **Suggested questions**: Quick-fire buttons ("Why did you decide this?", "What about the price?", "Do you trust the brand?", "Tell me about your morning routine")
6. **Persona card sidebar**: Show persona demographics, psychographic highlights, decision outcome while chatting
7. **Quality indicator**: Green/yellow/red dot based on `check_interview_quality()` result
8. Session state preserves conversation history across rerenders
9. Must work in mock LLM mode for demos without API keys

### D7: ReportAgent Interactive (Codex)

**File**: `app/pages/6_report.py`

Requirements:
1. **Scenario selector**: Pick scenario to generate report for
2. **Generate button**: Triggers `ReportAgent.generate_report()` with spinner
3. **Report display**: Render `raw_markdown` output with `st.markdown`
4. **Section navigation**: Tabs or expanders for each report section
5. **Supporting data**: Show raw data tables behind each section in expandable panels
6. **Tool call log**: Show which tools the ReportAgent called and in what order
7. **Download button**: `st.download_button` to export report as markdown file
8. Must work in mock LLM mode

### D8: Plotly Chart Helpers (Cursor)

**File**: `src/utils/viz.py` — replace stubs

```python
def create_funnel_chart(waterfall: list[WaterfallStage]) -> go.Figure:
def create_segment_heatmap(segments: list[SegmentAnalysis], group_by: str) -> go.Figure:
def create_barrier_chart(barriers: list[BarrierDistribution]) -> go.Figure:
def create_temporal_chart(result: TemporalSimulationResult) -> go.Figure:
def create_importance_bar(importances: list[VariableImportance]) -> go.Figure:
def create_counterfactual_comparison(results: list[CounterfactualResult]) -> go.Figure:
```

Requirements:
1. All charts return `plotly.graph_objects.Figure`
2. Consistent color scheme: use LittleJoys brand colors (define in constants)
3. Hover labels with full detail
4. Responsive sizing (`fig.update_layout(autosize=True)`)
5. No chart should take > 1 second to render for 300 personas

### D9: Reusable Components (Antigravity)

**Files**: `app/components/persona_card.py`, `app/components/funnel_chart.py`, `app/components/heatmap.py`

Thin wrappers that call `src/utils/viz.py` helpers and render via `st.plotly_chart()`. Persona card renders demographics + psychographics in a formatted card layout.

### D10: Visual Polish + Loading States (Antigravity)

Requirements:
1. `st.spinner` on all simulation/LLM calls
2. `st.toast` for success/error notifications
3. Consistent page headers and descriptions
4. Empty states: helpful messages when no data is loaded
5. Pre-load all 4 scenario results on app startup for instant demo

---

## Constants

Add to `src/constants.py`:
```python
# Dashboard
DASHBOARD_PAGE_TITLE = "LittleJoys Persona Engine"
DASHBOARD_BRAND_COLORS = {
    "primary": "#FF6B6B",
    "secondary": "#4ECDC4",
    "accent": "#45B7D1",
    "adopt": "#2ECC71",
    "reject": "#E74C3C",
    "neutral": "#95A5A6",
}
DASHBOARD_DEFAULT_POPULATION_PATH = "data/population"
DASHBOARD_DEFAULT_RESULTS_PATH = "data/results"
DASHBOARD_CHART_HEIGHT = 500
DASHBOARD_HEATMAP_COLORSCALE = "RdYlGn"
```

---

## Pre-Computed Data Script

**File**: `scripts/precompute_results.py`

Run all 4 scenarios + counterfactuals and save results to `data/results/` for instant dashboard loading:
```python
def precompute_all() -> None:
    # Generate population if needed
    # Run static simulation for all 4 scenarios
    # Run predefined counterfactuals for all 4 scenarios
    # Save all results as JSON to data/results/
```

This is Sprint 5 prep but should be built now so the dashboard has data to show.

---

## Tests

Dashboard pages are hard to unit test. Focus on:

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

```python
# tests/unit/test_precompute.py
test_precompute_creates_result_files()
test_precompute_idempotent()
```

---

## Acceptance Criteria

- [ ] All 6 pages render without errors
- [ ] Full demo flow: Population -> Scenario -> Results -> Counterfactual -> Interview -> Report
- [ ] Charts are interactive (hover, zoom) via Plotly
- [ ] Interview chat works in mock mode
- [ ] Report generation works in mock mode
- [ ] What-if mode: changing a slider and clicking "Run" produces updated results
- [ ] Pre-computed results load instantly (no spinner on first view)
- [ ] No crashes on edge cases (empty population, missing data files)
- [ ] `streamlit run app/streamlit_app.py` launches cleanly
