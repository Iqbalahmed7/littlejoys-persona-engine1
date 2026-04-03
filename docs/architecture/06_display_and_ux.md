# Display Layer and UX

## Overview

The Streamlit application provides a 7-page interactive dashboard over the simulation engine. It loads a pre-generated population on startup and exposes all five simulation phases through a sidebar-navigated multi-page layout.

---

## Page Structure

| File | Page | Phase | Purpose |
|---|---|---|---|
| `app/streamlit_app.py` | Home | — | Engine initialisation, population load, session state setup |
| `app/pages/1_personas.py` | Personas | Generation | Browse and filter the 200 synthetic households |
| `app/pages/2_research.py` | Research | Probing | Run scenario research, view problem trees, execute probes |
| `app/pages/3_results.py` | Results | Analysis | Funnel charts, SHAP importance, barrier waterfall, cohort tables |
| `app/pages/2_diagnose.py` | Diagnose | Phase A | Problem decomposition, hypothesis generation |
| `app/pages/4_interviews.py` | Interviews | Probing | Deep-dive LLM conversations with individual personas |
| `app/pages/5_comparison.py` | Comparison | Analysis | Side-by-side scenario comparison charts |
| `app/pages/6_simulate.py` | Simulate | Phase C | Intervention quadrant runner, lift leaderboard |

---

## Session State Architecture

The Streamlit app uses `st.session_state` as the shared data store across pages (Streamlit does not support cross-page global state otherwise). All keys are set during initialisation in `streamlit_app.py`.

### Initialisation Keys

| Key | Type | Set By | Purpose |
|---|---|---|---|
| `population` | `Population` | Home on load | The 200-persona synthetic population |
| `scenario_results` | `dict[str, SimulationResult]` | Home on load | Pre-run static simulation results for all 4 scenarios |
| `selected_scenario_id` | `str` | User interaction | Currently active scenario for all analysis pages |
| `research_results` | `dict` | Research page | Research probe results by question ID |
| `interview_session` | `InterviewSession` | Interviews page | Active interview conversation state |
| `consolidation_cache` | `dict` | Results page | Cached ConsolidatedReport per scenario |
| `intervention_quadrant` | `InterventionQuadrant` | Simulate page | Current quadrant definition |
| `quadrant_run_result` | `QuadrantRunResult` | Simulate page | Results from the last quadrant run |
| `demo_mode` | `bool` | Config | When True: mock LLM, no API calls |

### Population Loading

```python
if "population" not in st.session_state:
    if pop_path.exists():
        st.session_state.population = Population.load(pop_path)
        for sid in SCENARIO_IDS:
            st.session_state.scenario_results[sid] = run_static_simulation(
                st.session_state.population, get_scenario(sid)
            )
```

If `data/population/` does not exist, the app enters demo mode with mock data.

---

## Demo Mode (`app/utils/demo_mode.py`)

When `demo_mode=True` or no population data exists:
- All LLM calls return fixture responses
- Population is replaced with a smaller seeded mock population
- API cost is zero

Demo mode is detected by checking for `ANTHROPIC_API_KEY` in the environment and the presence of `data/population/`. The Render deployment uses real data; local development without an API key falls back automatically.

---

## Label and Display Translation (`src/utils/display.py`)

Every raw field name, code, and enum value is translated before display. Direct field names never appear in the UI.

### Key Translation Functions

| Function | Input | Output |
|---|---|---|
| `display_name(field)` | `"budget_consciousness"` | `"Price Sensitivity"` |
| `describe_attribute_value(field, value)` | `"health_anxiety", 0.76` | `"very high health worry level"` |
| `outcome_label(code)` | `"adopt"` | `"Would try"` |
| `city_tier_label(tier)` | `"Tier1"` | `"Metro"` |
| `cohort_label(cohort_id)` | `"lapsed_user"` | `"Lapsed Users"` |
| `rejection_reason_label(reason)` | `"price_too_high"` | `"Price too high"` |
| `stage_label(stage)` | `"need_recognition"` | `"Need Recognition"` |
| `scope_label(scope)` | `"cohort_specific"` | `"Cohort-Specific"` |
| `temporality_label(t)` | `"non_temporal"` | `"Non-Temporal"` |
| `qualitative_level(value)` | `0.76` | `"High"` |
| `income_bracket_ui_label(code)` | `"low_income"` | `"Under ₹8L"` |
| `scenario_product_display_name(id)` | `"nutrimix_2_6"` | `"NutriMix (ages 2-6)"` |

