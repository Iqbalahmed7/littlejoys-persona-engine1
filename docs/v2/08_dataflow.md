# Data Flow — Session State, Module I/O, and JSON File Flow

## Section 1: Session State Keys

All page-to-page data handoff happens via `st.session_state`. The table below documents every key, who writes it, who reads it, and what it contains.

| Key | Written by | Read by | Contains |
|-----|-----------|---------|---------|
| `population` | Home page (on generation/load) | All pages | `Population` object with 200 `Persona` objects |
| `baseline_temporal` | Page 3 (after sim run) | Page 3 (for post-sim narrative) | `TemporalSimulationResult` |
| `baseline_cohorts` | Page 3 (after sim run) | Pages 4, 5, 6, 7, 8, 9 | `PopulationCohorts` with 5 cohorts |
| `baseline_problem_id` | Page 3 | Pages 4, 6, 8 | `str` — selected problem ID (same as scenario ID) |
| `baseline_scenario_id` | Page 3 | Pages 4, 5, 6, 7, 8, 9 | `str` — e.g. `"nutrimix_2_6"` |
| `selected_problem_id` | Page 3 (problem cards) | Page 3 | `str` — currently selected problem |
| `hypothesis_enabled` | Page 4 (checkboxes) | Page 4 | `dict[str, bool]` — per-hypothesis enable state |
| `custom_hypotheses_{problem_id}` | Page 4 (custom form) | Page 4 | `list[dict]` — serialised custom Hypothesis dicts |
| `partial_probe_results` | Page 4 (on_probe_complete callback) | Page 4 (live tree view) | `dict[hypothesis_id → list[ProbeResult]]` |
| `probe_results` | Page 4 (after investigation) | Pages 5, 6, 8, 9 | `dict` with keys: `synthesis`, `verdicts`, `probes`, `problem`, `hypotheses` |
| `core_finding` | Page 5 (on every render) | Pages 6, 8, 9 | `dict` — finding_text, dominant_hypothesis_title, overall_confidence, evidence_chain, etc. |
| `intervention_results` | Page 6 (on page load) | Pages 6, 8 | `InterventionQuadrant` object |
| `intervention_run` | Page 6 (after run all) | Pages 7, 8, 9 | `dict` — `{all_results, scenario_id, baseline_cohorts}` |
| `compare_cohorts_{scenario_id}` | Page 10 (Compare) | Page 10 | `PopulationCohorts` per scenario |
| `segment_persona_ids` | Page 3 (segment builder) | Future use | `list[str]` — persona IDs in a custom segment |

### Phase Gate Mapping

`app/utils/phase_state.py` defines which session state key unlocks each phase:

| Phase | Unlock Key | Meaning |
|-------|-----------|---------|
| 0 | (always) | Population Explore — always accessible |
| 1 | `population` | Population loaded on home page |
| 2 | `baseline_cohorts` | Baseline simulation complete |
| 3 | `probe_results` | Investigation run complete |
| 4 | `intervention_results` | Intervention engine has run |

---

## Section 2: Module I/O Dataflow

