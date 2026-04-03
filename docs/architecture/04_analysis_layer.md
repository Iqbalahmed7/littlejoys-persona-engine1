# Analysis Layer

## Overview

The analysis layer transforms raw simulation outputs into decision-quality insights. It covers four concerns:

1. **SHAP feature importance** — which persona attributes most drive adoption
2. **Barrier analysis** — where and why personas drop off the funnel
3. **Cohort segmentation** — which population segments behave distinctly
4. **Executive summary** — LLM-generated PM-ready narrative

All analysis modules in `src/analysis/`.

---

## SHAP Feature Importance (`src/analysis/causal.py`)

### Purpose
Identifies which of the 145 persona attributes have the strongest causal relationship with adoption vs rejection. Answers: "What should we change to improve conversion?"

### Method
1. Flatten all persona attributes and decision results into a feature matrix X (one row per persona).
2. Fit a `LogisticRegression` (sklearn, max_iter=1000, random_state=42) on `outcome` as the binary target.
3. Run `shap.LinearExplainer` on the fitted model to compute per-feature SHAP values.
4. Rank by `mean(|SHAP|)` across all personas.

### VariableImportance Model
```python
class VariableImportance(BaseModel):
    variable_name: str
    coefficient: float       # logistic regression coefficient
    shap_mean_abs: float     # mean absolute SHAP value across population
    direction: str           # "positive" | "negative"
    rank: int                # 1 = most important
```

### CausalStatement Generation
For each top-N variable (default N=8):
1. Split population at the median value of the variable.
2. Compute adoption rate above vs below the median.
3. Calculate lift ratio.
4. Generate a human-readable statement: "Personas with X above 0.62 are 2.4x more likely to adopt because..."
5. For high-importance variables (SHAP > 2× mean), also generate segment-specific statements by city_tier and income_bracket.

```python
class CausalStatement(BaseModel):
    statement: str
    supporting_variables: list[str]
    evidence_strength: float     # normalised SHAP rank (0–1)
    segment: str | None          # e.g. "Tier1", "low_income" — or None for population-level
```

---

## Barrier Analysis (`src/analysis/barriers.py`)

### Purpose
Quantifies exactly where personas exit the funnel and the distribution of rejection reasons, enabling prioritisation of marketing and product interventions.

### BarrierDistribution Model
```python
class BarrierDistribution(BaseModel):
    stage: str        # "need_recognition" | "awareness" | "consideration" | "purchase"
    barrier: str      # rejection reason label
    count: int
    percentage: float # fraction of total population
```

### StageSummary Model
```python
class StageSummary(BaseModel):
    stage: str
    total_dropped: int
    percentage_of_rejections: float    # this stage's share of all rejection events
    top_reasons: list[str]             # top 3 rejection reasons for this stage
```

### Process
1. `analyze_barriers(results)` — iterates all DecisionResult rows, counts `(rejection_stage, rejection_reason)` pairs.
2. `summarize_barrier_stages(results)` — groups by stage, computes percentage of total rejections, ranks top reasons.
3. Output is sorted by `count` descending.

Typical breakdown for NutriMix 2–6:
- Consideration accounts for ~36% of rejections (primary bottleneck)
- Need recognition ~29%
- Purchase ~23%
- Awareness ~13%

---

## Cohort Segmentation (`src/analysis/cohort_classifier.py`)

### Purpose
Groups personas into meaningful segments for targeted intervention design. Segments are used as `target_cohort_id` in the simulation module.

### Defined Cohorts

| Cohort ID | Definition |
|---|---|
| `lapsed_user` | Has purchased before, currently inactive |
| `current_user` | Currently active (has purchased in last simulation period) |
| `first_time_buyer` | Adopted but total purchases ≤ 1 |
| `never_aware` | Awareness score = 0 across all scenarios |
| `aware_not_tried` | Awareness score > 0 but no purchase |
| `high_need_rejecters` | High need score but rejected at consideration or purchase |
| `low_income_families` | household_income_lpa ≤ 8 LPA |
| `trust_skeptics` | medical_authority_trust ≤ 0.40 |
| `time_scarce_parents` | perceived_time_scarcity ≥ 0.70 |
| `committed_users` | total purchases ≥ 3 |

