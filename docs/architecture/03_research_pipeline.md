# Research Pipeline

## Overview

The research pipeline answers business questions through a hybrid of three probe types: LLM-driven interviews with personas, counterfactual scenario simulations, and statistical attribute analysis. These are organised into a hierarchical **Probing Tree** structure: Problem → Hypotheses → Probes.

Entry points:
- `src/probing/` — models, question bank, predefined trees, engine
- `src/analysis/research_consolidator.py` — merges all probe results into one report
- `src/simulation/research_runner.py` — batch orchestration

---

## Core Data Models (`src/probing/models.py`)

### ProblemStatement
A single business question to investigate.
```
id, title, scenario_id, context, success_metric, target_population_filter
```

### Hypothesis
One testable explanation for a problem statement.
```
id, problem_id, title, rationale,
indicator_attributes: list[str]   # attribute names to test statistically
counterfactual_modifications: dict  # scenario param overrides for simulation probe
enabled: bool
order: int
```

### Probe
A single investigation step within a hypothesis.
```
id, hypothesis_id,
probe_type: ProbeType  # "interview" | "simulation" | "attribute"
question_template: str | None
target_outcome: str | None
follow_up_questions: list[str]
scenario_modifications: dict | None
comparison_metric: str | None
analysis_attributes: list[str]
split_by: str | None
status: str  # "pending" | "completed"
result: ProbeResult | None
```

### ProbeResult
Output of executing one probe.
```
probe_id, confidence, evidence_summary, sample_size, population_size,
clustering_method: str | None
interview_responses: list[InterviewResponse]
response_clusters: list[ResponseCluster]
baseline_metric, modified_metric, lift   # for simulation probes
attribute_splits: list[AttributeSplit]   # for attribute probes
```

### ResponseCluster
A thematic grouping of interview responses.
```
theme, description, persona_count, percentage,
representative_quotes: list[str],
dominant_attributes: dict[str, float]
```

### AttributeSplit
Statistical comparison of one attribute between adopter and rejector groups.
```
attribute, adopter_mean, rejector_mean, effect_size, significant
```

### HypothesisVerdict
Synthesised conclusion per hypothesis, produced by the tree engine.
```
hypothesis_id, confidence, status, evidence_summary,
key_persona_segments, recommended_actions, consistency_score
```

### TreeSynthesis
Final cross-hypothesis synthesis for the problem statement.
```
problem_id, hypotheses_tested, hypotheses_confirmed, dominant_hypothesis,
confidence_ranking: list[tuple[str, float]]
synthesis_narrative, recommended_actions, overall_confidence
```

---

## Probe Types

### Interview Probe (`probe_type = "interview"`)

The LLM is prompted to role-play as the persona, responding to a structured open-ended question. Responses are clustered by `src/probing/clustering.py` (k-means on embedding vectors) to surface thematic patterns across the sample.

Key parameters:
- Sample selection: stratified sample of 15 personas (adopters + rejectors + fragile borderline cases) via `src/probing/sampling.py`
- Clustering: k=3 clusters, method stored in `ProbeResult.clustering_method`
- Output: `response_clusters` with representative quotes and dominant attribute profiles

### Simulation Probe (`probe_type = "simulation"`)

The scenario is modified via `counterfactual_modifications` and re-run against the full population to compute adoption lift.

```
baseline_metric = run_funnel(population, base_scenario).adoption_rate
modified_metric = run_funnel(population, modified_scenario).adoption_rate
lift = modified_metric - baseline_metric
```

Scenario modifications are applied by `src/simulation/counterfactual.py — apply_scenario_modifications()`, which traverses dot-path keys (e.g., `"marketing.pediatrician_endorsement"`) and updates the relevant nested field.

### Attribute Probe (`probe_type = "attribute"`)

Statistical analysis of which attributes differ most between adopters and rejectors.

For each `analysis_attributes` field:
1. Split population into adopter/rejector groups
2. Compute mean for each group
3. Compute Cohen's d effect size
4. Record as `AttributeSplit` in the result

---

