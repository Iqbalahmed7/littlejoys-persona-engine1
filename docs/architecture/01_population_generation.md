# Population Generation

## Overview

The population generator produces a synthetic cohort of 200 Indian urban parent households. Every run from the same seed is byte-identical, making results reproducible for demos, A/B tests, and regression baselines.

Entry point: `src/generation/population.py` — `Population` class and `generate_population()`.

---

## Two-Stage Architecture

Generation is split into two tiers that run sequentially.

### Tier 1 — Statistical Shell (all 200 personas)

`src/generation/tier1_generator.py`

1. A seeded NumPy RNG (`np.random.default_rng(seed)`) is initialised.
2. Demographic fields are sampled first from `DistributionTables` (see below).
3. Psychographic continuous fields (~90 float attributes) are drawn from a **Gaussian copula** (`src/taxonomy/correlations.py — GaussianCopulaGenerator`) that enforces a validated inter-attribute correlation matrix. This prevents statistically impossible combinations (e.g., very high `indie_brand_openness` combined with very high `status_quo_bias`).
4. A **conditional rule engine** (`ConditionalRuleEngine`) then applies additive z-score shifts based on known demographic→psychographic relationships, for example:
   - Working mothers receive `perceived_time_scarcity += 0.15`
   - Tier 3 city residents receive `authority_bias += 0.10`
   - First-time parents receive `health_anxiety += 0.12`
   - Joint-family households receive `elder_advice_weight += 0.15`
5. All values are clipped to `[0.0, 1.0]`.

### Tier 2 — Deep Narrative Selection (30 of 200)

`src/generation/tier2_generator.py`

1. K-means clustering (k=8, `n_init=10`) is run on the standardised psychographic matrix of all Tier 1 personas.
2. Cluster-stratified sampling selects 30 personas that maximise coverage of the psychographic space.
3. For each selected persona an LLM narrative prompt is sent to Claude (`src/utils/llm.py`) and the returned ~400-word first-person narrative is stored in `persona.narrative`.
4. A `display_name` is generated via `src/generation/names.py`.

---

## Distribution Tables (`src/taxonomy/distributions.py`)

`DistributionTables` is a class of `ClassVar` dicts that define the sampling distributions for every categorical and continuous demographic field.

| Field | Distribution | Notes |
|---|---|---|
| `city_tier` | Categorical | Tier1: 45%, Tier2: 35%, Tier3: 20% |
| `household_income_lpa` | Truncated normal, tier-conditional | Tier1: μ=18, σ=8, [5, 80]; Tier2: μ=12, σ=6, [3, 50]; Tier3: μ=7, σ=4, [2, 30] |
| `parent_age` | Truncated normal | μ=32, σ=4, [22, 45] |
| `child_ages` | Uniform over [2, 14] | One draw per child; validated against `MIN_PARENT_CHILD_AGE_GAP=18` |
| `num_children` | Categorical | 1: 35%, 2: 45%, 3: 15%, 4: 4%, 5: 1% |
| `education_level` | Categorical, tier-conditional | Tier1 skews postgraduate; Tier3 skews high_school |
| `employment_status` | Categorical | homemaker: 30%, full_time: 35%, part_time: 15%, self_employed: 14%, freelance: 6% |
| `family_structure` | Categorical | nuclear: 55%, joint: 35%, single_parent: 10% |

---

## Persona Schema (`src/taxonomy/schema.py`)

The `Persona` model is a Pydantic `BaseModel` with `extra="forbid"` (strict). It is composed of 12 nested identity sub-models plus memory and state layers.

### Identity Layers

