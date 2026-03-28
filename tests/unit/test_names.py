from __future__ import annotations

from unittest.mock import patch

from src.generation.names import generate_persona_id, generate_persona_name
from src.generation.population import PopulationGenerator
from src.taxonomy.validation import PersonaValidator, ValidationResult


def test_generate_persona_name_deterministic() -> None:
    name_a = generate_persona_name(gender="female", index=3, seed=99)
    name_b = generate_persona_name(gender="female", index=3, seed=99)
    assert name_a == name_b


def test_generate_persona_name_male_vs_female() -> None:
    name_f = generate_persona_name(gender="female", index=5, seed=42)
    name_m = generate_persona_name(gender="male", index=5, seed=42)
    assert name_f != name_m


def test_generate_persona_id_format() -> None:
    pid = generate_persona_id(
        name="Priya",
        city_name="New Delhi",
        gender="female",
        parent_age=32,
        index=7,
    )
    assert pid == "Priya-NewDelhi-Mom-32"


def test_duplicate_id_resolution() -> None:
    """Population generation handles duplicate IDs."""

    def _always_same_pid(*_args, **_kwargs) -> str:
        return "SameCity-Mom-30"

    def _always_valid(self: PersonaValidator, persona_id: str, flat: dict) -> ValidationResult:
        return ValidationResult(
            persona_id=persona_id,
            is_valid=True,
            hard_failures=[],
            soft_warnings=[],
        )

    with (
        patch("src.generation.population.generate_persona_id", side_effect=_always_same_pid),
        patch("src.generation.population.PersonaValidator.validate_persona", _always_valid),
    ):
        pop = PopulationGenerator().generate(size=6, seed=1, deep_persona_count=0)

    ids = [p.id for p in pop.tier1_personas]
    assert len(ids) == 6
    assert len(set(ids)) == 6

    assert ids[0] == "SameCity-Mom-30"
    assert ids[1] == "SameCity-Mom-30-2"
    assert ids[2] == "SameCity-Mom-30-3"
