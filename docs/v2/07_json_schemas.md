# JSON Schemas — All Data Models with Annotated Examples

This document describes every Pydantic model in the system as an annotated JSON schema. For each model: source file, field definitions, and a complete example JSON block.

---

## 1. Persona

**Source**: `src/taxonomy/schema.py`
**Produced by**: `PopulationGenerator.generate()`
**Consumed by**: All simulation, probing, and analysis modules.

```json
{
  "id": "MUM-F-34-2C",                      // short-form ID: city-gender-age-children
  "generation_seed": 42,                     // RNG seed used
  "generation_timestamp": "2024-11-15T08:32:11Z",  // ISO-8601 UTC
  "tier": "statistical",                     // "statistical" or "deep"
  "display_name": "Priya M.",                // LLM-assigned human name
  "narrative": "Priya is a 34-year-old...", // 150-300 word backstory
  "product_relationship": "current_user",    // cohort assignment after classification

  "demographics": {
    "city_tier": "Tier1",                    // "Tier1"/"Tier2"/"Tier3"
    "city_name": "Mumbai",
    "region": "West",                        // "North"/"South"/"East"/"West"/"NE"
    "urban_vs_periurban": "urban",
    "household_income_lpa": 22.5,            // annual income in lakhs [1.0, 100.0]
    "parent_age": 34,                        // [18, 55]
    "parent_gender": "female",               // "female"/"male"
    "marital_status": "married",
    "birth_order": "experienced_parent",     // "firstborn_parent"/"experienced_parent"
    "num_children": 2,
    "child_ages": [3, 7],                    // list of ages [0, 14]
    "child_genders": ["female", "male"],
    "youngest_child_age": 3,
    "oldest_child_age": 7,
    "family_structure": "nuclear",           // "nuclear"/"joint"/"single_parent"
    "elder_influence": 0.31,                 // [0, 1]
    "spouse_involvement_in_purchases": 0.44, // [0, 1]
    "income_stability": "salaried",          // "salaried"/"business"/"freelance"/"gig"
    "socioeconomic_class": "A2",             // "A1"/"A2"/"B1"/"B2"/"C1"/"C2"
    "dual_income_household": true
  },

  "health": {
    "child_health_status": "healthy",        // "healthy"/"recurring_issues"/"chronic_condition"
    "child_nutrition_concerns": ["picky_eater", "low_immunity"],
    "child_dietary_restrictions": [],
    "pediatrician_visit_frequency": "quarterly",
    "vaccination_attitude": "proactive",
    "own_supplement_usage": true,
    "fitness_engagement": 0.68,              // [0, 1]
    "diet_consciousness": 0.74,
    "organic_preference": 0.61,
    "health_info_sources": ["pediatrician", "instagram", "google"],
    "medical_authority_trust": 0.77,
    "self_research_tendency": 0.82,
    "child_health_proactivity": 0.79,
    "immunity_concern": 0.85,
    "growth_concern": 0.58,
    "nutrition_gap_awareness": 0.71
  },

  "psychology": {
    "decision_speed": 0.45,
    "information_need": 0.88,
    "risk_tolerance": 0.38,
    "analysis_paralysis_tendency": 0.62,
    "regret_sensitivity": 0.71,
    "authority_bias": 0.64,
    "social_proof_bias": 0.59,
    "anchoring_bias": 0.47,
    "status_quo_bias": 0.33,
    "loss_aversion": 0.68,
    "halo_effect_susceptibility": 0.44,
    "health_anxiety": 0.76,
    "comparison_anxiety": 0.52,
    "guilt_sensitivity": 0.65,
    "control_need": 0.71,
    "mental_bandwidth": 0.54,
    "decision_fatigue_level": 0.48,
    "simplicity_preference": 0.41
  },

  "cultural": {
    "cultural_region": "Maharashtra Urban",
    "dietary_culture": "non_vegetarian",
    "traditional_vs_modern_spectrum": 0.67,
    "ayurveda_affinity": 0.42,
    "western_brand_trust": 0.58,
    "social_circle_ses": "aspirational",     // "similar"/"aspirational"/"mixed"
    "mommy_group_membership": true,
    "social_media_active": true,
    "community_orientation": 0.61,
    "primary_language": "Marathi",
    "english_proficiency": 0.84,
    "content_language_preference": "bilingual"
  },

  "relationships": {
    "primary_decision_maker": "joint",       // "self"/"spouse"/"joint"/"elder"
    "peer_influence_strength": 0.55,
    "influencer_trust": 0.39,
    "elder_advice_weight": 0.28,
    "pediatrician_influence": 0.83,
    "wom_receiver_openness": 0.64,
    "wom_transmitter_tendency": 0.48,
    "negative_wom_amplification": 0.54,
    "child_pester_power": 0.42,
    "child_taste_veto": 0.61,
    "child_autonomy_given": 0.38,
    "partner_involvement": 0.52
  },

  "career": {
    "employment_status": "full_time",
    "work_hours_per_week": 44,
    "work_from_home": true,
    "career_ambition": 0.72,
    "perceived_time_scarcity": 0.69,
    "morning_routine_complexity": 0.74,
    "cooking_time_available": 0.35
  },

  "education_learning": {                    // field alias: "education"
    "education_level": "masters",
    "science_literacy": 0.78,
    "nutrition_knowledge": 0.66,
    "label_reading_habit": 0.83,
    "research_before_purchase": 0.87,
    "content_consumption_depth": 0.74,
    "ingredient_awareness": 0.79
  },

  "lifestyle": {                             // field alias: "lifestyle_interests"
    "cooking_enthusiasm": 0.48,
    "recipe_experimentation": 0.39,
    "meal_planning_habit": 0.62,
    "convenience_food_acceptance": 0.57,
    "wellness_trend_follower": 0.71,
    "clean_label_importance": 0.88,
    "superfood_awareness": 0.67,
    "parenting_philosophy": "authoritative",
    "screen_time_strictness": 0.64,
    "structured_vs_intuitive_feeding": 0.71
  },

  "daily_routine": {
    "online_vs_offline_preference": 0.81,
    "primary_shopping_platform": "amazon",
    "subscription_comfort": 0.63,
    "bulk_buying_tendency": 0.44,
    "deal_seeking_intensity": 0.38,
    "impulse_purchase_tendency": 0.27,
    "budget_consciousness": 0.34,
    "health_spend_priority": 0.82,
    "price_reference_point": 600.0,          // mental price anchor [0, 5000]
    "value_perception_driver": "ingredients",// "price_per_unit"/"brand"/"ingredients"/"results"
    "cashback_coupon_sensitivity": 0.31,
    "breakfast_routine": "quick",            // "elaborate"/"quick"/"skipped"
    "milk_supplement_current": "none",
    "gummy_vitamin_usage": false,
    "snacking_pattern": "structured"
  },

  "values": {
    "supplement_necessity_belief": 0.72,
    "natural_vs_synthetic_preference": 0.74,
    "food_first_belief": 0.58,
    "preventive_vs_reactive_health": 0.79,
    "brand_loyalty_tendency": 0.41,
    "indie_brand_openness": 0.69,
    "transparency_importance": 0.91,
    "made_in_india_preference": 0.52,
    "best_for_my_child_intensity": 0.88,
    "guilt_driven_spending": 0.61,
    "peer_comparison_drive": 0.43
  },

  "emotional": {
    "emotional_persuasion_susceptibility": 0.52,
    "fear_appeal_responsiveness": 0.66,
    "aspirational_messaging_responsiveness": 0.71,
    "testimonial_impact": 0.58,
    "buyer_remorse_tendency": 0.48,
    "confirmation_bias_strength": 0.55,
    "review_writing_tendency": 0.44
  },

  "media": {
    "primary_social_platform": "instagram",
    "daily_social_media_hours": 1.8,
    "content_format_preference": "reels",
    "ad_receptivity": 0.44,
    "product_discovery_channel": "search",
    "review_platform_trust": "amazon_reviews",
    "search_behavior": "active_seeker",
    "app_download_willingness": 0.67,
    "wallet_topup_comfort": 0.74,
    "digital_payment_comfort": 0.88
  },

  "episodic_memory": [
    {
      "timestamp": "2024-09-03T00:00:00Z",
      "event_type": "brand_exposure",
      "content": "Saw Instagram reel about LittleJoys",
      "emotional_valence": 0.3,              // [-1, 1]
      "salience": 0.6                        // [0, 1]
    }
  ],

  "semantic_memory": {
    "brand_impressions": {"littlejoys": "curious but waiting"},
    "category_beliefs": ["Supplements should be last resort"]
  },

  "brand_memories": {
    "littlejoys": {
      "brand_name": "littlejoys",
      "first_exposure": "2024-09-03",
      "exposure_channel": "instagram",
      "trust_level": 0.28,
      "purchase_count": 0,
      "last_purchase_date": null,
      "satisfaction_history": [],
      "has_pass": false,
      "word_of_mouth_received": ["Friend said picky eating improved"],
      "word_of_mouth_given": []
    }
  },

  "purchase_history": [
    {
      "product_name": "Nutrimix",             // field alias for "product"
      "timestamp": "month_3",
      "price_paid": 599.0,
      "channel": "simulation",
      "trigger": "funnel_adopt",             // "funnel_adopt" or "repeat_purchase"
      "outcome": "purchased",               // "purchased"/"repurchased"/"churned"
      "satisfaction": 0.72
    }
  ],

  "time_state": {                            // field alias for "state"
    "current_month": 3,
    "current_awareness": {"nutrimix_2_6": 0.55},
    "current_consideration_set": ["nutrimix_2_6"],
    "current_satisfaction": {"nutrimix_2_6": 0.72},
    "has_purchased": true,
    "consecutive_purchase_months": 1,
    "has_lj_pass": false,
    "satisfaction_trajectory": [0.72],
    "wom_received_from": ["DEL-F-29-1C"]
  }
}
```

