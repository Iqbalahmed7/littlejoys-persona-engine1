# Sprints 19–21: Calibration → Pitch Features → Demo Hardening

**Written by:** Tech Lead (Claude Opus) — 2026-03-30
**Status:** Planning complete, ready for execution

---

## Current State (post Sprint 18)

The simulation engine is structurally complete but numerically too optimistic:

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Trial rate (month 3) | 48% | 15–30% | −18pp minimum |
| Repeat rate | 94% | 40–60% | −34pp minimum |
| Month-12 active | 26% | 10–20% | −6pp |
| Purchases/adopter | 4.28 | 3.0–6.0 | ✅ PASS |
| Revenue/adopter (₹) | 2,563 | 2,000–4,000 | ✅ PASS |
| Behaviour clusters | 4 | ≥4 | ✅ PASS |
| Churn peak month | 5 | 3–5 | ✅ PASS |

The dashboard has 4 pages (Home, Personas, Research, Results + Interviews) and is functional end-to-end in mock mode. Missing for pitch: PDF export, scenario comparison, calibrated numbers, UI polish.

---

## Sprint 19: Calibration
**Goal:** All 7 calibration metrics pass. Simulation produces face-valid consumer behaviour.

### Root Cause Analysis

**Trial rate 48% (target 15–30%):** `brand_salience` initialises at `awareness_level` (0.6 for nutrimix_2_6). The awareness threshold is ~0.25. Almost every persona crosses it by day 2. Fix: dampen initial brand_salience and/or increase awareness threshold.

**Repeat rate 94% (target 40–60%):** Three compounding problems:
1. `usage_consistent` fires at 80% daily probability → habit_strength climbs relentlessly
2. `fatigue` grows at only 0.0043/day → takes 140 days to reach 0.6 churn threshold
3. `child_acceptance` starts high (0.7 * taste_appeal) and `child_boredom` is rare (1% daily, needs fatigue > 0.3)

**Month-12 active 26% (target 10–20%):** Downstream consequence of the above. If repeat is fixed, this will partially self-correct.

### Parameter Changes (Codex)

#### constants.py changes:
```
EVENT_FATIGUE_GROWTH_PER_DAY:        0.0043 → 0.008    (doubles fatigue accumulation)
EVENT_IMPACT_HABIT_STRENGTH_USAGE_DAILY: 0.001 → 0.0005 (halves daily habit micro-boost)
EVENT_PROB_CHILD_BOREDOM_BASE:       0.01 → 0.025      (boredom 2.5x more likely)
EVENT_FATIGUE_THRESHOLD_BOREDOM:     0.3 → 0.2         (boredom triggers earlier)
EVENT_PROB_USAGE_DROP_BASE:          0.02 → 0.04       (usage drop 2x more likely)
EVENT_BRAND_SALIENCE_DECAY_PER_DAY:  0.02 → 0.025      (faster awareness decay)
```

#### state_model.py changes:
```python
# initialize_state: dampen initial brand_salience
brand_salience=_clip(scenario.marketing.awareness_level * 0.45),
# (was: awareness_level unscaled — 0.6 → 0.27 for nutrimix_2_6)

# initialize_state: lower initial child_acceptance
child_acceptance=_clip(
    scenario.product.taste_appeal * 0.65 * (1.0 - (0.3 * float(child_veto)))
),
# (was: taste_appeal * 1.0 — now 0.65 multiplier)
```

#### event_engine.py changes:
```python
# evaluate_decision: tighten repeat conditions
can_reorder = (
    state.reorder_urgency > 0.4
    and state.habit_strength > habit_threshold
    and state.child_acceptance > 0.35      # was 0.3
    and state.perceived_value > state.price_salience
    and state.fatigue < 0.55               # was 0.6
    and state.discretionary_budget > (price_ratio * 0.25)
)
```

### Iterative Tuning Protocol
Codex applies the changes above, runs `scripts/calibrate_event_params.py`, reads the output, and iterates. The brief includes exact target ranges and a 3-iteration budget. If all 7 checks don't pass in 3 iterations, Codex documents which metrics are still off and what was tried.

### Engineer Assignments

| Engineer | Task | Files |
|----------|------|-------|
| **Codex** | Parameter tuning: apply changes above, run calibration script, iterate up to 3 rounds | `src/constants.py`, `src/simulation/state_model.py`, `src/simulation/event_engine.py` |
| **Antigravity** | Add calibration metric assertions as proper tests; update any tests broken by parameter changes | `tests/unit/test_state_model.py`, `tests/unit/test_event_engine.py`, `tests/unit/test_event_grammar.py` |

