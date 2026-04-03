# Intervention Simulation (Phase C)

## Overview

Phase C maps research insights into actionable interventions and tests their impact through simulation. The intervention space is organised into a 2×2 quadrant grid (scope × temporality), enabling rapid comparison of broad vs targeted and immediate vs sustained strategies.

Entry points:
- `src/analysis/intervention_engine.py` — Intervention models and quadrant templates
- `src/simulation/quadrant_runner.py` — Batch simulation executor

---

## The 2×2 Quadrant Grid

```
              NON-TEMPORAL          TEMPORAL
              (one-shot changes)    (ongoing over months)
GENERAL     ┌─────────────────┬──────────────────┐
(all pop.)  │  Price cuts,    │  LJ Pass,        │
            │  trust signals, │  recipe content  │
            │  endorsements   │  subscriptions   │
            ├─────────────────┼──────────────────┤
COHORT-     │  Lapsed user    │  Loyalty tiers,  │
SPECIFIC    │  coupons,       │  habit formation │
            │  first-time     │  nudge sequences │
            │  starter kits   │                  │
            └─────────────────┴──────────────────┘
```

Quadrant keys:
- `general_non_temporal`
- `general_temporal`
- `cohort_non_temporal`
- `cohort_temporal`

---

## Intervention Model (`src/analysis/intervention_engine.py`)

```python
class Intervention(BaseModel):
    id: str
    name: str
    description: str
    scope: Literal["general", "cohort_specific"]
    temporality: Literal["temporal", "non_temporal"]
    target_cohort_id: str | None          # None for general scope
    parameter_modifications: dict[str, Any]  # dot-path overrides
    expected_mechanism: str
```

### parameter_modifications Format

Modifications use dot-path notation matching the `ScenarioConfig` structure:

| Path | Effect |
|---|---|
| `"marketing.pediatrician_endorsement": True` | Activates pediatrician trust boost |
| `"marketing.discount_available": 0.15` | Sets 15% discount signal |
| `"product.price_inr": 499.0` | Reduces product price |
| `"product.taste_appeal": 0.85` | Increases child taste acceptance |
| `"product.effort_to_acquire": 0.2` | Reduces acquisition effort |
| `"lj_pass_available": True` | Activates LJ Pass subscription |
| `"lj_pass.discount_percent": 15.0` | Sets Pass discount level |
| `"marketing.social_buzz": 0.75` | Raises organic social proof |
| `"marketing.awareness_budget": 0.65` | Increases awareness spend |
| `"marketing.school_partnership": True` | Activates school channel |

---

## Intervention Templates

Pre-defined intervention templates exist for all 4 scenarios. Example for `nutrimix_2_6`:

### general_non_temporal (3 interventions)
| ID | Name | Mechanism |
|---|---|---|
| `nm26_discount_returning_15` | 15% Returning Customer Discount | Reduces price friction at reorder |
| `nm26_free_sample_flavor` | Free Sample of New Flavour | Raises child acceptance |
| `nm26_peds_campaign` | Pediatrician Endorsement Campaign | Improves trust, reduces post-trial drop-off |

### general_temporal (3 interventions)
| ID | Name | Mechanism |
|---|---|---|
| `nm26_lj_pass_199_quarter` | LJ Pass (₹199/quarter) | Commitment + lower friction |
| `nm26_recipe_subscription` | Monthly Recipe Content Subscription | Mitigates taste fatigue |
| `nm26_brand_ambassador` | Brand Ambassador Program | Sustains salience and social proof |

### cohort_non_temporal (3 interventions — lapsed, first-time, current users)
| ID | Name | Target Cohort |
|---|---|---|
| `nm26_lapsed_coupon_100` | 'We Miss You' ₹100 Coupon | lapsed_user |
| `nm26_first_time_starter_kit` | Starter Kit Bundle Discount | first_time_buyer |
| `nm26_current_referral_150` | Referral Reward (₹150) | current_user |

### cohort_temporal (3 interventions)
| ID | Name | Target Cohort |
|---|---|---|
| `nm26_lapsed_day22_nudge` | Day-22 Reminder + Flavour Rotation | lapsed_user |
| `nm26_current_loyalty_tiers` | Loyalty Tier Program (Bronze→Silver→Gold) | current_user |
| `nm26_first_time_90d_nudge` | 90-day Habit Formation Nudge Sequence | first_time_buyer |

---

## Quadrant Runner (`src/simulation/quadrant_runner.py`)