### Trajectory Clustering (`src/analysis/trajectory_clustering.py`)
For temporal simulations, personas are clustered by their 12-month active/inactive time series (TSLEARN k-means on monthly snapshots), producing cluster labels like "Early converters", "Late adopters", "One-and-done".

### Segments Module (`src/analysis/segments.py`)
Computes adoption rates sliced by `city_tier`, `income_bracket`, `employment_status`, `child_age_group`, and `education_level`. Output used for the comparison dashboard page.

---

## Problem Decomposition (`src/analysis/problem_decomposition.py`)

Maps raw simulation results to a structured diagnosis, including:
- Primary adoption barriers ranked by count
- Segment-level lift opportunities
- Recommended probe types per barrier

Used as input to the Intervention Engine in Phase C.

---

## Executive Summary (`src/analysis/executive_summary.py`)

### Purpose
Generates a PM-readable 5-field narrative summary of the consolidated simulation results.

### ExecutiveSummary Model
```python
class ExecutiveSummary(BaseModel):
    headline: str                   # one sentence
    trajectory_summary: str         # 2–3 sentences on the arc
    key_drivers: list[str]          # exactly 3 items
    recommendations: list[str]      # exactly 3 actionable items
    risk_factors: list[str]         # exactly 2 items
    raw_llm_response: str
    mock_mode: bool
```

### LLM Prompt Construction
The prompt contains:
- Scenario metadata (name, price, age range)
- Month-by-month active counts (up to 14 months)
- Behaviour/trajectory cluster breakdown
- Top decision drivers from the event model
- Best counterfactual lift result
- Funnel trial rate and month-12 active rate

Model: Claude `bulk` tier (Haiku-class), temperature=0.4, max_tokens=900.

### Mock Mode
When `mock_mode=True`, a fixture response is returned immediately without calling the API. This is used in demo deployments and CI tests.

---

## Report Agent (`src/analysis/report_agent.py`)

An agentic loop (`ReportAgent`) that iteratively calls analysis tools (funnel summary, causal analysis, barrier analysis, segment comparison) to build a comprehensive markdown report. Configurable iteration limit: `REPORT_AGENT_MAX_ITERATIONS=8`.

---

## Waterfall Analysis (`src/analysis/waterfall.py`)

Computes a Sankey/waterfall representation of funnel drop-offs, showing the volume at each layer and the split by rejection reason. Used by the Results dashboard page.

---

## Quadrant Analysis (`src/analysis/quadrant_analysis.py`)

Scenario-comparison utility that plots personas on a 2D psychographic scatter (configurable axes) and labels by adoption outcome. Supports filtering by cohort and displaying quadrant interpretation text from `src/utils/display.py — QUADRANT_INTERPRETATIONS`.

---

## Files

| File | Role |
|---|---|
| `src/analysis/causal.py` | SHAP importance + causal statement generation |
| `src/analysis/barriers.py` | Funnel barrier distribution analysis |
| `src/analysis/cohort_classifier.py` | Cohort definition and classification |
| `src/analysis/segments.py` | Segment-level adoption rate slicing |
| `src/analysis/trajectory_clustering.py` | Temporal trajectory k-means |
| `src/analysis/executive_summary.py` | LLM executive narrative |
| `src/analysis/problem_decomposition.py` | Problem-to-intervention mapping |
| `src/analysis/report_agent.py` | Agentic report builder |
| `src/analysis/waterfall.py` | Funnel waterfall / Sankey data |
| `src/analysis/quadrant_analysis.py` | 2D psychographic scatter analysis |
| `src/analysis/research_consolidator.py` | ConsolidatedReport assembly |
| `src/analysis/scenario_comparison.py` | Cross-scenario adoption comparison |
| `src/analysis/pdf_export.py` | PDF export of results report |
