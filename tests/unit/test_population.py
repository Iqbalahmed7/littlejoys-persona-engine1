"""Unit tests for population generation orchestrator."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.constants import DATAFRAME_MIN_EXPECTED_COLUMNS
from src.generation.population import Population, PopulationGenerator
from src.taxonomy.validation import PersonaValidator, ValidationResult


def test_generate_returns_correct_count() -> None:
    gen = PopulationGenerator()
    pop = gen.generate(size=50, seed=7, deep_persona_count=5)
    assert len(pop.tier1_personas) == 50
    assert len(pop.tier2_personas) == 5


def test_generate_deterministic_with_seed() -> None:
    gen = PopulationGenerator()
    a = gen.generate(size=20, seed=12345, deep_persona_count=4)
    b = gen.generate(size=20, seed=12345, deep_persona_count=4)
    assert a.tier1_personas[0].to_flat_dict() == b.tier1_personas[0].to_flat_dict()
    assert a.tier1_personas[0].generation_seed == b.tier1_personas[0].generation_seed
    sig_a = sorted(json.dumps(p.to_flat_dict(), sort_keys=True) for p in a.tier2_personas)
    sig_b = sorted(json.dumps(p.to_flat_dict(), sort_keys=True) for p in b.tier2_personas)
    assert sig_a == sig_b


def test_population_to_dataframe_has_all_columns() -> None:
    gen = PopulationGenerator()
    pop = gen.generate(size=15, seed=3, deep_persona_count=3)
    df = pop.to_dataframe()
    assert len(df) == len(pop.tier1_personas) + len(pop.tier2_personas)
    assert "id" in df.columns and "tier" in df.columns
    assert len(df.columns) >= DATAFRAME_MIN_EXPECTED_COLUMNS


def test_population_save_and_load_roundtrip(tmp_path) -> None:
    gen = PopulationGenerator()
    pop = gen.generate(size=12, seed=99, deep_persona_count=3)
    out = tmp_path / "pop_export"
    pop.save(out)
    loaded = Population.load(out)
    assert loaded.id == pop.id
    assert len(loaded.tier1_personas) == len(pop.tier1_personas)
    assert len(loaded.tier2_personas) == len(pop.tier2_personas)
    assert loaded.tier1_personas[0].model_dump_json() == pop.tier1_personas[0].model_dump_json()
    assert loaded.tier2_personas[0].tier == "deep"


def test_tier2_selection_maximizes_diversity() -> None:
    gen = PopulationGenerator()
    pop = gen.generate(size=100, seed=42, deep_persona_count=15)
    tiers = {p.demographics.city_tier for p in pop.tier2_personas}
    assert len(tiers) >= 2


def test_filter_by_attribute_works() -> None:
    gen = PopulationGenerator()
    pop = gen.generate(size=40, seed=11, deep_persona_count=5)
    tier1_only = [p for p in pop.tier1_personas if p.demographics.city_tier == "Tier1"]
    if not tier1_only:
        pytest.skip("no Tier1 personas in this sample")
    filtered = pop.filter(city_tier="Tier1")
    assert all(p.demographics.city_tier == "Tier1" for p in filtered)
    assert len(filtered) >= len(tier1_only)


def test_get_persona_by_id() -> None:
    gen = PopulationGenerator()
    pop = gen.generate(size=10, seed=5, deep_persona_count=2)
    pid = pop.tier1_personas[3].id
    assert pop.get_persona(pid).id == pid
    tid = pop.tier2_personas[0].id
    assert pop.get_persona(tid).tier == "deep"


def test_get_persona_missing_raises() -> None:
    gen = PopulationGenerator()
    pop = gen.generate(size=5, seed=6, deep_persona_count=1)
    with pytest.raises(KeyError):
        pop.get_persona("nonexistent-id")


def test_invalid_personas_are_regenerated() -> None:
    real_validate = PersonaValidator.validate_persona
    call_state = {"first": True}

    def _patched(self: PersonaValidator, persona_id: str, flat: dict) -> ValidationResult:
        if call_state["first"] and persona_id.endswith("-t1-00000"):
            call_state["first"] = False
            return ValidationResult(
                persona_id=persona_id,
                is_valid=False,
                hard_failures=["injected_failure"],
                soft_warnings=[],
            )
        return real_validate(self, persona_id, flat)

    gen = PopulationGenerator()
    with patch.object(PersonaValidator, "validate_persona", _patched):
        pop = gen.generate(size=8, seed=2020, deep_persona_count=2)

    assert pop.metadata.validation_retry_attempts > 0
    assert len(pop.tier1_personas) == 8
