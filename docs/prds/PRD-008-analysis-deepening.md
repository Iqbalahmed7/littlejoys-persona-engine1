# PRD-008: Analysis Deepening

> **Sprint**: 3
> **Priority**: P0 (Critical Path)
> **Assignees**: Cursor (segments, barriers, waterfall), Antigravity (waterfall data), Codex (causal statements)
> **Depends On**: PRD-004 (decision engine), PRD-006 (simulation runners), PRD-007 (counterfactual)
> **Status**: Ready for Development

---

## Objective

Deepen the analysis layer to produce causal insights grounded in specific variables and thresholds. The Sprint 2 modules (`segments.py`, `barriers.py`, `causal.py`) provide raw analytics — this PRD completes the pipeline with causal statement generation, funnel waterfall data, and cross-scenario comparison.

---

## Context

Sprint 2 delivered:
- `analyze_segments()` — group-by any attribute, adoption rates, avg funnel scores, top barriers
- `analyze_barriers()` — rejection distribution by stage/reason
- `compute_variable_importance()` — logistic regression + SHAP ranking
- `generate_causal_statements()` — stub (raises `NotImplementedError`)

Sprint 3 completes the analysis story.

---

## Deliverables

### D1: Causal Statement Generator (Codex)

**File**: `src/analysis/causal.py` — implement `generate_causal_statements()`

The function receives ranked `VariableImportance` objects and raw results, and produces grounded `CausalStatement` objects.

Requirements:
1. Generate 5-8 causal statements per scenario
2. Each statement must reference **specific variable names and threshold values** — no generic claims
3. Evidence strength must be derived from SHAP mean absolute values (normalized to [0, 1])
4. Segment-specific statements when a variable's impact differs significantly across segments
5. Statements must follow this structure:
   - "Personas with {variable} above {threshold} are {X}x more likely to adopt because {mechanism}"
   - "The strongest barrier for {segment} is {variable} — {N}% of rejections in this group cite {stage}"

```python
def generate_causal_statements(
    importances: list[VariableImportance],
    results: dict[str, dict[str, Any]],
    scenario_id: str | None = None,
    top_n: int = 8,
) -> list[CausalStatement]:
```

Logic:
1. Take top `top_n` variables by SHAP importance
2. For each variable, compute the adoption rate split at the median value
3. Compute lift ratio (above-median adoption / below-median adoption)
4. Generate a `CausalStatement` with the variable name, threshold (median), lift, and direction
5. For variables with SHAP > 2x the mean, check segment-level variation (city_tier, income_bracket) and add segment-specific statements if lift differs > 1.5x across segments
6. Sort by `evidence_strength` descending

### D2: Funnel Waterfall Data Pipeline (Antigravity)

**File**: `src/analysis/waterfall.py` (new file)

Compute the step-by-step funnel drop-off for visualization.

```python
class WaterfallStage(BaseModel):
    stage: str
    entered: int
    passed: int
    dropped: int
    pass_rate: float
    cumulative_pass_rate: float

def compute_funnel_waterfall(
    results: dict[str, dict[str, Any]],
) -> list[WaterfallStage]:
```

Requirements:
1. Track personas through each funnel stage: need_recognition -> awareness -> consideration -> purchase -> adopt
2. `entered` = personas who reached this stage (not filtered by previous stages)
3. `dropped` = personas rejected at this stage
4. `pass_rate` = passed / entered for this stage
5. `cumulative_pass_rate` = adopted / total_population
6. Handle edge cases: empty results, all-adopt, all-reject
7. Use `rejection_stage` from simulation results to determine where each persona dropped

### D3: Enhance Segment Analysis (Cursor)

**File**: `src/analysis/segments.py` — extend `analyze_segments()`

Add cross-scenario comparison support:

```python
class CrossScenarioSegment(BaseModel):
    segment_key: str
    segment_value: str
    scenario_results: dict[str, SegmentAnalysis]  # scenario_id -> analysis
    best_scenario: str
    worst_scenario: str

def compare_segments_across_scenarios(
    scenario_results: dict[str, dict[str, dict[str, Any]]],  # scenario_id -> persona_id -> result
    group_by: str,
) -> list[CrossScenarioSegment]:
```

Requirements:
1. Run `analyze_segments()` for each scenario
2. For each segment value, collect results across all scenarios
3. Identify best/worst scenario by adoption rate for each segment
4. Sort by maximum adoption rate spread (most interesting segments first)

### D4: Enhance Barrier Analysis (Cursor)

**File**: `src/analysis/barriers.py` — add stage-level summary

```python
class StageSummary(BaseModel):
    stage: str
    total_dropped: int
    percentage_of_rejections: float
    top_reasons: list[str]

def summarize_barrier_stages(
    results: dict[str, dict[str, Any]],
) -> list[StageSummary]:
```

Requirements:
1. Aggregate `BarrierDistribution` results by stage
2. Compute what percentage of all rejections happen at each stage
3. Include top 3 reasons per stage
4. Sort by total_dropped descending

---

## Tests

### Causal Statements (Codex)
```python
# tests/unit/test_causal.py (extend existing)
test_causal_statements_reference_specific_variables()
test_causal_statements_sorted_by_evidence_strength()
test_causal_statements_include_threshold_values()
test_causal_statements_empty_input_returns_empty()
test_segment_specific_statements_generated_when_lift_differs()
```

### Waterfall (Antigravity)
```python
# tests/unit/test_waterfall.py
test_waterfall_stages_in_funnel_order()
test_waterfall_entered_decreases_monotonically()
test_waterfall_all_adopt_shows_zero_drops()
test_waterfall_all_reject_shows_full_drop_at_first_stage()
test_waterfall_empty_input()
test_waterfall_cumulative_rate_matches_adoption()
```

### Cross-Scenario Segments (Cursor)
```python
# tests/unit/test_segments.py (extend existing)
test_cross_scenario_identifies_best_worst()
test_cross_scenario_sorts_by_spread()
test_cross_scenario_empty_input()
```

### Stage Summary (Cursor)
```python
# tests/unit/test_barriers.py (extend existing)
test_stage_summary_percentages_sum_to_100()
test_stage_summary_sorted_by_drop_count()
test_stage_summary_top_reasons_max_three()
```

---

## Acceptance Criteria

- [ ] Causal statements reference specific variable names — no generic "some factors"
- [ ] Causal statements include threshold values derived from actual data
- [ ] Evidence strength correlates with SHAP importance
- [ ] Waterfall stage counts are internally consistent (entered - dropped = passed to next)
- [ ] Cross-scenario comparison correctly identifies best/worst scenario per segment
- [ ] All tests pass
- [ ] structlog used for all logging
- [ ] No magic numbers — all thresholds in `src/constants.py`
