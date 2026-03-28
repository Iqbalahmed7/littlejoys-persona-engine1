# Cursor — Sprint 3 Briefing

> **Sprint**: 3 (Days 5-6)
> **Branch**: `feat/PRD-008-analysis` from `staging`
> **PRD**: PRD-008 (Analysis Deepening)

---

## Your Assignments

### Task 1: Cross-Scenario Segment Comparison (P0)

**File**: `src/analysis/segments.py` — extend with new function

Add `CrossScenarioSegment` model and `compare_segments_across_scenarios()` function.

Input: dict of scenario_id -> persona_id -> result dict, plus a `group_by` attribute.
Output: list of `CrossScenarioSegment` sorted by adoption rate spread (most interesting first).

Logic:
1. Call existing `analyze_segments()` for each scenario's results
2. For each unique segment value, collect the `SegmentAnalysis` from every scenario
3. Identify best/worst scenario by adoption rate
4. Sort by `max_adoption - min_adoption` descending

Tests to add in `tests/unit/test_segments.py`:
- `test_cross_scenario_identifies_best_worst`
- `test_cross_scenario_sorts_by_spread`
- `test_cross_scenario_empty_input`

### Task 2: Barrier Stage Summary (P0)

**File**: `src/analysis/barriers.py` — extend with new function

Add `StageSummary` model and `summarize_barrier_stages()` function.

Input: dict of persona_id -> result dict.
Output: list of `StageSummary` sorted by total_dropped descending.

Logic:
1. Call existing `analyze_barriers()` to get per-reason distributions
2. Group by stage, sum counts
3. Compute percentage_of_rejections for each stage (out of total rejections, not total population)
4. Include top 3 reasons per stage

Tests to add in `tests/unit/test_barriers.py`:
- `test_stage_summary_percentages_sum_to_100`
- `test_stage_summary_sorted_by_drop_count`
- `test_stage_summary_top_reasons_max_three`

---

## Standards Reminder

- All models: Pydantic `BaseModel` with `ConfigDict(extra="forbid")`
- Logging: `structlog.get_logger(__name__)` — no bare `logging` or `print`
- No magic numbers — put thresholds in `src/constants.py`
- Type hints on all function signatures
- Run before submitting:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest tests/unit/test_segments.py tests/unit/test_barriers.py -v
  ```

---

## Sprint 2 Feedback

Your composite was **7.2/10** — brought down by the dead-code rejection labels and skipped tests. Both were caught in review and fixed promptly. For Sprint 3:
- No skipped tests
- No duplicate/placeholder logic — if a branch exists, it must do something distinct
- Extract all numeric thresholds to constants on first pass, not after review