**Goose, Cursor, OpenCode:** Idle this sprint (or start Sprint 20 prep).

### Execution Order
```
Codex (parameter tuning, 3 iterations) → Antigravity (update tests)
```

---

## Sprint 20: Pitch Features
**Goal:** PDF export, scenario comparison, UI polish — the demo feels production-ready.

### Feature 1: PDF Export (Cursor)
Add a "Download Report (PDF)" button next to the existing JSON button on `3_results.py`. The PDF should contain:

1. **Cover page:** Scenario name, date, population size, key headline metric
2. **Executive summary:** Headline + trajectory + drivers/recommendations/risks
3. **Funnel waterfall:** Rasterised Plotly chart (use `fig.to_image(format="png")`)
4. **Segment heatmap:** Rasterised
5. **Barrier summary table:** Stage, barrier, count
6. **Temporal trajectory chart:** Rasterised (if available)
7. **Counterfactual table:** Intervention, baseline rate, CF rate, lift%, revenue impact
8. **Interview themes table:** Theme, count, percentage, top quote

**Library:** `fpdf2` (pure Python, no system deps, pip install). Alternative: `reportlab`.

**Implementation approach:**
- New module `src/analysis/pdf_export.py` with `generate_pdf(report, scenario) -> bytes`
- Each section is a function that writes to the PDF object
- Charts rendered via `plotly.io.to_image()` (requires `kaleido` for static image export)
- Button in `3_results.py`: `st.download_button("Download Report (PDF)", data=pdf_bytes, ...)`

### Feature 2: Scenario Comparison (Codex + OpenCode)
Allow running 2 scenarios and comparing them side-by-side.

**Backend (Codex):** New module `src/analysis/scenario_comparison.py`:
```python
class ScenarioComparisonResult(BaseModel):
    scenario_a_id: str
    scenario_b_id: str
    scenario_a_name: str
    scenario_b_name: str
    adoption_rate_a: float
    adoption_rate_b: float
    adoption_delta: float
    active_rate_a: float | None
    active_rate_b: float | None
    active_delta: float | None
    revenue_a: float | None
    revenue_b: float | None
    barrier_comparison: list[dict]  # stage, barrier, count_a, count_b, delta
    driver_comparison: list[dict]   # variable, importance_a, importance_b

def compare_scenarios(
    population: Population,
    scenario_a: ScenarioConfig,
    scenario_b: ScenarioConfig,
    seed: int = 42,
) -> ScenarioComparisonResult:
    ...
```

**Frontend (OpenCode):** New section at the bottom of `3_results.py` or a new page `5_comparison.py`:
- Two dropdown selectors for scenario A and scenario B
- "Compare" button
- Delta table: metric, scenario A, scenario B, difference
- Overlaid retention curves (two lines, different colours)

### Feature 3: UI Polish (OpenCode)
- Replace raw field names with human-readable labels throughout results page
- Add loading spinner with progress text during consolidation
- Mock executive summary should display its content (currently it does, but verify)
- Ensure all chart titles use sentence case, not snake_case
- Add tooltips to metrics that use jargon (e.g., "Price Salience" → hover shows explanation)

### Feature 4: Persona CSV Export (Goose)
- Add "Export Personas (CSV)" button to `1_personas.py`
- Include: persona_id, city_tier, income_bracket, education_level, family_structure, youngest_child_age, top 10 psychographic scores, narrative_summary (first 200 chars)
- Respect active filters (export only the currently filtered set)

### Engineer Assignments

| Engineer | Task | Files |
|----------|------|-------|
| **Cursor** | PDF export: new module + button wiring + chart rasterisation | `src/analysis/pdf_export.py` (new), `app/pages/3_results.py`, `pyproject.toml` (add fpdf2, kaleido) |
| **Codex** | Scenario comparison backend: comparison model + runner | `src/analysis/scenario_comparison.py` (new) |
| **OpenCode** | Scenario comparison UI + UI polish (labels, tooltips, loading) | `app/pages/3_results.py` or `app/pages/5_comparison.py` (new), `app/pages/1_personas.py` |
| **Goose** | Persona CSV export with filter support | `app/pages/1_personas.py` |
| **Antigravity** | Tests: PDF export (mock), scenario comparison, CSV export | `tests/unit/test_pdf_export.py` (new), `tests/unit/test_scenario_comparison.py` (new) |

### Execution Order
```
Codex (comparison backend) ──────────────────────→ OpenCode (comparison UI + polish)
Cursor (PDF export) ─────────────────────────────→ │
Goose (persona CSV) ─────────────────────────────→ │
                                                    ↓
                                              Antigravity (all tests)
```