| Sub-model | Category | Key Fields |
|---|---|---|
| `DemographicAttributes` | demographics | city_tier, city_name, region, household_income_lpa, parent_age, parent_gender, num_children, child_ages, family_structure, socioeconomic_class |
| `HealthAttributes` | health | child_health_status, child_nutrition_concerns, vaccination_attitude, medical_authority_trust, immunity_concern, growth_concern, nutrition_gap_awareness |
| `PsychologyAttributes` | psychology | health_anxiety, decision_speed, information_need, risk_tolerance, social_proof_bias, loss_aversion, guilt_sensitivity, mental_bandwidth |
| `CulturalAttributes` | cultural | dietary_culture, traditional_vs_modern_spectrum, ayurveda_affinity, western_brand_trust, community_orientation |
| `RelationshipAttributes` | relationships | primary_decision_maker, peer_influence_strength, pediatrician_influence, wom_receiver_openness, child_pester_power |
| `CareerAttributes` | career | employment_status, work_hours_per_week, perceived_time_scarcity, cooking_time_available |
| `EducationLearningAttributes` | education_learning | education_level, science_literacy, nutrition_knowledge, label_reading_habit, research_before_purchase, ingredient_awareness |
| `LifestyleAttributes` | lifestyle | cooking_enthusiasm, clean_label_importance, wellness_trend_follower, parenting_philosophy, structured_vs_intuitive_feeding |
| `DailyRoutineAttributes` | daily_routine | online_vs_offline_preference, primary_shopping_platform, budget_consciousness, health_spend_priority, price_reference_point, milk_supplement_current |
| `ValueAttributes` | values | supplement_necessity_belief, food_first_belief, indie_brand_openness, transparency_importance, best_for_my_child_intensity |
| `EmotionalAttributes` | emotional | emotional_persuasion_susceptibility, fear_appeal_responsiveness, aspirational_messaging_responsiveness, testimonial_impact |
| `MediaAttributes` | media | primary_social_platform, daily_social_media_hours, ad_receptivity, product_discovery_channel, digital_payment_comfort |

All continuous psychographic fields are typed `UnitInterval = Annotated[float, Field(ge=0.0, le=1.0)]`.

### Memory and State Layers

| Field | Type | Purpose |
|---|---|---|
| `episodic_memory` | `list[MemoryEntry]` | Timestamped brand or category events with emotional valence |
| `semantic_memory` | `dict[str, Any]` | Free-form belief and impression storage |
| `brand_memories` | `dict[str, BrandMemory]` | Per-brand trust, purchase count, WOM records |
| `purchase_history` | `list[PurchaseEvent]` | All prior purchase events with outcomes |
| `state` | `TemporalState` | Live simulation state: awareness, consideration set, active status |

### Key Constants

```
TOTAL_ATTRIBUTE_COUNT = 145
DEFAULT_POPULATION_SIZE = 300
DEFAULT_DEEP_PERSONA_COUNT = 30
DEFAULT_SEED = 42
PARENT_AGE_MIN = 22, PARENT_AGE_MAX = 45
CHILD_AGE_MIN = 2, CHILD_AGE_MAX = 14
MIN_PARENT_CHILD_AGE_GAP = 18
```

---

## Seed-Based Reproducibility

Every call to `generate_population(seed=N)` produces the exact same 200 personas. The seed flows through:
1. NumPy RNG for all sampling draws
2. K-means random state for Tier 2 cluster selection
3. LLM cache keying (SHA-256 of prompt → file in `data/.llm_cache/`) so narrative generation is skipped on repeat runs

The `Population` class serialises to `data/population/` as JSON and is reloaded by the Streamlit app without re-generating.

---

## Files

| File | Role |
|---|---|
| `src/generation/population.py` | Orchestrator: `Population`, `generate_population()`, serialise/load |
| `src/generation/tier1_generator.py` | Statistical shell generation |
| `src/generation/tier2_generator.py` | Narrative generation via LLM |
| `src/generation/names.py` | Persona ID and display name generation |
| `src/taxonomy/schema.py` | All Pydantic models |
| `src/taxonomy/distributions.py` | Sampling distribution tables |
| `src/taxonomy/correlations.py` | Gaussian copula + conditional rule engine |
| `src/taxonomy/validation.py` | `PersonaValidator` and `PopulationValidationReport` |
