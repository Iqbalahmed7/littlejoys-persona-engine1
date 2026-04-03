# Decision Engine

## Overview

The decision engine evaluates each persona against each scenario through a 4-layer purchase funnel. Every layer produces a float score in `[0, 1]` and is compared against a configurable threshold. Failure at any layer produces an early exit with a labelled rejection reason, enabling fine-grained barrier analysis.

Entry point: `src/decision/funnel.py — run_funnel()`.

---

## Funnel Architecture

```
Layer 0: Need Recognition  (does the parent perceive a nutrition gap?)
Layer 1: Awareness         (has the parent encountered this product?)
Layer 2: Consideration     (does the parent seriously evaluate it?)
Layer 3: Purchase          (does the parent decide to buy?)
```

Each layer is computed only if the previous layer passed its threshold. This sequential design reflects the real consumer decision journey and prevents inflated adoption counts.

---

## Layer 0 — Need Recognition

**Function:** `compute_need_recognition(persona, scenario) → float`

**Inputs:**
- `health_anxiety` — psychological need driver
- `nutrition_gap_awareness` — perceived gap in child's current diet
- `child_health_proactivity` — tendency to seek preventive measures
- `immunity_concern` — scenario-specific if product targets immunity
- `growth_concern` — scenario-specific if product targets growth
- `child_ages` vs `scenario.target_age_range` — age relevance factor

**Formula:**
```
core = 0.20 × health_anxiety
     + 0.25 × nutrition_gap_awareness
     + 0.20 × child_health_proactivity
     + 0.15 × immunity_concern  [if product targets immunity]
     + 0.15 × growth_concern    [if product targets growth]

need_score = core × age_relevance_factor
```

Age relevance factor = 1.0 if any child is within the scenario's target age range, otherwise 0.3.

**Rejection reasons at Layer 0:**
- `low_need` — score below threshold but child is in range
- `age_irrelevant` — child's age is outside the target band

**Default threshold:** `FUNNEL_THRESHOLD_NEED_RECOGNITION = 0.25`

---

## Layer 1 — Awareness

**Function:** `compute_awareness(persona, scenario, *, awareness_boost=0.0) → float`

**Inputs:**
- `marketing.awareness_budget` — scenario's marketing spend (0–1)
- Channel match: weighted combination of Instagram, YouTube, WhatsApp affinity
- `marketing.pediatrician_endorsement` + `medical_authority_trust`
- `marketing.school_partnership` + `community_orientation` + `peer_influence_strength`
- `marketing.influencer_campaign` + `influencer_trust`
- `awareness_boost` — additive boost from temporal WOM dynamics

**Channel match formula:**
```
insta_match = ad_receptivity × (1.0 if primary_platform==instagram else 0.55)
youtube_match = wellness_trend_follower × (1.0 if primary_platform==youtube else 0.55)
whatsapp_match = (0.5 + 0.5 × mommy_group_membership) × wom_receiver_openness
channel_match = weighted_average(mix, [insta, youtube, whatsapp])
```

**Boost rules (additive):**
- Pediatrician endorsement active AND medical_authority_trust > 0.60: `+0.15`
- School partnership active AND community engagement proxy > 0.50: `+0.20`
- Influencer campaign active AND influencer_trust > 0.50: `+0.10`

**Rejection reason at Layer 1:** `low_awareness`

**Default threshold:** `FUNNEL_THRESHOLD_AWARENESS = 0.15`

---

## Layer 2 — Consideration

**Function:** `compute_consideration(persona, scenario, awareness) → float`

**Inputs:**
- Trust factor: average of `medical_authority_trust` and `social_proof_bias`
- Research factor: `research_before_purchase × science_literacy`
- Cultural fit: 1.0 (compatible) or 0.5 (dietary mismatch — vegan vs dairy, lactose intolerant vs milk-based)
- Brand factor: `indie_brand_openness` for LittleJoys products, `brand_loyalty_tendency` for established brands
- Risk factor: `1 − (0.40 × (1 − risk_tolerance))` for unfamiliar brands

**Weighted formula:**
```
consideration = 0.30 × trust_factor
              + 0.20 × research_factor
              + 0.15 × cultural_fit
              + 0.20 × brand_factor
              + 0.15 × risk_factor
```

**Rejection reasons at Layer 2:**
- `dietary_incompatible` — cultural/dietary mismatch detected
- `insufficient_trust` — trust factor below 0.25
- `insufficient_research` — general consideration score failure

**Default threshold:** `FUNNEL_THRESHOLD_CONSIDERATION = 0.35`

---

