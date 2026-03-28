# PRD-012: Hardening, QA & Demo Prep

**Sprint**: 5 (Final)
**Status**: Draft
**Goal**: Fix known bugs, add integration tests, generate precomputed demo data, polish the Streamlit app for live demo.

---

## 1. Bug Fixes (P0)

### 1.1 Broken `persona_card.py` component
`app/components/persona_card.py` references fields that do not exist on the actual Persona schema:
- `persona.demographics.name` → does not exist
- `persona.demographics.age` → field is `parent_age`
- `persona.demographics.location.city` → field is `city_name` (flat string, not nested)
- `persona.financials.*` → no `financials` sub-model; income is `demographics.household_income_lpa`
- `persona.psychology.*` → no `psychology` sub-model; these are in `psychographics`

**Fix**: Rewrite `render_persona_card()` to use actual schema fields:
- Header: `persona.id` + `persona.demographics.city_name`
- Demographics: `city_tier`, `region`, `household_income_lpa`, `parent_age`, `num_children`
- Psychographics: `health_consciousness`, `brand_loyalty_tendency`, `social_proof_susceptibility`
- Decision result: `outcome`, `rejection_stage`, `rejection_reason` (these come from `decision_result` dict, not model attrs — use `.get()`)

### 1.2 Bare `assert` in calibration.py
`src/decision/calibration.py:425` uses `assert best_result is not None` — bandit S101.
**Fix**: Replace with `if best_result is None: raise RuntimeError("calibration failed to converge")`.

### 1.3 Component wrappers alignment
`app/components/funnel_chart.py` and `app/components/heatmap.py` are thin wrappers. Verify they call the correct `src/utils/viz` functions and pass through kwargs correctly. Fix any mismatches.

---

## 2. Integration Tests (P0)

### 2.1 End-to-end precompute pipeline
Test that `precompute_results()` produces a valid manifest with all expected keys for each scenario. Run with mock LLM and a small population (size=20).

### 2.2 Page logic smoke tests
For each Streamlit page, extract the core data-preparation logic into testable functions (where not already done) and add tests:
- `1_population.py`: `_tier1_dataframe()` produces expected columns
- `3_results.py`: `_coerce_static()` handles dict, model, and None inputs
- `4_counterfactual.py`: counterfactual loading from precomputed JSON
- `5_interviews.py`: `_coerce_turns()` handles mixed valid/invalid inputs
- `6_report.py`: precomputed report markdown loading

### 2.3 Cross-scenario regression
Run all 4 scenarios through static simulation and verify adoption rates are in [0, 1] and population sizes match.

---

## 3. Demo Preparation (P0)

### 3.1 Generate precomputed artifacts
Run `scripts/precompute_results.py` with `--mock-llm` to produce:
- `data/results/precomputed/precompute_manifest.json`
- Per-scenario simulation, decision_rows, counterfactual JSONs
- Per-scenario report markdown files
- Executive summary

### 3.2 Streamlit home page polish
- Replace static sidebar markdown with dynamic page list
- Add version/seed info display
- Ensure population auto-loads from `data/population/` on startup
- Add a "Generate Population" button if no data exists

### 3.3 Verify all 6 pages render
Manual verification checklist (document in test):
- [ ] Home page loads, population metrics display
- [ ] Population Explorer shows demographics + psychographics
- [ ] Scenario Configurator allows lever adjustments
- [ ] Results Dashboard shows KPIs, funnel, heatmap, barriers, importance
- [ ] Counterfactual page shows predefined + custom what-if
- [ ] Interviews page allows chat with personas
- [ ] Report page shows precomputed or generates new

---

## 4. Polish (P1)

### 4.1 Consistent error states
All pages should show a clear message when prerequisites are missing (no population, no simulation results) rather than crashing.

### 4.2 Sidebar consistency
Ensure all pages use consistent sidebar control patterns (scenario selector, mock LLM toggle where applicable).

---

## Engineer Assignments

| Task | Engineer | Priority |
|---|---|---|
| 2.1, 2.2, 2.3 Integration tests | Codex | P0 |
| 1.1 persona_card fix, 1.3 component wrappers, 4.1 error states | Cursor | P0 |
| 3.1 precompute data, 3.2 home page polish, 3.3 render verification | Antigravity | P0 |
| 1.2 bare assert fix, 4.2 sidebar consistency audit | OpenCode | P1 |

---

## Acceptance Criteria
- All tests pass (target: 175+)
- `ruff check` clean
- Precomputed demo data exists in `data/results/precomputed/`
- All 6 Streamlit pages render without errors when population is loaded
- No runtime `AttributeError` from schema mismatches in components
