# PRD-005: Scenario Configuration & Threshold Calibration

> **Sprint**: 2
> **Priority**: P0 (Critical Path)
> **Assignee**: Codex
> **Depends On**: PRD-004 (decision engine)
> **Status**: Ready for Development

---

## Objective

Define the 4 business problem scenarios with all product/marketing parameters, and calibrate decision thresholds so the baseline scenario (Nutrimix 2-6) produces a plausible adoption rate.

---

## Deliverables

### D1: Four Scenario Configurations

**File**: `src/decision/scenarios.py`

Implement `get_scenario()` and `get_all_scenarios()` with these 4 configs:

**Scenario 1: Nutrimix 2-6 (Baseline)**
```python
ScenarioConfig(
    id="nutrimix_2_6",
    name="Nutrimix for 2-6 year olds",
    description="Existing core product — repeat purchase and LJ Pass modeling",
    product=ProductConfig(
        name="Nutrimix",
        category="nutrition_powder",
        price_inr=599,
        age_range=(2, 6),
        key_benefits=["immunity", "growth", "brain_development"],
        form_factor="powder_mix",
        taste_appeal=0.7,
        effort_to_acquire=0.3,  # Available online
    ),
    marketing=MarketingConfig(
        awareness_budget=0.5,
        channel_mix={"instagram": 0.35, "youtube": 0.25, "whatsapp": 0.20, "pediatrician": 0.20},
        trust_signals=["pediatrician_approved", "clean_label", "no_added_sugar"],
        pediatrician_endorsement=True,
        influencer_campaign=True,
    ),
    target_age_range=(2, 6),
    lj_pass_available=True,
)
```

**Scenario 2: Nutrimix 7-14 (Expansion)**
```python
ScenarioConfig(
    id="nutrimix_7_14",
    name="Nutrimix expansion to 7-14 year olds",
    description="Can the same product work for older children?",
    product=ProductConfig(
        name="Nutrimix 7+",
        category="nutrition_powder",
        price_inr=649,
        age_range=(7, 14),
        key_benefits=["focus", "energy", "immunity"],
        form_factor="powder_mix",
        taste_appeal=0.55,  # Older kids are pickier
        effort_to_acquire=0.3,
    ),
    marketing=MarketingConfig(
        awareness_budget=0.35,
        channel_mix={"instagram": 0.30, "youtube": 0.30, "school": 0.25, "whatsapp": 0.15},
        trust_signals=["school_approved", "clean_label"],
        school_partnership=True,
    ),
    target_age_range=(7, 14),
    lj_pass_available=True,
)
```

**Scenario 3: Magnesium Gummies (New Product)**
```python
ScenarioConfig(
    id="magnesium_gummies",
    name="Magnesium Gummies for Kids",
    description="New supplement category — awareness is the primary challenge",
    product=ProductConfig(
        name="MagBites",
        category="supplement_gummies",
        price_inr=499,
        age_range=(4, 12),
        key_benefits=["sleep", "calm", "focus"],
        form_factor="gummy",
        taste_appeal=0.85,  # Kids love gummies
        effort_to_acquire=0.4,  # Less available than Nutrimix
    ),
    marketing=MarketingConfig(
        awareness_budget=0.25,  # Lower budget — new product
        channel_mix={"instagram": 0.40, "youtube": 0.30, "whatsapp": 0.30},
        trust_signals=["imported_ingredients", "pediatrician_recommended"],
        influencer_campaign=True,
    ),
    target_age_range=(4, 12),
    lj_pass_available=False,
)
```

**Scenario 4: ProteinMix (Effort Challenge)**
```python
ScenarioConfig(
    id="protein_mix",
    name="ProteinMix for Active Kids",
    description="Protein supplement — effort and routine are the primary barriers",
    product=ProductConfig(
        name="ProteinMix",
        category="protein_supplement",
        price_inr=799,
        age_range=(6, 14),
        key_benefits=["muscle", "growth", "energy"],
        form_factor="powder_shake",
        taste_appeal=0.50,  # Protein taste is polarizing
        effort_to_acquire=0.6,  # Requires daily shake preparation
    ),
    marketing=MarketingConfig(
        awareness_budget=0.30,
        channel_mix={"instagram": 0.25, "youtube": 0.35, "sports_clubs": 0.25, "whatsapp": 0.15},
        trust_signals=["sports_nutrition_certified", "no_artificial_sweeteners"],
    ),
    target_age_range=(6, 14),
    lj_pass_available=False,
)
```

### D2: Threshold Calibration

**File**: `src/decision/calibration.py`

Implement `calibrate_thresholds()`:
1. Run Nutrimix 2-6 scenario on the full population
2. Target adoption rate: 12-18% (realistic for a D2C nutrition brand in India)
3. Binary search on layer thresholds to achieve target
4. Output the calibrated thresholds as a dict
5. Save calibration results to `data/results/calibration.json`

```python
DEFAULT_THRESHOLDS = {
    "need_recognition": 0.35,
    "awareness": 0.30,
    "consideration": 0.40,
    "purchase": 0.45,
}
```

Calibration adjusts these until the baseline scenario hits the target range.

---

## Tests

```python
# tests/unit/test_scenarios.py
test_get_scenario_returns_correct_config()
test_get_all_scenarios_returns_four()
test_scenario_age_ranges_are_valid()
test_scenario_prices_are_positive()
test_channel_mix_sums_to_approximately_one()

# tests/unit/test_calibration.py
test_calibration_converges()
test_calibrated_thresholds_produce_target_adoption()
test_calibration_result_saved_to_disk()
```

---

## Acceptance Criteria

- [ ] All 4 scenarios defined with complete product + marketing configs
- [ ] Calibration converges to target adoption rate within tolerance
- [ ] Calibrated thresholds saved and loadable
- [ ] All tests pass
