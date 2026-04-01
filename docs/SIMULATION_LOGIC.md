# LittleJoys — Base Simulation Logic
*Last updated: 2026-03-31. Audience: Product, GTM, and investment stakeholders.*

---

## What the simulation answers

> "If we put our product in front of 200 realistic Indian households with this marketing mix, how many buy it — and what happens next?"

The simulation is not a forecast. It is a **probabilistic experiment** run on a synthetic but demographically calibrated population. Every persona has 133 correlated psychographic attributes drawn from a Gaussian Copula. Every decision they make flows through an explicit, inspectable formula. Nothing is hard-coded to a target outcome.

---

## Stage 0 — Population Generation

Before any simulation, 200 synthetic personas are created.

**How:**
- Demographics (city tier, income, education, child ages, occupation) are sampled from distribution tables calibrated to Indian urban household data.
- 133 psychographic attributes (health anxiety, brand trust, price sensitivity, influencer openness, taste preferences, etc.) are generated via **Gaussian Copula** — a statistical method that preserves real-world correlations between attributes (e.g. high health anxiety correlates with high medical authority trust).
- A **Conditional Rule Engine** then applies demographic conditioning — e.g. households with children under 4 are shifted to higher `health_anxiety`, older children (11+) get higher `child_taste_veto` and `child_autonomy`.

**Child age distribution:** Each persona has a `child_ages` list (integers, 2–14). `youngest_child_age` and `oldest_child_age` are auto-computed. This is what drives age-band segmentation.

**Seed:** Each run uses a unique seed (`DEFAULT_SEED + run_count × 7919`) so results are reproducible per run but genuinely different across re-runs.

---

## Stage 1 — GTM Scenario Configuration

The marketing mix is not fixed — it is fully configurable before each run:

| Parameter | What it controls |
|---|---|
| `awareness_budget` | Overall marketing spend intensity (0–1) |
| `channel_mix` | Allocation across Instagram, YouTube, WhatsApp, Google Ads, Pediatrician, Momfluencer, etc. |
| `influencer_campaign` | Boolean — enables influencer trust boost in funnel |
| `pediatrician_endorsement` | Boolean — enables doctor-referral trust boost |
| `school_partnership` | Boolean — enables school community awareness boost |
| `referral_program_boost` | Additive awareness delta from referral WoM |
| `discount_available` | Launch discount intensity (0–0.30) — feeds purchase layer |
| `social_buzz` | Organic WoM momentum |

These parameters are compiled into a **ScenarioConfig** object before the simulation runs. Each scenario also defines a `target_age_range` (e.g. `(2, 6)` for Nutrimix 2–6).

---

## Stage 2 — The 4-Layer Adoption Funnel (Static Phase)

Every persona passes through four sequential gates. Failing any gate stops the persona at that stage — they do not proceed further.

### Layer 0 — Need Recognition

**Question:** Does this parent feel a genuine need for this product?

```
core = (health_anxiety × 0.20)
     + (nutrition_gap_awareness × 0.25)
     + (child_health_proactivity × 0.20)
     + (immunity_concern × 0.15, if product targets immunity)
     + (growth_concern × 0.15, if product targets growth)

need_score = core × age_relevance_factor
```

**Age relevance factor:** `1.0` if any child is within the scenario's `target_age_range`, else `0.3` (a 70% penalty). This is the primary mechanism that differentiates conversion rates by child age.

**Threshold:** `need_score ≥ 0.35` to proceed. Below → cohort = **Never Aware**.

### Layer 1 — Awareness

**Question:** Did this persona actually encounter the product?

```
base = awareness_budget × channel_fit_score
score = max(base, 0.15)  # floor prevents complete invisibility
score += 0.15  if pediatrician_endorsement AND medical_authority_trust > 0.6
score += 0.20  if school_partnership AND community_engagement > 0.5
score += 0.10  if influencer_campaign AND influencer_trust > 0.5
score += social_buzz × wom_receiver_openness × 0.20
score += awareness_boost  (from temporal WoM — grows each month as adopters spread word)
```

**Channel fit:** Each persona has a profile match score across channels (Instagram reach × Instagram affinity, WhatsApp usage, etc.). Low channel fit = low base awareness even at high budget.

