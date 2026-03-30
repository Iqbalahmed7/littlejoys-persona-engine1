import pytest

from src.analysis.cohort_classifier import PopulationCohorts
from src.analysis.problem_decomposition import ProblemDecomposition, decompose_problem
from src.decision.scenarios import get_scenario
from src.generation.population import GenerationParams, Population, PopulationMetadata
from src.probing.question_bank import get_questions_for_scenario


@pytest.fixture
def mock_population():
    params = GenerationParams(size=10, seed=42, deep_persona_count=0)
    meta = PopulationMetadata(
        generation_timestamp="2024-01-01T00:00:00Z",
        generation_duration_seconds=0.1,
        engine_version="1.0.0"
    )
    return Population(
        id="test_pop",
        generation_params=params,
        tier1_personas=[],
        metadata=meta
    )

@pytest.fixture
def mock_cohorts():
    return PopulationCohorts(
        scenario_id="test_scenario",
        cohorts={"never_aware": [], "aware_not_tried": [], "first_time_buyer": [], "current_user": [], "lapsed_user": []},
        summary={"never_aware": 2, "aware_not_tried": 2, "first_time_buyer": 2, "current_user": 2, "lapsed_user": 2}
    )

def test_decompose_problem_scenarios(mock_population, mock_cohorts):
    scenario_ids = ["nutrimix_2_6", "nutrimix_7_14", "magnesium_gummies", "protein_mix"]

    for sid in scenario_ids:
        scenario = get_scenario(sid)
        question = get_questions_for_scenario(sid)[0]

        decomposition = decompose_problem(scenario, question, mock_population, mock_cohorts)

        assert isinstance(decomposition, ProblemDecomposition)
        assert decomposition.problem_id == question.id
        assert len(decomposition.sub_problems) >= 3
        assert len(decomposition.cohorts) >= 2

        # Cohort sizes sum to population size in mock_cohorts
        total_size = sum(c.size for c in decomposition.cohorts)
        assert total_size == 10

        # Check sub-problems have required fields
        for sp in decomposition.sub_problems:
            assert sp.id.startswith(f"{sid}_sp_")
            assert len(sp.title) > 0
            assert len(sp.description) > 0
            assert len(sp.indicator_variables) > 0

def test_filter_by_cohort_wrapper(mock_population):
    from src.generation.population import PopulationGenerator
    gen = PopulationGenerator()
    pop = gen.generate(size=1, seed=42)
    p1 = pop.personas[0]
    p1.product_relationship = "current_user"

    mock_population.tier1_personas = [p1]

    filtered_pop = mock_population.filter_by_cohort("current_user")
    assert isinstance(filtered_pop, Population)
    assert len(filtered_pop.personas) == 1
    assert filtered_pop.personas[0].id == p1.id

    empty_pop = mock_population.filter_by_cohort("non_existent")
    assert len(empty_pop.personas) == 0

def test_scenario_subproblems_edge_cases():
    from src.analysis.problem_decomposition import _scenario_subproblems
    assert _scenario_subproblems("unknown_id") == []
    assert len(_scenario_subproblems("nutrimix_2_6")) == 5

def test_template_problem_title_fallback():
    from src.analysis.problem_decomposition import _template_problem_title
    from src.probing.question_bank import BusinessQuestion

    q = BusinessQuestion(
        id="q1", scenario_id="s1", title="Original Title",
        description="", probing_tree_id=None, success_metric="m"
    )
    # Scenario without template should fallback to question title
    assert _template_problem_title("unknown_scenario", q) == "Original Title"

    # nutrimix_2_6 has a template problem title
    assert _template_problem_title("nutrimix_2_6", q) == "High NPS but low repeat purchase"
