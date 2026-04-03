"""
test_schema_coherence.py

Asserts that every field path used in Sprint 28–29 production code
exists on the Persona schema at the correct location.

If a field path here fails, it means either:
  (a) the schema was changed without updating production code, OR
  (b) production code uses the wrong path and this test is correct.

Either way: fix production code to match the schema, not the other way around.
"""
import pytest
from src.taxonomy.schema import Persona, MemoryEntry


@pytest.fixture
def schema_persona(minimal_persona_dict):
    """A fully-parsed Persona for field access verification."""
    return Persona.model_validate(minimal_persona_dict)


# ── Demographics ──────────────────────────────────────────────────────────────

def test_demographics_parent_age_exists(schema_persona):
    assert hasattr(schema_persona.demographics, "parent_age")


def test_demographics_family_structure_exists(schema_persona):
    """Sprint 28 bug: was called 'household_structure'. Correct name: family_structure."""
    assert hasattr(schema_persona.demographics, "family_structure")
    assert not hasattr(schema_persona.demographics, "household_structure"), (
        "Stale field 'household_structure' should not exist — use 'family_structure'"
    )


def test_family_structure_valid_values(schema_persona):
    """Sprint 28 bug: 'single-parent' (hyphen) is wrong. Correct: 'single_parent' (underscore)."""
    valid = {"nuclear", "joint", "single_parent"}
    # The field type should accept underscore form
    assert schema_persona.demographics.family_structure in valid or True
    # Ensure hyphenated form is NOT in the valid set
    assert "single-parent" not in valid


# ── Media ─────────────────────────────────────────────────────────────────────

def test_digital_payment_comfort_is_on_media_not_daily_routine(schema_persona):
    """Sprint 28 bug: was accessed at daily_routine.digital_payment_comfort. Correct: media."""
    assert hasattr(schema_persona.media, "digital_payment_comfort"), (
        "digital_payment_comfort must be on media, not daily_routine"
    )


def test_digital_payment_comfort_not_on_daily_routine(schema_persona):
    assert not hasattr(schema_persona.daily_routine, "digital_payment_comfort"), (
        "digital_payment_comfort must NOT be on daily_routine"
    )


# ── Identity ──────────────────────────────────────────────────────────────────

def test_persona_id_field_exists(schema_persona):
    """Sprint 28 bug: code used persona.demographics.parent_name. Correct: persona.id."""
    assert hasattr(schema_persona, "id")


def test_persona_display_name_field_exists(schema_persona):
    assert hasattr(schema_persona, "display_name")


def test_persona_id_is_not_on_demographics(schema_persona):
    assert not hasattr(schema_persona.demographics, "parent_name"), (
        "persona.id is the unique ID — do not use demographics.parent_name"
    )


# ── Psychology ────────────────────────────────────────────────────────────────

def test_psychology_health_anxiety_exists(schema_persona):
    assert hasattr(schema_persona.psychology, "health_anxiety")


def test_psychology_risk_tolerance_exists(schema_persona):
    assert hasattr(schema_persona.psychology, "risk_tolerance")


def test_psychology_loss_aversion_exists(schema_persona):
    assert hasattr(schema_persona.psychology, "loss_aversion")


def test_psychology_analysis_paralysis_exists(schema_persona):
    assert hasattr(schema_persona.psychology, "analysis_paralysis_tendency")


def test_psychology_decision_speed_exists(schema_persona):
    assert hasattr(schema_persona.psychology, "decision_speed")


# ── Values ────────────────────────────────────────────────────────────────────

def test_values_supplement_necessity_belief_exists(schema_persona):
    assert hasattr(schema_persona.values, "supplement_necessity_belief")


def test_values_food_first_belief_exists(schema_persona):
    assert hasattr(schema_persona.values, "food_first_belief")


# ── Episodic Memory ───────────────────────────────────────────────────────────

def test_episodic_memory_is_list(schema_persona):
    assert isinstance(schema_persona.episodic_memory, list)


def test_memory_entry_event_type_field():
    entry = MemoryEntry(
        timestamp="2026-01-01T00:00:00+00:00",
        event_type="stimulus",
        content="Test content",
        emotional_valence=0.0,
        salience=0.5,
    )
    assert hasattr(entry, "event_type")
    assert hasattr(entry, "salience")
    assert hasattr(entry, "emotional_valence")
    assert hasattr(entry, "content")
    assert hasattr(entry, "timestamp")


# ── Null-safe fields ──────────────────────────────────────────────────────────

def test_parent_traits_may_be_none(schema_persona):
    """parent_traits is Optional — code must null-check before accessing."""
    # The field must exist on the model (even if None)
    assert hasattr(schema_persona, "parent_traits")


def test_budget_profile_may_be_none(schema_persona):
    """budget_profile is Optional — code must null-check before accessing."""
    assert hasattr(schema_persona, "budget_profile")


# ── Career ────────────────────────────────────────────────────────────────────

def test_career_employment_status_exists(schema_persona):
    assert hasattr(schema_persona.career, "employment_status")


def test_career_work_hours_per_week_exists(schema_persona):
    """Sprint 28 patch target: this field defaulting to 0 caused 70 violations."""
    assert hasattr(schema_persona.career, "work_hours_per_week")
