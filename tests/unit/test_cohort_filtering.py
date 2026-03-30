import pytest

from src.analysis.cohort_classifier import PopulationCohorts, classify_population
from src.decision.scenarios import get_scenario
from src.generation.population import Population, PopulationGenerator


@pytest.fixture
def generator():
    return PopulationGenerator()

def test_classify_and_filter_nutrimix(generator):
    scenario = get_scenario("nutrimix_2_6")
    # Small size for unit test
    pop = generator.generate(size=5, seed=42)

    # Run classification
    cohorts = classify_population(pop, scenario, seed=42)

    assert isinstance(cohorts, PopulationCohorts)
    assert len(cohorts.classifications) == 5

    # Check that all personas have a product_relationship assigned
    for persona in pop.personas:
        assert persona.product_relationship in cohorts.cohorts

    # Test filtering for each cohort that has personas
    for cohort_id, persona_ids in cohorts.cohorts.items():
        if not persona_ids:
            continue

        filtered_pop = pop.filter_by_cohort(cohort_id)
        assert isinstance(filtered_pop, Population)
        assert len(filtered_pop.personas) == len(persona_ids)
        for p in filtered_pop.personas:
            assert p.product_relationship == cohort_id

def test_cohort_filtering_edge_case_small_pop(generator):
    scenario = get_scenario("magnesium_gummies")
    # Very small population might lead to empty cohorts
    pop = generator.generate(size=2, seed=123)

    cohorts = classify_population(pop, scenario, seed=123)

    # Ensure it doesn't crash on filtering empty cohorts
    for cohort_id in ["never_aware", "aware_not_tried", "first_time_buyer", "current_user", "lapsed_user"]:
        filtered_pop = pop.filter_by_cohort(cohort_id)
        assert isinstance(filtered_pop, Population)
        # It's okay if it's empty
        if cohort_id not in cohorts.cohorts or not cohorts.cohorts[cohort_id]:
            assert len(filtered_pop.personas) == 0

def test_population_get_cohort_summary(generator):
    pop = generator.generate(size=5, seed=789)
    scenario = get_scenario("protein_mix")
    _ = classify_population(pop, scenario, seed=789)

    summary = pop.get_cohort_summary()
    assert isinstance(summary, dict)
    assert sum(summary.values()) == 5

def test_static_reject_cohort_mapping():
    from src.analysis.cohort_classifier import _static_reject_cohort
    assert _static_reject_cohort("need_recognition") == "never_aware"
    assert _static_reject_cohort("awareness") == "never_aware"
    assert _static_reject_cohort("consideration") == "aware_not_tried"
    assert _static_reject_cohort(None) == "aware_not_tried"

def test_dominant_churn_signal_mapping():
    from src.analysis.cohort_classifier import _dominant_churn_signal
    assert _dominant_churn_signal({"child_acceptance": 0.1}) == "child_acceptance < 0.2"
    assert _dominant_churn_signal({"fatigue": 0.8}) == "fatigue > 0.7"
    assert _dominant_churn_signal({"trust": 0.2}) == "trust < 0.3"
    assert _dominant_churn_signal({"other": 0.5}) == "other"
    assert _dominant_churn_signal(None) is None

def test_static_reason_mapping():
    from src.analysis.cohort_classifier import _static_reason
    assert "Never passed awareness" in _static_reason("need_recognition", None)
    assert "blocked at purchase" in _static_reason(None, "price_too_high")
