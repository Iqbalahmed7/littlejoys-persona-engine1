# Antigravity — Sprint 5 Briefing

**PRD**: PRD-012 Hardening, QA & Demo Prep
**Branch**: `feat/PRD-012-hardening`
**Priority**: P0

---

## Your Tasks

### 1. Generate precomputed demo artifacts (P0)

Run the precompute pipeline to produce demo-ready data:

```bash
uv run python scripts/precompute_results.py \
    --population-path data/population \
    --output-dir data/results/precomputed \
    --size 200 \
    --deep-persona-count 10 \
    --seed 42 \
    --mock-llm \
    --include-counterfactuals \
    --include-reports
```

Verify output:
- `data/results/precomputed/precompute_manifest.json` exists and contains all 4 scenarios
- Each scenario has `_simulation.json`, `_decision_rows.json`, `_counterfactuals.json`
- `data/results/precomputed/reports/` contains per-scenario report `.md` files + `executive_summary.md`
- All files are valid JSON / valid Markdown

If the script errors, fix the issue in the script or underlying code and report the fix.

### 2. Polish `app/streamlit_app.py` home page (P0)

Current issues:
- Sidebar is static markdown listing page names — this is redundant (Streamlit auto-generates sidebar from `pages/` folder)
- No "Generate Population" button for first-time users
- Caption text uses jargon ("baseline configurations", "demographic schemas")

**Changes needed:**
1. Remove the static `st.sidebar.markdown()` block (lines 48-55) — Streamlit handles navigation automatically
2. Add a "Generate Population" button that creates + saves population when none exists:
   ```python
   if "population" not in st.session_state:
       if st.button("Generate Population"):
           from src.generation.population import PopulationGenerator
           pop = PopulationGenerator().generate(seed=42)
           pop.save(Path("data/population"))
           st.session_state.population = pop
           st.rerun()
   ```
3. Show population summary metrics when loaded: Tier 1 count, Tier 2 count, scenarios precomputed
4. Simplify caption to: "Synthetic persona engine for kids nutrition D2C in India."

### 3. Verify all pages render (P1)

After precompute data exists and population is loaded, manually verify each page:
- Home: metrics display, no errors
- Population Explorer: demographics charts render
- Scenario Configurator: sliders functional
- Results Dashboard: KPIs + all charts
- Counterfactual: predefined buttons work
- Interviews: persona selector populates
- Report: precomputed report displays

Report any errors encountered.

---

## Standards
- `from __future__ import annotations`
- No `print()` — use `structlog`
- Constants from `src.constants` (use `DEFAULT_SEED`, `DEFAULT_POPULATION_SIZE`)
- Keep the home page under 70 lines
- Concise commit messages

## Run
```bash
uv run python scripts/precompute_results.py --mock-llm
uv run streamlit run app/streamlit_app.py
uv run ruff check app/streamlit_app.py
```
