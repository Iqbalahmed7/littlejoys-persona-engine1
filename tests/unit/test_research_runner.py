"""Unit tests for research runner orchestration (Sprint 12)."""

from __future__ import annotations

import pytest

from src.config import Config
from src.decision.scenarios import get_scenario
from src.generation.population import GenerationParams, Population, PopulationMetadata
from src.probing.question_bank import get_questions_for_scenario
from src.simulation.research_runner import ResearchRunner
from src.taxonomy.schema import (
    CareerAttributes,
    CulturalAttributes,
    DailyRoutineAttributes,
    DemographicAttributes,
    EducationLearningAttributes,
    EmotionalAttributes,
    HealthAttributes,
    LifestyleAttributes,
    MediaAttributes,
    Persona,
    PsychologyAttributes,
    RelationshipAttributes,
    ValueAttributes,
)
from src.utils.llm import LLMClient


def mk_persona(pid: str, income: float = 10.0, budget: float = 0.5, ref_point: float = 500.0) -> Persona:
    return Persona(
        id=pid,
        generation_seed=42,
        generation_timestamp="2024-01-01T00:00:00Z",
        tier="deep",
        demographics=DemographicAttributes(
            city_tier="Tier1",
            socioeconomic_class="A1",
            city_name="Mumbai",
            region="West",
            parent_age=30,
            parent_gender="female",
            num_children=1,
            child_ages=[3],
            child_genders=["female"],
            youngest_child_age=3,
            oldest_child_age=3,
            household_income_lpa=income
        ),
        career=CareerAttributes(employment_status="full_time"),
        health=HealthAttributes(),
        psychology=PsychologyAttributes(),
        cultural=CulturalAttributes(),
        relationships=RelationshipAttributes(),
        education=EducationLearningAttributes(),
        lifestyle_interests=LifestyleAttributes(),
        daily_routine=DailyRoutineAttributes(
            budget_consciousness=budget,
            price_reference_point=ref_point,
            health_spend_priority=0.5
        ),
        values=ValueAttributes(),
        emotional=EmotionalAttributes(),
        media=MediaAttributes()
    )

@pytest.fixture
def mock_runner():
    """Create a ResearchRunner with a mock population and mock LLM."""
    # Split population: 13 high-budget/low-ref-point (will reject), 12 normal (will adopt)
    personas = []
    for i in range(25):
        if i < 13:
            # Rejection profile
            personas.append(mk_persona(f"p{i}", income=2.0, budget=1.0, ref_point=100.0))
        else:
            # Adoption profile
            personas.append(mk_persona(f"p{i}", income=20.0, budget=0.2, ref_point=800.0))

    pop = Population(
        id="test_pop",
        generation_params=GenerationParams(size=25, seed=42, deep_persona_count=25),
        tier1_personas=personas,
        tier2_personas=[],
        metadata=PopulationMetadata(
            generation_timestamp="2024-01-01T00:00:00Z",
            generation_duration_seconds=1.0,
            engine_version="0.1.0"
        )
    )
    scenario = get_scenario("nutrimix_2_6")
    questions = get_questions_for_scenario("nutrimix_2_6")
    llm = LLMClient(Config(llm_mock_enabled=True, llm_cache_enabled=False, anthropic_api_key=""))
    return ResearchRunner(
        population=pop,
        scenario=scenario,
        question=questions[0],
        llm_client=llm,
        mock_mode=True,
        alternative_count=5,
        sample_size=10,
    )

def test_full_mock_run(mock_runner) -> None:
    """ResearchRunner.run() should return a ResearchResult."""
    result = mock_runner.run()
    # Adoption rate should be ~12/25 = 0.48
    assert 0.4 <= result.primary_funnel.adoption_rate <= 0.6
    assert len(result.smart_sample.selections) > 0
    assert len(result.interview_results) > 0
    assert len(result.alternative_runs) > 0
    assert result.metadata.mock_mode is True

def test_progress_callback_invoked(mock_runner) -> None:
    """Progress callback should be called with increasing values."""
    progress_values = []
    def cb(msg: str, p: float):
        progress_values.append(p)

    mock_runner.progress_callback = cb
    mock_runner.run()

    assert len(progress_values) > 1
    for i in range(len(progress_values) - 1):
        assert progress_values[i] <= progress_values[i+1]
    assert progress_values[-1] >= 0.98

def test_alternative_count(mock_runner) -> None:
    """Requesting N alternatives should return up to N variants."""
    mock_runner.alternative_count = 3
    result = mock_runner.run()
    assert len(result.alternative_runs) <= 3

def test_interview_results_match_sample(mock_runner) -> None:
    """Every persona interviewed must be part of the smart sample."""
    result = mock_runner.run()
    sample_ids = set(result.smart_sample.persona_ids)
    for res in result.interview_results:
        assert res.persona_id in sample_ids

def test_metadata_populated(mock_runner) -> None:
    """Metadata fields should be non-null and reasonable."""
    result = mock_runner.run()
    m = result.metadata
    assert m.duration_seconds > 0
    assert m.population_size == 25
    assert m.sample_size == len(result.smart_sample.selections)
    assert m.estimated_cost_usd == 0.0

def test_alternatives_sorted_by_delta(mock_runner) -> None:
    """Alternative runs should be sorted by delta_vs_primary DESC."""
    result = mock_runner.run()
    assert len(result.alternative_runs) > 0
    deltas = [r.delta_vs_primary for r in result.alternative_runs]
    assert deltas == sorted(deltas, reverse=True)
