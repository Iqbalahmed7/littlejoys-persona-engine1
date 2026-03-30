import pytest

from src.analysis.cohort_classifier import classify_population
from src.analysis.intervention_engine import generate_intervention_quadrant
from src.analysis.problem_decomposition import decompose_problem
from src.analysis.quadrant_analysis import QuadrantAnalysis, analyze_quadrant_results
from src.decision.scenarios import get_scenario
from src.generation.population import PopulationGenerator
from src.probing.question_bank import get_questions_for_scenario
from src.simulation.quadrant_runner import run_intervention_quadrant


@pytest.mark.integration
def test_diagnose_to_simulate_handoff():
    # End-to-end Phase A -> Phase C pipeline
    # 1. Generate Population
    gen = PopulationGenerator()
    pop = gen.generate(size=5, seed=42)

    # 2. Scenario
    sid = "nutrimix_2_6"
    scenario = get_scenario(sid)
    question = get_questions_for_scenario(sid)[0]

    # 3. Classify Population into Cohorts (Phase A)
    cohorts = classify_population(pop, scenario, seed=42)
    assert len(cohorts.classifications) == 5

    # 4. Decompose Problem (Phase A)
    decomposition = decompose_problem(scenario, question, pop, cohorts)
    assert decomposition.problem_id == question.id

    # 5. Generate Intervention Quadrant (Phase A)
    quadrant = generate_intervention_quadrant(decomposition, scenario)
    total_interventions = sum(len(v) for v in quadrant.quadrants.values())
    assert total_interventions > 0

    # 6. Run Simulation (Phase C)
    run_result = run_intervention_quadrant(quadrant, pop, scenario, seed=42)
    assert run_result.scenario_id == sid
    assert len(run_result.results) == total_interventions

    # 7. Analyze Results (Phase C)
    analysis = analyze_quadrant_results(run_result, quadrant)
    assert isinstance(analysis, QuadrantAnalysis)
    assert analysis.top_recommendation.rank == 1
    assert len(analysis.ranked_interventions) == total_interventions