The complete pipeline from population generation through synthesis:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         POPULATION LAYER                                 │
│                                                                          │
│  PopulationGenerator.generate(seed=42, size=200)                        │
│  ├─ DistributionTables.sample_demographics(200, 42)                     │
│  ├─ GaussianCopulaGenerator.generate(200, demographics, 42)             │
│  ├─ ConditionalRuleEngine.apply(merged_df)                              │
│  ├─ Persona.from_flat_dict() × 200                                      │
│  └─ Tier2NarrativeGenerator.generate_batch(personas)                   │
│                                                                          │
│  Output: Population(tier1_personas=[Persona × 200], metadata)           │
│  Stored: session_state["population"]                                    │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ Population
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        SIMULATION LAYER                                  │
│                                                                          │
│  run_temporal_simulation(population, scenario, months=12)               │
│  Output: TemporalSimulationResult                                       │
│  Stored: session_state["baseline_temporal"]                             │
│                                                                          │
│  classify_population(population, scenario, seed=42)                     │
│  ├─ evaluate_scenario_adoption() → static funnel results               │
│  └─ run_event_simulation() → PersonaTrajectory per adopter             │
│  Output: PopulationCohorts(cohorts, classifications, summary)           │
│  Stored: session_state["baseline_cohorts"]                             │
│  Side effect: persona.product_relationship assigned for all personas   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ Population + PopulationCohorts + scenario_id
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PROBING LAYER                                    │
│                                                                          │
│  get_problem_tree(problem_id)                                            │
│  → ProblemStatement, list[Hypothesis] (4), list[Probe] (8-12)          │
│                                                                          │
│  User may add custom Hypotheses (is_custom=True)                        │
│                                                                          │
│  ProbingTreeEngine.execute_tree(problem, hypotheses, probes)            │
│  FOR each enabled hypothesis:                                            │
│    FOR each probe:                                                       │
│      ├─ INTERVIEW: PersonaInterviewer.interview() × sample_size        │
│      │   → cluster_responses_mock() → ResponseCluster list             │
│      │   → compute_interview_confidence()                               │
│      ├─ SIMULATION: run_counterfactual(baseline, modifications)         │
│      │   → compute_simulation_confidence()                              │
│      └─ ATTRIBUTE: compare adopter vs rejector means                   │
│          → compute_attribute_confidence(splits)                         │
│    → ProbeResult (confidence, evidence_summary, clusters/splits/lift)  │
│    → HypothesisVerdict (confidence, status, key_segments, actions)     │
│  → TreeSynthesis (dominant_hypothesis, confidence_ranking, narrative)  │
│                                                                          │
│  detect_contradictions(hypotheses, verdicts, probes)                    │
│  → list[ContradictionWarning]                                           │
│                                                                          │
│  Output stored: session_state["probe_results"] = {                     │
│    "synthesis": TreeSynthesis,                                           │
│    "verdicts": dict[str, HypothesisVerdict],                            │
│    "probes": list[Probe],                                               │
│    "problem": ProblemStatement,                                          │
│    "hypotheses": list[Hypothesis]                                       │
│  }                                                                       │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ probe_results
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          FINDING LAYER                                   │
│                                                                          │
│  Page 5 (4_finding.py) reads probe_results and assembles:              │
│  ├─ dominant_hypothesis_title from synthesis.dominant_hypothesis        │
│  ├─ overall_confidence from synthesis.overall_confidence                │
│  ├─ evidence_chain = [h.id for h where verdict.status in confirmed]    │
│  └─ finding_text from synthesis_narrative (first sentence)             │
│                                                                          │
│  Output: session_state["core_finding"] = {                             │
│    "finding_text": str,                                                  │
│    "scenario_id": str,                                                   │
│    "dominant_hypothesis": str,       # hypothesis ID                   │
│    "dominant_hypothesis_title": str,                                    │
│    "evidence_chain": list[str],                                         │
│    "overall_confidence": float,                                         │
│    "hypotheses_tested": int,                                            │
│    "hypotheses_confirmed": int                                          │
│  }                                                                       │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ core_finding
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       INTERVENTION LAYER                                 │
│                                                                          │
│  generate_intervention_quadrant(InterventionInput(problem_id), scenario)│
│  → InterventionQuadrant(problem_id, quadrants: dict[str, list[IV]])    │
│  Stored: session_state["intervention_results"]                          │
│                                                                          │
│  FOR each Intervention:                                                  │
│    run_counterfactual(population, base_scenario,                        │
│                       iv.parameter_modifications, iv.name)              │
│    → CounterfactualResult(baseline_adoption_rate,                       │
│                            counterfactual_adoption_rate,                │
│                            absolute_lift, relative_lift_percent,        │
│                            most_affected_segments)                      │
│                                                                          │
│  Output: session_state["intervention_run"] = {                          │
│    "all_results": [{"intervention": IV, "result": CFResult}],           │
│    "scenario_id": str,                                                   │
│    "baseline_cohorts": PopulationCohorts                                │
│  }                                                                       │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ core_finding + intervention_run
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        SYNTHESIS LAYER                                   │
│                                                                          │
│  Page 9 (8_synthesis_report.py) assembles from session state:          │
│  ├─ Business problem label from scenario_id                             │
│  ├─ Cohort summary from baseline_cohorts.summary                       │
│  ├─ Core finding from core_finding.dominant_hypothesis_title           │
│  ├─ Evidence chain from probe_results.verdicts                         │
│  └─ Top 5 interventions from intervention_run.all_results              │
│     sorted by result.absolute_lift descending                          │
│                                                                          │
│  Exports:                                                                │
│  ├─ {scenario_id}_synthesis_report.txt  — structured text brief        │
│  └─ {scenario_id}_synthesis_report.json — structured data export       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Section 3: JSON File Flow

These are the JSON files that can be written to disk or downloaded:

