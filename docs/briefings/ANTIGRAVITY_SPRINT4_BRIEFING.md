# Antigravity — Sprint 4 Briefing

> **Sprint**: 4 (Days 7-8)
> **Branch**: `feat/PRD-011-scenario-counterfactual-pages` from `staging`
> **PRD**: PRD-011 (Streamlit Dashboard)

---

## Your Assignments

You own the scenario input page, counterfactual page, reusable components, and visual polish.

### Task 1: Scenario Configurator Page (P0)

**File**: `app/pages/2_scenario.py`

1. **Scenario selector**: `st.selectbox` with all 4 scenarios, show name + description
2. **Product parameters panel**: `st.slider` for:
   - `price_inr` (100 - 1500, step 50)
   - `taste_appeal` (0.0 - 1.0, step 0.05)
   - `effort_to_acquire` (0.0 - 1.0, step 0.05)
   - `clean_label_score` (0.0 - 1.0, step 0.05)
   - `health_relevance` (0.0 - 1.0, step 0.05)
3. **Marketing parameters panel**: `st.slider` for:
   - `awareness_budget` (0.0 - 1.0)
   - `awareness_level` (0.0 - 1.0)
   - `trust_signal` (0.0 - 1.0)
   - `social_proof` (0.0 - 1.0)
   - `expert_endorsement` (0.0 - 1.0)
   - `discount_available` (0.0 - 0.5)
4. **Channel mix**: Multiple sliders for channels, show sum with validation (`st.error` if sum > 1.05 or < 0.95)
5. **Toggles**: `st.toggle` for school_partnership, pediatrician_endorsement, influencer_campaign, lj_pass_available
6. **Side-by-side comparison**: Two `st.column`s showing original vs modified parameters
7. **Run button**: `st.button("Run Simulation")` with `st.spinner`, stores results in `st.session_state.scenario_results[scenario_id]`
8. **Reset button**: Restore original scenario defaults

### Task 2: Counterfactual Comparison Page (P0)

**File**: `app/pages/4_counterfactual.py`

1. **Scenario selector**: Pick baseline scenario
2. **Predefined counterfactuals**: List available counterfactuals for selected scenario as `st.button` cards. Show name + description.
3. **Run counterfactual**: Click runs `run_predefined_counterfactual()` with `st.spinner`
4. **Results comparison**: Two `st.column`s — baseline metrics vs counterfactual metrics
5. **Lift visualization**: `st.plotly_chart` bar showing absolute lift for each counterfactual run so far
6. **Segment impact table**: `st.dataframe` showing which segments benefit most
7. **Custom counterfactual**: `st.expander("Custom What-If")` with sliders to modify any parameter + run button
8. Store counterfactual results in `st.session_state` for persistence across rerenders

### Task 3: Reusable Components (P1)

**Files**:
- `app/components/persona_card.py` — function `render_persona_card(persona, decision_result)` that displays demographics, psychographic highlights, and outcome in a formatted card using `st.container` + `st.columns`
- `app/components/funnel_chart.py` — thin wrapper: takes waterfall data, calls `create_funnel_chart()`, renders via `st.plotly_chart`
- `app/components/heatmap.py` — thin wrapper: takes segment data, calls `create_segment_heatmap()`, renders via `st.plotly_chart`

### Task 4: Visual Polish + Loading States (P1)

Apply across all pages:
1. `st.spinner` on all simulation/LLM calls (verify all pages have them)
2. `st.toast` for success notifications after simulation runs
3. Consistent page headers: `st.header` + `st.caption` description on every page
4. Empty states: `st.info("No data loaded. Click Generate to create a population.")` when data is missing
5. Pre-load all 4 scenario results on app startup if precomputed data exists in `data/results/`

---

## Standards

- Use `st.session_state` for mutable state
- `@st.cache_data` for expensive data operations
- `st.spinner` on every simulation call
- No bare `print` or `logging` — `structlog` if needed
- Channel mix validation must be user-visible (`st.error` / `st.warning`)
- All sliders must have sensible min/max/step values
- Run before submitting:
  ```
  uv run ruff check app/
  streamlit run app/streamlit_app.py  # manual smoke test all pages
  ```

---

## Sprint 3 Feedback

Composite was **8.2**. Code quality was solid but communication was overly verbose. For Sprint 4: keep completion reports clear and concise — list what you built, what tests passed, and any issues. Skip the jargon.

Also: add `structlog` to `waterfall.py` from Sprint 3 if you touch it again — it was the one gap flagged in review.
