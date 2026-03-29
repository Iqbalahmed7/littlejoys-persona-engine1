# Option C: Hybrid Research Engine — Sprint Plan

## Architecture Summary
Funnel runs fast on all 200 personas (quantitative). LLM interviews run on a smart sample of 15-20 personas flagged as interesting by the funnel (qualitative). Results page presents both as a unified research report.

## New Page Structure
| # | Page | Purpose |
|---|------|---------|
| 1 | **Home + Personas** | Compact dashboard: metrics, demographic charts (static + filtered), persona browser with spider charts |
| 2 | **Research Design** | Scenario config + business question + probing tree + run button |
| 3 | **Results** | Research report: quantitative overview + qualitative deep-dive + alternatives + what-if |
| 4 | **Interviews** | Optional deep-dive: manually interview any persona (keep existing) |

Pages removed/merged: Population (→ Home), Probing Tree (→ Research Design), Explorer (→ silent auto-run inside Research Design), Counterfactual (→ What-If section in Results), Report (→ Results page IS the report).

## Engineer Capabilities (Current)
| Engineer | Model | Strengths | Constraints |
|----------|-------|-----------|-------------|
| **Cursor** | Claude | Architecture, complex refactors, system design | None |
| **Codex** | GPT 5.3 Medium | Backend algorithms, data processing | Medium reasoning — needs well-specified PRDs |
| **OpenCode** | GPT 5.4 Nano (→ Pro on request) | UI/Streamlit, frontend | Nano is weak on complex logic |
| **Antigravity** | Gemini 3 Flash | Tests, validation, lighter tasks | Flash model — keep tasks scoped |

---

## Sprint 12: Foundation Layer
**Goal:** Build all new components that Sprint 13-14 pages will consume. No page restructuring yet.

### Cursor — Smart Sampling Algorithm + Language Shift
**Files:** `src/probing/smart_sample.py` (new), `src/utils/display.py` (edit)

1. **Smart Sampling Algorithm** (`src/probing/smart_sample.py`)
   - Input: list of personas + funnel decisions (outcome, scores)
   - Output: 15-20 personas selected for LLM interviews
   - Selection strategy:
     - 3-4 "fragile yes" — adopted but score within 10% of threshold
     - 3-4 "persuadable no" — rejected but score within 10% of threshold
     - 3-4 strong adopters from underrepresented segments (minority city_tier or SEC)
     - 3-4 strong rejecters with high need_score (why the disconnect?)
     - 2-3 random control (deterministic via seed)
   - Must be deterministic (same seed → same sample)
   - Return `SmartSample` dataclass with personas + selection_reason per persona

2. **Language Shift** — rename all user-facing labels:
   - "Adoption rate" → "Positive response rate"
   - "Adopt" / "Reject" → "Would try" / "Wouldn't try"
   - "Purchase intent" → "Openness to trial"
   - "Funnel" → "Decision pathway" (in UI labels only, code internals unchanged)
   - Update `src/utils/display.py` label maps + all `st.metric` / `st.markdown` in pages
   - Do NOT rename internal code variables/functions — only user-facing strings

### Codex — Business Question Bank + Run Orchestrator
**Files:** `src/probing/question_bank.py` (new), `src/simulation/research_runner.py` (new)

1. **Business Question Bank** (`src/probing/question_bank.py`)
   - 3-4 business questions per scenario (4 scenarios × 4 questions = 16 total)
   - Each question is a `BusinessQuestion` Pydantic model:
     ```python
     class BusinessQuestion(BaseModel):
         id: str
         scenario_id: str
         title: str  # e.g. "How can we improve repeat purchase for NutriMix?"
         description: str  # 2-3 sentence context
         probing_tree_id: str  # maps to existing predefined tree
         success_metric: str
     ```
   - Map to existing predefined probing trees where possible (4 exist already)
   - For questions without a tree, create lightweight trees (2-3 hypotheses each)
   - Function: `get_questions_for_scenario(scenario_id) -> list[BusinessQuestion]`
   - Function: `get_question(question_id) -> BusinessQuestion`

