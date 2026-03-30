# Sprint 19 Brief — Codex
## Calibration: Tune Event Parameters for Face Validity

### Context

The event simulation engine works but produces unrealistic numbers. Trial rate is 48% (target 15–30%), repeat rate is 94% (target 40–60%), month-12 active is 26% (target 10–20%). Your job is to tune parameters until all 7 calibration metrics pass.

### Root Causes

1. **Trial too high:** `brand_salience` initialises at raw `awareness_level` (0.6). Almost every persona immediately crosses the awareness threshold (~0.25).
2. **Repeat too high:** `usage_consistent` fires 80% of days, pumping `habit_strength`. Fatigue grows at only 0.0043/day — takes 140 days to reach 0.6 churn threshold. Child boredom is rare (1%/day, needs fatigue > 0.3).
3. **Active rate too high:** Downstream consequence of (1) and (2).

### Changes to Apply

#### File: `src/constants.py`

| Constant | Old | New | Rationale |
|----------|-----|-----|-----------|
| `EVENT_FATIGUE_GROWTH_PER_DAY` | 0.0043 | 0.008 | Fatigue reaches 0.55 in ~69 days (was ~128) |
| `EVENT_IMPACT_HABIT_STRENGTH_USAGE_DAILY` | 0.001 | 0.0005 | Halves daily habit micro-boost |
| `EVENT_PROB_CHILD_BOREDOM_BASE` | 0.01 | 0.025 | Boredom 2.5x more likely |
| `EVENT_FATIGUE_THRESHOLD_BOREDOM` | 0.3 | 0.2 | Boredom triggers earlier |
| `EVENT_PROB_USAGE_DROP_BASE` | 0.02 | 0.04 | Usage drop 2x more likely |
| `EVENT_BRAND_SALIENCE_DECAY_PER_DAY` | 0.02 | 0.025 | Faster awareness fade |

#### File: `src/simulation/state_model.py` — `initialize_state()`

```python
# Dampen initial brand_salience (was: awareness_level unscaled)
brand_salience=_clip(scenario.marketing.awareness_level * 0.45),

# Lower initial child_acceptance (was: taste_appeal * 1.0 * ...)
child_acceptance=_clip(
    scenario.product.taste_appeal * 0.65 * (1.0 - (0.3 * float(child_veto)))
),
```

#### File: `src/simulation/event_engine.py` — `evaluate_decision()`

```python
# Tighten repeat conditions (inside can_reorder block)
and state.child_acceptance > 0.35      # was 0.3
and state.fatigue < 0.55               # was 0.6
```

### Iteration Protocol

1. Apply all changes above
2. Run: `.venv/bin/python scripts/calibrate_event_params.py`
3. Read the output — check all 7 metrics
4. If any metric FAILs, make a targeted adjustment:
   - Trial still too high? Lower `awareness_level * 0.45` multiplier to 0.35
   - Repeat still too high? Raise `EVENT_FATIGUE_GROWTH_PER_DAY` to 0.010
   - Active rate still too high? Lower `fatigue < 0.55` to `fatigue < 0.50`
   - Purchases/adopter dropped below 3.0? Lower `EVENT_FATIGUE_GROWTH_PER_DAY` slightly
   - Churn peak shifted outside 3–5? Adjust fatigue growth rate
5. Re-run calibration
6. Maximum 3 iterations. Document each iteration's results.

### Target Ranges (all 7 must PASS)

```
Trial rate by month 3:         0.15 – 0.30
Repeat rate of adopters:       0.40 – 0.60
Month-12 active rate:          0.10 – 0.20
Mean purchases per adopter:    3.0  – 6.0
Revenue per adopter (INR):     2000 – 4000
Behaviour clusters populated:  >= 4
Churn peak month:              3 – 5
```

### Verification

After final iteration:
```bash
uv run python scripts/calibrate_event_params.py   # all 7 PASS
uv run pytest tests/ -x -q                         # all tests pass
uv run ruff check .                                # clean
```

### Deliverable

Report each iteration's calibration output, final parameter values, and test results. If any metric still FAILs after 3 iterations, document what was tried and what the closest values were.

### Files to Modify
- `src/constants.py`
- `src/simulation/state_model.py`
- `src/simulation/event_engine.py`

### Constraints
- Do NOT modify any other files
- Do NOT change the calibration script itself
- Do NOT change model structure (only numeric constants and thresholds)
- All existing tests must still pass (some numeric assertions may need updating — flag them)
