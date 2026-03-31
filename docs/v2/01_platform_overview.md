# Platform Overview — LittleJoys Persona Simulation Engine

## Executive Summary

The LittleJoys Persona Simulation Engine is a Streamlit-based research platform that generates a synthetic population of 200 Indian parent personas, runs multi-month behavioral simulations of their product purchase journeys, and then guides a structured investigation pipeline — from problem definition through hypothesis testing, counterfactual analysis, and intervention recommendation — producing a shareable synthesis report at the end. The platform replaces traditional focus groups and survey-based research with a repeatable, deterministic synthetic environment that can be interrogated in minutes rather than weeks.

---

## The 5-Phase Investigation Pipeline

The platform is organised as a linear pipeline. Each phase gates the next via session state keys. Completing one phase unlocks the next.

### Phase 0 — Population Exploration
The home page loads (or generates) the 200-persona synthetic population. Users can browse individual personas, filter by demographic and psychographic attributes, view attribute distributions, and inspect each persona's full narrative and purchase history. No business question has been selected yet; this phase is pure exploration.

### Phase 1 — Business Problem and Baseline Simulation
The user selects one of four predefined business problems. The system maps the selection to a scenario configuration (product, price, marketing parameters) and runs a 12-month temporal simulation across all 200 personas. Each persona's behavioral trajectory is computed month by month — who became aware, who tried, who repeated, who lapsed. The simulation output is classified into five behavioral cohorts: Never Aware, Aware But Not Tried, First-Time Buyer, Current User, and Lapsed User. A funnel chart, cohort breakdown, and per-cohort journey map are rendered.

### Phase 2 — Decomposition and Probing
Given the baseline cohort distribution, the platform presents 4 predefined hypotheses for the selected problem. Users can enable/disable individual hypotheses and add their own custom hypotheses. Once the investigation is run, each enabled hypothesis is tested through a combination of three probe types: Interview (LLM-simulated personas answer structured questions), Simulation (counterfactual scenarios compare adoption rates), and Attribute (statistical comparison of persona attributes between adopters and rejectors). Results are synthesised into a verdict per hypothesis (Confirmed, Partially Confirmed, Inconclusive, Rejected). A contradiction detector runs cross-hypothesis consistency checks.

### Phase 3 — Core Finding
The evidence from Phase 2 is assembled into a ranked evidence chain, a dominant hypothesis is identified, and a Core Finding statement is generated. A quote bank of representative interview responses is displayed. The Core Finding is written to session state and is available for JSON and text export.

### Phase 4 — Interventions
The Core Finding drives automatic generation of an intervention playbook. Each scenario has up to 12 interventions organised in a 2×2 quadrant by scope (General vs. Cohort-specific) and timing (One-time vs. Temporal/Sustained). Each intervention is a parameterised modification to the baseline scenario (e.g., enable pediatrician endorsement, reduce price by 15%, activate LJ Pass). The user clicks "Run All Simulations" to run a counterfactual simulation for every intervention. Results are ranked by absolute adoption lift and written to session state.

### Phase 5 — Synthesis Report
The terminal phase assembles findings from all prior phases into a single downloadable brief. It renders the business problem, population baseline, core finding with evidence, and top intervention results in one view. The report is exportable as a structured `.txt` brief or `.json` data file.

---

## The 9 Streamlit Pages

| Page | File | What it does |
|------|------|-------------|
| Home | `streamlit_app.py` | Population loading, global metrics, getting-started navigation |
| Personas | `pages/1_personas.py` | Persona browser with filters, charts, expanded deep-dive view |
| Problem | `pages/2_problem.py` | Business problem selection, baseline simulation, cohort dashboard |
| Decompose | `pages/3_decompose.py` | Hypothesis review, custom hypothesis input, investigation run, contradiction detection |
| Finding | `pages/4_finding.py` | Evidence chain, quote bank, Core Finding generation, JSON/txt export |
| Intervention | `pages/5_intervention.py` | Intervention table, quadrant map, run-all simulations trigger |
| Intervention Results | `pages/6_intervention_results.py` | Comparison table, counterfactual deep-dive, top recommendation |
| Interviews | `pages/7_interviews.py` | Per-hypothesis probes, cross-hypothesis themes, persona deep-dive |
| Synthesis Report | `pages/8_synthesis_report.py` | Full 4-section synthesis brief, .txt and .json export |
| Compare | `pages/9_compare.py` | Side-by-side scenario comparison across multiple runs |

---

## Key Capabilities

**Synthetic Population Generation**
200 statistically-grounded parent personas generated from Indian demographic distributions. Each persona has 12 attribute categories (demographics, health, psychology, cultural, relationships, career, education, lifestyle, daily routine, values, emotional, media) and an LLM-generated narrative. The population is reproducible from a seed.

**Behavioral Simulation**
Two simulation modes: static (single-pass funnel) and temporal (month-by-month with awareness growth, WOM spreading, repeat purchase, and churn). The temporal simulation runs across 12 months by default and writes purchase events to each persona's `purchase_history`.

**Hypothesis Probing**
Three probe types covering qualitative (interview), causal (counterfactual simulation), and statistical (attribute split) evidence channels. Confidence scores from all three types are combined into a per-hypothesis verdict.

**Counterfactual Analysis**
Any scenario parameter can be modified via dot-path notation (e.g., `product.price_inr`, `marketing.pediatrician_endorsement`). The engine re-runs adoption scoring against the modified scenario and computes absolute and relative lift.

**Intervention Engine**
12 pre-built interventions per problem, organised in a 2×2 quadrant. Each intervention specifies parameter modifications and an expected mechanism. All interventions can be simulated in a single click.

**Export**
Core Finding exports as `.json` and `.txt`. Synthesis Report exports as `.txt` and `.json`. The JSON export includes population baseline, confirmed hypotheses, and ranked intervention results.

---

## Deployment and Access

The platform runs as a multi-page Streamlit application. It can be launched locally with:

```bash
streamlit run streamlit_app.py
```

Or via the helper script `run_app.sh`. The application is deployed to Render as a web service. Environment variables control the LLM provider (`ANTHROPIC_API_KEY`) and mock mode (`LLM_MOCK_ENABLED=true` for development without API calls).

The default configuration (`LLM_MOCK_ENABLED=true`) runs all interview probes using a deterministic mock response builder — no API calls are made. Setting `LLM_MOCK_ENABLED=false` routes interview probes through the Anthropic Claude API.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.11+ | Core runtime |
| Web UI | Streamlit 1.30+ | All pages and interactive components |
| Data validation | Pydantic v2 | All data models with strict validation |
| Numeric | NumPy, SciPy, scikit-learn | Gaussian copula, K-means, pooled statistics |
| Data manipulation | Pandas 2.2+ | DataFrame operations, Parquet I/O |
| Visualisation | Plotly 5.18+ | All charts (bar, funnel, scatter) |
| LLM | Anthropic Claude (anthropic SDK 0.40+) | Interview probes, narrative generation |
| Structured logging | structlog | All module-level logging |
| Persistence | Parquet (tier1.parquet) + JSON (population_meta.json) | Population save/load |
| Testing | pytest 8+, pytest-asyncio, hypothesis | Unit, integration, property-based tests |
| Deployment | Render (web service) | Production hosting |
| Source control | GitHub | Version control, CI |
| Linting | Ruff, mypy (strict) | Code quality |
