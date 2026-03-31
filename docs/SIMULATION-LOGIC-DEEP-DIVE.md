# LittleJoys Persona Simulation Engine — Logic Deep Dive

**Version:** Sprint 27 | **Date:** March 2026
**Purpose:** Understand signal sources, perception, decision-making, insight generation, and LLM integration

---

## 1. Signals Used to Create Personas

Personas are built from **145 attributes across 12 identity categories**, all constrained to `[0, 1]` (unit interval) unless categorical.

### 12 Identity Categories

| # | Category | Key Signals | Count |
|---|----------|-------------|-------|
| 1 | **Demographics** | city_tier, household_income_lpa (1–100), parent_age (22–45), child_ages (2–14), family_structure (nuclear/joint/single_parent), socioeconomic_class (A1–C2), income_stability, spousal_involvement | ~10 |
| 2 | **Health** | child_health_status, nutrition_concerns, pediatrician_visit_frequency, vaccination_attitude, medical_authority_trust, health_anxiety, immunity_concern, growth_concern, nutrition_gap_awareness, self_research_tendency | ~14 |
| 3 | **Psychology** | decision_speed, risk_tolerance, regret_sensitivity, authority_bias, social_proof_bias, anchoring_bias, loss_aversion, halo_effect_susceptibility, health_anxiety, comparison_anxiety, guilt_sensitivity, control_need, mental_bandwidth, decision_fatigue_level, analysis_paralysis_tendency | ~18 |
| 4 | **Cultural** | dietary_culture (veg/non-veg/jain), traditional_vs_modern, ayurveda_affinity, western_brand_trust, mommy_group_membership, community_orientation, language_preference | ~10 |
| 5 | **Relationships** | primary_decision_maker, peer_influence, influencer_trust, elder_influence, pediatrician_influence, wom_receiver_openness, wom_transmitter_tendency, child_pester_power, child_taste_veto, partner_involvement | ~11 |
| 6 | **Career** | employment_status (homemaker/part_time/full_time/self_employed), work_hours_per_week, perceived_time_scarcity, cooking_time_available, morning_routine_complexity | ~7 |
| 7 | **Education & Learning** | education_level, science_literacy, nutrition_knowledge, label_reading, research_before_purchase, ingredient_awareness | ~7 |
| 8 | **Lifestyle** | cooking_enthusiasm, convenience_acceptance, wellness_trend_follower, clean_label_importance, superfood_awareness, parenting_philosophy (helicopter→permissive), screen_time_strictness | ~10 |
| 9 | **Daily Routine** | online_vs_offline_preference, primary_shopping_platform, subscription_comfort, impulse_purchase_tendency, budget_consciousness, health_spend_priority, price_reference_point (₹0–5000), value_driver (price/brand/ingredients/results), current_supplement_brand (Horlicks/Bournvita/PediaSure/LittleJoys/none) | ~15 |
| 10 | **Values** | supplement_necessity_belief, natural_vs_synthetic_preference, food_first_belief, brand_loyalty, indie_brand_openness, transparency_importance, made_in_india_preference, best_for_my_child_intensity, guilt_driven_spending | ~11 |
| 11 | **Emotional** | emotional_persuasion_susceptibility, fear_appeal_responsiveness, aspirational_messaging_responsiveness, testimonial_impact, buyer_remorse_tendency, confirmation_bias_strength | ~7 |
| 12 | **Media** | primary_social_platform (Instagram/YouTube/WhatsApp/Facebook), daily_social_media_hours, ad_receptivity, product_discovery_channel (social/search/doctor/friend/store), review_platform_trust, content_format_preference (reels/stories/long_video/text) | ~12 |

### How Attributes Are Generated

```
Step 1: Demographic Sampling (stratified by city_tier + income band)
  ↓
Step 2: Gaussian Copula generates 133 correlated psychographic scores [0,1]
        — demographic inputs set conditional correlations
        — e.g., higher income → higher western_brand_trust, lower budget_consciousness
  ↓
Step 3: ConditionalRuleEngine applies hard logical constraints
        — e.g., if health_anxiety > 0.7 → medical_authority_trust lifted
        — e.g., if family_structure == "joint" → elder_influence lifted
  ↓
Step 4: PersonaValidator checks coherence (parent_age ≥ child_age + 18, etc.)
  ↓
Step 5: Assign human-readable name + deterministic ID (hash of name+city+age)
```

**Files:** `src/taxonomy/schema.py`, `src/taxonomy/correlations.py`, `src/taxonomy/distributions.py`, `src/generation/population.py`

---

## 2. Making Personas Context-Heavy with Real-World Signals