## Layer 3 — Purchase

**Function:** `compute_purchase(persona, scenario, consideration) → tuple[float, str | None]`

**Inputs:**
- `price_inr` vs `price_reference_point` — price barrier
- `effort_to_acquire` vs online shopping comfort — effort barrier
- `taste_appeal` and `key_benefits` count — benefit mix
- `transparency_importance` + `ingredient_awareness` — value perception
- `emotional_persuasion_susceptibility` + `guilt_driven_spending` + `best_for_my_child_intensity` — emotional pull

**Formula:**
```
price_barrier   = budget_consciousness × min(2.0, price_inr/price_reference_point) / 2
effort_barrier  = effort_to_acquire × (1 − online_shopping_comfort)
benefit_mix     = taste_appeal×0.5 + min(1, len(benefits)/5)×0.5
value_core      = transparency_importance×0.5 + ingredient_awareness×0.5
value           = value_core × benefit_mix
emotional       = emotional_persuasion×0.3 + guilt_spending×0.3 + best_for_child×0.4

combo = value + emotional − price_barrier − effort_barrier   [clipped to [0, 1]]
```

**Rejection reasons at Layer 3:**
- `price_too_high` — price barrier dominates
- `effort_too_high` — effort barrier dominates
- `insufficient_trust` — no dominant barrier, general failure

**Default threshold:** `FUNNEL_THRESHOLD_PURCHASE = 0.30`

---

## DecisionResult

```python
@dataclass(frozen=True, slots=True)
class DecisionResult:
    persona_id: str
    need_score: float
    awareness_score: float
    consideration_score: float
    purchase_score: float
    outcome: str                  # "adopt" | "reject"
    rejection_stage: str | None   # "need_recognition" | "awareness" | "consideration" | "purchase"
    rejection_reason: str | None  # see taxonomy below
```

### Rejection Reason Taxonomy

| Reason | Layer | Meaning |
|---|---|---|
| `age_irrelevant` | need_recognition | No child in the product's target age range |
| `low_need` | need_recognition | Insufficient health anxiety / nutrition concern |
| `low_awareness` | awareness | Persona has not been reached by marketing |
| `dietary_incompatible` | consideration | Product ingredient conflicts with household diet |
| `insufficient_trust` | consideration / purchase | Trust score too low to progress |
| `insufficient_research` | consideration | Research + science literacy below threshold |
| `price_too_high` | purchase | Price barrier exceeds value + emotional pull |
| `effort_too_high` | purchase | Acquisition effort too high relative to digital comfort |

---

## Scenario Structure

`src/decision/scenarios.py` defines `ScenarioConfig`, composed of:

### ProductConfig
`name`, `category`, `price_inr`, `age_range`, `key_benefits` (list), `form_factor`, `taste_appeal`, `effort_to_acquire`, `clean_label_score`, `health_relevance`, `subscription_available`, `addresses_concerns`

### MarketingConfig
`awareness_budget`, `channel_mix` (dict summing to 1.0), `trust_signals`, `pediatrician_endorsement`, `school_partnership`, `influencer_campaign`, `perceived_quality`, `trust_signal`, `expert_endorsement`, `social_proof`, `social_buzz`, `discount_available`

### LJPassConfig
`monthly_price_inr=299`, `discount_percent=15`, `free_trial_months=1`, `retention_boost=0.10`, `churn_reduction=0.20`

### Four Pre-built Scenarios

| ID | Product | Price | Age Range | Mode |
|---|---|---|---|---|
| `nutrimix_2_6` | Nutrimix | ₹599 | 2–6 | temporal |
| `nutrimix_7_14` | Nutrimix 7+ | ₹649 | 7–14 | temporal |
| `magnesium_gummies` | MagBites | ₹499 | 4–12 | static |
| `protein_mix` | ProteinMix | ₹799 | 6–14 | static |

---

## Calibration

`src/decision/calibration.py`

The funnel thresholds are calibrated via binary search to achieve a target adoption rate window of 12–18% (midpoint 15%), reflecting realistic first-purchase rates for new-to-category supplements. Calibration runs are stored in `data/results/calibration.json`.

---

## Files

| File | Role |
|---|---|
| `src/decision/funnel.py` | Four layer functions + `run_funnel()` |
| `src/decision/scenarios.py` | Pydantic scenario models + catalog of 4 scenarios |
| `src/decision/calibration.py` | Binary search threshold calibration |
| `src/decision/repeat.py` | Repeat purchase probability (habit formation, LJ Pass) |
| `src/constants.py` | All funnel threshold constants and weights |
