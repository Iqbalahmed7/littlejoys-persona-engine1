# Sprint 18 Brief — Codex (GPT-5.4 — Upgrade for this sprint)
## Repeat Purchase Fix + Counterfactual Engine + Calibration Script

### Context

Sprint 17 built the day-level event engine, but the simulation is BROKEN:
- **0 repeat purchases** across 200 personas in 12 months
- **100% churn** — every adopter eventually drops off
- **Root cause**: `habit_strength` threshold for reorder is 0.2, but first purchase only gives +0.08. Impossible to reorder.
- **Contributing**: No positive events fire (child_positive_reaction, usage_consistent), so child_acceptance only declines and fatigue only grows.

This sprint has 3 tasks: fix the repeat logic, build a counterfactual engine, and write a calibration diagnostic.

### Task 1: Fix Repeat Purchase Logic (`src/simulation/event_engine.py`)

**Problem**: In `evaluate_decision()`, the repeat purchase conditions are too strict for first-time reorderers:

```python
can_reorder = (
    state.reorder_urgency > 0.4      # ✓ pack_finished sets this to 0.6
    and state.habit_strength > 0.2    # ✗ IMPOSSIBLE after 1 purchase (only 0.08)
    and state.child_acceptance > 0.3  # ✓ usually starts ~0.6
    and state.perceived_value > state.price_salience  # ✓ usually true
    and state.fatigue < 0.6           # ✓ initially
    and state.discretionary_budget > (price_ratio * 0.25)  # ✓ usually
)
```

**Fix**: Replace the flat `habit_strength > 0.2` check with a progressive threshold:

```python
# First reorder is easier (habit builds with experience)
habit_threshold = 0.05 if state.total_purchases < 3 else 0.2
can_reorder = (
    state.reorder_urgency > 0.4
    and state.habit_strength > habit_threshold
    and state.child_acceptance > 0.3
    and state.perceived_value > state.price_salience
    and state.fatigue < 0.6
    and state.discretionary_budget > (price_ratio * 0.25)
)
```

Also update `apply_decision` to give a larger habit boost for the first purchase:

```python
if decision in {"purchase", "reorder", "subscribe"}:
    ...
    # First purchase: bigger habit kick to bootstrap the reorder cycle
    habit_boost = 0.15 if state.total_purchases == 0 else 0.08
    state.habit_strength = min(1.0, state.habit_strength + habit_boost)
    ...
```

Wait — `total_purchases` has already been incremented at this point (line above). Adjust:

```python
if decision in {"purchase", "reorder", "subscribe"}:
    state.total_purchases += 1
    ...
    habit_boost = 0.15 if state.total_purchases <= 1 else 0.08
    state.habit_strength = min(1.0, state.habit_strength + habit_boost)
```

**Also fix the infinite pack_finished loop**: When the persona delays after pack_finished, `current_pack_day` keeps incrementing and pack_finished fires EVERY day forever. Add pack reset on extended overstay:

In `apply_daily_dynamics` in `src/simulation/state_model.py`:

```python
# If pack is overstayed by more than 10 days and persona hasn't reordered,
# they've effectively run out — reset pack tracking
if state.is_active and state.current_pack_day > state.pack_duration + 10:
    state.current_pack_day = 0  # No longer has a pack
    state.reorder_urgency = max(state.reorder_urgency, 0.8)  # High urgency
```

### Task 2: Counterfactual Engine (`src/simulation/counterfactual.py` — NEW)

Build a module that re-runs the event simulation with parameter perturbations to measure causal lift.

```python
class CounterfactualScenario(BaseModel):
    """One perturbation to test."""
    id: str                              # e.g. "add_pediatrician"
    label: str                           # "Add pediatrician endorsement"
    parameter_changes: dict[str, object] # {"marketing.pediatrician_endorsement": True}

class CounterfactualResult(BaseModel):
    """Result of one counterfactual comparison."""
    scenario_id: str
    label: str
    baseline_active_rate: float
    counterfactual_active_rate: float
    lift: float                          # counterfactual - baseline
    lift_pct: float                      # (cf - baseline) / baseline * 100
    baseline_revenue: float
    counterfactual_revenue: float
    revenue_lift: float
    parameter_changes: dict[str, object]

class CounterfactualReport(BaseModel):
    """Full counterfactual analysis."""
    baseline_scenario_id: str
    results: list[CounterfactualResult]
    top_intervention: str                # ID of best-performing scenario
    population_size: int
    duration_days: int

def generate_default_counterfactuals(scenario: ScenarioConfig) -> list[CounterfactualScenario]:
    """Generate 8-12 standard business counterfactuals."""
    # Examples:
    # 1. Add pediatrician endorsement
    # 2. Add school partnership
    # 3. Price -15%
    # 4. Price +15%
    # 5. Double awareness budget
    # 6. Add influencer campaign
    # 7. Enable LJ Pass (if not already)
    # 8. Improve taste appeal by 0.1
    # 9. Reduce effort to acquire by 0.15
    # 10. Add sports club partnership

def run_counterfactual_analysis(
    population: Population,
    baseline_scenario: ScenarioConfig,
    counterfactuals: list[CounterfactualScenario],
    duration_days: int = 360,
    seed: int = 42,
    progress_callback: Callable[[float], None] | None = None,
) -> CounterfactualReport:
    """Run baseline + all counterfactual scenarios, compute lift."""
```

**Implementation**:
1. Run baseline event simulation once
2. For each counterfactual: deep-copy scenario, apply parameter changes, run event simulation
3. Compare final_active_rate and total_revenue_estimate vs baseline
4. Sort by lift descending
5. Return ranked results

**Parameter change application**: Use `scenario.model_copy(deep=True)` then set nested fields. For dotted paths like `"marketing.pediatrician_endorsement"`, split on "." and setattr.

### Task 3: Calibration Diagnostic (`scripts/calibrate_event_params.py` — NEW)

A standalone script that runs the simulation and reports key health metrics:

```python
"""
Run: uv run python scripts/calibrate_event_params.py

Outputs a diagnostic report showing whether the simulation produces
realistic behavioural patterns.
"""

# Target ranges (what a healthy simulation should produce):
# - Trial rate by month 3: 15-30%
# - Repeat rate (of adopters): 40-60%
# - Month-12 active rate: 10-20%
# - Mean purchases per adopter: 3-6
# - At least 4 of 6 behavioural clusters populated
# - Churn peak: months 3-5 (not month 1)
# - Revenue per adopter: ₹2000-4000

# Steps:
# 1. Generate 200-persona population (seed=42)
# 2. Run event simulation (360 days, seed=42)
# 3. Compute all metrics above
# 4. Print PASS/FAIL for each metric with actual vs target
# 5. Suggest parameter adjustments if metrics are off
```

This script should NOT be part of the test suite — it's a development tool.

### Files to Create
- `src/simulation/counterfactual.py`
- `scripts/calibrate_event_params.py`

### Files to Modify
- `src/simulation/event_engine.py` (fix repeat logic, habit boost)
- `src/simulation/state_model.py` (fix pack overstay)

### Constraints
- All existing tests must pass: `uv run pytest tests/ -x -q`
- Run `uv run ruff check .` before delivery
- Counterfactual engine must be deterministic (same seed → same results)
- Do NOT modify `event_grammar.py` (Goose is handling that)

### Execution Order
Goose (grammar) runs in PARALLEL with your work. Your fixes to event_engine.py and state_model.py are independent of Goose's changes to event_grammar.py.
