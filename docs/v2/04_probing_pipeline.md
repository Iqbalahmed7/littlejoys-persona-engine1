# Probing Pipeline — Hypothesis Investigation System

## Overview

The probing pipeline investigates why a population behaves the way it does. Given a `ProblemStatement` and a set of `Hypothesis` objects, the `ProbingTreeEngine` executes a mix of interview, simulation, and attribute probes for each hypothesis. Results are aggregated into a `HypothesisVerdict` per hypothesis and a `TreeSynthesis` across all hypotheses. A contradiction detector then identifies cross-hypothesis conflicts.

---

## Pipeline Flow

```
ProblemStatement
       │
       │  get_problem_tree(problem_id)
       ▼
list[Hypothesis] (4 auto-generated + optional custom)
list[Probe]      (2-3 probes per hypothesis)
       │
       │  ProbingTreeEngine.execute_tree(problem, hypotheses, probes)
       ▼
FOR each enabled Hypothesis (sorted by order):
  FOR each Probe of that Hypothesis:
    ├─ ProbeType.INTERVIEW  → _run_interview_probe()
    │   → LLM interviews sampled personas
    │   → cluster_responses_mock()
    │   → compute_interview_confidence(clusters)
    │   → ProbeResult (interview_responses, response_clusters, confidence)
    │
    ├─ ProbeType.SIMULATION → _run_simulation_probe()
    │   → run_counterfactual(baseline, modifications)
    │   → compute_simulation_confidence(baseline_rate, cf_rate, n)
    │   → ProbeResult (baseline_metric, modified_metric, lift, confidence)
    │
    └─ ProbeType.ATTRIBUTE  → _run_attribute_probe()
        → compare adopter vs rejector means per attribute
        → compute pooled effect size (Cohen's d)
        → compute_attribute_confidence(splits)
        → ProbeResult (attribute_splits, confidence)
       │
       ▼
  _build_hypothesis_verdict(hypothesis, probes)
  → compute_hypothesis_confidence([probe confidences])
  → classify_hypothesis(final_confidence)
  → HypothesisVerdict
       │
       ▼
_build_tree_synthesis(problem, hypotheses, probes)
  → rank by confidence
  → dominant_hypothesis = highest confidence
  → TreeSynthesis
       │
       ▼
detect_contradictions(hypotheses, verdicts, probes)
  → list[ContradictionWarning]
```

---

## Data Models

### ProblemStatement

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Problem identifier, e.g. `"repeat_purchase_low"` |
| `title` | `str` | Human-readable title |
| `scenario_id` | `str` | Associated scenario |
| `context` | `str` | Why this problem matters |
| `success_metric` | `str` | What we are trying to improve |
| `target_population_filter` | `dict[str, Any]` | Optional persona filter constraints |

### Hypothesis

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique hypothesis ID |
| `problem_id` | `str` | Parent problem ID |
| `title` | `str` | Short hypothesis statement |
| `rationale` | `str` | Why we believe this might be true |
| `signals` | `list[str]` | Observable signals that would confirm this |
| `indicator_attributes` | `list[str]` | Persona attribute names that are evidence for this hypothesis |
| `counterfactual_modifications` | `dict[str, Any] or None` | Scenario parameter changes to test this hypothesis |
| `is_custom` | `bool` | `True` if user-entered via the custom hypothesis form |
| `enabled` | `bool` | Whether this branch runs during investigation |
| `order` | `int` | Display and execution order |

**Custom hypotheses** created by the user have `is_custom=True`, empty `indicator_attributes`, and no `counterfactual_modifications`. The engine falls back to generating 2 generic interview probes for them.

