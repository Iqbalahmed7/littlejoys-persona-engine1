"""Stratified sampling for probing tree interview probes."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from src.constants import DEFAULT_SEED

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona

PROBE_SAMPLE_SIZE = 30
PROBE_STRATIFY_BY = ["socioeconomic_class", "city_tier"]


def _hash_sort_key(seed: int, salt: str, persona_id: str) -> str:
    return hashlib.md5(f"{seed}_{salt}_{persona_id}".encode()).hexdigest()


def sample_personas_for_probe(
    personas: list[Persona],
    outcomes: dict[str, str],
    target_outcome: str | None = None,
    sample_size: int = PROBE_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
) -> list[Persona]:
    """Return a deterministic SEC x city-tier stratified sample."""

    pool = personas
    if target_outcome:
        # "reject" probes should also include "lapsed" personas (bought once, didn't reorder)
        # since journey-aware outcomes distinguish lapsed from full rejectors.
        if target_outcome == "reject":
            pool = [p for p in personas if outcomes.get(p.id) in ("reject", "lapsed")]
        elif target_outcome == "adopt":
            pool = [p for p in personas if outcomes.get(p.id) in ("adopt", "reorder")]
        else:
            pool = [p for p in personas if outcomes.get(p.id) == target_outcome]

    if len(pool) <= sample_size:
        return list(pool)

    strata: dict[str, list[Persona]] = {}
    for persona in pool:
        flat = persona.to_flat_dict()
        key = "_".join(str(flat.get(field, "unknown")) for field in PROBE_STRATIFY_BY)
        strata.setdefault(key, []).append(persona)

    sampled: list[Persona] = []
    sampled_ids: set[str] = set()
    for stratum_key in sorted(strata):
        stratum_personas = strata[stratum_key]
        proportion = len(stratum_personas) / len(pool)
        allocation = max(1, round(proportion * sample_size))
        sorted_personas = sorted(
            stratum_personas,
            key=lambda persona: _hash_sort_key(seed, stratum_key, persona.id),
        )
        for persona in sorted_personas[:allocation]:
            if persona.id not in sampled_ids:
                sampled.append(persona)
                sampled_ids.add(persona.id)

    if len(sampled) < sample_size:
        remaining = [
            persona
            for persona in pool
            if persona.id not in sampled_ids
        ]
        remaining.sort(key=lambda persona: _hash_sort_key(seed, "fill", persona.id))
        sampled.extend(remaining[: sample_size - len(sampled)])

    if len(sampled) > sample_size:
        sampled = sorted(
            sampled,
            key=lambda persona: _hash_sort_key(seed, "trim", persona.id),
        )[:sample_size]

    return sampled
