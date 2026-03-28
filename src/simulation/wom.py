"""
Word-of-mouth propagation model for temporal simulation.

Models how satisfied customers spread awareness to their social network.
See ARCHITECTURE.md §9.2.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from src.constants import (
    DEFAULT_WOM_TRANSMISSION_RATE,
    TEMPORAL_WOM_REACH_MAX,
    TEMPORAL_WOM_REACH_MIN,
    WOM_TRANSMISSION_DECAY,
)

if TYPE_CHECKING:
    from src.generation.population import Population


def propagate_wom(
    population: Population,
    adopter_ids: list[str],
    month: int,
    transmission_rate: float = DEFAULT_WOM_TRANSMISSION_RATE,
    decay: float = WOM_TRANSMISSION_DECAY,
    *,
    seed: int = 42,
) -> dict[str, float]:
    """
    Propagate word-of-mouth from adopters to non-adopters.

    Each adopter stochastically reaches a small set of non-adopters; boost scales with
    transmitter tendency, transmission rate, exponential decay by month, and receiver
    social proof bias.

    Args:
        population: Full population (Tier 1 used for id lookup).
        adopter_ids: Personas who can transmit this month.
        month: Current simulation month (0-based or 1-based; decay uses magnitude).
        transmission_rate: Base transmission strength.
        decay: Per-month decay factor applied as ``decay ** month``.
        seed: RNG seed for reproducible reach sets.

    Returns:
        Mapping of receiver persona id → awareness delta (non-adopters only).
    """

    tier1_ids = [p.id for p in population.tier1_personas]
    adopter_set = set(adopter_ids)
    non_adopters = [pid for pid in tier1_ids if pid not in adopter_set]
    if not non_adopters or not adopter_ids:
        return {}

    rng = random.Random(seed ^ (month * 1_000_003) ^ (len(adopter_ids) * 97))
    decay_factor = decay ** max(0, month)
    deltas: dict[str, float] = {}

    for adopter_id in adopter_ids:
        adopter = population.get_persona(adopter_id)
        transmitter = adopter.relationships.wom_transmitter_tendency

        if transmitter <= 0.3:
            continue

        reach = rng.randint(TEMPORAL_WOM_REACH_MIN, TEMPORAL_WOM_REACH_MAX)
        if len(non_adopters) <= reach:
            targets = list(non_adopters)
        else:
            targets = rng.sample(non_adopters, k=reach)

        for target_id in targets:
            receiver = population.get_persona(target_id)
            boost = (
                transmitter
                * transmission_rate
                * decay_factor
                * (1.0 + receiver.psychology.social_proof_bias)
            )
            deltas[target_id] = deltas.get(target_id, 0.0) + boost

    for target_id in deltas:
        deltas[target_id] = min(deltas[target_id], 0.3)

    return deltas