### ATTRIBUTE_DISPLAY_NAMES Dictionary

A comprehensive mapping of all 145 field names to human-readable labels, grouped by domain:
- Demographics: city_tier → "City Classification", household_income_lpa → "Household Income (₹ Lakhs/year)"
- Health: health_anxiety → "Health Worry Level", immunity_concern → "Immunity Concern"
- Psychology: budget_consciousness → "Price Sensitivity", social_proof_bias → "Peer Influence"
- Values: best_for_my_child_intensity → "Best-for-My-Child Drive"

### SEC Descriptions
```python
SEC_DESCRIPTIONS = {
    "A1": "Urban Affluent — highest disposable income, premium brand affinity",
    "A2": "Upper Middle — professional households, quality-conscious spending",
    "B1": "Middle Class — stable salaried, value-for-money seekers",
    ...
}
```

### Channel Help Text
`CHANNEL_HELP` provides contextual descriptions for each marketing channel shown in the scenario editor (instagram, youtube, whatsapp, pediatrician, school, sports_clubs).

### Rejection Reason Display
```python
REJECTION_REASON_DISPLAY = {
    "age_irrelevant": "Product not relevant for child's age",
    "price_too_high": "Price too high",
    "low_need": "No perceived need",
    "insufficient_trust": "Insufficient trust in brand",
    ...
}
```

---

## Visualisation Utilities (`src/utils/viz.py`)

Plotly chart builders used across pages:
- Funnel chart: bar chart showing population at each funnel stage
- SHAP bar chart: horizontal bars for top-N variable importance
- Scatter chart: psychographic 2D scatter coloured by adoption outcome
- Waterfall: rejection reason breakdown by stage
- Monthly line chart: temporal active rate trajectory

Brand colour constants from `src/constants.py`:
```python
DASHBOARD_BRAND_COLORS = {
    "primary": "#FF6B6B",   # coral red
    "secondary": "#4ECDC4", # teal
    "accent": "#45B7D1",    # sky blue
    "adopt": "#2ECC71",     # green
    "reject": "#E74C3C",    # red
    "neutral": "#95A5A6",   # grey
}
```

---

## Key UX Design Principles

1. **No raw field names** — every attribute name goes through `display_name()` before rendering.
2. **Graphs show insights** — chart titles are written as insight statements, not axis labels.
3. **Human-readable persona IDs** — personas are identified by city + parent age (e.g., "Mumbai · Parent's Age 34"), not internal UUID strings.
4. **Qualitative levels** — float values (0–1) are always accompanied by Low / Medium / High labels via `qualitative_level()`.
5. **Contextual help** — every marketing channel has a tooltip explanation. Every intervention shows its expected mechanism.

---

## Files

| File | Role |
|---|---|
| `app/streamlit_app.py` | Home page, session state init, population load |
| `app/pages/1_personas.py` | Persona browser and explorer |
| `app/pages/2_research.py` | Research question runner and probe tree viewer |
| `app/pages/2_diagnose.py` | Phase A problem decomposition |
| `app/pages/3_results.py` | Funnel analysis, SHAP, barriers, cohorts |
| `app/pages/4_interviews.py` | LLM persona interview sessions |
| `app/pages/5_comparison.py` | Cross-scenario comparison dashboard |
| `app/pages/6_simulate.py` | Phase C intervention quadrant runner |
| `app/utils/demo_mode.py` | Mock data and API-free operation |
| `src/utils/display.py` | All label translation and display helpers |
| `src/utils/viz.py` | Plotly chart builders |
| `src/utils/dashboard_data.py` | Data preparation utilities for pages |