### LLM Narrative Enrichment (Tier 2)

The top 30 statistically-generated personas are enriched with **LLM-generated biographical context** via a 3-stage pipeline:

#### Stage 1 — Anchor Inference
The LLM reads the top psychographic extremes and infers:
- `core_values`: e.g., `["care", "practicality", "trust", "consistency"]`
- `life_attitude`: 2–3 sentence worldview summary
- `parent_motivations`: e.g., `["steady growth", "strong immunity", "less daily friction"]`

**Input to LLM:** Demographic attributes + top 10 psychographic extremes as JSON
**Output:** Structured JSON (`AnchorInference` schema)

#### Stage 2 — Life Story Generation
Using the inferred values, the LLM generates 2–3 biographical events:
- Title, concrete event description, personal impact
- At least one story must relate to the parenting journey
- Must be consistent with all demographics

**Input:** Anchor inference + persona attribute summary
**Output:** JSON array of `{title, event, impact}` objects

#### Stage 3 — Full Narrative (300–500 words)
Third-person biographical narrative that:
- References ≥10 persona attributes by name
- Uses Hindi-English code-mixing where culturally appropriate
- Describes daily routine, parenting approach, purchase decision style
- Avoids generic template phrasing

**Input:** Full persona attributes + anchor + life stories
**Output:** Free-form text stored in `persona.narrative`

### Real-World Scraping (Currently Stubs)

| Source | Intent | Status |
|--------|--------|--------|
| Amazon Reviews | Product sentiment, switching reasons, price concerns | **Blocked** (anti-scraping) |
| Google Trends | Search interest for "kids nutrition powder India" etc. | **Conditional** (needs pytrends) |
| Parenting Forums | Community opinions, recurring concerns | **Placeholder** |

**Current state:** All sampling uses hardcoded distributions (`DistributionTables`). No live data injection into decisions.

**Files:** `src/generation/tier2_generator.py`, `src/scraping/amazon_reviews.py`, `src/scraping/google_trends.py`

---

## 3. How Personas Perceive Simulation Signals

### The 4-Layer Perception Funnel

Each persona processes a product launch through **4 sequential perception gates**. A signal must clear all 4 to produce adoption.

```
PRODUCT + MARKETING SIGNALS
         ↓
   ┌─────────────┐
   │   Layer 0   │  NEED RECOGNITION
   │             │  "Does this product solve a problem I feel?"
   └─────┬───────┘
         │ score ≥ 0.25
         ↓
   ┌─────────────┐
   │   Layer 1   │  AWARENESS
   │             │  "Have I been reached by this product's marketing?"
   └─────┬───────┘
         │ score ≥ 0.15
         ↓
   ┌─────────────┐
   │   Layer 2   │  CONSIDERATION
   │             │  "Does this product fit my trust, values, and lifestyle?"
   └─────┬───────┘
         │ score ≥ 0.35
         ↓
   ┌─────────────┐
   │   Layer 3   │  PURCHASE
   │             │  "Can I justify the price and effort?"
   └─────┬───────┘
         │ score ≥ 0.30
         ↓
      ADOPT
```

### Layer 0: Need Recognition

**Persona attributes used:**
- `health_anxiety` (weight: 0.20)
- `nutrition_gap_awareness` (weight: 0.25)
- `child_health_proactivity` (weight: 0.20)
- `immunity_concern` (weight: 0.15, if product targets immunity)
- `growth_concern` (weight: 0.15, if product targets growth)

**Age filter:** Score multiplied by `1.0` if child age ∈ scenario target range, else `0.3`

### Layer 1: Awareness

**How marketing signals are perceived:**

| Channel Signal | Persona Attributes That Amplify It |
|---------------|-----------------------------------|
| Instagram / Reels | `ad_receptivity` × platform match bonus |
| YouTube | `wellness_trend_follower` × platform match |
| WhatsApp (mom groups) | `mommy_group_membership` × `wom_receiver_openness` |
| Pediatrician endorsement | `medical_authority_trust > 0.6` → +0.15 boost |
| School partnership | `community_engagement > 0.5` → +0.20 boost |
| Influencer campaign | `influencer_trust > 0.5` → +0.10 boost |

**WoM from other adopters** adds an `awareness_boost` accumulated month-by-month.

**Base formula:**
```
awareness = awareness_budget × channel_persona_match + partnership_boosts + wom_boost
```

### Layer 2: Consideration

