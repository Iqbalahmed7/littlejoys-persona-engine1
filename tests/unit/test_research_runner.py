"""Unit tests for research runner orchestration (Sprint 12)."""

from __future__ import annotations

import pytest

from src.config import Config
from src.decision.scenarios import get_scenario
from src.generation.population import GenerationParams, Population, PopulationMetadata
from src.probing.question_bank import get_questions_for_scenario
from src.simulation.counterfactual import CounterfactualReport, CounterfactualResult
from src.simulation.event_engine import EventSimulationResult
from src.simulation.explorer import ScenarioVariant
from src.simulation.research_runner import ResearchRunner
from src.simulation.static import StaticSimulationResult
from src.simulation.temporal import MonthlySnapshot, TemporalSimulationResult
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
def mock_runner(monkeypatch: pytest.MonkeyPatch):
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

    def _stub_counterfactual(
        *, population, baseline_scenario, counterfactuals, **kwargs
    ):  # type: ignore[no-untyped-def]
        del counterfactuals
        bid = baseline_scenario.id
        ber = kwargs.get("baseline_event_result")
        base = 0.2 if ber is None else float(ber.final_active_rate)
        return CounterfactualReport(
            baseline_scenario_id=bid,
            results=[
                CounterfactualResult(
                    scenario_id="stub_cf",
                    label="Stub intervention",
                    baseline_active_rate=base,
                    counterfactual_active_rate=min(1.0, base + 0.02),
                    lift=0.02,
                    lift_pct=10.0,
                    baseline_revenue=1000.0,
                    counterfactual_revenue=1020.0,
                    revenue_lift=20.0,
                    baseline_scenario_id=bid,
                    counterfactual_name="stub_cf",
                    parameter_changes={"product.price_inr": 500.0},
                    baseline_adoption_rate=base,
                    counterfactual_adoption_rate=min(1.0, base + 0.02),
                    absolute_lift=0.02,
                    relative_lift_percent=10.0,
                )
            ],
            top_intervention="stub_cf",
            population_size=len(population.personas),
            duration_days=int(kwargs.get("duration_days", 180)),
        )

    monkeypatch.setattr(
        "src.simulation.research_runner.run_counterfactual_analysis",
        _stub_counterfactual,
    )

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


def test_temporal_mode_populates_temporal_result(mock_runner) -> None:
    """Temporal scenario runs include primary and alternative temporal metrics."""

    mock_runner.scenario = mock_runner.scenario.model_copy(
        update={"mode": "temporal", "months": 4},
        deep=True,
    )
    mock_runner.alternative_count = 4
    result = mock_runner.run()

    assert result.temporal_result is not None
    assert result.temporal_result.months == 4
    assert all(run.temporal_active_rate is not None for run in result.alternative_runs)


def test_temporal_alternatives_limited_to_top_10(mock_runner, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only the top 10 static alternatives should run temporal simulation."""

    mock_runner.scenario = mock_runner.scenario.model_copy(
        update={"mode": "temporal", "months": 3},
        deep=True,
    )
    mock_runner.alternative_count = 15

    variants = [
        ScenarioVariant(
            variant_id=f"alt_{idx}",
            variant_name=f"Alt {idx}",
            strategy="smart",
            modifications={"product.price_inr": 500 + idx},
            scenario_config=mock_runner.scenario.model_copy(update={"id": f"alt_{idx}"}, deep=True),
        )
        for idx in range(15)
    ]
    monkeypatch.setattr(
        "src.simulation.research_runner.generate_variants",
        lambda **_: variants,
    )

    def fake_static(population, scenario, seed):  # type: ignore[no-untyped-def]
        rate = 0.1
        if scenario.id.startswith("alt_"):
            rate = int(scenario.id.split("_")[1]) / 100
        return StaticSimulationResult(
            scenario_id=scenario.id,
            population_size=len(population.personas),
            adoption_count=int(rate * len(population.personas)),
            adoption_rate=rate,
            results_by_persona={
                persona.id: {
                    "scenario_id": scenario.id,
                    "outcome": "adopt",
                    "need_score": 0.8,
                    "awareness_score": 0.8,
                    "consideration_score": 0.8,
                    "purchase_score": 0.8,
                }
                for persona in population.personas
            },
            rejection_distribution={},
            random_seed=seed,
        )

    temporal_calls: list[str] = []

    def fake_temporal(population, scenario, thresholds=None, months=12, seed=42):  # type: ignore[no-untyped-def]
        temporal_calls.append(scenario.id)
        idx = int(scenario.id.split("_")[1]) if scenario.id.startswith("alt_") else 0
        active_rate = 0.2 + (idx / 100)
        return TemporalSimulationResult(
            scenario_id=scenario.id,
            months=months,
            population_size=len(population.personas),
            monthly_snapshots=[
                MonthlySnapshot(
                    month=1,
                    new_adopters=1,
                    repeat_purchasers=0,
                    churned=0,
                    total_active=max(1, int(active_rate * len(population.personas))),
                    cumulative_adopters=1,
                    awareness_level_mean=0.5,
                    lj_pass_holders=0,
                )
            ],
            final_adoption_rate=active_rate,
            final_active_rate=active_rate,
            total_revenue_estimate=1000.0,
            random_seed=seed,
        )

    def fake_event(population, scenario, duration_days=90, seed=42, progress_callback=None):  # type: ignore[no-untyped-def]
        del duration_days, seed
        if progress_callback:
            progress_callback(1.0)
        idx = int(scenario.id.split("_")[1]) if scenario.id.startswith("alt_") else 0
        rate = 0.2 + (idx / 100)
        return EventSimulationResult(
            scenario_id=scenario.id,
            duration_days=1,
            population_size=len(population.personas),
            trajectories=[],
            aggregate_monthly=[],
            final_active_count=max(1, int(rate * len(population.personas))),
            final_active_rate=rate,
            total_revenue_estimate=0.0,
            random_seed=42,
        )

    monkeypatch.setattr("src.simulation.research_runner.run_static_simulation", fake_static)
    monkeypatch.setattr("src.simulation.research_runner.run_temporal_simulation", fake_temporal)
    monkeypatch.setattr("src.simulation.research_runner.run_event_simulation", fake_event)

    result = mock_runner.run()

    assert len(temporal_calls) == 11  # primary + top 10 alternatives
    temporal_scored = [row for row in result.alternative_runs if row.temporal_active_rate is not None]
    assert len(temporal_scored) == 10
    assert result.alternative_runs[0].variant_id == "alt_14"
