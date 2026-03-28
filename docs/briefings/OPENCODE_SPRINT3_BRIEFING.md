# OpenCode — Sprint 3 Briefing

> **Sprint**: 3 (Days 5-6)
> **Branch**: `feat/PRD-008-funnel-waterfall-tests` from `staging`
> **PRD**: PRD-008 (Analysis Deepening) — support tasks

---

## Your Assignments

### Task 1: Extend Segment Analysis Tests (P1)

**File**: `tests/unit/test_segments.py` — add missing test coverage

The Sprint 2 review identified gaps in test coverage. Add these tests:

```python
test_segment_funnel_score_averaging_correct()
# Create results with known funnel scores, verify avg_funnel_scores values match

test_segment_results_sorted_by_adoption_rate_descending()
# Create 3+ segments with different adoption rates, verify sort order

test_segment_top_barriers_max_three()
# Create a segment with 5+ rejection reasons, verify only top 3 returned

test_segment_non_dict_rows_skipped()
# Include a non-dict value in results, verify it doesn't crash

test_segment_none_group_value_skipped()
# Include a row where group_by value is None, verify it's excluded
```

### Task 2: Extend Barrier Analysis Tests (P1)

**File**: `tests/unit/test_barriers.py` — add missing test coverage

```python
test_barrier_percentage_relative_to_total_population()
# Verify percentage = count / total_personas (not count / total_rejections)

test_barrier_sorted_by_count_descending()
# Create barriers with known counts, verify sort order

test_barrier_handles_missing_stage_key()
# Row with rejection_reason but no rejection_stage should be skipped
```

### Task 3: Add Waterfall Integration Test (P1)

**File**: `tests/unit/test_waterfall.py` — add after Antigravity delivers the waterfall module

```python
test_waterfall_with_realistic_simulation_data()
# Generate a small population (20 personas), run through a scenario,
# pass results to compute_funnel_waterfall, verify stage counts add up
```

**Note**: This depends on Antigravity's waterfall module. If it's not ready yet, write the test with the expected import and mark it as `@pytest.mark.skip(reason="awaiting waterfall module")` — we'll un-skip when it lands.

---

## Standards Reminder

- Use `pytest` fixtures for shared test data
- Assert on specific values, not just "no crash"
- No real API calls — mock everything external
- Run before submitting:
  ```
  uv run ruff check tests/
  uv run pytest tests/unit/test_segments.py tests/unit/test_barriers.py -v
  ```

---

## Sprint 2 Feedback

Composite was **7.8/10** for your trial run — strong code quality, no bugs. The main gap was test coverage (5 tests, happy path only). Sprint 3 assignments focus on closing that gap. This is a good fit for the free-tier models — test writing doesn't require heavy reasoning.

Show me you can write thorough tests and you'll get production module assignments in Sprint 4.
