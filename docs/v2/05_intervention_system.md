# Intervention System — Counterfactual Analysis and Intervention Engine

## Overview

The intervention system takes the Core Finding (dominant hypothesis, scenario ID) and generates a structured playbook of targeted interventions. Each intervention is a parameterised modification to the baseline scenario. A counterfactual engine re-runs adoption scoring with each modification applied, computing absolute and relative adoption lift. Results are ranked and stored for display in the synthesis report.

---

## Intervention Generation

`generate_intervention_quadrant(intervention_input, scenario)` looks up the scenario-specific intervention templates from a static catalog and returns an `InterventionQuadrant` with 12 interventions (3 per quadrant).

`InterventionInput` only requires `problem_id`. The engine maps this to the scenario catalog by matching `scenario.id`.

### The Four Scenarios and Their Intervention Counts

| Scenario | Problem | Interventions |
|----------|---------|---------------|
| `nutrimix_2_6` | Repeat purchase | 12 (3+3+3+3) |
| `nutrimix_7_14` | Age expansion | 5 across quadrants |
| `magnesium_gummies` | Niche supplement growth | 4 across quadrants |
| `protein_mix` | Effort barrier | 4 across quadrants |

---

## Intervention Model

### `Intervention`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique intervention identifier, e.g. `"nm26_peds_campaign"` |
| `name` | `str` | Human-readable name, e.g. `"Pediatrician Endorsement Campaign"` |
| `description` | `str` | What this intervention does operationally |
| `scope` | `"general" or "cohort_specific"` | Applies to all personas vs. a specific cohort |
| `temporality` | `"temporal" or "non_temporal"` | Ongoing programme vs. one-time change |
| `target_cohort_id` | `str or None` | Cohort targeted (e.g. `"lapsed_user"`, `null` for general) |
| `parameter_modifications` | `dict[str, Any]` | Dot-path parameter changes, e.g. `{"marketing.pediatrician_endorsement": True}` |
| `expected_mechanism` | `str` | Causal explanation of why this should work |

### `InterventionQuadrant`

| Field | Type | Description |
|-------|------|-------------|
| `problem_id` | `str` | Problem this quadrant addresses |
| `quadrants` | `dict[str, list[Intervention]]` | Keys: `general_temporal`, `general_non_temporal`, `cohort_temporal`, `cohort_non_temporal` |

---

## The 2×2 Quadrant Map

Interventions are organised by two dimensions:

```
                        SCOPE
              General          Cohort-Specific
          ┌───────────────┬──────────────────────┐
  One-    │ Broad reach,  │ Targeted, precise,   │
  time    │ immediate     │ immediate             │
(non_     │               │                       │
temporal) │ e.g. Peds     │ e.g. Lapsed Users    │
          │ Endorsement   │ ₹100 Coupon          │
  TIMING  ├───────────────┼──────────────────────┤
  Sus-    │ Broad reach,  │ Targeted, precise,   │
  tained  │ ongoing       │ ongoing              │
(temporal)│ commitment    │ resource-intensive   │
          │               │                       │
          │ e.g. LJ Pass  │ e.g. 90-day Habit    │
          │ subscription  │ Nudge Sequence        │
          └───────────────┴──────────────────────┘
```

| Quadrant Key | Scope | Temporality | Character |
|--------------|-------|-------------|-----------|
| `general_non_temporal` | General | One-time | Broadest reach, lowest friction to deploy |
| `general_temporal` | General | Sustained | Highest reach, ongoing commitment |
| `cohort_non_temporal` | Cohort-specific | One-time | Targeted and immediate |
| `cohort_temporal` | Cohort-specific | Sustained | Most precise, highest resource intensity |

---

## Example Interventions (nutrimix_2_6)

| Quadrant | ID | Name | Key Parameter Change |
|----------|----|------|---------------------|
| general_non_temporal | `nm26_peds_campaign` | Pediatrician Endorsement Campaign | `marketing.pediatrician_endorsement: True` |
| general_non_temporal | `nm26_free_sample_flavor` | Free Sample of New Flavour | `product.taste_appeal: 0.8` |
| general_non_temporal | `nm26_discount_returning_15` | 15% Returning Customer Discount | `marketing.discount_available: 0.15` |
| general_temporal | `nm26_lj_pass_199_quarter` | LJ Pass (₹199/quarter) | `lj_pass_available: True`, `lj_pass.monthly_price_inr: 66.33` |
| general_temporal | `nm26_recipe_subscription` | Monthly Recipe Content Subscription | `product.taste_appeal: 0.82` |
| general_temporal | `nm26_brand_ambassador` | Brand Ambassador Program | `marketing.social_buzz: 0.75` |
| cohort_non_temporal | `nm26_lapsed_coupon_100` | Lapsed Users ₹100 Coupon | `marketing.discount_available: 0.17` |
| cohort_non_temporal | `nm26_first_time_starter_kit` | First-time Buyers Starter Kit | `product.effort_to_acquire: 0.2` |
| cohort_non_temporal | `nm26_current_referral_150` | Current Users Referral Reward | `marketing.social_buzz: 0.7` |
| cohort_temporal | `nm26_lapsed_day22_nudge` | Lapsed Users Day-22 Reminder | `product.taste_appeal: 0.83` |
| cohort_temporal | `nm26_current_loyalty_tiers` | Current Users Loyalty Tier Program | `lj_pass.retention_boost: 0.2` |
| cohort_temporal | `nm26_first_time_90d_nudge` | First-time Buyers 90-day Habit Nudge | `marketing.awareness_budget: 0.65` |