---

## 2. Population

**Source**: `src/generation/population.py`
**Produced by**: `PopulationGenerator.generate()`
**Consumed by**: All simulation and analysis modules via `st.session_state["population"]`

```json
{
  "id": "a3f2c1d4e5b6...",                    // MD5 of (seed, size, filters)
  "generation_params": {
    "size": 200,                               // requested population size
    "seed": 42,
    "deep_persona_count": 30,                  // kept for backward compatibility
    "target_filters": {}                       // optional demographic filters
  },
  "tier1_personas": ["<Persona objects>"],     // list of all 200 Persona objects
  "tier2_personas": [],                        // always empty in current version
  "metadata": {
    "generation_timestamp": "2024-11-15T08:00:00Z",
    "generation_duration_seconds": 12.4,
    "engine_version": "2.0.0",
    "personas_skipped_after_validation": 0,
    "validation_retry_attempts": 3
  },
  "validation_report": {
    "issues": [],
    "warnings": []
  }
}
```

---

## 3. ScenarioConfig

**Source**: `src/decision/scenarios.py`
**Produced by**: `get_scenario(scenario_id)` / `_scenario_catalog()`
**Consumed by**: All simulation, probing, and intervention modules.

```json
{
  "id": "nutrimix_2_6",
  "name": "Nutrimix for 2-6 year olds",
  "description": "Existing core product — repeat purchase and LJ Pass modeling",
  "mode": "temporal",                          // "static" or "temporal"
  "months": 6,                                 // simulation duration
  "target_age_range": [2, 6],
  "lj_pass_available": true,

  "product": {
    "name": "Nutrimix",
    "category": "nutrition_powder",
    "price_inr": 599.0,
    "age_range": [2, 6],
    "key_benefits": ["immunity", "growth", "brain_development"],
    "form_factor": "powder_mix",
    "taste_appeal": 0.7,
    "effort_to_acquire": 0.3,
    "category_need_baseline": 0.65,
    "clean_label_score": 0.85,
    "health_relevance": 0.75,
    "complexity": 0.1,
    "cooking_required": 0.0,
    "premium_positioning": 0.6,
    "superfood_score": 0.7,
    "subscription_available": true,
    "addresses_concerns": ["low_immunity", "underweight", "picky_eater", "low_energy"]
  },

  "marketing": {
    "awareness_budget": 0.5,
    "channel_mix": {"instagram": 0.40, "youtube": 0.30, "whatsapp": 0.30},
    "trust_signals": ["pediatrician_approved", "clean_label", "no_added_sugar"],
    "school_partnership": false,
    "influencer_campaign": true,
    "pediatrician_endorsement": true,
    "sports_club_partnership": false,
    "perceived_quality": 0.75,
    "trust_signal": 0.70,
    "expert_endorsement": 0.50,
    "social_proof": 0.70,
    "influencer_signal": 0.50,
    "awareness_level": 0.60,
    "social_buzz": 0.50,
    "discount_available": 0.07
  },

  "lj_pass": {
    "monthly_price_inr": 99.0,
    "discount_percent": 10.0,
    "free_trial_months": 1,
    "retention_boost": 0.15,
    "churn_reduction": 0.20
  },

  "thresholds": {
    "need_recognition": 0.3,
    "awareness": 0.25,
    "consideration": 0.4,
    "purchase": 0.45
  }
}
```

