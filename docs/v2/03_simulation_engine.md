# Simulation Engine — Static and Temporal Modes

## Overview

The simulation engine has two modes: **static** (single-pass funnel) and **temporal** (multi-month event loop with repeat purchase, WOM, and churn). Both modes share the same underlying purchase funnel (`run_funnel`). The temporal mode additionally models habituation, satisfaction decay, and word-of-mouth propagation. Cohort classification runs after the temporal simulation to assign each persona to one of five behavioral cohorts.

---

## Static Simulation (Mode A)

### How It Works

`run_static_simulation(population, scenario, thresholds, seed)` passes every persona through `run_funnel()` once. The funnel is a four-stage decision model:

1. **Need Recognition** — Does the persona recognise a child nutrition gap?
2. **Awareness** — Has the persona been exposed to this product?
3. **Consideration** — Does the persona actively evaluate the product?
4. **Purchase** — Does the persona convert?

Each stage computes a score from persona attributes and scenario parameters, then compares it against a threshold. If the score is below threshold, the persona exits with a `rejection_stage` label.

### Decision Tree

```
                    ┌───────────────────────┐
                    │       Persona          │
                    └────────────┬──────────┘
                                 │
                    ┌────────────▼──────────────┐
                    │  Need Recognition stage    │
                    │  score = f(health_anxiety, │
                    │   nutrition_gap_awareness, │
                    │   child_health_proactivity)│
                    └────────────┬──────────────┘
                   score < threshold │  score >= threshold
                         │           │
                 reject: need_recognition  │
                                    ┌──────▼──────────────┐
                                    │  Awareness stage     │
                                    │  score = f(awareness │
                                    │  budget, social,     │
                                    │  WOM boost)          │
                                    └──────┬──────────────┘
                        score < threshold  │  score >= threshold
                              │            │
                  reject: awareness   ┌────▼────────────────┐
                                      │  Consideration stage│
                                      │  score = f(trust,   │
                                      │  research tendency, │
                                      │  indie_brand_open)  │
                                      └────┬───────────────┘
                        score < threshold  │  score >= threshold
                              │            │
                 reject: consideration ┌───▼────────────────┐
                                       │  Purchase stage     │
                                       │  score = f(price,  │
                                       │  budget_conscious, │
                                       │  effort, value_perc)│
                                       └───┬───────────────┘
                       score < threshold   │  score >= threshold
                             │             │
                    reject: purchase    outcome: "adopt"
```

### StaticSimulationResult

| Field | Type | Description |
|-------|------|-------------|
| `scenario_id` | `str` | ID of the scenario simulated |
| `population_size` | `int` | Total number of personas |
| `adoption_count` | `int` | Number of personas who adopted |
| `adoption_rate` | `float` | `adoption_count / population_size` |
| `results_by_persona` | `dict[str, dict]` | Per-persona funnel decision dict |
| `rejection_distribution` | `dict[str, int]` | Count of rejections per stage |
| `random_seed` | `int` | Seed recorded for reproducibility |

---

## Temporal Simulation (Mode B)

### How It Works

`run_temporal_simulation(population, scenario, thresholds, months, seed)` runs a month-by-month loop for `months` iterations (default 12). Each month:

1. **Awareness Growth** — Every persona's `awareness_boost` increases by `TEMPORAL_MONTHLY_AWARENESS_INCREMENT × scenario.marketing.awareness_budget`, capped at 1.0.

2. **WOM Propagation** — `propagate_wom()` identifies currently-active personas and propagates awareness boosts to their social network neighbours. Transmission rate is `DEFAULT_WOM_TRANSMISSION_RATE`. Each receiving persona's `awareness_boost` increases by up to 0.4.

3. **New Adoption** — Non-adopter personas run through `run_funnel()` with their accumulated `awareness_boost`. Those who pass all four stages are marked as `ever_adopted = True`, `active = True`. Their first `PurchaseEvent` is appended to `persona.purchase_history`.

4. **Repeat Purchase and Churn** — For each already-active persona:
   - `compute_satisfaction(persona, scenario.product, month)` scores satisfaction
   - `compute_churn_probability(persona, satisfaction_trajectory, has_lj_pass)` gives a churn probability
   - If churn roll succeeds, `active = False`, `consecutive_months = 0`
   - Otherwise, `compute_repeat_probability(persona, satisfaction, consecutive_months, has_lj_pass)` gives a repeat purchase probability
   - If repeat roll succeeds, a `PurchaseEvent` with `trigger="repeat_purchase"` is appended

5. **Snapshot** — A `MonthlySnapshot` is recorded: new_adopters, repeat_purchasers, churned, total_active, cumulative_adopters, awareness_level_mean, lj_pass_holders.

### Temporal Simulation Loop Diagram