Codex, Cursor, Goose can run in parallel. OpenCode waits for Codex (needs comparison backend). Antigravity waits for all.

---

## Sprint 21: Demo Hardening
**Goal:** Zero crashes during live demo. Graceful error states. Performance within acceptable bounds.

### Task 1: Error Boundaries (Cursor)
- Wrap every major section of `3_results.py` in try/except with user-friendly st.error messages
- If event simulation fails, results page still shows static funnel results
- If PDF generation fails, show error toast instead of crashing
- If LLM call times out, fall back to mock summary with a warning banner

### Task 2: Demo Script + Guided Mode (OpenCode)
- Add a "Demo Mode" toggle to Home page
- In demo mode: pre-selects nutrimix_2_6, pre-generates population, auto-navigates through pages with explanation text
- Sidebar shows numbered steps: "Step 1: Population generated ✓ → Step 2: Research designed → Step 3: Running..."
- This is the pitch walkthrough sequence

### Task 3: Performance Guardrails (Codex)
- Profile the full pipeline on 200 personas: identify any step > 30 seconds
- Add `@st.cache_data` to any expensive computation not already cached
- Ensure PDF generation < 5 seconds
- Ensure scenario comparison < 30 seconds
- Add memory guard: if population > 500, warn user about expected runtime

### Task 4: All-Scenario Smoke Test (Goose)
- Run the full pipeline (population → research → consolidate → PDF) for all 4 scenarios
- Document any scenario-specific failures
- Verify counterfactual engine works for static-mode scenarios (magnesium_gummies, protein_mix)
- Verify persona CSV export works with all filter combinations

### Task 5: Final Test Suite (Antigravity)
- Integration test: full pipeline for all 4 scenarios (mock mode)
- Smoke test: PDF export for each scenario
- Edge case tests: empty population, single persona, zero-adoption scenario
- Performance assertion: full pipeline < 120 seconds for 200 personas
- Final ruff + mypy pass across entire codebase

### Engineer Assignments

| Engineer | Task | Files |
|----------|------|-------|
| **Cursor** | Error boundaries across results page + PDF fallback | `app/pages/3_results.py` |
| **OpenCode** | Demo mode toggle + guided walkthrough | `app/Home.py` or `streamlit_app.py`, `app/pages/*.py` |
| **Codex** | Performance profiling + caching + guardrails | Various `src/` files, `app/pages/3_results.py` |
| **Goose** | All-scenario smoke test + documentation | `scripts/smoke_test.py` (new) |
| **Antigravity** | Final test suite: 4-scenario integration, edge cases, perf | `tests/integration/test_full_demo.py` (new), various test files |

### Execution Order
```
All 5 engineers can work in parallel (no inter-dependencies)
            ↓
Tech Lead: final review + commit + deploy
```

---

## Dependency Graph (Sprints 19–21)

```
Sprint 18 ✅ (Event engine complete, 603 tests)
        │
        ▼
Sprint 19 (Calibration) ──── 2 engineers, focused
  ├── Codex: parameter tuning (3 iterations)
  └── Antigravity: update tests
        │
        ▼
Sprint 20 (Pitch Features) ──── all 5 engineers
  ├── Cursor: PDF export
  ├── Codex: scenario comparison backend
  ├── OpenCode: comparison UI + polish
  ├── Goose: persona CSV export
  └── Antigravity: tests for all
        │
        ▼
Sprint 21 (Demo Hardening) ──── all 5 engineers
  ├── Cursor: error boundaries
  ├── OpenCode: demo mode
  ├── Codex: performance
  ├── Goose: smoke tests
  └── Antigravity: final test suite
        │
        ▼
    PITCH READY
```

---

## Risk Register

| Risk | Mitigation |
|------|-----------|
| Calibration takes > 3 iterations | Codex has exact parameter change spec; worst case Tech Lead intervenes with binary search |
| `kaleido` doesn't install cleanly | Fall back to `orca` or screenshot-based export |
| Scenario comparison is slow (2 full pipelines) | Use mock mode for the comparison, cache aggressively |
| Demo crashes on live data | Sprint 21 error boundaries + smoke tests are the safety net |
| Goose delivers structurally broken code again | Brief is minimal scope (CSV button); validate immediately |

---

## Estimated Timeline

| Sprint | Effort | Calendar time (parallel engineers) |
|--------|--------|------------------------------------|
| Sprint 19 | 2 engineers, focused | ~2 hours |
| Sprint 20 | 5 engineers, parallel | ~4 hours |
| Sprint 21 | 5 engineers, parallel | ~3 hours |
| **Total** | | **~9 hours of wall-clock time** |