---

## 4. StaticSimulationResult

**Source**: `src/simulation/static.py`
**Produced by**: `run_static_simulation()`
**Consumed by**: Cohort classifier, counterfactual engine.

```json
{
  "scenario_id": "nutrimix_2_6",
  "population_size": 200,
  "adoption_count": 31,
  "adoption_rate": 0.155,
  "results_by_persona": {
    "MUM-F-34-2C": {
      "outcome": "adopt",
      "rejection_stage": null,
      "rejection_reason": null
    },
    "DEL-F-29-1C": {
      "outcome": "reject",
      "rejection_stage": "consideration",
      "rejection_reason": "insufficient_trust"
    }
  },
  "rejection_distribution": {
    "need_recognition": 48,
    "awareness": 22,
    "consideration": 61,
    "purchase": 38
  },
  "random_seed": 42
}
```

---

## 5. PopulationCohorts

**Source**: `src/analysis/cohort_classifier.py`
**Produced by**: `classify_population()`
**Consumed by**: Pages 3–9 via `st.session_state["baseline_cohorts"]`.

```json
{
  "scenario_id": "nutrimix_2_6",
  "cohorts": {
    "never_aware": ["BAN-F-27-1C", "CHE-M-32-2C"],
    "aware_not_tried": ["DEL-F-29-1C", "HYD-F-31-1C"],
    "first_time_buyer": ["PUN-F-33-1C"],
    "current_user": ["MUM-F-34-2C"],
    "lapsed_user": ["KOL-M-35-2C"]
  },
  "classifications": [
    {
      "persona_id": "MUM-F-34-2C",
      "cohort_id": "current_user",
      "cohort_name": "Current User",
      "classification_reason": "Active repeat buyer (3 purchases, still active at end)"
    }
  ],
  "summary": {
    "never_aware": 45,
    "aware_not_tried": 80,
    "first_time_buyer": 35,
    "current_user": 22,
    "lapsed_user": 18
  }
}
```

