# Sprint 32 — Research Intelligence Platform

**Completed**: 2026-04-03
**Owner**: Claude (Tech Lead)

---

## What was shipped

### Sprint 1a — Probing Tree Upgrade (`src/probing/`)

**`src/probing/models.py`** — 6 new fields added to `Hypothesis`:
- `confidence_prior: float` (0.0–1.0, default 0.5) — Bayesian prior on how likely this is a real driver
- `real_world_analogy: str` — Indian FMCG brand evidence string
- `why_level: int` (1–5, default 1) — 5-WHY depth level
- `parent_hypothesis_id: str | None` — links sub-hypotheses to parent
- `cohort_filter: dict[str, Any]` — population slice filter (e.g. `{"outcome": "lapsed"}`)
- `edge_case: bool` — flags low-probability strategic hypotheses

**`src/probing/predefined_trees.py`** — all 4 trees fully rewritten:

| Tree | Top-level | Sub-hyps | Edge cases | Probes |
|---|---|---|---|---|
| `repeat_purchase_low` | 5 | 10 | 1 | 37 |
| `nutrimix_7_14_expansion` | 5 | 10 | 1 | 30 |
| `magnesium_gummies_growth` | 5 | 10 | 2 | 31 |
| `protein_mix_launch` | 5 | 10 | 2 | 31 |

Every hypothesis has `confidence_prior`, `real_world_analogy` (Horlicks/HUL, Complan/IRI, PediaSure/Abbott, Mamaearth, Dabur Chyawanprash, Emami, Himalaya, Bournvita, Nestle, Amrutanjan), `cohort_filter`, and `edge_case`.

---

### Sprint 1b — Dynamic Hypothesis Generator

**`src/probing/dynamic_generator.py`** — new module:
- `generate_hypothesis_tree(problem_text, scenario_id, n_hypotheses, max_why_depth, model) -> ProblemTreeDefinition`
- Uses Claude Sonnet to generate 5 top-level hypotheses + 2 sub-hypotheses each + 2 probes per hypothesis
- Grounded prompt requires Indian FMCG analogies and confidence priors per hypothesis
- Handles JSON parsing (strips markdown fences, fallback extraction)
- `is_dynamic_generator_available()` — returns True if `ANTHROPIC_API_KEY` set

---

### Sprint 3 — Investigate Page

**`app/streamlit_app.py`** — added nav item "Investigate" (position 2) and `page_investigate()`:

**Tab 1: Problem Selection**
- 2×2 card grid for 4 predefined problems — click to set `investigate_problem_id`
- Custom problem text area + "Generate Hypothesis Tree" button (uses `dynamic_generator`)

**Tab 2: Hypothesis Tree**
- Top-level hypotheses in expanders with confidence badge (green/amber/red), real-world analogy, cohort pills, edge-case badge
- Sub-hypotheses listed inline below parent
- Enable/disable checkboxes per hypothesis
- "Run N probes across M personas" button → `ProbingTreeEngine.execute_probe()` per probe
- Inline results: interview quotes, attribute bar charts, simulation before/after

**Tab 3: Findings**
- `TreeSynthesis` display: narrative, overall confidence, hypothesis ranking, recommended actions
- Falls back to raw results table if synthesis not available

---

### Simulation Builder Fixes (`app/streamlit_app.py`)

**Purchase channels** expanded from 5 to 12:
`bigbasket, blinkit, zepto, swiggy_instamart, firstcry_online, amazon, d2c, pharmacy, hospital_pharmacy, dmart, kirana_local, modern_trade`

**Marketing mix** expanded from 3 to 6 toggles:
Added: TV/OTT ad, Free sample/trial kit, Discount/cashback

**Stimulus injection** — `_build_config()` now injects new stimulus rows when a toggle is turned ON (not just filters when OFF). Each new channel injects a contextually appropriate stimulus at the right tick relative to the first decision point.

**LP Pass metric** — new 5th metric column in results panel: % of personas who engaged (trial/buy/research_more) vs. immediately rejecting/deferring.

**Objection/driver deduplication** — semantic normalization before display (case-insensitive, strip punctuation, collapse plural forms).

**Persona table** — now interactive using `st.dataframe(selection_mode="single-row")`. Clicking a row expands a decision detail panel showing reasoning trace, key drivers, and objections per decision tick.

---

### Journey C Results

Journey C (Nutrimix 7–14 Expansion) results written to `data/population/journey_C_results.json`:
- 50 personas, 0 errors
- First purchase: 30% (trial 26%, buy 4%)
- LP Pass: 86% (most personas reached research/consideration stage)
- Reorder: 100% among first buyers (small sample n=15; simulation artifact — high-intent first-buyers in expansion scenario)

Journey A (50 personas): 72% first purchase, 97% reorder
Journey B (50 personas): 56% first purchase, 96% reorder

> Note: simulation reorder rates reflect ideal-scenario conditions. Real-world baselines are typically 20–40pp lower.

---

## Architecture decisions

**Thread safety**: `CognitiveAgent._get_client()` creates a fresh `anthropic.Anthropic()` client per LLM call — required by httpx 0.28+ transport model when running in `ThreadPoolExecutor`.

**Tick extraction**: `_extract_decision()` in `journey_result.py` checks ticks `{20, 28, 35}` for first decision and `{45, 60}` for second, plus fallback scanning of all decision-bearing snapshots. Journey C uses tick 28 for first decision.

**Widget state**: Streamlit radio nav uses `index=` only (no `key=`). Writing to a widget's session_state key after render raises `StreamlitAPIException`.

---

## Next sprint (Sprint 33)

- Intervention simulation builder upgrade: cohort targeting, temporal simulation, run queue/history
- Counterfactual agent: background auto-runs, suggestions dashboard
- Fix simulation builder stimulus types to react dynamically to marketing mix changes in real-time (currently requires re-run)
- Rerun all 3 journeys with full 200 personas (current results are 50-persona previews)
