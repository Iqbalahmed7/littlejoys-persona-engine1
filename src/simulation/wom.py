"""
Word-of-mouth propagation model for temporal simulation.

Models how satisfied customers spread awareness to their social network.
See ARCHITECTURE.md §9.2.
Full implementation in PRD-006 (Antigravity).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.generation.population import Population


def propagate_wom(
    population: Population,
    adopter_ids: list[str],
    month: int,
    transmission_rate: float = 0.15,
    decay: float = 0.85,
) -> dict[str, float]:
    """
    Propagate word-of-mouth from adopters to non-adopters.

    Returns dict of persona_id → awareness_boost for affected personas.
    """
    raise NotImplementedError("Full implementation in PRD-006")