2. **Research Run Orchestrator** (`src/simulation/research_runner.py`)
   - Coordinates the full Option C hybrid run:
     ```python
     class ResearchRunner:
         def run(self, population, scenario, question, probing_config) -> ResearchResult:
             # Step 1: Static funnel on all 200 personas
             # Step 2: Smart sample selection (15-20)
             # Step 3: LLM interviews on sample (with probing tree questions)
             # Step 4: Auto-generate 50 parameter variants
             # Step 5: Run funnel-only on all variants
             # Return unified ResearchResult
     ```
   - `ResearchResult` model:
     ```python
     class ResearchResult(BaseModel):
         primary_funnel: StaticSimulationResult
         smart_sample: SmartSample
         interview_responses: list[InterviewResponse]
         alternative_runs: list[AlternativeRunSummary]
         metadata: ResearchMetadata  # timestamp, duration, costs
     ```
   - Progress callback for UI progress bar
   - Must handle mock mode (no LLM) gracefully

### OpenCode — Persona Spider Chart Component
**Files:** `app/components/persona_spider.py` (new)

1. **Spider/Radar Chart Component**
   - Input: single Persona object
   - Output: Plotly radar chart showing top 5 anchor traits
   - Trait selection logic:
     - From persona's flat dict, pick the 5 attributes with most extreme values (furthest from 0.5 in either direction)
     - Exclude demographic fields (age, income, city) — only psychographic/behavioral
     - Use `display_name()` for axis labels
   - Styling: match existing DASHBOARD_BRAND_COLORS
   - Function: `render_persona_spider(persona: Persona, key: str) -> None`
   - Should be compact (fit in a column alongside persona card text)

### Antigravity — Tests for Sprint 12 Components
**Files:** `tests/unit/test_smart_sample.py`, `tests/unit/test_question_bank.py`, `tests/unit/test_research_runner.py`

1. **Smart Sampling Tests**
   - Test determinism (same seed → same output)
   - Test all 5 selection buckets are represented
   - Test edge case: population of 15 (fewer than sample size)
   - Test edge case: all personas adopt (no rejecters to sample)

2. **Question Bank Tests**
   - Every scenario has 3-4 questions
   - Every question maps to a valid probing tree
   - No duplicate question IDs

3. **Research Runner Tests** (mock mode only)
   - Full run produces a valid ResearchResult
   - Progress callback is invoked
   - Alternative runs count matches expected

---

## Sprint 13: Research Design Page
**Goal:** Build the unified Scenario + Question + Probing Tree + Run page. This replaces pages 2 (Scenario), 6 (Probing Tree), and 7 (Explorer).

### Cursor — Research Design Page Architecture
**Files:** `app/pages/2_research.py` (new, replaces `2_scenario.py`)

1. **Section A — Scenario & Question** (top of page)
   - Scenario selector (existing dropdown)
   - Business question selector (from question bank)
   - Scenario description + question context displayed
   - Product/marketing parameter sliders in a collapsed `st.expander("Advanced: Tune Parameters")`
   - Channel mix + campaign toggles inside the expander

2. **Section B — Probing Tree** (middle)
   - Auto-loads the probing tree for the selected question
   - Display hypotheses as toggleable cards (checkbox to enable/disable each branch)
   - Show probe count per hypothesis
   - Visual tree structure (can reuse existing tree viz from page 6)

3. **Section C — Run** (bottom)
   - Summary before run: "200 personas × funnel + ~18 deep interviews + ~50 alternative scenarios"
   - Cost estimate if using real LLM
   - Single "Run Research" button (primary, full width)
   - Progress: multi-step progress bar (funnel → sampling → interviews → alternatives)
   - Completion: metric cards showing counts + "View Results →" button that navigates to results page
   - Stores `ResearchResult` in `st.session_state["research_result"]`

### Codex — Alternative Scenario Auto-Generator
**Files:** `src/simulation/auto_variants.py` (new, refactored from explorer.py)

1. Refactor the variant generation from `src/simulation/explorer.py` into a focused module
   - Keep only `generate_smart_variants()` strategy (the most useful one)
   - Add `generate_business_variants()` — parameter changes that map to business-meaningful actions:
     - "What if we added pediatrician endorsement?"
     - "What if we dropped price by 15%?"
     - "What if we doubled awareness budget?"
   - Each variant gets a `business_rationale: str` field explaining the change in plain English
   - Target: 50 variants per run (fast, funnel-only)