---

## 6. CohortClassification

**Source**: `src/analysis/cohort_classifier.py`
**Produced by**: `classify_population()`

```json
{
  "persona_id": "MUM-F-34-2C",
  "cohort_id": "current_user",
  "cohort_name": "Current User",
  "classification_reason": "Active repeat buyer (3 purchases, still active at end)"
}
```

---

## 7. Hypothesis

**Source**: `src/probing/models.py`
**Produced by**: `get_problem_tree(problem_id)` or user input
**Consumed by**: `ProbingTreeEngine`

```json
{
  "id": "h_trial_medical_proof",
  "problem_id": "repeat_purchase_low",
  "title": "Trust barrier: parents need medical authority proof before trial",
  "rationale": "Pediatrician influence is high in our population — without clinical backing the product cannot clear consideration.",
  "signals": ["high medical_authority_trust correlates with adoption", "pediatrician endorsement boosts awareness"],
  "indicator_attributes": ["medical_authority_trust", "health_anxiety", "indie_brand_openness"],
  "counterfactual_modifications": {"marketing.pediatrician_endorsement": true},
  "is_custom": false,
  "enabled": true,
  "order": 1
}
```

---

## 8. Probe

**Source**: `src/probing/models.py`
**Produced by**: `get_problem_tree(problem_id)`