### Probe

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Probe identifier |
| `hypothesis_id` | `str` | Parent hypothesis ID |
| `probe_type` | `ProbeType` | `"interview"`, `"simulation"`, or `"attribute"` |
| `order` | `int` | Execution order within the hypothesis |
| `question_template` | `str or None` | Question text for interview probes |
| `target_outcome` | `str or None` | `"adopt"` or `"reject"` — filters sampled personas |
| `follow_up_questions` | `list[str]` | Optional follow-up question text |
| `scenario_modifications` | `dict[str, Any] or None` | Parameter changes for simulation probes |
| `comparison_metric` | `str or None` | Metric label for simulation comparison |
| `analysis_attributes` | `list[str]` | Attribute names for attribute probes |
| `split_by` | `str or None` | Optional secondary split variable |
| `status` | `str` | `"pending"`, `"running"`, or `"complete"` |
| `result` | `ProbeResult or None` | Populated after execution |

---

## Probe Types in Detail

### Interview Probe

The engine samples up to `PROBE_SAMPLE_SIZE` personas from the population (stratified by `target_outcome` if specified). For each sampled persona, `PersonaInterviewer.interview()` is called with the `question_template`. The LLM (or mock) produces an in-character response grounded in the persona's full attribute profile and funnel decision outcome.

Responses are clustered by `cluster_responses_mock()` (keyword-based grouping) into `ResponseCluster` objects. Interview confidence is computed from the dominant cluster's cohesion and percentage.

**`InterviewResponse`**:
| Field | Type | Description |
|-------|------|-------------|
| `persona_id` | `str` | Persona who responded |
| `persona_name` | `str` | Display name |
| `outcome` | `str` | Funnel outcome (`"adopt"` or `"reject"`) |
| `content` | `str` | The response text |

**`ResponseCluster`**:
| Field | Type | Description |
|-------|------|-------------|
| `theme` | `str` | Theme label |
| `description` | `str` | What this cluster represents |
| `persona_count` | `int` | Number of personas in this cluster |
| `percentage` | `float` | Fraction of sample in this cluster |
| `representative_quotes` | `list[str]` | Sample quotes |
| `dominant_attributes` | `dict[str, float]` | Mean attribute values for cluster members |

### Simulation Probe

The engine applies the probe's `scenario_modifications` to the baseline scenario via `run_counterfactual()`. The result compares adoption rates between baseline and modified scenarios. Simulation confidence is computed from the magnitude of the absolute lift relative to population size.

### Attribute Probe