**Persona attributes used:**
- `medical_authority_trust` + `social_proof_bias` → trust factor (weight: 0.30)
- `research_before_purchase` × `science_literacy` → research factor (weight: 0.20)
- Dietary cultural fit (weight: 0.15) — 0.5 penalty for dietary mismatch
- `indie_brand_openness` or `brand_loyalty` → brand factor (weight: 0.20)
- `risk_tolerance` → risk factor for unfamiliar brands (weight: 0.15)

### Layer 3: Purchase

**Perception of price:**
```
price_barrier = budget_consciousness × (product_price / price_reference_point) / 2
```

**Perception of effort:**
```
effort_barrier = effort_to_acquire × (1 - online_shopping_comfort)
```

**Emotional drivers:**
```
emotional = 0.3 × emotional_persuasion_susceptibility
          + 0.3 × guilt_driven_spending
          + 0.4 × best_for_my_child_intensity
```

**Rejection signal returned:**
- `"price_too_high"` — if price_barrier dominates
- `"effort_too_high"` — if effort_barrier ≥ 0.15
- `"insufficient_trust"` — otherwise

**File:** `src/decision/funnel.py`

---

## 4. How Personas Form Opinions and Take Decisions

### Decision Outcome Types

Every persona run through the funnel produces a `DecisionResult`:

| Outcome | Condition | Cohort |
|---------|-----------|--------|
| `reject` at `need_recognition` | score < 0.25 | `never_aware` |
| `reject` at `awareness` | score < 0.15 | `never_aware` |
| `reject` at `consideration` | score < 0.35 | `aware_not_tried` |
| `reject` at `purchase` | score < 0.30 | `aware_not_tried` |
| `adopt` | all thresholds cleared | `first_time_buyer → current_user / lapsed_user` |

### Post-Adoption Decision Loop (Temporal)

After first purchase, each persona decides every month:

**Satisfaction** (how the product is actually experienced):
```
satisfaction = 0.35 × taste_alignment
             + 0.40 × perceived_effectiveness
             + 0.25 × price_value_perception
```

Where:
- `taste_alignment = taste_appeal × (1 - child_taste_veto × 0.5)`
- `perceived_effectiveness = taste_appeal × 0.45 + science_literacy × 0.55`
- `price_value = 1.0 - (price_ratio - 1) × 0.35`

**Repeat probability:**
```
habit_strength = 0.3 + 0.1 × consecutive_months_active
repeat_prob = satisfaction × habit_strength × (1.1 if lj_pass else 1.0)
```

**Churn probability:**
```
recent_sat = mean(last_3_months_satisfaction)
churn_prob = (1 - recent_sat) × (0.8 if lj_pass else 1.0)
```

The LJ Pass acts as a **retention lever**: +10% repeat probability, −20% churn probability.

**File:** `src/decision/repeat.py`

---

## 5. How Personas Generate Insights

### Cohort Classification → Evidence Chains

After simulation, every persona is classified into one of 5 behavioral cohorts based on their actual trajectory:

| Cohort | Classification Logic |
|--------|---------------------|
| `never_aware` | Rejected at need or awareness stage |
| `aware_not_tried` | Reached awareness but rejected at consideration/purchase |
| `first_time_buyer` | Adopted once, didn't reach 2nd repeat |
| `current_user` | ≥2 purchases, still active at end of simulation |
| `lapsed_user` | Churned after ≥2 purchases |

### Parameters That Drive Insight Selection

From the cohort profiles, the engine identifies **which persona attributes differ most** between cohorts vs. the full population:

```
delta = cohort_mean(attribute) - population_mean(attribute)
insight_signal = attributes with |delta| > threshold
```

For example:
- `current_user` cohort → high `health_anxiety`, high `supplement_necessity_belief`, high `decision_speed`
- `lapsed_user` cohort → lower `perceived_effectiveness`, high `child_taste_veto`, lower `habit_strength`

### Hypothesis Probing

The engine generates structured probe trees per hypothesis:

**Example (Magnesium Gummies, H2):**
- Hypothesis: "Parents doubt gummy supplements can meaningfully support their child's overall development"
- Probes run against `aware_not_tried` cohort
- Evidence aggregated: % who scored low on `supplement_necessity_belief`, % with high `food_first_belief`
- Verdict: SUPPORTED / PARTIAL / REFUTED with confidence %

**Core Finding pattern:**
- Winning hypothesis → becomes the Core Finding
- Top evidence nodes → become the Evidence Chain
- Representative voices → 3 personas from the cohort with LLM-narrated quotes

**Files:** `src/analysis/cohort_classifier.py`, `src/probing/predefined_trees.py`, `src/analysis/barriers.py`

---

## 6. LLM Inputs — What Goes to the Model

### LLM Client Architecture

