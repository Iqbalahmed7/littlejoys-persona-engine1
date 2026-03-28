# PRD-004: Decision Engine — Purchase Funnel (Layers 0-4)

> **Sprint**: 2
> **Priority**: P0 (Critical Path)
> **Assignee**: Cursor
> **Depends On**: PRD-001 (schema), PRD-003 (population)
> **Status**: Ready for Development

---

## Objective

Implement the 5-layer purchase decision funnel that determines whether each persona adopts a product. This is the core simulation logic — every downstream analysis depends on it.

---

## Decision Model (from ARCHITECTURE.md §8)

```
Layer 0: Need Recognition   → Does this parent recognize a nutrition need?
Layer 1: Awareness           → Has this parent heard of the product?
Layer 2: Consideration       → Does this parent seriously consider buying?
Layer 3: Purchase            → Does this parent actually buy?
Layer 4: Repeat Purchase     → Does this parent buy again? (temporal mode only)
```

Each layer produces a score [0, 1]. The persona progresses to the next layer only if the score exceeds a threshold. If rejected at any layer, the rejection stage and reason are recorded.

---

## Deliverables

### D1: Layer 0 — Need Recognition

**File**: `src/decision/funnel.py`

```python
def compute_need_recognition(persona: Persona, scenario: ScenarioConfig) -> float:
```

Score = weighted combination of:
- `health_anxiety` × 0.20
- `nutrition_gap_awareness` × 0.25
- `child_health_proactivity` × 0.20
- `immunity_concern` × 0.15 (if product targets immunity)
- `growth_concern` × 0.15 (if product targets growth)
- Age relevance factor: 1.0 if child in product's target age range, 0.3 if outside

Threshold: ~0.35 (calibrated in PRD-005)

### D2: Layer 1 — Awareness

```python
def compute_awareness(persona: Persona, scenario: ScenarioConfig) -> float:
```

Score = f(scenario.marketing.awareness_budget, persona media attributes):
- Base awareness from marketing budget × channel-persona match
- Channel match: `instagram_engagement` × instagram_spend + `youtube_parenting_content` × youtube_spend + `whatsapp_group_activity` × whatsapp_spend
- Trust signal boost: +0.15 if `pediatrician_endorsement` and `medical_authority_trust > 0.6`
- School partnership boost: +0.20 if `school_partnership` and `school_community_engagement > 0.5`
- Influencer boost: +0.10 if `influencer_campaign` and `influencer_trust > 0.5`

Threshold: ~0.30

### D3: Layer 2 — Consideration

```python
def compute_consideration(persona: Persona, scenario: ScenarioConfig, awareness: float) -> float:
```

Consideration requires awareness. Score = awareness × consideration_factors:
- Trust factor: (`medical_authority_trust` + `social_proof_bias`) / 2
- Research factor: `research_before_purchase` × `science_literacy`
- Cultural fit: 1.0 if dietary_culture compatible with product, 0.5 if not
- Brand factor: `brand_loyalty` if known brand, `novelty_seeking` if new brand (LittleJoys)
- Risk factor: (1 - `risk_tolerance`) reduces consideration for unfamiliar products

Threshold: ~0.40

### D4: Layer 3 — Purchase

```python
def compute_purchase(persona: Persona, scenario: ScenarioConfig, consideration: float) -> tuple[float, str]:
```

Purchase decision. Returns (score, rejection_reason_if_rejected):
- Price barrier: `price_sensitivity` × (product_price / reference_price_for_tier)
- Effort barrier: `effort_to_acquire` × (1 - `online_shopping_comfort`)
- Value perception: `value_for_money_orientation` × product_benefit_score
- Convenience: `convenience_priority` × (1 - effort_to_acquire)
- Emotional trigger: `emotional_persuasion_susceptibility` × `guilt_driven_spending` × `best_for_my_child_intensity`
- Final = consideration × (value + emotional - price_barrier - effort_barrier)

Threshold: ~0.45

Rejection reasons must be SPECIFIC: "price_too_high", "effort_too_high", "insufficient_trust", "dietary_incompatible", "age_irrelevant", "low_awareness", "low_need"

### D5: Layer 4 — Repeat Purchase

**File**: `src/decision/repeat.py`

```python
def compute_satisfaction(persona: Persona, product: ProductConfig, month: int) -> float:
def compute_repeat_probability(persona, satisfaction, consecutive_months, has_lj_pass) -> float:
def compute_churn_probability(persona, satisfaction_trajectory, has_lj_pass) -> float:
```

Satisfaction = f(taste_appeal match, perceived_effectiveness, price_value_ratio)
Repeat = satisfaction × habit_strength × (1.1 if has_lj_pass else 1.0)
Habit strength = min(1.0, 0.3 + 0.1 × consecutive_months)
Churn = (1 - satisfaction_mean_last_3_months) × (0.8 if has_lj_pass else 1.0)

### D6: Full Funnel Runner

```python
def run_funnel(persona: Persona, scenario: ScenarioConfig) -> DecisionResult:
```

Chains layers 0→3. Records score at each stage, final outcome, and rejection details.

---

## Tests

```python
# tests/unit/test_funnel.py
test_zero_awareness_produces_zero_adoption()
test_high_need_high_awareness_produces_adoption()
test_price_sensitive_persona_rejects_expensive_product()
test_dietary_incompatible_reduces_consideration()
test_age_outside_range_reduces_need()
test_rejection_reason_always_populated_for_rejections()
test_adoption_never_has_rejection_reason()
test_funnel_scores_monotonically_decrease_or_equal()
test_pediatrician_endorsement_boosts_awareness()
test_school_partnership_boosts_awareness()

# tests/unit/test_repeat.py
test_satisfaction_increases_repeat_probability()
test_lj_pass_increases_repeat_rate()
test_habit_formation_increases_with_months()
test_churn_increases_with_low_satisfaction()
test_churn_lower_with_lj_pass()
```

---

## Acceptance Criteria

- [ ] All 5 layers implemented with correct formulas
- [ ] Every rejection has a specific, traceable reason
- [ ] Monotonicity: higher price never increases adoption (all else equal)
- [ ] Monotonicity: higher awareness never decreases consideration
- [ ] Funnel scores decrease or stay equal across layers
- [ ] All tests pass
- [ ] No NaN/Inf in any output