### OpenCode — Home + Personas Dashboard
**Files:** `app/streamlit_app.py` (edit), `app/pages/1_population.py` (major refactor → compact dashboard)

1. **Merge landing page with population page**
   - Top panel: 3 metrics (Personas, With Narratives, Scenarios)
   - Static section: city tier, income, family structure, age group — small bar charts in a 2×2 grid, no filters
   - Dynamic section:
     - Common filter bar at top (city tier, income bracket, age, dietary preference) — all multiselect, empty = show all
     - Filtered charts below: update live based on filters
     - Remove scatter plots (those move to Results page in Sprint 14)
   - Persona browser (bottom):
     - Same filters apply
     - Each persona card: name, demographics summary, backstory excerpt
     - Spider chart (from Sprint 12 component) showing top 5 traits
     - Expandable narrative
     - NO decision outcomes, NO scenario data
   - Remove all psychographic scatter / quadrant analysis (moves to Results)

### Antigravity — Tests for Research Design
**Files:** `tests/unit/test_auto_variants.py`, `tests/unit/test_research_page.py`

1. Auto-variant tests: each variant has a business_rationale, all mixes sum to 1.0, no duplicate variants
2. Page logic tests: mock population + scenario → ResearchResult stored in session state

---

## Sprint 14: Results Report Page
**Goal:** Build the research report results page that consumes ResearchResult.

### Cursor — Results Page Architecture + Qualitative Clustering
**Files:** `app/pages/3_results.py` (major rewrite), `src/analysis/qualitative.py` (new)

1. **Results Page Layout**
   - Header: date/time, scenario name, business question, personas sampled, run duration, LLM cost
   - Section 1 — Quantitative Overview (from funnel):
     - Decision pathway waterfall (renamed funnel)
     - Segment response heatmap
     - Barrier distribution
     - Psychographic scatter (moved from population page) with response coloring
   - Section 2 — Qualitative Deep-Dive (from LLM interviews):
     - Response theme clusters (grouped by sentiment/topic)
     - Key concerns raised (ranked list)
     - Representative quotes from persona interviews
     - Per-persona interview cards for the smart sample
   - Section 3 — Alternative Scenarios:
     - Top 5 best-performing variants with business rationale
     - "If you had done X, Y% more personas would respond positively"
     - Parameter sensitivity chart (which levers matter most)
   - Section 4 — What-If:
     - Quick-tweak buttons (±15% price, toggle endorsement, etc.)
     - Re-runs funnel on current population, shows delta vs primary

2. **Qualitative Response Clustering** (`src/analysis/qualitative.py`)
   - Input: list of InterviewResponse objects
   - Group responses by theme/sentiment
   - Extract key concerns (most-mentioned barriers)
   - Select representative quotes
   - Mock mode: use keyword extraction from mock responses
   - Real mode: use LLM to cluster and summarize

### Codex — Results Data Pipeline
**Files:** `src/analysis/research_report.py` (new)

1. **Research Report Generator**
   - Input: `ResearchResult`
   - Output: `ResearchReport` with pre-computed sections:
     - `quantitative_summary`: adoption rate, funnel stage counts, segment breakdown
     - `qualitative_summary`: theme clusters, top concerns, quote selections
     - `alternative_insights`: top variants ranked by improvement, sensitivity analysis
     - `actionable_recommendations`: 3-5 business actions derived from the data
   - Each recommendation must be:
     - Action-driven ("Increase pediatrician endorsement spend") not observational ("Pediatricians are trusted")
     - Grounded in evidence (cite specific persona responses or funnel data)
     - Quantified where possible ("could improve positive response by ~8%")

### OpenCode — Results Page UI Components
**Files:** `app/components/research_report.py` (new), `app/components/quote_card.py` (new)

1. **Research Report Renderer**
   - Render `ResearchReport` sections with proper Streamlit layout
   - Waterfall chart for decision pathway
   - Heatmap for segment responses
   - Bar chart for barrier distribution
   - Scatter plot (moved from population page) with response coloring

2. **Quote Card Component**
   - Render a persona quote with: persona name, city tier, key trait, quote text, sentiment tag
   - Used in the qualitative section

