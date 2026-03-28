"""Unit tests for full-population narrative generation."""

from __future__ import annotations

import re

from src.generation.population import PopulationGenerator


def test_all_personas_get_narratives() -> None:
    """Population generation produces narratives for every persona."""

    pop = PopulationGenerator().generate(size=10, seed=42)
    for persona in pop.tier1_personas:
        assert persona.narrative is not None
        assert len(persona.narrative) > 50


def test_narrative_references_persona_name() -> None:
    """Mock narrative includes the persona's display name."""

    pop = PopulationGenerator().generate(size=5, seed=42)
    for persona in pop.tier1_personas:
        if persona.display_name and persona.narrative:
            assert persona.display_name in persona.narrative


def test_narrative_variety() -> None:
    """Different personas get different narrative openings."""

    pop = PopulationGenerator().generate(size=10, seed=42)
    openings = {persona.narrative[:80] for persona in pop.tier1_personas if persona.narrative}
    assert len(openings) > 1


def test_all_personas_are_deep() -> None:
    """All personas have tier='deep'."""

    pop = PopulationGenerator().generate(size=10, seed=42)
    for persona in pop.tier1_personas:
        assert persona.tier == "deep"


def test_mock_narratives_avoid_raw_decimal_scores() -> None:
    """Narratives should read like prose, not raw score dumps."""

    pop = PopulationGenerator().generate(size=6, seed=42)
    for persona in pop.tier1_personas:
        assert persona.narrative is not None
        assert re.search(r"\b0\.\d+\b", persona.narrative) is None