**Threshold:** `awareness_score ≥ 0.30` to proceed. Below → cohort = **Never Aware**.

### Layer 2 — Consideration

**Question:** Having heard of it, does this persona seriously evaluate it?

```
trust = (medical_authority_trust + social_proof_bias) / 2
research = research_before_purchase × science_literacy
cultural_fit = 1.0 (compatible) or 0.5 (dietary mismatch: vegan/vegetarian/allergen conflict)
brand_factor = indie_brand_openness (for LittleJoys) or brand_loyalty (if established)
risk_factor = risk_tolerance × (1 - unfamiliar_brand_weight × 0.4)

consideration = trust × 0.30
              + research × 0.20
              + cultural_fit × 0.15
              + brand_factor × 0.20
              + risk_factor × 0.15
```

**Threshold:** `consideration_score ≥ 0.40` to proceed. Below → cohort = **Aware, Not Tried**.

### Layer 3 — Purchase

**Question:** Does the evaluation convert to an actual purchase?

```
value = transparency_importance × 0.5 + ingredient_awareness × 0.5
emotional = emotional_persuasion_susceptibility × 0.30
           + guilt_spending × 0.30
           + best_for_child_conviction × 0.40
deal_boost = discount_available × cashback_coupon_sensitivity × 0.25

price_barrier = budget_consciousness × (price_inr / reference_price) / 2
effort_barrier = effort_to_acquire × (1 − online_shopping_comfort)

purchase_score = value + emotional + deal_boost − price_barrier − effort_barrier
```

**Threshold:** `purchase_score ≥ 0.45` to proceed. Below → cohort = **Aware, Not Tried**.

**Pass all 4 layers** → persona enters the temporal simulation as an initial adopter.

---

## Stage 3 — Temporal Simulation (Month-by-Month Loop)

For personas who passed the funnel, the simulation runs for 6–12 months. Each month has three steps.

### Step A — Awareness Growth (affects non-adopters)

Every month, active adopters spread word-of-mouth:
- Each active persona reaches 3–5 other personas (random draw within range)
- WoM transmission rate: 15% per contact → received as `awareness_boost` delta
- Referral program adds a secondary boost on top of organic WoM
- This means: as more people adopt, awareness grows for the remaining population — a network effect

### Step B — Churn Decision (affects existing active buyers)

For each persona currently active (has bought before):

```
satisfaction_this_month = taste_alignment × 0.35
                        + perceived_effectiveness × 0.40
                        + price_value_ratio × 0.25

  where:
    taste_alignment = taste_appeal × (1 − child_taste_veto × 0.5)
    perceived_effectiveness = taste_appeal × 0.45 + science_literacy × 0.55
    price_value_ratio = 1 − (price_ratio − 1) × 0.35

churn_probability = 1.0 − mean(satisfaction over last 3 months)
churn_probability ×= 0.8  if persona has LJ Pass
```

**Draw:** `if random() < churn_probability` → persona becomes **inactive**. Their consecutive_months counter resets.

### Step C — Repeat Purchase Decision (affects non-churned active buyers)

```
habit_score = 0.3 + (0.1 × consecutive_active_months)  [caps at 1.0]
repeat_probability = satisfaction × habit_score × (1.1 if has_LJ_Pass else 1.0)
```

**Draw:** `if random() < repeat_probability` → persona makes a repeat purchase, revenue logged.

**Habit builds over time.** A persona in month 1 has `habit = 0.3`; by month 7 they have `habit = 1.0` (capped). This is why early churn is more likely — the habit hasn't formed yet.

---

## Stage 4 — Cohort Assignment

At the end of all months, each persona is classified based on two variables:

| `total_purchases` | `is_active` at end | Cohort |
|---|---|---|
| Failed any funnel layer at Need or Awareness | — | **Never Aware** |
| Failed funnel at Consideration or Purchase | — | **Aware, Not Tried** |
| ≥ 1 | True and only 1 purchase | **First-Time Buyer** |
| ≥ 1 | False and only 1 purchase | **First-Time Buyer** |
| ≥ 2 | True | **Current User** |
| ≥ 2 | False | **Lapsed User** |

The `is_active` flag reflects whether the persona survived all churn draws through the final simulation month.

---

## Answering the PM: "Our real conversion is higher — why doesn't the simulation match?"