The engine compares means of the probe's `analysis_attributes` between adopters and rejectors in the full population. For each attribute, it computes:
- `adopter_mean`, `rejector_mean`
- `effect_size` = `(adopter_mean - rejector_mean) / pooled_std` (Cohen's d)
- `significant` = `abs(effect_size) > 0.3`

Splits are sorted by `abs(effect_size)`. Attribute confidence is computed from the number and magnitude of significant splits.

---

## Confidence Computation

### Per-probe confidence
- **Interview**: based on dominant cluster percentage and cohesion
- **Simulation**: based on absolute lift magnitude, scaled by population size
- **Attribute**: based on count and effect size of significant attribute splits

### Per-hypothesis confidence
`compute_hypothesis_confidence(confidences: list[float])` returns `(final_confidence, consistency_score)`:
- `final_confidence` = weighted mean of probe confidences (higher-confidence probes weighted more)
- `consistency_score` = 1 - std(confidences) — measures whether probes agree with each other

### Verdict Classification

| Status | Confidence Threshold |
|--------|---------------------|
| `confirmed` | ≥ 0.70 |
| `partially_confirmed` | ≥ 0.50 and < 0.70 |
| `inconclusive` | ≥ 0.30 and < 0.50 |
| `rejected` | < 0.30 |

---

## ProbeResult Model

| Field | Type | Description |
|-------|------|-------------|
| `probe_id` | `str` | Probe identifier |
| `confidence` | `float` | Computed confidence [0, 1] |
| `evidence_summary` | `str` | Human-readable summary |
| `sample_size` | `int` | Number of personas used |
| `population_size` | `int or None` | Total population size |
| `clustering_method` | `str or None` | `"keyword"` for mock clustering |
| `interview_responses` | `list[InterviewResponse]` | Only for interview probes |
| `response_clusters` | `list[ResponseCluster]` | Only for interview probes |
| `baseline_metric` | `float or None` | Only for simulation probes |
| `modified_metric` | `float or None` | Only for simulation probes |
| `lift` | `float or None` | `modified_metric - baseline_metric` |
| `attribute_splits` | `list[AttributeSplit]` | Only for attribute probes |

**`AttributeSplit`**:
| Field | Type | Description |
|-------|------|-------------|
| `attribute` | `str` | Attribute name |
| `adopter_mean` | `float` | Mean value among adopters |
| `rejector_mean` | `float` | Mean value among rejectors |
| `effect_size` | `float` | Cohen's d |
| `significant` | `bool` | `abs(effect_size) > 0.3` |

---

## HypothesisVerdict Model

| Field | Type | Description |
|-------|------|-------------|
| `hypothesis_id` | `str` | Hypothesis identifier |
| `confidence` | `float` | Combined confidence across all probes |
| `status` | `str` | `"confirmed"`, `"partially_confirmed"`, `"inconclusive"`, or `"rejected"` |
| `evidence_summary` | `str` | Synthesised narrative of evidence |
| `key_persona_segments` | `list[str]` | Up to 3 identified persona sub-segments |
| `recommended_actions` | `list[str]` | 1-2 action recommendations |
| `consistency_score` | `float` | Agreement between probes [0, 1] |

---

## TreeSynthesis Model

| Field | Type | Description |
|-------|------|-------------|
| `problem_id` | `str` | Problem this synthesis covers |
| `hypotheses_tested` | `int` | Number of enabled hypotheses run |
| `hypotheses_confirmed` | `int` | Count of confirmed + partially_confirmed |
| `dominant_hypothesis` | `str` | ID of highest-confidence hypothesis |
| `confidence_ranking` | `list[tuple[str, float]]` | All hypotheses sorted descending by confidence |
| `synthesis_narrative` | `str` | Cross-hypothesis narrative |
| `recommended_actions` | `list[str]` | Top 5 actions from all verdicts |
| `overall_confidence` | `float` | Confidence of the dominant hypothesis |
| `disabled_hypotheses` | `list[str]` | IDs of hypotheses the user disabled |
| `confidence_impact_of_disabled` | `float` | Max confidence difference if disabled were re-enabled |
| `total_cost_estimate` | `float` | Estimated API cost in USD (0.0 in mock mode) |

---

## Contradiction Detection

`detect_contradictions(hypotheses, verdicts, probes)` applies three rules:

### Rule 1: Confidence Conflict
Two hypotheses A and B that share at least one `indicator_attribute` but reach opposite conclusions (one `confirmed` ≥ 0.70, the other `rejected` < 0.30) produce a HIGH severity warning.

### Rule 2: Mechanism Overlap
Two hypotheses whose dominant interview cluster theme is identical but whose verdicts differ (one confirmed, one not) produce a MEDIUM severity warning. This detects cases where the same underlying driver is being attributed to two different hypotheses.

### Rule 3: Simulation Divergence
A hypothesis that is `inconclusive` or `rejected` by interview evidence but has a simulation probe showing lift > 2pp produces a LOW severity warning. This indicates the simulation and qualitative evidence are pointing in different directions.

**`ContradictionWarning`**:
| Field | Type | Description |
|-------|------|-------------|
| `hypothesis_a_id` | `str` | First hypothesis in the pair |
| `hypothesis_b_id` | `str` | Second hypothesis (same as A for Rule 3) |
| `contradiction_type` | `str` | `"confidence_conflict"`, `"mechanism_overlap"`, or `"simulation_divergence"` |
| `description` | `str` | Explanation |
| `severity` | `str` | `"high"`, `"medium"`, or `"low"` |

Warnings are sorted high → medium → low, then by hypothesis ID for stable ordering.