3. **Alternative Scenario Cards**
   - Compact card per variant: what changed, result delta, business rationale
   - Top 5 shown by default, expandable to see all

### Antigravity — Tests + Integration Validation
**Files:** `tests/unit/test_qualitative.py`, `tests/unit/test_research_report.py`, `tests/integration/test_full_research_run.py`

1. Unit tests for qualitative clustering (mock responses → themes)
2. Unit tests for report generator (ResearchResult → ResearchReport)
3. Integration test: full mock run from population → ResearchResult → ResearchReport

---

## Sprint 15: Polish + Deploy
**Goal:** Remove deprecated pages, fix edge cases, deploy shareable demo.

### Cursor — Page Cleanup + Navigation
1. Remove deprecated pages: `4_counterfactual.py`, `6_probing_tree.py`, `6_report.py`, `7_explorer.py`
2. Renumber pages: 1_personas.py, 2_research.py, 3_results.py, 4_interviews.py
3. Update navigation, cross-page links, session state keys
4. Ensure real LLM mode works end-to-end with spend tracking

### Codex — Performance + Caching
1. Cache funnel results across page navigation (don't re-run on page switch)
2. Cache smart sample selection
3. Optimize alternative scenario batch run (parallel where possible)
4. Ensure ResearchResult serializes/deserializes for session state persistence

### OpenCode — UX Polish
1. Loading states and progress indicators for all async operations
2. Mobile-responsive layout for co-founder demo
3. Empty states for pages without data ("Run a research study first")
4. Consistent styling across all new components

### Antigravity — End-to-End Tests + Deploy Validation
1. Full E2E test: generate population → run research → view results
2. Verify Streamlit Cloud deployment works
3. Test with real API key (1 run, verify cost tracking)

---

## Dependency Graph
```
Sprint 12 (Foundation)
  ├── Smart Sampling ──────────────┐
  ├── Question Bank ───────────────┤
  ├── Research Runner ─────────────┤
  └── Spider Chart ────────────────┤
                                   ▼
Sprint 13 (Research Design)        │
  ├── Research Design Page ────────┤
  ├── Auto-Variants ───────────────┤
  ├── Personas Dashboard ──────────┤
  └── Tests ───────────────────────┤
                                   ▼
Sprint 14 (Results Report)         │
  ├── Results Page + Clustering ───┤
  ├── Report Data Pipeline ────────┤
  ├── UI Components ───────────────┤
  └── Tests ───────────────────────┤
                                   ▼
Sprint 15 (Polish + Deploy)
  ├── Cleanup deprecated pages
  ├── Caching + performance
  ├── UX polish
  └── E2E tests + deploy
```

## Risk Mitigation
- **LLM cost for 18 interviews per run:** ~$0.15-0.30 per run with Sonnet. Budget allows ~10 runs per session at $2 cap.
- **OpenCode on Nano for Sprint 13 dashboard:** Recommend upgrading to Pro for the population page refactor — it's complex layout work.
- **Probing tree ↔ interview integration:** Sprint 12 ResearchRunner is the critical path. If it slips, Sprint 13 page can still render with funnel-only results.

---

# Phase 2: Simulation-Native Architecture Transition

## Architecture Shift
The Phase 1 system (Sprints 12-15) produces static funnel snapshots + LLM interviews. Phase 2 transitions to a **simulation-native architecture** where temporal behavioral modeling is the primary source of evidence. The probing tree becomes a diagnostic overlay rather than the primary execution layer.

**Priority Scenarios:**
1. Nutrimix Repeat Purchase (2-6 year olds) — temporal, 12-month simulation
2. Nutrimix 7-14 Expansion — static with social/school dynamics

**Cost Target:** < $0.50 per simulation run (rule-based simulation + 2-3 targeted LLM interviews)

**What's stripped for POC:**
- Deep interviews capped at 2-3 per run (down from 18)
- Magnesium Gummies and ProteinMix scenarios deferred
- Spider charts and persona comparison tools deferred
- Probing tree UI removed from primary flow (becomes background diagnostic)

---

## Sprint 16: Wire Temporal Simulation into Research Pipeline
**Goal:** When a PM runs research on "repeat purchase for Nutrimix", they see month-by-month trajectories, behavioural clusters, and intervention comparisons — not just a static funnel snapshot.

### Codex — Backend Pipeline (Core)
**Files:** `src/simulation/research_runner.py` (edit), `src/simulation/temporal.py` (edit), `src/analysis/research_consolidator.py` (edit), `src/analysis/trajectory_clustering.py` (new)
1. Wire `run_temporal_simulation()` into `ResearchRunner.run()` for temporal scenarios
2. Add per-persona trajectory export (`PersonaTrajectory` model)
3. Run temporal simulation on top 10 alternative scenarios
4. Build trajectory clustering (heuristic-based: loyal, fatigued, switcher, forgot, never-reached)
5. Extend `ConsolidatedReport` with temporal fields

### Cursor — Temporal Results Page
**Files:** `app/pages/3_results.py` (edit)
1. Add trajectory line chart (active/new/churned per month)
2. Add temporal metric cards (month-12 active rate, peak churn, revenue, LJ Pass holders)
3. Add behavioural segment visualization (bar chart + cluster detail expanders)
4. Add intervention comparison (static vs temporal adoption for top alternatives)
5. Guard: skip temporal sections for static scenarios

### OpenCode — Research Design Cleanup
**Files:** `app/pages/2_research.py` (edit)
1. Add simulation mode indicator (temporal vs static badge)
2. Add mock mode banner
3. Dynamic run button label ("Run 12-Month Simulation" vs "Run Scenario Analysis")

### Antigravity — Tests
**Files:** `tests/unit/test_trajectory_clustering.py` (new), `tests/unit/test_temporal_trajectories.py` (new), `tests/integration/test_temporal_pipeline.py` (new)
1. Trajectory clustering tests (cluster validity, assignment, edge cases)
2. Trajectory export tests (per-persona state, determinism)
3. Integration pipeline test (full temporal research run end-to-end)

### Execution Order
```
Codex (backend) ──→ Cursor (results page)
       │                                   } ──→ Antigravity (tests)
       └──────→ OpenCode (research cleanup)
```

---

## Sprint 17: Event-Driven Simulation Engine (Planned)
**Goal:** Replace month-granularity with day-level events. Model specific triggers (pack finish, child taste reaction, competitor promo, reminder) rather than aggregate monthly satisfaction.

### Planned Tasks
- Codex: `EventEngine` class with event grammar, day-level loop, event-driven state updates
- Cursor: Event timeline visualization in results page
- Codex: Competitive context model (switching to Horlicks/Bournvita as explicit alternative)
- Antigravity: Event engine tests + trajectory validation

---

## Sprint 18-19: Intelligence Layer (Planned)
**Goal:** Counterfactual engine + LLM calibration + executive summary generation.

### Planned Tasks
- Counterfactual engine: re-run temporal simulation with parameter perturbations, measure causal lift
- LLM-calibrated thresholds: run LLM on 5-10 representative personas to extract decision parameters, apply as rules to full population
- Executive summary: single LLM call to synthesize temporal findings into PM-ready narrative
- Extend to Nutrimix 7-14 scenario (school context, peer influence, different event grammar)

---

## Sprint 20-21: Presentation + Second Scenario (Planned)
**Goal:** Polish the PM-facing experience for POC demo.

### Planned Tasks
- Cohort heatmaps and retention curves
- Intervention recommendation engine
- Nutrimix 7-14 full temporal scenario
- Demo mode with guided walkthrough

---

## Dependency Graph (Phase 2)
```
Sprint 16 (Temporal Pipeline)
  ├── Temporal → Research Runner ───────┐
  ├── Trajectory Clustering ────────────┤
  ├── Results Page (Temporal) ──────────┤
  └── Tests ────────────────────────────┤
                                        ▼
Sprint 17 (Event Engine)               │
  ├── Day-level events ─────────────────┤
  ├── Competitive context ──────────────┤
  └── Event timeline UI ────────────────┤
                                        ▼
Sprint 18-19 (Intelligence)            │
  ├── Counterfactual engine ────────────┤
  ├── LLM calibration ─────────────────┤
  ├── Executive summary ────────────────┤
  └── Nutrimix 7-14 scenario ──────────┤
                                        ▼
Sprint 20-21 (Presentation)
  ├── Retention curves / heatmaps
  ├── Recommendation engine
  └── Demo walkthrough
```
