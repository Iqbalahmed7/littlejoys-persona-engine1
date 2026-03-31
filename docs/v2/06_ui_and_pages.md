# UI and Pages — Streamlit Application Guide

## Navigation Model

The platform uses Streamlit's multi-page app structure. A sidebar renders the phase navigation with lock/unlock status for each phase. Phase gates are enforced by checking session state keys:

| Phase | Unlock Key | Unlocked When |
|-------|-----------|---------------|
| 0 — Explore Population | (always unlocked) | Application loads |
| 1 — Problem and Simulation | `population` in session state | Population is loaded on home page |
| 2 — Decomposition | `baseline_cohorts` in session state | Baseline simulation has run |
| 3 — Core Finding | `probe_results` in session state | Investigation has run |
| 4 — Interventions | `intervention_results` in session state | Intervention engine has run |

The Compare page (`9_compare.py`) is always accessible via a sidebar link regardless of phase state.

---

## Page 1 — Home (`streamlit_app.py`)

**URL slug**: `/` (root)

**Phase gate**: None — always accessible.

**What it renders**:
- Platform title and welcome banner
- Population load status (whether a population is already in session state)
- "Generate Population" button that calls `PopulationGenerator.generate(seed=42)`
- Top-level population metrics: total personas, Tier 1 count, generation seed
- Getting-started guidance card pointing to Page 2

**Writes to session state**:
- `population` — the `Population` object after generation or load

**Navigation**: Page links to Phase 1 (Problem) once population is loaded.

---

## Page 2 — Personas (`pages/1_personas.py`)

**URL slug**: `/personas`

**Phase gate**: `population` must be in session state.

**What it renders**:
- Filter sidebar: city tier, socioeconomic class, employment status, age range
- Demographic distribution charts (age histogram, income scatter, city tier breakdown)
- Persona browser table: ID, display name, city, income, child ages
- Persona deep-dive expander: all 12 attribute sections, narrative, purchase history
- Psychographic radar or bar chart for selected persona

**Writes to session state**: Nothing — read-only exploration page.

**Navigation**: Links to Phase 1 (Problem).

---

## Page 3 — Problem and Simulation (`pages/2_problem.py`)

**URL slug**: `/problem`

**Phase gate**: `population` must be in session state. Shows warning and stops if not present.

**What it renders**:
1. **Problem selection grid** (2×2 card layout): four business problems, each with label, context, success metric, and a "Select this problem" button.
2. **System Voice callout** explaining what the simulation will do.
3. **Run Baseline Simulation button** — triggers `run_temporal_simulation()` and `classify_population()`.
4. **Simulation progress log** showing month-3, month-6, month-9, month-12 checkpoints.
5. **Post-simulation system voice** narrating key findings from actual results.
6. **5-cohort tile row** (Never Aware, Aware Not Tried, First-Time Buyer, Current User, Lapsed User) with counts and percentages.
7. **Horizontal bar chart** showing cohort distribution.
8. **Funnel chart** (Became Aware → Tried → Repeated → Still Active).
9. **Cohort profile expanders** with representative personas and behavioral hints.
10. **Journey map radio** — select a cohort, see up to 50 persona rows with classification reasons and delta insights.

**Key interactions**:
- Selecting a different problem clears `baseline_cohorts`, `baseline_temporal`, `probe_results`, `core_finding`, and `intervention_results` to prevent stale downstream data.
- Re-run button clears and re-runs if needed.

**Writes to session state**:
- `baseline_temporal` — `TemporalSimulationResult`
- `baseline_cohorts` — `PopulationCohorts`
- `baseline_problem_id` — `str`
- `baseline_scenario_id` — `str` (same value as problem ID)

**Navigation**: Bottom banner with link to Phase 2 (Decompose).

---

## Page 4 — Decompose (`pages/3_decompose.py`)

**URL slug**: `/decompose`

**Phase gate**: `baseline_cohorts` must be in session state. Shows warning and stops if not.