---

## Counterfactual Engine

`run_counterfactual(population, baseline_scenario, modifications, counterfactual_name, seed)` runs the following:

1. `_apply_modifications(baseline_scenario, modifications)` — applies dot-path changes to the scenario config, returning a modified `ScenarioConfig` and a `parameter_changes` dict.
2. `evaluate_scenario_adoption(population, baseline_scenario)` — runs the funnel for every persona under the baseline.
3. `evaluate_scenario_adoption(population, modified_scenario)` — runs the funnel for every persona under the modified scenario.
4. Computes `absolute_lift = counterfactual_adoption_rate - baseline_adoption_rate`.
5. Computes `relative_lift_percent = (absolute_lift / baseline_adoption_rate) × 100`.
6. `_segment_impacts()` breaks down the lift by demographic segments (income bracket, city tier, child age group) to identify which segments benefit most.

### CounterfactualResult Model

| Field | Type | Description |
|-------|------|-------------|
| `baseline_scenario_id` | `str` | Baseline scenario ID |
| `counterfactual_name` | `str` | Intervention name or ID |
| `parameter_changes` | `dict[str, Any]` | What changed (old_val, new_val) pairs |
| `baseline_adoption_rate` | `float` | Adoption rate without intervention |
| `counterfactual_adoption_rate` | `float` | Adoption rate with intervention |
| `absolute_lift` | `float` | `counterfactual - baseline` (percentage points) |
| `relative_lift_percent` | `float` | `(absolute_lift / baseline) × 100` |
| `most_affected_segments` | `list[SegmentImpact]` | Top N segments by lift |

**`SegmentImpact`**:
| Field | Type | Description |
|-------|------|-------------|
| `segment_attribute` | `str` | Attribute used for segmentation |
| `segment_value` | `str` | Value within that attribute |
| `baseline_adoption_rate` | `float` | Baseline rate within this segment |
| `counterfactual_adoption_rate` | `float` | Modified rate within this segment |
| `lift` | `float` | Segment-level lift |

---

## Predefined Counterfactuals (generate_default_counterfactuals)

`generate_default_counterfactuals(scenario)` generates 9–10 standard micro-tweaks for event-simulation counterfactual analysis:

| ID | Change |
|----|--------|
| `add_pediatrician` | `marketing.pediatrician_endorsement: True` |
| `add_school_partnership` | `marketing.school_partnership: True` |
| `price_minus_15` | `product.price_inr` × 0.85 |
| `price_plus_15` | `product.price_inr` × 1.15 |
| `double_awareness_budget` | `marketing.awareness_budget` × 2.0 (capped at 1.0) |
| `add_influencer_campaign` | `marketing.influencer_campaign: True` |
| `improve_taste_appeal` | `product.taste_appeal` + 0.1 (capped at 1.0) |
| `reduce_acquisition_effort` | `product.effort_to_acquire` - 0.15 (floored at 0.0) |
| `add_sports_club_partnership` | `marketing.sports_club_partnership: True` |
| `enable_lj_pass` (if not already enabled) | `lj_pass_available: True` |

---

## Dot-Path Parameter Modification

Scenario modifications use dot-path notation to modify nested fields:

| Path | Target |
|------|--------|
| `product.price_inr` | `scenario.product.price_inr` |
| `product.taste_appeal` | `scenario.product.taste_appeal` |
| `product.effort_to_acquire` | `scenario.product.effort_to_acquire` |
| `marketing.pediatrician_endorsement` | `scenario.marketing.pediatrician_endorsement` |
| `marketing.school_partnership` | `scenario.marketing.school_partnership` |
| `marketing.awareness_budget` | `scenario.marketing.awareness_budget` |
| `marketing.discount_available` | `scenario.marketing.discount_available` |
| `marketing.social_buzz` | `scenario.marketing.social_buzz` |
| `lj_pass_available` | `scenario.lj_pass_available` |
| `lj_pass.monthly_price_inr` | `scenario.lj_pass.monthly_price_inr` |
| `lj_pass.retention_boost` | `scenario.lj_pass.retention_boost` |

---

## How Intervention Results Are Stored

After "Run All Simulations" completes on Page 5, results are stored in session state under `"intervention_run"`:

```python
st.session_state["intervention_run"] = {
    "all_results": [
        {"intervention": Intervention, "result": CounterfactualResult},
        ...  # one entry per intervention
    ],
    "scenario_id": str,           # baseline scenario ID
    "baseline_cohorts": PopulationCohorts,  # cohorts from Phase 1
}
```

The Synthesis Report (Page 8) reads `intervention_run["all_results"]`, sorts by `result.absolute_lift` descending, and displays the top 5 interventions with their lift and final adoption rate.