```
FOR month IN range(1, months+1):
│
├─ [AWARENESS GROWTH]
│   awareness_boost += monthly_increment × marketing.awareness_budget
│   (capped at 1.0 for all personas)
│
├─ [WOM PROPAGATION]
│   active_ids → propagate_wom() → deltas → awareness_boost +=
│
├─ [NEW ADOPTION PASS]
│   FOR each never-adopted persona:
│   │   run_funnel(persona, scenario, awareness_boost=st.awareness_boost)
│   │   if "adopt": mark active, append PurchaseEvent("funnel_adopt")
│
├─ [REPEAT PURCHASE + CHURN PASS]
│   FOR each active persona:
│   │   sat = compute_satisfaction(persona, product, month)
│   │   churn_p = compute_churn_probability(sat_trajectory, has_lj_pass)
│   │   if random() < churn_p: active=False, consecutive_months=0
│   │   else:
│   │       repeat_p = compute_repeat_probability(sat, consecutive_months, has_lj_pass)
│   │       if random() < repeat_p: append PurchaseEvent("repeat_purchase")
│   │       consecutive_months += 1
│
└─ [SNAPSHOT]
    MonthlySnapshot(month, new_adopters, repeat_purchasers,
                    churned, total_active, cumulative_adopters,
                    awareness_level_mean, lj_pass_holders)
```

### TemporalSimulationResult

| Field | Type | Description |
|-------|------|-------------|
| `scenario_id` | `str` | Scenario ID |
| `months` | `int` | Number of months simulated |
| `population_size` | `int` | Total personas |
| `monthly_snapshots` | `list[MonthlySnapshot]` | Per-month state |
| `final_adoption_rate` | `float` | Cumulative adopters / population |
| `final_active_rate` | `float` | Active buyers / population at end |
| `total_revenue_estimate` | `float` | Sum of all purchase events × price |
| `random_seed` | `int` | Seed used |

### MonthlySnapshot Fields

| Field | Type | Description |
|-------|------|-------------|
| `month` | `int` | Month number (1-indexed) |
| `new_adopters` | `int` | First purchases this month |
| `repeat_purchasers` | `int` | Repeat purchases this month |
| `churned` | `int` | Personas who churned this month |
| `total_active` | `int` | Currently active buyers |
| `cumulative_adopters` | `int` | All personas ever adopted |
| `awareness_level_mean` | `float` | Mean awareness score across population |
| `lj_pass_holders` | `int` | Personas assigned an LJ Pass |

---

## Cohort Classifier

### What It Does

`classify_population(population, scenario, seed)` runs both static and event simulations, then assigns each persona to one of five research cohorts based on their behavioral trajectory:

| Cohort ID | Name | Classification Logic |
|-----------|------|---------------------|
| `never_aware` | Never Aware | Rejected at `need_recognition` or `awareness` stage |
| `aware_not_tried` | Aware But Not Tried | Rejected at `consideration` or `purchase` stage |
| `first_time_buyer` | First-Time Buyer | Adopted once, either lapsed after 1 purchase or still nominally active but never repeated |
| `current_user` | Current User | Active at simulation end with ≥ 2 purchases |
| `lapsed_user` | Lapsed User | Ever adopted with ≥ 2 purchases, but churned before simulation end |

### Classification Logic

1. Static funnel runs first. Non-adopters are immediately assigned to `never_aware` or `aware_not_tried` based on their `rejection_stage`.

2. For personas who adopted in the static pass, an event simulation runs for `scenario.months × 30` days. Each persona's `PersonaTrajectory` is inspected:
   - `is_active AND total_purchases >= 2` → `current_user`
   - `is_active AND total_purchases <= 1` → `first_time_buyer`
   - `not is_active AND total_purchases <= 1` → `first_time_buyer`
   - `not is_active AND total_purchases >= 2` → `lapsed_user`

3. `persona.product_relationship` is updated to the assigned cohort ID.

### PopulationCohorts Model

| Field | Type | Description |
|-------|------|-------------|
| `scenario_id` | `str` | Scenario the classification was run for |
| `cohorts` | `dict[str, list[str]]` | Maps cohort ID → list of persona IDs |
| `classifications` | `list[CohortClassification]` | Per-persona verdict with reason |
| `summary` | `dict[str, int]` | Maps cohort ID → count |

### CohortClassification Model

| Field | Type | Description |
|-------|------|-------------|
| `persona_id` | `str` | Persona ID |
| `cohort_id` | `str` | Assigned cohort (e.g. `"current_user"`) |
| `cohort_name` | `str` | Human-readable cohort name |
| `classification_reason` | `str` | Natural language explanation (e.g. `"Active repeat buyer (3 purchases, still active at end)"`) |
