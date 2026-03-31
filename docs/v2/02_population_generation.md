# Population Generation — Architecture and Implementation

## Overview

The population generation system produces a synthetic cohort of Indian parent personas. Each persona is a fully-specified, internally-consistent individual with demographic attributes, correlated psychographic scores, and an LLM-generated narrative. The pipeline is deterministic: given the same seed, it always produces the same population.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        POPULATION GENERATOR                              │
│                   PopulationGenerator.generate(seed=42)                   │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  DistributionTables          │
                    │  .sample_demographics(n,seed)│
                    │  Output: demographics DataFrame│
                    └──────────────┬──────────────┘
                                   │ demographics (city_tier, income, age, etc.)
                    ┌──────────────▼──────────────┐
                    │  GaussianCopulaGenerator     │
                    │  .generate(n, demographics, seed)│
                    │  Output: psychographics DataFrame│
                    │  (correlated [0,1] float attrs)  │
                    └──────────────┬──────────────┘
                                   │ demographics + psychographics
                    ┌──────────────▼──────────────┐
                    │  ConditionalRuleEngine       │
                    │  .apply(merged_df)            │
                    │  Applies demographic→psycho  │
                    │  adjustment rules            │
                    └──────────────┬──────────────┘
                                   │ merged row per persona
                    ┌──────────────▼──────────────┐
                    │  Persona.from_flat_dict()    │
                    │  PersonaValidator.validate() │
                    │  → 200 Tier 1 Personas       │
                    │  (retry on validation fail)  │
                    └──────────────┬──────────────┘
                                   │ list[Persona] (statistical tier)
                    ┌──────────────▼──────────────┐
                    │  Tier2NarrativeGenerator     │
                    │  .generate_batch(personas)   │
                    │  LLM writes persona.narrative│
                    │  for every persona           │
                    └──────────────┬──────────────┘
                                   │ list[Persona] with narratives
                    ┌──────────────▼──────────────┐
                    │  Population object           │
                    │  (tier1_personas, metadata,  │
                    │   validation_report)         │
                    └─────────────────────────────┘
