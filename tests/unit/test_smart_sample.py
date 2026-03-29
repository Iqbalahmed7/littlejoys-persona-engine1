"""Unit tests for smart sampling (Sprint 12)."""

from __future__ import annotations

import pytest
from src.probing.smart_sample import select_smart_sample
from src.taxonomy.schema import (
    Persona, 
    DemographicAttributes, 
    CareerAttributes,
    HealthAttributes,
    PsychologyAttributes,
    CulturalAttributes,
    RelationshipAttributes,
    EducationLearningAttributes,
    LifestyleAttributes,
    DailyRoutineAttributes,
    ValueAttributes,
    EmotionalAttributes,
    MediaAttributes
)

def mk_persona(pid: str, tier: str = "Tier1", sec: str = "A1") -> Persona:
    """Helper to create minimal personas for sampling tests."""
    return Persona(
        id=pid,
        generation_seed=42,
        generation_timestamp="2024-01-01T00:00:00Z",
        tier="deep",
        demographics=DemographicAttributes(
            city_tier=tier,  # type: ignore
            socioeconomic_class=sec, # type: ignore
            city_name="Mumbai",
            region="West",
            household_income_lpa=10.0,
            parent_age=30,
            parent_gender="female",
            num_children=1,
            child_ages=[3],
            child_genders=["female"],
            youngest_child_age=3,
            oldest_child_age=3,
        ),
        career=CareerAttributes(employment_status="full_time"),
        health=HealthAttributes(),
        psychology=PsychologyAttributes(),
        cultural=CulturalAttributes(),
        relationships=RelationshipAttributes(),
        education=EducationLearningAttributes(),
        lifestyle_interests=LifestyleAttributes(),
        daily_routine=DailyRoutineAttributes(),
        values=ValueAttributes(),
        emotional=EmotionalAttributes(),
        media=MediaAttributes()
    )

@pytest.fixture
def mock_population_data() -> tuple[list[Persona], dict[str, dict]]:
    """Create a diverse pool of 30 personas and mock funnel decisions."""
    personas = [mk_persona(f"p{i}", "Tier1" if i < 20 else "Tier3", "A1" if i % 2 == 0 else "C1") for i in range(30)]
    
    # Force persona 5 to be an adopter in a TRULY minority segment
    # Current segments: Tier1_A1 (9), Tier1_C1 (10), Tier3_A1 (5), Tier3_C1 (5)
    # Move p5 to Tier2_B1 (Count 1, which is < 6)
    personas[5].demographics = personas[5].demographics.model_copy(update={"city_tier": "Tier2", "socioeconomic_class": "B1"})

    decisions = {}
    for i, p in enumerate(personas):
        # i < 10 are adopters
        if i < 10:
            outcome = "adopt"
            stage = None
            # Threshold 0.30. 0.32 is fragile margin
            scores = {"need_score": 0.8, "awareness_score": 0.8, "consideration_score": 0.8, "purchase_score": 0.32}
        elif i < 20:
            outcome = "reject"
            stage = "purchase"
            # Threshold 0.30. 0.28 is persuadable gap
            scores = {"need_score": 0.7, "awareness_score": 0.8, "consideration_score": 0.8, "purchase_score": 0.28}
        else:
            outcome = "reject"
            stage = "awareness"
            # Threshold 0.25 (need). 0.70 is "high_need_rejecter"
            scores = {"need_score": 0.70, "awareness_score": 0.2, "consideration_score": 0.0, "purchase_score": 0.0}
        
        decisions[p.id] = {
            "outcome": outcome,
            "rejection_stage": stage,
            **scores
        }
    return personas, decisions

def test_determinism(mock_population_data) -> None:
    """Same inputs + seed produce identical SmartSample output."""
    personas, decisions = mock_population_data
    sample1 = select_smart_sample(personas, decisions, seed=42)
    sample2 = select_smart_sample(personas, decisions, seed=42)
    assert sample1.persona_ids == sample2.persona_ids
    
    # Different seed should likely produce different order/control group
    sample3 = select_smart_sample(personas, decisions, seed=43)
    assert sample3.persona_ids != sample1.persona_ids

def test_sample_size(mock_population_data) -> None:
    """Output has exactly target_size personas (default 18)."""
    personas, decisions = mock_population_data
    sample = select_smart_sample(personas, decisions, target_size=12)
    assert len(sample.selections) == 12
    assert sample.population_size == 30

def test_all_buckets_represented(mock_population_data) -> None:
    """The sample contains at least 1 persona from each major reason if available."""
    personas, decisions = mock_population_data
    sample = select_smart_sample(personas, decisions, target_size=20)
    
    reasons = {s.selection_reason for s in sample.selections}
    assert "fragile_yes" in reasons
    assert "persuadable_no" in reasons
    assert "high_need_rejecter" in reasons
    assert "control" in reasons
    assert "underrepresented" in reasons

def test_no_duplicates(mock_population_data) -> None:
    """No persona_id appears twice in the sample."""
    personas, decisions = mock_population_data
    sample = select_smart_sample(personas, decisions, target_size=25)
    assert len(sample.persona_ids) == len(set(sample.persona_ids))

def test_small_population(mock_population_data) -> None:
    """Population smaller than target_size returns all personas."""
    personas, decisions = mock_population_data
    small_p = personas[:5]
    small_d = {p.id: decisions[p.id] for p in small_p}
    sample = select_smart_sample(small_p, small_d, target_size=18)
    assert len(sample.selections) == 5
    assert set(sample.persona_ids) == {p.id for p in small_p}

def test_all_adopt(mock_population_data) -> None:
    """Edge case: every persona adopted."""
    personas, _ = mock_population_data
    decisions = {p.id: {"outcome": "adopt", "need_score": 0.9, "awareness_score": 0.9, "consideration_score": 0.9, "purchase_score": 0.9} for p in personas}
    sample = select_smart_sample(personas, decisions)
    assert len(sample.selections) > 0
    assert all(s.selection_reason in ["fragile_yes", "underrepresented", "control"] for s in sample.selections)

def test_all_reject(mock_population_data) -> None:
    """Edge case: every persona rejected."""
    personas, _ = mock_population_data
    decisions = {p.id: {"outcome": "reject", "rejection_stage": "awareness", "need_score": 0.1, "awareness_score": 0.1, "consideration_score": 0.1, "purchase_score": 0.1} for p in personas}
    sample = select_smart_sample(personas, decisions)
    assert len(sample.selections) > 0
    assert all(s.selection_reason in ["persuadable_no", "high_need_rejecter", "underrepresented", "control"] for s in sample.selections)

def test_reason_detail_populated(mock_population_data) -> None:
    """Every SampledPersona in the output has a non-empty reason_detail string."""
    personas, decisions = mock_population_data
    sample = select_smart_sample(personas, decisions)
    for s in sample.selections:
        assert isinstance(s.reason_detail, str)
        assert len(s.reason_detail) > 0