## Question Bank (`src/probing/question_bank.py`)

13 pre-defined business questions across all 4 scenarios.

| Scenario | Question ID | Title |
|---|---|---|
| nutrimix_2_6 | q_nm26_repeat_purchase | How can we improve repeat purchase for NutriMix? |
| nutrimix_2_6 | q_nm26_first_trial | What drives first-time trial among health-anxious parents? |
| nutrimix_2_6 | q_nm26_lj_pass_effectiveness | How effective is the LJ Pass in building purchase habits? |
| nutrimix_2_6 | q_nm26_segment_potential | Which parent segments show highest untapped potential? |
| nutrimix_7_14 | q_nm714_brand_extension | Can the NutriMix brand extend credibly to older children? |
| nutrimix_7_14 | q_nm714_school_trust | What role do school partnerships play in building trust? |
| nutrimix_7_14 | q_nm714_taste_by_age | How do taste preferences differ between age groups? |
| magnesium_gummies | q_mg_trial_drivers | What drives initial trial for a new gummy supplement? |
| magnesium_gummies | q_mg_doctor_vs_peer | How important is pediatrician endorsement vs peer recommendation? |
| magnesium_gummies | q_mg_concern_match | Which parent concerns does this product address most effectively? |
| protein_mix | q_pm_adoption_barriers | What are the primary barriers to protein supplement adoption? |
| protein_mix | q_pm_price_point | How does the higher price point affect consideration? |
| protein_mix | q_pm_sports_partnership | Does sports club partnership move the needle for active families? |

Each question has either a **predefined tree** (full 3-probe hierarchy) or a **lightweight tree** (auto-generated from hypotheses) accessible via `get_tree_for_question(question_id)`.

---

## Predefined Trees (`src/probing/predefined_trees.py`)

Four fully-specified probing trees for the main business problems:
- `repeat_purchase_low` — NutriMix 2–6 repeat behavior
- `nutrimix_7_14_expansion` — brand extension viability
- `magnesium_gummies_growth` — awareness and trial
- `protein_mix_launch` — adoption barrier ranking

Each tree contains 3–4 hypotheses and 9–12 probes covering all three probe types in sequence.

---

## Engine (`src/probing/engine.py`)

`ProbingTreeEngine.run(tree, population, scenario, llm_client)` steps:

1. For each hypothesis (in `order` sequence):
   a. Execute all probes for that hypothesis
   b. Merge results into a `HypothesisVerdict`
2. After all hypotheses: produce `TreeSynthesis`
3. Persist a `TreeExecutionSnapshot` for resume on failure

Confidence scoring per hypothesis:
- Interview cluster cohesion → contributes 40%
- Simulation lift magnitude → contributes 40%
- Attribute split effect sizes → contributes 20%

---

## Research Consolidator (`src/analysis/research_consolidator.py`)

`consolidate_results(tree_snapshot, scenario_results, population)` produces a `ConsolidatedReport` containing:
- `funnel` — adoption rates and stage breakdown
- `event_monthly_rollup` — temporal monthly snapshots (if applicable)
- `behaviour_clusters` — trajectory clusters
- `decision_rationale_summary` — ranked rejection reasons
- `counterfactual_results` — all simulation probe lifts
- `variable_importance` — SHAP ranking from causal analysis
- `executive_summary` — LLM-generated narrative

---

## Files

| File | Role |
|---|---|
| `src/probing/models.py` | All Pydantic data models |
| `src/probing/question_bank.py` | 13 business questions + lightweight trees |
| `src/probing/predefined_trees.py` | 4 full probing trees |
| `src/probing/engine.py` | Execution orchestrator |
| `src/probing/sampling.py` | Stratified persona sample selection |
| `src/probing/clustering.py` | Interview response k-means clustering |
| `src/probing/confidence.py` | Confidence scoring functions |
| `src/probing/smart_sample.py` | Smart borderline-aware sampling |
| `src/analysis/research_consolidator.py` | Result merging into ConsolidatedReport |
| `src/simulation/research_runner.py` | Batch probing tree runner |
