# Sprint 19 Brief — Antigravity
## Update Tests for Calibrated Parameters

### Context

Codex is tuning simulation parameters in Sprint 19 to hit calibration targets. Some existing tests have hard-coded numeric assertions that may break when constants change. Your job is to update those tests and add calibration-level assertions.

### Dependency
Wait for Codex to deliver and confirm calibration results before running.

### Task 1: Fix Broken Numeric Assertions

After Codex changes constants, run the full test suite:
```bash
uv run pytest tests/ -x -q
```

Any test that fails due to changed parameter values (e.g., `assert state.fatigue == pytest.approx(0.0043)`) needs its expected value updated to match the new constants.

Common patterns to check:
- `tests/unit/test_state_model.py` — tests for `apply_daily_dynamics` (fatigue growth, brand salience decay)
- `tests/unit/test_event_grammar.py` — tests for impact deltas (habit_strength, child_acceptance)
- `tests/unit/test_event_engine.py` — tests for repeat purchase thresholds

### Task 2: Add Calibration Smoke Tests

Add to `tests/integration/test_calibration.py` (new file):

```python
def test_calibration_trial_rate_in_range():
    """Trial rate by month 3 should be 15-30% for nutrimix_2_6."""
    # Run 100-persona simulation, seed=42
    # Assert 0.15 <= trial_rate <= 0.35  (slightly wider for small population)

def test_calibration_repeat_rate_in_range():
    """Repeat rate should be 35-65% for nutrimix_2_6."""
    # Use same simulation as above
    # Assert 0.35 <= repeat_rate <= 0.65  (wider band)

def test_calibration_final_active_rate():
    """Month-12 active rate should be 8-25%."""
    # Assert 0.08 <= final_active_rate <= 0.25  (wider band)

def test_calibration_churn_peak_timing():
    """Churn should peak between months 2-6."""
    # Assert 2 <= peak_month <= 6

def test_calibration_cluster_diversity():
    """Should produce at least 3 populated clusters."""
    # Assert populated_clusters >= 3
```

Use wider bands than the calibration script (which uses 200 personas). With 100 personas there's more variance, so relax bounds by ~5pp each side.

### Task 3: Update Event Grammar Impact Tests

If Codex changed `EVENT_IMPACT_HABIT_STRENGTH_USAGE_DAILY` from 0.001 to 0.0005, any test asserting exact deltas needs updating. Check:
- `test_usage_consistent_boosts_habit` — expected delta should match new constant
- `test_child_boredom_requires_fatigue` — threshold changed from 0.3 to 0.2

### Files to Create
- `tests/integration/test_calibration.py`

### Files to Modify
- `tests/unit/test_state_model.py`
- `tests/unit/test_event_grammar.py`
- `tests/unit/test_event_engine.py`
- Any other test file that breaks

### Constraints
- Use 100 personas max for calibration tests (speed)
- Total new test runtime < 30 seconds
- All 603+ previous tests must still pass
- Run `uv run ruff check .` before delivery