```json
{
  "id": "h_trial_medical_proof_i1",
  "hypothesis_id": "h_trial_medical_proof",
  "probe_type": "interview",
  "order": 1,
  "question_template": "What is the strongest signal for what drives first-time trial among health-anxious parents?",
  "target_outcome": "adopt",
  "follow_up_questions": ["What would make you trust this product more?"],
  "scenario_modifications": null,
  "comparison_metric": null,
  "analysis_attributes": [],
  "split_by": null,
  "status": "complete",
  "result": "<ProbeResult>"
}
```

---

## 9. ProbeResult

**Source**: `src/probing/models.py`
**Produced by**: `ProbingTreeEngine.execute_probe()`

```json
{
  "probe_id": "h_trial_medical_proof_i1",
  "confidence": 0.78,
  "evidence_summary": "The dominant interview theme was medical validation seeking, appearing in 47% of sampled responses.",
  "sample_size": 15,
  "population_size": 200,
  "clustering_method": "keyword",
  "interview_responses": [
    {
      "persona_id": "MUM-F-34-2C",
      "persona_name": "Priya M.",
      "outcome": "adopt",
      "content": "My paediatrician mentioned clean-label nutrition supplements..."
    }
  ],
  "response_clusters": [
    {
      "theme": "Medical Validation Seekers",
      "description": "Parents who require explicit clinical endorsement before trial.",
      "persona_count": 7,
      "percentage": 0.467,
      "representative_quotes": ["My paediatrician's word matters more than any ad"],
      "dominant_attributes": {"medical_authority_trust": 0.81, "health_anxiety": 0.79}
    }
  ],
  "baseline_metric": null,
  "modified_metric": null,
  "lift": null,
  "attribute_splits": []
}
```

---

## 10. ResponseCluster

**Source**: `src/probing/models.py`

```json
{
  "theme": "Medical Validation Seekers",
  "description": "Parents who require clinical endorsement before trial",
  "persona_count": 7,
  "percentage": 0.467,
  "representative_quotes": [
    "My paediatrician's word matters more than any ad I see",
    "I only buy what the doctor says is safe"
  ],
  "dominant_attributes": {
    "medical_authority_trust": 0.81,
    "health_anxiety": 0.79,
    "risk_tolerance": 0.31
  }
}
```

---

## 11. HypothesisVerdict

**Source**: `src/probing/models.py`
**Produced by**: `ProbingTreeEngine._build_hypothesis_verdict()`

```json
{
  "hypothesis_id": "h_trial_medical_proof",
  "confidence": 0.81,
  "status": "confirmed",                     // "confirmed"/"partially_confirmed"/"inconclusive"/"rejected"
  "evidence_summary": "Trust barrier: parents need medical authority proof before trial is confirmed at 81% confidence. Strongest evidence: 12 of 15 adopter interviews cited paediatrician recommendation as tipping point.",
  "key_persona_segments": [
    "Parents who require explicit clinical endorsement before trial",
    "Adopters with higher medical_authority_trust"
  ],
  "recommended_actions": [
    "Scale pediatrician co-marketing materials with clinical language",
    "Create a 'recommended by your doctor' QR-code onboarding flow"
  ],
  "consistency_score": 0.78
}
```

---

