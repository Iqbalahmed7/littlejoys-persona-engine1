import pytest
from pydantic import ValidationError

from src.analysis.quadrant_analysis import analyze_quadrant_results
from src.decision.scenarios import MarketingConfig, ProductConfig, ScenarioConfig
from src.generation.population import GenerationParams, Population, PopulationMetadata
from src.probing.question_bank import BusinessQuestion


@pytest.fixture
def empty_pop():
    params = GenerationParams(size=0, seed=42, deep_persona_count=0)
    meta = PopulationMetadata(
        generation_timestamp="2024-01-01T00:00:00Z",
        generation_duration_seconds=0.1,
        engine_version="1.0.0"
    )
    return Population(id="empty", generation_params=params, tier1_personas=[], metadata=meta)

@pytest.fixture
def minimal_scenario():
    return ScenarioConfig(
        id="min", name="Min", description="D",
        product=ProductConfig(name="P", category="C", price_inr=100.0, age_range=(2, 6), form_factor="gummy"),
        marketing=MarketingConfig(),
        target_age_range=(2, 6),
        months=1, mode="static"
    )

@pytest.fixture
def minimal_question():
    return BusinessQuestion(
        id="q", scenario_id="min", title="Q", description="D",
        probing_tree_id=None, success_metric="M"
    )

def test_scenario_config_rejects_none_id():
    # ScenarioConfig.id is a required str — None is not accepted.
    # Empty string "" is structurally valid (Pydantic str allows it).
    with pytest.raises(ValidationError):
        ScenarioConfig(
            id=None, name="N", description="D",
            product=ProductConfig(name="P", category="C", price_inr=100.0, age_range=(2, 6), form_factor="gummy"),
            marketing=MarketingConfig(),
            target_age_range=(2, 6),
            months=1, mode="static"
        )

@pytest.mark.parametrize("price", [-1.0, 100.0])
def test_product_price_edge_cases(price):
    if price < 0:
        with pytest.raises(ValidationError):
            ProductConfig(name="P", category="C", price_inr=price, age_range=(2, 6), form_factor="gummy")
    else:
        p = ProductConfig(name="P", category="C", price_inr=price, age_range=(2, 6), form_factor="gummy")
        assert p.price_inr == price

def test_analyze_results_empty_list(minimal_scenario):
    from src.analysis.intervention_engine import InterventionQuadrant
    from src.simulation.quadrant_runner import QuadrantRunResult
    res = QuadrantRunResult(
        scenario_id="s1", baseline_adoption_rate=0.5, results=[],
        duration_seconds=1.0, population_size=10, seed=42
    )
    quad = InterventionQuadrant(problem_id="p1", quadrants={})
    with pytest.raises(ValueError, match="run_result does not include any intervention runs"):
        analyze_quadrant_results(res, quad)

@pytest.mark.parametrize("ratio", [0.0, 0.5, 1.0, 2.0])
def test_safe_pct_math(ratio):
    from src.analysis.quadrant_analysis import _safe_pct
    if ratio == 0:
        assert _safe_pct(10, 0) == 0.0
    else:
        assert _safe_pct(ratio*10, 10) == ratio * 100

@pytest.mark.parametrize("scope, temp, expected", [
    ("general", "temporal", "general_temporal"),
    ("general", "non_temporal", "general_non_temporal"),
    ("cohort_specific", "temporal", "cohort_temporal"),
    ("cohort_specific", "non_temporal", "cohort_non_temporal"),
    ("unknown", "unknown", "general_non_temporal"),
])
def test_quadrant_key_mapping(scope, temp, expected):
    from src.analysis.intervention_engine import quadrant_key
    assert quadrant_key(scope, temp) == expected