| JSON Output | Produced by | Consumed by | Key Fields |
|-------------|------------|------------|------------|
| `tier1.parquet` | `Population.save(path)` | `Population.load(path)` | Columnar storage of `persona_json` strings |
| `population_meta.json` | `Population.save(path)` | `Population.load(path)` | population_id, generation_params, metadata, tier1_parquet filename |
| `{scenario_id}_core_finding.json` | Page 5 (download button) | Phase 8 (synthesis), Phase 9 (compare) | finding_text, dominant_hypothesis_title, overall_confidence, evidence_chain |
| `{scenario_id}_core_finding.txt` | Page 5 (download button) | Human stakeholders | Text brief with evidence chain and representative quotes |
| `{scenario_id}_synthesis_report.json` | Page 9 (download button) | Stakeholders, external tools | generated_at, scenario_id, population_baseline, core_finding, intervention_results |
| `{scenario_id}_synthesis_report.txt` | Page 9 (download button) | Stakeholders | Formatted text brief of entire investigation |

### Synthesis Report JSON Structure

```json
{
  "generated_at": "2024-11-22T10:00:00",
  "scenario_id": "nutrimix_2_6",
  "business_problem": "Why is repeat purchase low despite high NPS? (Nutrimix 2-6)",
  "population_baseline": {
    "never_aware": 45,
    "aware_not_tried": 80,
    "first_time_buyer": 35,
    "current_user": 22,
    "lapsed_user": 18
  },
  "core_finding": {
    "statement": "Trust barrier: parents need medical authority proof before trial",
    "confidence": 0.81,
    "confirmed_hypotheses": [
      {
        "title": "Trust barrier: parents need medical authority proof before trial",
        "confidence": 0.81,
        "status": "confirmed"
      }
    ]
  },
  "intervention_results": [
    {
      "name": "Pediatrician Endorsement Campaign",
      "adoption_rate": 0.195,
      "lift": 0.04,
      "relative_lift_pct": 25.8
    }
  ]
}
```

---

## Section 4: Module Dependency Map

```
src/taxonomy/schema.py
  └─ Persona, PurchaseEvent, TemporalState, BrandMemory, MemoryEntry

src/taxonomy/distributions.py
  └─ DistributionTables → used by PopulationGenerator

src/taxonomy/correlations.py
  └─ GaussianCopulaGenerator, ConditionalRuleEngine → used by PopulationGenerator

src/generation/population.py
  └─ Population, PopulationGenerator, GenerationParams, PopulationMetadata

src/generation/tier2_generator.py
  └─ Tier2NarrativeGenerator → called by PopulationGenerator

src/decision/scenarios.py
  └─ ScenarioConfig, ProductConfig, MarketingConfig, LJPassConfig

src/decision/funnel.py
  └─ run_funnel(), DecisionResult → used by static, temporal, counterfactual

src/simulation/static.py
  └─ run_static_simulation() → StaticSimulationResult

src/simulation/temporal.py
  └─ run_temporal_simulation() → TemporalSimulationResult, MonthlySnapshot

src/simulation/counterfactual.py
  └─ run_counterfactual() → CounterfactualResult
  └─ generate_default_counterfactuals() → list[CounterfactualScenario]

src/analysis/cohort_classifier.py
  └─ classify_population() → PopulationCohorts, CohortClassification

src/probing/models.py
  └─ ProblemStatement, Hypothesis, Probe, ProbeResult, ResponseCluster,
     AttributeSplit, HypothesisVerdict, TreeSynthesis

src/probing/engine.py
  └─ ProbingTreeEngine → execute_tree() → TreeSynthesis

src/probing/predefined_trees.py
  └─ get_problem_tree(problem_id) → (ProblemStatement, list[Hypothesis], list[Probe])

src/analysis/contradiction_detector.py
  └─ detect_contradictions() → list[ContradictionWarning]

src/analysis/intervention_engine.py
  └─ generate_intervention_quadrant() → InterventionQuadrant
  └─ Intervention, InterventionQuadrant

app/utils/phase_state.py
  └─ phase_complete(), render_phase_sidebar()

app/pages/2_problem.py     → writes: baseline_cohorts, baseline_temporal, baseline_scenario_id
app/pages/3_decompose.py   → writes: probe_results
app/pages/4_finding.py     → writes: core_finding
app/pages/5_intervention.py→ writes: intervention_results, intervention_run
app/pages/8_synthesis_report.py → reads all, exports JSON + TXT
```