## 12. TreeSynthesis

**Source**: `src/probing/models.py`
**Produced by**: `ProbingTreeEngine._build_tree_synthesis()`

```json
{
  "problem_id": "repeat_purchase_low",
  "hypotheses_tested": 4,
  "hypotheses_confirmed": 2,
  "dominant_hypothesis": "h_trial_medical_proof",
  "confidence_ranking": [
    ["h_trial_medical_proof", 0.81],
    ["h_trial_low_friction", 0.64],
    ["h_competitor_alternatives", 0.42],
    ["h_irrelevance_older_kids", 0.28]
  ],
  "synthesis_narrative": "The strongest explanation is Trust barrier: parents need medical authority proof before trial with 81% confidence. The next best-supported branch is Price and friction barrier at 64% confidence. Overall tree confidence sits at 81%.",
  "recommended_actions": [
    "Scale pediatrician co-marketing materials",
    "Test a ₹499 introductory trial pack",
    "Run a focused follow-up test to sharpen the strongest signal"
  ],
  "overall_confidence": 0.81,
  "disabled_hypotheses": [],
  "confidence_impact_of_disabled": 0.0,
  "total_cost_estimate": 0.0018
}
```

---

## 13. Intervention

**Source**: `src/analysis/intervention_engine.py`
**Produced by**: `generate_intervention_quadrant()`

```json
{
  "id": "nm26_peds_campaign",
  "name": "Pediatrician Endorsement Campaign",
  "description": "Scale doctor-led trust messaging for repeat purchase.",
  "scope": "general",                          // "general" or "cohort_specific"
  "temporality": "non_temporal",               // "temporal" or "non_temporal"
  "target_cohort_id": null,                    // null for general, cohort ID for cohort_specific
  "parameter_modifications": {
    "marketing.pediatrician_endorsement": true
  },
  "expected_mechanism": "Improves trust and reduces post-trial drop-off."
}
```

---

## 14. CounterfactualResult

**Source**: `src/simulation/counterfactual.py`
**Produced by**: `run_counterfactual()`

```json
{
  "baseline_scenario_id": "nutrimix_2_6",
  "counterfactual_name": "Pediatrician Endorsement Campaign",
  "parameter_changes": {
    "marketing.pediatrician_endorsement": [false, true]  // [old_value, new_value]
  },
  "baseline_adoption_rate": 0.155,
  "counterfactual_adoption_rate": 0.195,
  "absolute_lift": 0.04,                       // 4 percentage points
  "relative_lift_percent": 25.8,               // 25.8% relative improvement
  "most_affected_segments": [
    {
      "segment_attribute": "city_tier",
      "segment_value": "Tier1",
      "baseline_adoption_rate": 0.18,
      "counterfactual_adoption_rate": 0.24,
      "lift": 0.06
    }
  ],
  // Event-simulation fields (may be null for static-funnel counterfactuals):
  "scenario_id": null,
  "label": null,
  "baseline_active_rate": null,
  "counterfactual_active_rate": null,
  "lift": null,
  "lift_pct": null,
  "baseline_revenue": null,
  "counterfactual_revenue": null,
  "revenue_lift": null
}
```

---

## 15. CoreFinding (session state dict)

**Written by**: `pages/4_finding.py`
**Consumed by**: Pages 5 (Intervention), 8 (Synthesis Report), 9 (Compare)

```json
{
  "finding_text": "The primary barrier identified is Trust barrier: parents need medical authority proof before trial, supported by 8 probes at 81% overall confidence.",
  "scenario_id": "nutrimix_2_6",
  "dominant_hypothesis": "h_trial_medical_proof",        // hypothesis ID
  "dominant_hypothesis_title": "Trust barrier: parents need medical authority proof before trial",
  "evidence_chain": ["h_trial_medical_proof", "h_trial_low_friction"],  // confirmed hypothesis IDs
  "overall_confidence": 0.81,
  "hypotheses_tested": 4,
  "hypotheses_confirmed": 2
}
```