- **Provider:** Anthropic Claude API
- **Reasoning tasks:** `claude-opus-4-6`
- **Bulk generation:** `claude-sonnet-4-6`
- **Cache:** SHA256-keyed disk cache (prompt + model + temperature → response)
- **Retry:** Up to `LLM_MAX_RETRIES` with exponential backoff
- **Mock mode:** Deterministic local generation (no API calls)

### 6 Types of LLM Calls

#### Call Type 1: Anchor Inference
```
System: "You are creating a detailed biographical profile for a synthetic persona."
User:   {demographics_json} + {top_psychographic_extremes_json}
        "Based on these attributes, return JSON with:
         core_values (list), life_attitude (string), parent_motivations (list)"
Output: AnchorInference JSON schema
```

#### Call Type 2: Life Story Generation
```
System: "You are writing formative life events for a synthetic persona."
User:   {anchor_json} + {persona_attributes_json}
        "Generate 2–3 concrete life events shaped by this person's values.
         At least one must relate to their parenting journey.
         Return JSON: {stories: [{title, event, impact}]}"
Output: LifeStoryResponse JSON schema
```

#### Call Type 3: Full Narrative
```
System: "You are writing a third-person biographical narrative."
User:   {full_persona_attributes} + {anchor} + {stories}
        "Write 300–500 words. Reference ≥10 specific attributes.
         Use Hindi-English code-mixing where culturally authentic.
         Avoid generic template phrasing."
Output: Free-form narrative text
```

#### Call Type 4: Hypothesis Probe Generation (Custom)
```
System: "You are a qualitative research strategist."
User:   {hypothesis_text} + {product_context} + {cohort_data}
        "Generate 5–8 diagnostic probe questions for this hypothesis.
         Questions should expose the belief, emotion, or barrier behind it."
Output: List of probe questions with expected evidence attributes
```

#### Call Type 5: Interview Simulation
```
System: "You are roleplaying as {persona.name}, a parent in {city}, {demographics}."
User:   {persona narrative} + {probe_question}
        "Answer this question as this person would.
         Stay true to their psychology, values, and communication style."
Output: First-person interview response (100–200 words)
```

#### Call Type 6: Synthesis Report
```
System: "You are a strategic research analyst."
User:   {scenario} + {cohort_summaries} + {barrier_analysis} + {evidence_chains}
        "Synthesize into an executive memo with:
         Core finding, key barriers, top interventions, confidence levels."
Output: Structured report JSON with sections
```

**File:** `src/utils/llm.py`, `src/generation/tier2_generator.py`

---

## 7. Perception Engine & Decision Engine — Current vs. Simulatte Vision

### Current Architecture

The engine uses a **formula-driven funnel** — deterministic weighted sums with threshold gates. This is fast, auditable, and reproducible but lacks emergent behavior.

```
PERSONA ATTRIBUTES (145 dims)
         ↓
PERCEPTION LAYER (per-funnel-stage feature selection)
         ↓
WEIGHTED SCORING (fixed weights per stage)
         ↓
THRESHOLD GATE (binary pass/fail)
         ↓
OUTCOME + REJECTION SIGNAL
```

**Strengths:**
- Fully auditable (every score traceable to exact attributes + weights)
- Reproducible (deterministic with fixed seed)
- Fast (200 personas × 12 months in <5 seconds)