**What it renders**:
1. **System Voice callout** summarising the cohort breakdown and announcing the hypothesis count.
2. **Hypothesis review cards** — each hypothesis shown as an enabled/disabled card with title, rationale, and indicator attribute chips. Disabling a hypothesis excludes it from investigation.
3. **Custom hypothesis form** — text input for title and rationale, "Add hypothesis" button. Custom hypotheses appear with a purple left-border card.
4. **Run Investigation button** — disabled if no hypotheses are enabled.
5. **Live tree progress view** — as probes complete, the tree visualization updates in place showing partial results.
6. **Full investigation results** — after run completes:
   - Per-hypothesis verdict cards with confidence bar, badge (Confirmed/Partial/Inconclusive/Rejected), and probe evidence rows
   - Cross-hypothesis conflicts section
   - Cross-hypothesis synthesis narrative

**Key interactions**:
- Each hypothesis card has a checkbox. State is stored in `st.session_state["hypothesis_enabled"][hyp.id]`.
- Custom hypotheses are stored as serialised dicts in `st.session_state[f"custom_hypotheses_{problem_id}"]`.
- `on_probe_complete` callback updates `partial_probe_results` and re-renders the live tree view after each probe.

**Writes to session state**:
- `probe_results` — dict with keys `synthesis` (TreeSynthesis), `verdicts` (dict[str, HypothesisVerdict]), `probes` (list[Probe]), `problem` (ProblemStatement), `hypotheses` (list[Hypothesis])
- `partial_probe_results` — live accumulator during investigation run
- `hypothesis_enabled` — checkbox state dict
- `custom_hypotheses_{problem_id}` — list of custom hypothesis dicts

**Navigation**: Phase complete banner with link to Phase 3 (Core Finding).

---

## Page 5 — Core Finding (`pages/4_finding.py`)

**URL slug**: `/finding`

**Phase gate**: `probe_results` must be in session state.

