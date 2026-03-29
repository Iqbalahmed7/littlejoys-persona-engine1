# Canonical State Model V1
## Dynamic Variables for Temporal Persona Simulation

> **Author**: Technical Lead (Claude Opus)
> **Date**: 2026-03-29
> **Status**: Design — Implementation planned for Sprint 17
> **Reference**: Architecture_Change_Re-do_V1.md, Section 8 Item 1

---

## Overview

Each persona in the temporal simulation carries a **mutable state** that evolves over time. The identity attributes (200+ from taxonomy) are immutable. The state model captures what changes as the persona experiences events, makes purchases, and develops habits.

This model feeds into the rule-based decision engine. Decisions are made by comparing dynamic state values against persona-specific thresholds derived from immutable identity attributes.

---

## State Variables (V1)

| # | Variable | Type | Range | Initial Value | Update Triggers |
|---|----------|------|-------|---------------|----------------|
| 1 | `trust` | float | [0, 1] | `persona.health.medical_authority_trust * 0.3 + persona.psychology.social_proof_bias * 0.2` | +on doctor_recommendation, +on positive_peer_wom, -on negative_experience, +on consistent_usage |
| 2 | `habit_strength` | float | [0, 1] | 0.0 | +0.08/month of consecutive purchase, -0.15 on missed reorder window, decay 0.05/month when inactive |
| 3 | `child_acceptance` | float | [0, 1] | `scenario.product.taste_appeal * (1 - 0.3 * persona.demographics.child_taste_veto_power)` | -on child_rejection, -on child_boredom (gradual), +on child_positive_reaction, +on recipe_variation |
| 4 | `price_salience` | float | [0, 1] | `persona.daily_routine.budget_consciousness * 0.5` | +on budget_pressure_increase, -on payday_relief, +on competitor_discount, -on perceived_value increase |
| 5 | `reorder_urgency` | float | [0, 1] | 0.0 | +as pack depletion approaches (linear ramp last 5 days), reset to 0.0 on purchase, +on reminder event |
| 6 | `fatigue` | float | [0, 1] | 0.0 | +0.03/week of consistent usage (taste monotony), -on recipe_variation, -on new_flavor_event, cap at 0.8 |
| 7 | `perceived_value` | float | [0, 1] | `0.5 * scenario.product.taste_appeal + 0.3 * persona.education_learning.science_literacy + 0.2 * persona.health.nutrition_gap_awareness` | +on visible_child_health_improvement, -on price_increase, +on doctor_recommendation, -on fatigue > 0.5 |
| 8 | `brand_salience` | float | [0, 1] | 0.0 (pre-awareness), jumps on first touchpoint | +on ad_exposure, +on influencer_exposure, +on peer_mention, decay 0.02/day without touchpoint |
| 9 | `effort_friction` | float | [0, 1] | `persona.daily_routine.effort_to_acquire * (1 - persona.daily_routine.online_shopping_comfort)` | -on subscription_setup (LJ Pass), -on quick_commerce_availability, +on stockout_experience |
| 10 | `discretionary_budget` | float | [0, 1] | `1.0 - persona.daily_routine.budget_consciousness` | -on budget_pressure_increase, +on payday_relief, seasonal variation (lower in school fee months) |

---

## Decision Rules (V1)

### First Purchase Decision
```
PURCHASE if:
    brand_salience > persona.awareness_threshold
    AND trust > persona.trust_threshold
    AND perceived_value > price_salience
    AND discretionary_budget > (product.price_inr / persona.price_reference_point) * 0.3
    AND effort_friction < 0.7
```

### Repeat Purchase Decision (evaluated at pack_finished event)
```
REORDER if:
    reorder_urgency > 0.4
    AND habit_strength > 0.2
    AND child_acceptance > 0.3
    AND perceived_value > price_salience
    AND fatigue < 0.6
    AND discretionary_budget > (product.price_inr / persona.price_reference_point) * 0.25

SWITCH_TO_COMPETITOR if:
    NOT REORDER
    AND price_salience > 0.6
    AND competitor_discount event active
    AND trust < 0.5

CHURN if:
    NOT REORDER AND NOT SWITCH
    AND (child_acceptance < 0.2 OR fatigue > 0.7 OR trust < 0.3)

DELAY if:
    NOT REORDER AND NOT SWITCH AND NOT CHURN
    (will re-evaluate next cycle)
```

### LJ Pass Subscription Decision
```
SUBSCRIBE if:
    habit_strength > 0.5
    AND reorder_urgency > 0.3
    AND persona.daily_routine.subscription_comfort > 0.5
    AND discretionary_budget > (pass.monthly_fee / persona.price_reference_point) * 0.2
```

---

## Threshold Derivation from Identity

Each persona's decision thresholds are derived from their immutable identity attributes:

```python
awareness_threshold = 0.25 - 0.1 * persona.media.ad_receptivity
trust_threshold = 0.4 + 0.2 * (1 - persona.psychology.risk_tolerance)
price_reference_point = persona.daily_routine.price_reference_point  # already exists
```

---

## State Initialization

At simulation start (day 0):
1. All personas start with `brand_salience = 0` (unaware)
2. `trust`, `child_acceptance`, `perceived_value` are initialized from identity attributes (see table above)
3. `habit_strength`, `reorder_urgency`, `fatigue` start at 0
4. `price_salience` and `discretionary_budget` derived from economic attributes
5. `effort_friction` derived from shopping behavior attributes

---

## State Update Protocol

At each time step (daily in V1):
1. **Fire deterministic events** (pack_finished on known day, payday on known day)
2. **Fire stochastic events** (ad exposure with probability, child reaction with probability)
3. **Update state variables** based on event impacts (see Update Triggers column)
4. **Apply natural decay/growth** (brand_salience decays, fatigue grows, habit decays when inactive)
5. **Evaluate decision rules** if a decision point is reached (pack_finished, reminder, etc.)
6. **Log decision** with rationale (which variables were dominant in the decision)

---

## Relationship to Existing Code

| Existing Module | Relationship to State Model |
|---|---|
| `src/decision/funnel.py` | Computes initial purchase scores — will be replaced by state-based first-purchase decision |
| `src/decision/repeat.py` | `compute_satisfaction()` maps to `perceived_value` + `child_acceptance`. `compute_repeat_probability()` maps to `habit_strength` + `reorder_urgency`. `compute_churn_probability()` maps to `fatigue` + `child_acceptance` decline. |
| `src/simulation/temporal.py` | `_PersonaTemporalState` will be replaced by the full 10-variable state model. Monthly loop will be replaced by daily loop. |
| `src/simulation/wom.py` | WOM propagation updates `brand_salience` and `trust` for receivers. |
| `src/taxonomy/schema.py` | Identity attributes used for threshold derivation and state initialization. No changes needed. |

---

## Implementation Notes

- All state variables are `float` in `[0, 1]` for consistency
- State is stored per-persona, per-timestep (for trajectory analysis)
- Decision rationale logging captures which 2-3 variables were most influential
- Random seed ensures determinism: `seed + persona_hash + day` for stochastic events
- Full state history enables post-hoc trajectory clustering and counterfactual analysis