**Gaps vs. Simulatte vision:**
- No adaptive belief updating (persona beliefs don't evolve with new information)
- No memory of past marketing exposures beyond `awareness_boost` accumulation
- No competitive landscape perception (personas don't compare products)
- No emotional state machine (mood, fatigue, life events don't affect decisions)
- LLM narratives don't feed back into decision logic

### Simulatte-Inspired Enhancements (Proposed)

Based on the Simulatte architecture, here is what a full **Perception Engine + Decision Engine** would look like:

#### Perception Engine (What the persona notices)

```python
class PerceptionEngine:
    """
    Filters the world through the persona's attention model.
    A persona only perceives signals that break through their attention threshold.
    """
    def perceive(self, persona, signal) -> PerceivedSignal | None:
        # Attention filter
        attention = compute_attention(persona, signal)
        if attention < persona.mental_bandwidth:
            return None  # Signal ignored

        # Distortion through cognitive biases
        perceived_value = apply_biases(signal.value, persona.psychology)
        # e.g., anchoring_bias distorts price perception
        # e.g., social_proof_bias amplifies WoM signals
        # e.g., halo_effect elevates trusted brand signals

        # Emotional colouring
        emotional_weight = emotional_coloring(signal, persona.emotional)

        return PerceivedSignal(value=perceived_value, salience=attention, emotion=emotional_weight)
```

#### Decision Engine (What the persona concludes)

```python
class DecisionEngine:
    """
    Deliberates over perceived signals using belief state and decision heuristics.
    """
    def deliberate(self, persona, perceived_signals, current_belief_state) -> Decision:
        # Update belief state with new signals
        new_beliefs = belief_update(current_belief_state, perceived_signals)

        # Check decision readiness
        if persona.decision_speed < THRESHOLD and not enough_signals:
            return Decision(action="defer", reason="insufficient_confidence")

        # Apply decision heuristics (fast vs. slow thinking)
        if persona.analysis_paralysis_tendency > 0.7:
            # System 2 thinker: needs more proof
            return systematic_evaluation(new_beliefs, persona)
        else:
            # System 1 thinker: gut + social proof
            return heuristic_evaluation(new_beliefs, persona)
```

#### Full Simulatte-Style Flow

```
WORLD SIGNALS (product launch, campaign, WoM, price change)
         ↓
ATTENTION FILTER (mental_bandwidth, decision_fatigue)
         ↓
PERCEPTION ENGINE
  ├─ Cognitive bias distortion (anchoring, social_proof, halo_effect)
  ├─ Emotional colouring (fear, aspiration, guilt)
  └─ Salience weighting (recency, vividness, peer source)
         ↓
BELIEF STATE UPDATE (episodic memory + semantic memory)
         ↓
DECISION ENGINE
  ├─ Deliberation speed (decision_speed, analysis_paralysis)
  ├─ Heuristic vs. systematic path (System 1 / System 2)
  ├─ Risk assessment (risk_tolerance, loss_aversion)
  └─ Social validation check (WoM, peer approval, elder validation)
         ↓
ACTION (adopt / defer / reject / seek_more_info)
         ↓
OUTCOME UPDATE (satisfaction, memory encoding, WoM transmission)
         ↓
BELIEF STATE EVOLUTION (brand trust updates, category learning)
```

### Implementation Priority for Sprint 28+

| Component | Effort | Impact | Priority |
|-----------|--------|--------|----------|
| Cognitive bias distortion in awareness layer | Low | High | P1 |
| Belief state memory (brand trust evolves) | Medium | High | P1 |
| Competitive perception (compare vs. Horlicks/PediaSure) | Medium | High | P2 |
| Emotional state machine (anxiety, aspiration triggers) | High | Medium | P2 |
| System 1/System 2 decision path split | Medium | Medium | P3 |
| Life event triggers (child illness → urgency spike) | High | High | P3 |

---

## Summary: Full Data Flow

```
INPUTS
  Demographic constraints (city_tier, income_band, family_type)
  Product scenario (price, benefits, channels, budget)
  GTM strategy (channels, campaigns, referral, discount, months)
         ↓
PERSONA GENERATION
  Gaussian copula → 145 attributes
  ConditionalRuleEngine → coherent trait combinations
  LLM (3 calls) → narrative, anchor values, life stories
         ↓
BASE SIMULATION (Temporal, 3–12 months)
  Month 1–N loop:
    1. Awareness increment (budget × channel_match)
    2. WoM propagation (adopters → non-adopters)
    3. Referral boost (if referral_program_boost > 0)
    4. Funnel (non-adopters): Need → Awareness → Consideration → Purchase
    5. Repeat/Churn (adopters): Satisfaction → Repeat/Churn probability
         ↓
COHORT CLASSIFICATION
  5 cohorts: never_aware, aware_not_tried, first_time_buyer, current_user, lapsed_user
  Delta analysis: which attributes separate cohorts from population
         ↓
HYPOTHESIS PROBING
  4 predefined hypotheses per scenario
  Probe trees run against target cohort
  Evidence nodes scored → verdicts (SUPPORTED / PARTIAL / REFUTED)
         ↓
CORE FINDING
  Highest-confidence hypothesis → Core Finding
  Top evidence nodes → Evidence Chain
  LLM call → Representative Voice quotes from cohort personas
         ↓
INTERVENTIONS
  12 interventions scored on effort/cost/adoption_lift
  Quadrant analysis (impact vs. effort)
  Counterfactual sensitivity analysis per selected intervention
         ↓
OUTPUTS
  Cohort dashboard (counts, %, behavioral profiles)
  Adoption funnel (Became Aware → Tried → Repeated → Active)
  Core Finding + Evidence Chain
  Intervention ranking table + Quadrant Map
  Synthesis Report (PDF/TXT/JSON export)
  Persona narratives + interview transcripts
```
