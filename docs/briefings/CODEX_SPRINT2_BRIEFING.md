# CODEX — Sprint 2 Briefing

> **Role**: Senior Software Engineer (High Trust — 4.30)
> **Sprint**: 2
> **Branch**: `feat/PRD-005-scenarios` (create from `staging`)
> **Deadline**: End of Day 4

---

## YOUR ASSIGNMENTS

### Task 1: Scenario Configurations (P0)
**File**: `src/decision/scenarios.py`
**PRD**: PRD-005, D1

Implement `get_scenario(scenario_id)` and `get_all_scenarios()` with all 4 scenario configs. The Pydantic models (`ScenarioConfig`, `ProductConfig`, `MarketingConfig`) already exist — fill in the data.

See PRD-005 for all 4 configs with exact values:
- `nutrimix_2_6` — baseline, repeat purchase + LJ Pass
- `nutrimix_7_14` — expansion to older kids
- `magnesium_gummies` — new supplement, awareness challenge
- `protein_mix` — effort/routine challenge

### Task 2: Threshold Calibration (P0)
**File**: `src/decision/calibration.py`
**PRD**: PRD-005, D2

Implement `calibrate_thresholds()`:
1. Generate a test population (size=300, seed=42)
2. Run the baseline scenario (nutrimix_2_6) with current thresholds
3. Binary search: adjust thresholds until adoption rate is in [0.12, 0.18]
4. Save calibrated thresholds to `data/results/calibration.json`
5. Return `CalibrationResult`

Default starting thresholds: need=0.35, awareness=0.30, consideration=0.40, purchase=0.45.

**Note**: Calibration depends on Cursor's decision funnel. You can implement the calibration logic and test it with mock funnel results, then verify end-to-end once Cursor's code is merged.

### Task 3: Counterfactual Engine (P0)
**File**: `src/simulation/counterfactual.py`
**PRD**: PRD-007

Implement `run_counterfactual()`:
1. Run baseline scenario → baseline adoption
2. Clone scenario, apply parameter modifications
3. Run modified scenario → counterfactual adoption
4. Compare: absolute lift, relative lift %, most affected segments
5. Return `CounterfactualResult`

Also implement predefined counterfactuals for all 4 scenarios (see PRD-007 for the full list — ~15 counterfactuals total).

### Task 4: LJ Pass Modeling
**File**: extend `src/decision/scenarios.py`

Add LJ Pass configuration:
```python
class LJPassConfig(BaseModel):
    monthly_price_inr: float = 299
    discount_percent: float = 15.0
    free_trial_months: int = 1
    retention_boost: float = 0.10  # +10% repeat rate
    churn_reduction: float = 0.20  # -20% churn rate
```

Integrate with the Nutrimix 2-6 and 7-14 scenarios.

---

## CONTEXT FILES TO READ

1. `ARCHITECTURE.md` §8 (Decision Model), §9 (Simulation)
2. `src/decision/scenarios.py` — existing stubs you'll implement
3. `src/decision/calibration.py` — existing stub
4. `src/simulation/counterfactual.py` — existing stub
5. `src/generation/population.py` — PopulationGenerator you'll use for calibration
6. `docs/prds/PRD-005-scenario-config.md` — full spec
7. `docs/prds/PRD-007-counterfactual.md` — full spec

## TESTS TO WRITE

- `tests/unit/test_scenarios.py` — 5 tests
- `tests/unit/test_calibration.py` — 3 tests
- `tests/unit/test_counterfactual.py` — 6 tests

## WHEN DONE

1. `uv run ruff check .` passes
2. `uv run pytest tests/unit/ -v` — all tests pass
3. Commit: `feat(decision): scenario configs, calibration, counterfactual engine, LJ Pass`
4. Notify Tech Lead