### InterventionRunResult

```python
class InterventionRunResult(BaseModel):
    intervention_id: str
    intervention_name: str
    scope: str
    temporality: str
    target_cohort_id: str | None
    adoption_rate: float
    adoption_count: int
    population_tested: int
    final_active_rate: float | None    # populated for temporal runs
    total_revenue: float | None        # populated for temporal runs
    monthly_snapshots: list[dict] | None
    rejection_distribution: dict[str, int]
```

### QuadrantRunResult

```python
class QuadrantRunResult(BaseModel):
    scenario_id: str
    baseline_adoption_rate: float
    baseline_active_rate: float | None
    baseline_revenue: float | None
    results: list[InterventionRunResult]
    duration_seconds: float
    population_size: int
    seed: int
```

### Execution Flow

For each intervention in `InterventionQuadrant.quadrants`:

1. **Apply scenario modifications** — `apply_scenario_modifications(base_scenario, modifications)` produces a modified `ScenarioConfig`.
2. **Filter population** (cohort-specific only) — `population.filter_by_cohort(target_cohort_id)` returns a sub-population.
3. **Run static simulation** — `evaluate_scenario_adoption(sub_pop, modified_scenario)` returns adoption rate and count.
4. **Run temporal simulation** (if `temporality=="temporal"` and `scenario.mode=="temporal"`) — `run_event_simulation(sub_pop, modified_scenario, duration_days)` returns final active rate, revenue, and monthly snapshots.

---

## Lift Calculation

Lift is always computed relative to the **baseline** for the same population scope:

```
adoption_lift_pp  = intervention_adoption_rate - baseline_adoption_rate
adoption_lift_pct = adoption_lift_pp / baseline_adoption_rate × 100
```

For temporal interventions, `final_active_rate` lift uses the baseline temporal simulation's active rate at the same duration.

Interventions are ranked by `adoption_lift_pct` within each quadrant to identify the highest-leverage levers.

---

## Counterfactual Engine (`src/simulation/counterfactual.py`)

`apply_scenario_modifications(scenario, modifications)` accepts dot-path keys and applies them recursively:

```python
apply_scenario_modifications(scenario, {
    "marketing.pediatrician_endorsement": True,
    "product.price_inr": 499.0,
    "lj_pass_available": True,
    "lj_pass.discount_percent": 20.0
})
```

The function returns a deep copy of the scenario with the specified fields overridden, leaving all other fields intact.

---

## Auto-Variant Explorer (`src/simulation/auto_variants.py`)

An automated sweep that generates up to 2000 scenario variants by sampling from a configurable parameter grid (price range ₹199–₹999 in ₹100 steps, trust signals, channel mix weights). Identifies "missed insights" — parameter combinations with adoption lift > 5% that are not represented in the pre-defined intervention templates.

---

## Temporal Simulation (`src/simulation/temporal.py` and `event_engine.py`)

For `mode="temporal"` scenarios, the simulation runs month-by-month:
- Each month, awareness grows by `TEMPORAL_MONTHLY_AWARENESS_INCREMENT = 0.02`
- WOM transmission: adopters spread awareness to 3–5 contacts per month at `DEFAULT_WOM_TRANSMISSION_RATE = 0.15`
- LJ Pass uptake: 20% of active adopters convert to Pass each month
- Repeat probability is modelled by `src/decision/repeat.py` with habit formation and LJ Pass multipliers

The event engine (`src/simulation/event_engine.py`) runs a finer-grained daily simulation with stochastic event firing (ad exposures, doctor recommendations, competitor discounts, child reactions, pack depletion reminders).

---

## Files

| File | Role |
|---|---|
| `src/analysis/intervention_engine.py` | Intervention models, templates, SimulationRunConfig |
| `src/simulation/quadrant_runner.py` | Batch intervention runner, QuadrantRunResult |
| `src/simulation/counterfactual.py` | apply_scenario_modifications() |
| `src/simulation/static.py` | Static (point-in-time) simulation runner |
| `src/simulation/temporal.py` | Month-by-month temporal simulation |
| `src/simulation/event_engine.py` | Daily stochastic event engine |
| `src/simulation/auto_variants.py` | Automated parameter sweep explorer |
| `src/simulation/batch.py` | Batch multi-scenario runner |
| `src/simulation/consolidation.py` | Aggregation across batch runs |
| `src/simulation/state_model.py` | Per-persona simulation state management |
| `src/simulation/wom.py` | Word-of-mouth propagation model |
