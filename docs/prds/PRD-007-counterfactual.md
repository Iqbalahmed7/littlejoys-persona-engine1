# PRD-007: Counterfactual Engine

> **Sprint**: 2
> **Priority**: P0 (Critical Path)
> **Assignee**: Codex
> **Depends On**: PRD-006 (simulation runners)
> **Status**: Ready for Development

---

## Objective

Build the "what if" engine that compares baseline scenarios against modified versions to quantify the impact of specific interventions.

---

## Deliverables

### D1: Counterfactual Runner

**File**: `src/simulation/counterfactual.py`

```python
def run_counterfactual(population, baseline_scenario, modifications, name, seed) -> CounterfactualResult:
```

1. Run baseline scenario through static simulation → baseline_result
2. Clone scenario, apply modifications (e.g., reduce price, add school partnership)
3. Run modified scenario through static simulation → modified_result
4. Compare: absolute lift, relative lift, most affected segments
5. Return structured `CounterfactualResult`

### D2: Predefined Counterfactuals

For each of the 4 scenarios, define 3-4 counterfactuals:

**Nutrimix 2-6:**
- "price_reduction_20": price 599 → 479
- "school_partnership": add school_partnership=True
- "free_trial": effort_to_acquire 0.3 → 0.1
- "influencer_blitz": awareness_budget 0.5 → 0.8

**Nutrimix 7-14:**
- "taste_improvement": taste_appeal 0.55 → 0.75
- "age_specific_branding": add "made_for_tweens" trust signal
- "pediatrician_push": add pediatrician_endorsement=True

**Magnesium Gummies:**
- "awareness_campaign": awareness_budget 0.25 → 0.60
- "price_premium_reduction": price 499 → 349
- "doctor_endorsement": add pediatrician_endorsement=True

**ProteinMix:**
- "convenience_format": form_factor "shake" → "ready_to_drink", effort 0.6 → 0.2
- "taste_improvement": taste_appeal 0.50 → 0.75
- "school_sports_partnership": add school_partnership=True

### D3: Segment Impact Analysis

For each counterfactual, identify which segments benefit most:
```python
class SegmentImpact(BaseModel):
    segment_attribute: str
    segment_value: str
    baseline_adoption_rate: float
    counterfactual_adoption_rate: float
    lift: float
```

Group by: city_tier, income_bracket, employment_status, child_age_group, education_level

---

## Tests

```python
# tests/unit/test_counterfactual.py
test_counterfactual_different_from_baseline()
test_price_reduction_increases_adoption()
test_effort_reduction_increases_adoption()
test_counterfactual_preserves_population()
test_segment_impact_identifies_correct_winners()
test_relative_lift_is_positive_for_beneficial_changes()
```

---

## Acceptance Criteria

- [ ] Counterfactual engine produces structured comparison results
- [ ] Price reduction always increases adoption (monotonicity)
- [ ] Effort reduction always increases adoption
- [ ] Segment impact correctly identifies which groups benefit most
- [ ] All predefined counterfactuals produce plausible results
- [ ] All tests pass
