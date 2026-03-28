import math

import pytest

from src.taxonomy.validation import PersonaValidator


@pytest.fixture
def validator():
    return PersonaValidator()


@pytest.fixture
def valid_persona_base():
    return {
        "id": "p1",
        "city_tier": "Tier1",
        "city_name": "Mumbai",
        "household_income_lpa": 12.0,
        "parent_age": 30,
        "parent_gender": "female",
        "num_children": 1,
        "youngest_child_age": 5,
        "oldest_child_age": 5,
        "education_level": "bachelors",
        "employment_status": "full_time",
        "family_structure": "nuclear",
        "dietary_culture": "vegetarian",
        "health_anxiety": 0.5,
        "supplement_necessity_belief": 0.5,
        "digital_payment_comfort": 0.5,
        "best_for_my_child_intensity": 0.5,
        "perceived_time_scarcity": 0.5,
    }


def test_valid_persona_passes(validator, valid_persona_base):
    res = validator.validate_persona("p1", valid_persona_base)
    assert res.is_valid
    assert not res.hard_failures


def test_out_of_range_attribute_fails_hard(validator, valid_persona_base):
    p = valid_persona_base.copy()
    p["health_anxiety"] = 1.2
    res = validator.validate_persona("p1", p)
    assert not res.is_valid
    assert any("health_anxiety is outside [0, 1]" in hf for hf in res.hard_failures)


def test_nan_value_fails_hard(validator, valid_persona_base):
    p = valid_persona_base.copy()
    p["supplement_necessity_belief"] = math.nan
    res = validator.validate_persona("p1", p)
    assert not res.is_valid
    assert any("supplement_necessity_belief is NaN" in hf for hf in res.hard_failures)


def test_child_older_than_parent_fails_hard(validator, valid_persona_base):
    p = valid_persona_base.copy()
    p["parent_age"] = 25
    p["oldest_child_age"] = 10
    res = validator.validate_persona("p1", p)
    assert not res.is_valid
    assert any("parent_age (25) - oldest_child_age (10) < 18" in hf for hf in res.hard_failures)


def test_unusual_tier3_digital_warns_soft(validator, valid_persona_base):
    p = valid_persona_base.copy()
    p["city_tier"] = "Tier3"
    p["digital_payment_comfort"] = 0.9
    res = validator.validate_persona("p1", p)
    assert res.is_valid  # only soft warning!
    assert any("Tier3 + digital_payment_comfort" in sw for sw in res.soft_warnings)


def test_population_distribution_check_passes_good_data(validator, valid_persona_base):
    pop = [valid_persona_base.copy() for _ in range(100)]
    for i, p in enumerate(pop):
        p["city_tier"] = "Tier1" if i < 50 else ("Tier2" if i < 80 else "Tier3")

    target_dist = {"city_tier": {"Tier1": 0.5, "Tier2": 0.3, "Tier3": 0.2}}
    report = validator.validate_population(pop, target_dist, {})
    assert report.distribution_checks["city_tier"].passed
    assert report.overall_pass


def test_population_distribution_check_fails_bad_data(validator, valid_persona_base):
    pop = [valid_persona_base.copy() for _ in range(100)]
    # Target expects 50/30/20, we give 100/0/0
    target_dist = {"city_tier": {"Tier1": 0.5, "Tier2": 0.3, "Tier3": 0.2}}
    report = validator.validate_population(pop, target_dist, {})
    assert not report.distribution_checks["city_tier"].passed
    assert not report.overall_pass


def test_correlation_check_within_tolerance_passes(validator, valid_persona_base):
    pop = []
    # Make a and b perfectly correlated
    for i in range(100):
        p = valid_persona_base.copy()
        v = i / 100.0
        p["a"] = v
        p["b"] = v
        pop.append(p)

    report = validator.validate_population(pop, {}, {("a", "b"): 0.9})  # tolerance 0.15
    assert report.correlation_checks["a-b"].passed


def test_correlation_check_outside_tolerance_fails(validator, valid_persona_base):
    pop = []
    # Perfectly uncorrelated or slightly negative
    for i in range(100):
        p = valid_persona_base.copy()
        p["a"] = i / 100.0
        p["b"] = (100 - i) / 100.0
        pop.append(p)

    report = validator.validate_population(pop, {}, {("a", "b"): 0.8})  # actual will be -1
    assert not report.correlation_checks["a-b"].passed


def test_validation_report_overall_pass(validator, valid_persona_base):
    pop = [valid_persona_base.copy() for _ in range(100)]
    report = validator.validate_population(pop, {}, {})
    assert report.overall_pass