This is an expected and healthy challenge. Here is the precise answer:

### 1. The simulation is calibrated conservatively by default

Default scenario parameters (`awareness_budget`, `taste_appeal`, `channel_mix`) represent a **moderate/generic GTM**. They are not pre-tuned to LittleJoys' actual historical performance. If your real-world data shows higher conversion for 2–6 year olds, that signal should be reflected in the GTM panel:
- Raise `awareness_budget` to match your actual spend intensity
- Enable `pediatrician_endorsement` if doctors are actively recommending
- Set `discount_available` to match your actual introductory offer

### 2. The simulation models all 200 personas — not just your current customers

Your real conversion data comes from people who **already found your product** (i.e. they cleared Layers 0 and 1). The simulation starts from the full addressable population, including the 67% who never became aware. Of course the simulation's overall rate looks lower — it includes all the people your marketing hasn't reached yet. That's the point: it shows you the ceiling and where you're losing.

### 3. Age relevance is already the primary differentiator

The funnel applies a **0.3× multiplier** to the need recognition score for personas whose children fall outside the target age band. A household with a 10-year-old evaluating a product designed for 2–6 year olds has 70% of their need score suppressed before anything else runs. So the simulation **already explains** why the 2–6 band converts better — by design.

### 4. Calibration is the next step — not contradiction

The right response to "our real rate is 18%, simulation shows 12%" is not "the simulation is wrong." It is: **what parameters, when adjusted, produce 18%?** That tells you which specific levers are driving real-world performance — and makes the model more useful for predicting the effect of changing any one of them.

---

## Child Age-Band Breakdown — What It Shows

The age-band dashboard (visible after running a simulation) segments all 200 personas into three bands based on `youngest_child_age`:

| Band | Ages | What to look for |
|---|---|---|
| Toddler / Early | 2–6 | Highest need recognition for Nutrimix; pediatrician and school channels most effective |
| Middle Childhood | 7–10 | Transition zone — sports and peer influence start mattering; taste veto increases |
| Pre-Teen | 11–14 | Child autonomy rises; parent need recognition drops; pester power flips direction |

For each band the dashboard shows:
- Raw persona count per cohort
- **Trial Rate** = (First-Time + Current + Lapsed) ÷ total in band
- **Active Rate** = Current Users ÷ total in band
- **Repeat Rate** = (Current + Lapsed) ÷ tried in band

This allows you to answer: "Is our funnel leak happening at awareness, consideration, or purchase — and is that leak different for households with younger vs older children?"

---

## Constants Reference

| Constant | Value | Role |
|---|---|---|
| `FUNNEL_AGE_RELEVANCE_IN_RANGE` | 1.0 | Full need score for in-range households |
| `FUNNEL_AGE_RELEVANCE_OUTSIDE_RANGE` | 0.3 | 70% penalty for out-of-range households |
| `DEFAULT_NEED_RECOGNITION_THRESHOLD` | 0.35 | Minimum need score to proceed |
| `DEFAULT_AWARENESS_THRESHOLD` | 0.30 | Minimum awareness to proceed |
| `DEFAULT_CONSIDERATION_THRESHOLD` | 0.40 | Minimum consideration to proceed |
| `DEFAULT_PURCHASE_THRESHOLD` | 0.45 | Minimum purchase score to convert |
| `REPEAT_HABIT_BASE` | 0.3 | Starting repeat probability multiplier |
| `REPEAT_HABIT_PER_MONTH` | 0.1 | Monthly habit increment (caps at 1.0 after 7 months) |
| `TEMPORAL_MONTHLY_AWARENESS_INCREMENT` | 0.02 | Base WoM awareness growth per month per active persona |
| `DEFAULT_WOM_TRANSMISSION_RATE` | 0.15 | Probability each WoM contact takes |
| `REPEAT_CHURN_LJ_PASS_FACTOR` | 0.8 | Churn multiplier for LJ Pass holders (20% reduction) |
| `REPEAT_LJ_PASS_MULTIPLIER` | 1.1 | Repeat probability boost for LJ Pass holders |

---

*This document is auto-maintained. Re-generate by reviewing `src/decision/funnel.py`, `src/simulation/temporal.py`, `src/decision/repeat.py`, `src/analysis/cohort_classifier.py`, and `src/constants.py`.*