**What it renders**:
1. **System Voice callout** — "The investigation is complete."
2. **Core Finding orange box** — dominant hypothesis title + overall confidence. Source: first sentence of `synthesis_narrative` (or a generated fallback).
3. **Evidence chain** — ranked list of hypothesis verdicts, each with:
   - Position number, verdict badge, confidence progress bar
   - Per-probe evidence rows (type icon, confidence bar, evidence summary)
   - Effect size chips (lift %, Cohen's d)
   - Consistency score
4. **Representative Voices** — quote bank of interview response clusters (up to 5 themes, 3 quotes each). Falls back to raw interview responses if no clusters.
5. **Magic Moment green callout** — Key Insight box.
6. **Read full synthesis expander** — full narrative + recommended actions.
7. **JSON export button** — downloads `{scenario_id}_core_finding.json`
8. **Text brief export button** — downloads `{scenario_id}_core_finding.txt`
9. **Proceed to Interventions button**

**Writes to session state**:
```python
st.session_state["core_finding"] = {
    "finding_text": str,                    # Core Finding sentence
    "scenario_id": str,                     # Baseline scenario ID
    "dominant_hypothesis": str,             # Dominant hypothesis ID
    "dominant_hypothesis_title": str,       # Human-readable title
    "evidence_chain": list[str],            # IDs of confirmed hypotheses
    "overall_confidence": float,            # Dominant hypothesis confidence
    "hypotheses_tested": int,
    "hypotheses_confirmed": int,
}
```

**Navigation**: "Proceed to Interventions →" button switches to `pages/5_intervention.py`.

---

## Page 6 — Intervention (`pages/5_intervention.py`)

**URL slug**: `/intervention`

**Phase gate**: `core_finding` must be in session state.

**What it renders**:
1. **System Voice #1** — announces dominant hypothesis and number of interventions.
2. **Intervention comparison table** (custom HTML) — all interventions with name, scope chip, timing chip, target cohort, parameter changes summary, expected mechanism. Recommended intervention highlighted in blue.
3. **System Voice #2** — suggests starter and escalation interventions.
4. **System Voice #3** — simulation caveat.
5. **2×2 Quadrant Map** — four quadrant boxes showing which interventions fall in each.
6. **Intervention detail expanders** — full description, parameter modifications, mechanism.
7. **Population snapshot** — cohort tile row showing Phase 1 baseline cohorts.
8. **Run All Simulations button** — triggers `run_counterfactual()` for every intervention with a progress bar.

**Key interactions**:
- On "Run All Simulations" click: iterates all interventions, calls `run_counterfactual(population, base_scenario, iv.parameter_modifications, iv.name)`, accumulates results in `_all_results`.
- On completion: writes to `intervention_run` and switches to `pages/6_intervention_results.py`.

**Writes to session state**:
- `intervention_results` — `InterventionQuadrant` object (written immediately on page load)
- `intervention_run` — dict `{all_results: list[{intervention, result}], scenario_id, baseline_cohorts}` (written after simulations complete)

**Navigation**: Automatically switches to Page 7 (Intervention Results) after simulations complete.

---

## Page 7 — Intervention Results (`pages/6_intervention_results.py`)

**URL slug**: `/intervention_results`

**Phase gate**: `intervention_run` must be in session state.

**What it renders**:
- Sorted comparison table of all interventions ranked by `absolute_lift`
- Baseline adoption rate reference
- Per-intervention counterfactual deep-dive with segment impact breakdown
- Top recommendation callout

**Writes to session state**: Nothing — read-only display page.

**Navigation**: Links to Synthesis Report (Page 9).

---

## Page 8 — Interviews (`pages/7_interviews.py`)

**URL slug**: `/interviews`

**Phase gate**: `probe_results` must be in session state.

**What it renders**:
- Per-hypothesis interview probe results with response clusters
- Cross-hypothesis theme analysis
- Persona deep-dive: select a persona, see all their interview responses across hypotheses
- Side-by-side persona comparison

**Writes to session state**: Nothing — read-only exploration.

---

## Page 9 — Synthesis Report (`pages/8_synthesis_report.py`)

**URL slug**: `/synthesis_report`

**Phase gate**: `core_finding` must be in session state. Shows a warning if not found but does not stop.

**What it renders**:
1. **System Voice** — `X/4 phases complete` status.
2. **Section 1: Business Problem** — problem label for selected scenario.
3. **Section 2: Population Baseline** — 5-cohort metric tiles.
4. **Section 3: Core Finding** — dominant hypothesis orange box with confidence, followed by confirmed hypothesis evidence chain.
5. **Section 4: Intervention Recommendations** — top 5 interventions by lift with adoption rate.
6. **Export row**:
   - `.txt` download — structured text brief
   - `.json` download — structured data export with generated_at, scenario_id, population_baseline, core_finding, intervention_results

**JSON export structure**:
```json
{
  "generated_at": "2024-11-22T10:00:00",
  "scenario_id": "nutrimix_2_6",
  "business_problem": "Why is repeat purchase low...",
  "population_baseline": {"never_aware": 45, ...},
  "core_finding": {
    "statement": "dominant hypothesis title",
    "confidence": 0.74,
    "confirmed_hypotheses": [{"title": "...", "confidence": 0.81, "status": "confirmed"}]
  },
  "intervention_results": [{"name": "...", "adoption_rate": 0.195, "lift": 0.04, "relative_lift_pct": 25.8}]
}
```

**Navigation**: "Back to Interventions" button.

---

## Page 10 — Compare (`pages/9_compare.py`)

**URL slug**: `/compare`

**Phase gate**: None — always accessible.

**What it renders**:
- Scenario selector to choose two scenarios for comparison
- Side-by-side cohort breakdown, adoption metrics, and intervention lift tables
- Comparison delta highlighting

**Writes to session state**:
- `compare_cohorts_{scenario_id}` — `PopulationCohorts` for each scenario being compared

**Navigation**: Standalone page — links back to home.
