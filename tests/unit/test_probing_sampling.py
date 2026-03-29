"""Unit tests for probing persona sampling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.probing.sampling import sample_personas_for_probe

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


def _sampling_personas(template: Persona) -> list[Persona]:
    personas: list[Persona] = []
    for _sec_index, (sec, income) in enumerate([("A1", 28.0), ("B1", 14.0), ("C1", 6.0)]):
        for _tier_index, (tier, city) in enumerate(
            [("Tier1", "Mumbai"), ("Tier2", "Indore"), ("Tier3", "Nashik")]
        ):
            for repeat in range(4):
                personas.append(
                    template.model_copy(
                        update={
                            "id": f"persona-{sec.lower()}-{tier.lower()}-{repeat}",
                            "demographics": template.demographics.model_copy(
                                update={
                                    "socioeconomic_class": sec,
                                    "city_tier": tier,
                                    "city_name": f"{city}-{repeat}",
                                    "household_income_lpa": income + repeat,
                                }
                            ),
                        },
                        deep=True,
                    )
                )
    return personas


def test_sample_size_respected(sample_persona: Persona) -> None:
    """Returns exactly sample_size personas when pool is larger."""

    personas = _sampling_personas(sample_persona)
    outcomes = {
        persona.id: "adopt" if index % 2 == 0 else "reject"
        for index, persona in enumerate(personas)
    }

    sampled = sample_personas_for_probe(personas, outcomes, sample_size=12, seed=11)

    assert len(sampled) == 12


def test_sample_smaller_pool_returns_all(sample_persona: Persona) -> None:
    """Returns full pool when pool < sample_size."""

    personas = _sampling_personas(sample_persona)[:8]
    outcomes = {persona.id: "adopt" for persona in personas}

    sampled = sample_personas_for_probe(personas, outcomes, sample_size=20, seed=11)

    assert sampled == personas


def test_sample_target_outcome_filters(sample_persona: Persona) -> None:
    """Only returns personas matching target outcome."""

    personas = _sampling_personas(sample_persona)
    outcomes = {
        persona.id: "reject" if index % 3 == 0 else "adopt"
        for index, persona in enumerate(personas)
    }

    sampled = sample_personas_for_probe(
        personas,
        outcomes,
        target_outcome="reject",
        sample_size=8,
        seed=7,
    )

    assert sampled
    assert all(outcomes[persona.id] == "reject" for persona in sampled)


def test_sample_is_deterministic(sample_persona: Persona) -> None:
    """Same seed produces same sample."""

    personas = _sampling_personas(sample_persona)
    outcomes = {
        persona.id: "adopt" if index % 2 == 0 else "reject"
        for index, persona in enumerate(personas)
    }

    first = sample_personas_for_probe(personas, outcomes, sample_size=15, seed=13)
    second = sample_personas_for_probe(personas, outcomes, sample_size=15, seed=13)

    assert [persona.id for persona in first] == [persona.id for persona in second]


def test_sample_covers_strata(sample_persona: Persona) -> None:
    """Sample includes personas from multiple SEC classes."""

    personas = _sampling_personas(sample_persona)
    outcomes = {
        persona.id: "adopt" if index % 2 == 0 else "reject"
        for index, persona in enumerate(personas)
    }

    sampled = sample_personas_for_probe(personas, outcomes, sample_size=12, seed=21)

    sampled_secs = {persona.demographics.socioeconomic_class for persona in sampled}
    sampled_tiers = {persona.demographics.city_tier for persona in sampled}
    assert sampled_secs >= {"A1", "B1", "C1"}
    assert sampled_tiers >= {"Tier1", "Tier2", "Tier3"}


def test_sample_seed_changes_selection(sample_persona: Persona) -> None:
    """Different seeds change the selected members."""

    personas = _sampling_personas(sample_persona)
    outcomes = {
        persona.id: "adopt" if index % 2 == 0 else "reject"
        for index, persona in enumerate(personas)
    }

    first = sample_personas_for_probe(personas, outcomes, sample_size=12, seed=1)
    second = sample_personas_for_probe(personas, outcomes, sample_size=12, seed=2)

    assert [persona.id for persona in first] != [persona.id for persona in second]