```

---

## Stage 1: Demographic Sampling

`DistributionTables.sample_demographics(n, seed)` draws `n` rows from predefined Indian market distributions. Key demographic fields sampled at this stage:

- `city_tier` (Tier1/Tier2/Tier3), `city_name`, `region`
- `household_income_lpa` (annual household income, 1.0–100.0 lakhs)
- `parent_age` (18–55), `parent_gender`
- `num_children`, `child_ages`, `child_genders`
- `socioeconomic_class` (A1/A2/B1/B2/C1/C2)
- `family_structure`, `income_stability`

If `target_filters` are provided to `generate()`, the sampler runs in oversampling mode — it draws larger batches until `n` rows pass all filter conditions, up to `DEMOGRAPHIC_FILTER_MAX_ATTEMPTS` attempts before raising `ValueError`.

---

## Stage 2: Gaussian Copula for Correlated Psychographics

`GaussianCopulaGenerator` samples all `UnitInterval` (0.0–1.0) psychographic attributes with realistic inter-attribute correlations. The correlation structure is defined in `default_psych_correlation_rules()` as a `dict[tuple[str, str], float]` of pairwise Pearson-like correlations.

Example correlations modelled:
- `health_anxiety` ↔ `immunity_concern` (positive)
- `budget_consciousness` ↔ `health_spend_priority` (negative)
- `information_need` ↔ `research_before_purchase` (positive)
- `decision_fatigue_level` ↔ `mental_bandwidth` (negative)

The copula generates psychographic values conditioned on demographic context, so the psychographic profile of a high-income Tier 1 parent differs systematically from a low-income Tier 3 parent.

---

## Stage 3: Conditional Rule Engine

`ConditionalRuleEngine.apply(merged_df)` applies post-hoc adjustments that encode known behavioral patterns. Rules map demographic combinations to psychographic nudges:

- High-income Tier 1 mothers → higher `indie_brand_openness`, higher `label_reading_habit`
- Tier 3 households → higher `budget_consciousness`, lower `online_vs_offline_preference`
- Homemakers → higher `perceived_time_scarcity` on morning routines

These rules ensure the merged DataFrame is sociologically coherent before personas are constructed.

---

## Stage 4: Persona Construction and Validation

For each row in the merged DataFrame, `Persona.from_flat_dict()` constructs a strongly-typed `Persona` object. The persona ID is generated by `generate_persona_id()` using a short form like `MUM-F-34-2C` (city prefix, gender, parent age, num children).

`PersonaValidator.validate_persona()` checks:
- Demographic consistency (youngest/oldest child age bounds, parent-child age gap ≥ 18 years)
- Psychographic ranges (all UnitInterval fields in [0, 1])
- Required fields populated

On validation failure, the generator retries with a freshly-resampled row (`_resample_merged_row`). After `MAX_PERSONA_VALIDATION_RETRIES` attempts, the persona is skipped and counted in `metadata.personas_skipped_after_validation`.

Duplicate human-readable persona IDs (same short-form ID from different rows) are resolved by appending `-2`, `-3`, etc. as a deterministic suffix.

---

## Stage 5: Narrative Generation

`Tier2NarrativeGenerator.generate_batch(personas)` runs LLM inference (or mock generation) for every persona in the list. The LLM receives the persona's full attribute profile and produces a 150–300 word first-person backstory stored in `persona.narrative`.

This narrative is used:
- In the Personas page for UX display
- As context in interview system prompts
- As the base for mock interview responses

All narratives are generated concurrently up to `llm.config.llm_max_concurrency`.

---

## Persona Schema

All fields in a `Persona` object:

### Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Short-form human-readable ID, e.g. `MUM-F-34-2C` |
| `generation_seed` | `int` | RNG seed used for this persona |
| `generation_timestamp` | `str` | ISO-8601 UTC timestamp of generation |
| `tier` | `"statistical" or "deep"` | Always `"statistical"` post-generation |
| `display_name` | `str or None` | Human-readable display name for UX |
| `narrative` | `str or None` | LLM-generated backstory (150–300 words) |
| `product_relationship` | `str` | Cohort assignment, default `"unassigned"` |
| `episodic_memory` | `list[MemoryEntry]` | Brand exposures, WOM events |
| `semantic_memory` | `dict[str, Any]` | Category beliefs, brand impressions |
| `brand_memories` | `dict[str, BrandMemory]` | Per-brand trust, purchase history |
| `purchase_history` | `list[PurchaseEvent]` | Written by temporal simulation |
| `state` (alias: `time_state`) | `TemporalState` | Current simulation state |

### Demographics section (`persona.demographics`)

| Field | Type | Example |
|-------|------|---------|
| `city_tier` | `"Tier1"/"Tier2"/"Tier3"` | `"Tier1"` |
| `city_name` | `str` | `"Mumbai"` |
| `region` | `"North"/"South"/"East"/"West"/"NE"` | `"West"` |
| `urban_vs_periurban` | `"urban"/"periurban"` | `"urban"` |
| `household_income_lpa` | `float [1.0, 100.0]` | `22.5` |
| `parent_age` | `int [18, 55]` | `34` |
| `parent_gender` | `"female"/"male"` | `"female"` |
| `marital_status` | literal enum | `"married"` |
| `birth_order` | `"firstborn_parent"/"experienced_parent"` | `"experienced_parent"` |
| `num_children` | `int [1, 5]` | `2` |
| `child_ages` | `list[int]` | `[3, 7]` |
| `child_genders` | `list["female"/"male"]` | `["female", "male"]` |
| `youngest_child_age` | `int` | `3` |
| `oldest_child_age` | `int` | `7` |
| `family_structure` | `"nuclear"/"joint"/"single_parent"` | `"nuclear"` |
| `elder_influence` | `float [0, 1]` | `0.31` |
| `spouse_involvement_in_purchases` | `float [0, 1]` | `0.44` |
| `income_stability` | `"salaried"/"business"/"freelance"/"gig"` | `"salaried"` |
| `socioeconomic_class` | `"A1"/"A2"/"B1"/"B2"/"C1"/"C2"` | `"A2"` |
| `dual_income_household` | `bool` | `true` |

### Psychographic sections

The following sections each contain `UnitInterval` (float 0.0–1.0) attributes plus some categoricals:

- **health** (`persona.health`): `child_health_status`, `child_nutrition_concerns`, `medical_authority_trust`, `health_anxiety` (via psychology), `immunity_concern`, `growth_concern`, `nutrition_gap_awareness`, `organic_preference`, etc.
- **psychology** (`persona.psychology`): `decision_speed`, `information_need`, `risk_tolerance`, `health_anxiety`, `loss_aversion`, `mental_bandwidth`, `decision_fatigue_level`, `simplicity_preference`, etc.
- **cultural** (`persona.cultural`): `dietary_culture`, `traditional_vs_modern_spectrum`, `ayurveda_affinity`, `western_brand_trust`, `mommy_group_membership`, etc.
- **relationships** (`persona.relationships`): `peer_influence_strength`, `pediatrician_influence`, `child_taste_veto`, `wom_receiver_openness`, `wom_transmitter_tendency`, etc.
- **career** (`persona.career`): `employment_status`, `work_hours_per_week`, `perceived_time_scarcity`, `cooking_time_available`, etc.
- **education_learning** (`persona.education_learning`): `education_level`, `nutrition_knowledge`, `label_reading_habit`, `research_before_purchase`, etc.
- **lifestyle** (`persona.lifestyle`): `cooking_enthusiasm`, `clean_label_importance`, `wellness_trend_follower`, `parenting_philosophy`, etc.
- **daily_routine** (`persona.daily_routine`): `primary_shopping_platform`, `budget_consciousness`, `health_spend_priority`, `price_reference_point`, `breakfast_routine`, `milk_supplement_current`, etc.
- **values** (`persona.values`): `supplement_necessity_belief`, `natural_vs_synthetic_preference`, `brand_loyalty_tendency`, `indie_brand_openness`, `best_for_my_child_intensity`, etc.
- **emotional** (`persona.emotional`): `fear_appeal_responsiveness`, `aspirational_messaging_responsiveness`, `testimonial_impact`, etc.
- **media** (`persona.media`): `primary_social_platform`, `daily_social_media_hours`, `product_discovery_channel`, `ad_receptivity`, etc.

### Memory and state fields

**`PurchaseEvent`** (written by temporal simulation):
| Field | Type | Description |
|-------|------|-------------|
| `product` (alias: `product_name`) | `str` | Product name |
| `timestamp` | `str` | `"month_3"` format |
| `price_paid` | `float` | Price at time of purchase |
| `channel` | `str` | `"simulation"` |
| `trigger` | `str` | `"funnel_adopt"` or `"repeat_purchase"` |
| `outcome` | `"purchased"/"repurchased"/"churned"` | Purchase outcome |
| `satisfaction` | `float [0, 1]` | Satisfaction score at this event |

**`TemporalState`** (alias: `time_state`):
| Field | Type | Description |
|-------|------|-------------|
| `current_month` | `int` | Current simulation month |
| `current_awareness` | `dict[str, float]` | Awareness level per scenario |
| `has_purchased` | `bool` | Whether persona has ever purchased |
| `has_lj_pass` | `bool` | Whether persona holds an LJ Pass |
| `satisfaction_trajectory` | `list[float]` | Per-month satisfaction history |
| `wom_received_from` | `list[str]` | Persona IDs that transmitted WOM |

---

## Population Save and Load

`Population.save(path: Path)` writes:
- `tier1.parquet` — all 200 personas serialised as JSON rows
- `population_meta.json` — `id`, `generation_params`, `metadata`, `validation_report`, file references
- `tier2/` — empty directory (backward compatibility)

`Population.load(path: Path)` reconstructs the Population by reading the parquet file and deserialising each `persona_json` column entry via `Persona.model_validate_json()`.

---

## Seed Reproducibility

The `generate()` method derives the `population_id` as `MD5(f"{seed}-{size}-{filters}")`. The same seed, size, and filter combination always yields the same personas in the same order. Stochastic elements (psychographic copula sampling, K-means for Tier 2 selection) all accept the master seed as their RNG initialiser.
