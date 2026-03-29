"""
Deterministic smart sampling for LLM interview cohort selection (Sprint 12).

Selects a cross-section of personas that are most informative for qualitative follow-up
after a quantitative funnel run.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.constants import (
    FUNNEL_THRESHOLD_AWARENESS,
    FUNNEL_THRESHOLD_CONSIDERATION,
    FUNNEL_THRESHOLD_NEED_RECOGNITION,
    FUNNEL_THRESHOLD_PURCHASE,
)
from src.taxonomy.schema import Persona  # noqa: TC001

SelectionReason = Literal[
    "fragile_yes",
    "persuadable_no",
    "underrepresented",
    "high_need_rejecter",
    "control",
]


def _default_thresholds() -> dict[str, float]:
    return {
        "need": FUNNEL_THRESHOLD_NEED_RECOGNITION,
        "awareness": FUNNEL_THRESHOLD_AWARENESS,
        "consideration": FUNNEL_THRESHOLD_CONSIDERATION,
        "purchase": FUNNEL_THRESHOLD_PURCHASE,
    }


def _hash_sort_key(seed: int, salt: str, persona_id: str) -> str:
    """Deterministic ordering key (same pattern as ``probing.sampling``)."""
    return hashlib.md5(f"{seed}_{salt}_{persona_id}".encode()).hexdigest()


def _segment_key(persona: Persona) -> str:
    d = persona.demographics
    return f"{d.city_tier}_{d.socioeconomic_class}"


def _funnel_scores_row(decision: dict) -> dict[str, float]:
    return {
        "need_score": float(decision["need_score"]),
        "awareness_score": float(decision["awareness_score"]),
        "consideration_score": float(decision["consideration_score"]),
        "purchase_score": float(decision["purchase_score"]),
    }


class SampledPersona(BaseModel):
    """A persona selected for deep LLM interview with reason."""

    model_config = ConfigDict(extra="forbid")

    persona_id: str
    selection_reason: SelectionReason
    reason_detail: str
    funnel_scores: dict[str, float] = Field(default_factory=dict)


class SmartSample(BaseModel):
    """Result of smart sampling from a funnel run."""

    model_config = ConfigDict(extra="forbid")

    selections: list[SampledPersona]
    population_size: int
    total_adopters: int
    total_rejecters: int
    sample_seed: int

    @property
    def persona_ids(self) -> list[str]:
        return [s.persona_id for s in self.selections]

    def personas_by_reason(self, reason: SelectionReason) -> list[SampledPersona]:
        return [s for s in self.selections if s.selection_reason == reason]


def select_smart_sample(
    personas: list[Persona],
    decisions: dict[str, dict],
    thresholds: dict[str, float] | None = None,
    target_size: int = 18,
    seed: int = 42,
) -> SmartSample:
    """
    Select ``target_size`` personas across five insight buckets, deterministically.

    Unfilled bucket slots roll into the control bucket.
    """
    t = {**_default_thresholds(), **(thresholds or {})}
    n_pop = len(personas)
    if n_pop == 0:
        return SmartSample(
            selections=[],
            population_size=0,
            total_adopters=0,
            total_rejecters=0,
            sample_seed=seed,
        )

    total_adopters = sum(1 for p in personas if decisions.get(p.id, {}).get("outcome") == "adopt")
    total_rejecters = n_pop - total_adopters

    # --- Bucket candidates ---
    fragile: list[tuple[Persona, float, str]] = []
    persuadable: list[tuple[Persona, float, str]] = []
    underrep: list[tuple[Persona, float, str]] = []
    high_need: list[tuple[Persona, float, str]] = []

    seg_counts: Counter[str] = Counter(_segment_key(p) for p in personas)
    minority_segments = {s for s, c in seg_counts.items() if (c / n_pop) < 0.20}

    tp, tc = t["purchase"], t["consideration"]

    for persona in personas:
        pid = persona.id
        d = decisions.get(pid)
        if not d:
            continue
        fs = _funnel_scores_row(d)
        outcome = str(d.get("outcome", ""))

        if outcome == "adopt":
            ps = fs["purchase_score"]
            if tp <= ps <= tp + 0.10:
                margin = ps - tp
                fragile.append(
                    (
                        persona,
                        margin,
                        f"purchase_score {ps:.2f} vs threshold {tp:.2f} (margin +{margin:.2f})",
                    )
                )
            if _segment_key(persona) in minority_segments:
                underrep.append(
                    (
                        persona,
                        fs["purchase_score"],
                        f"minority segment {_segment_key(persona)} (adopter)",
                    )
                )

        if outcome == "reject":
            stage = d.get("rejection_stage")
            if stage == "purchase":
                ps = fs["purchase_score"]
                if ps < tp and ps >= tp - 0.10:
                    gap = tp - ps
                    persuadable.append(
                        (
                            persona,
                            gap,
                            f"purchase stage: purchase_score {ps:.2f} vs threshold {tp:.2f}",
                        )
                    )
            elif stage == "consideration":
                cs = fs["consideration_score"]
                if cs < tc and cs >= tc - 0.10:
                    gap = tc - cs
                    persuadable.append(
                        (
                            persona,
                            gap,
                            f"consideration stage: consideration_score {cs:.2f} vs threshold {tc:.2f}",
                        )
                    )

            ns = fs["need_score"]
            if ns >= 0.65:
                high_need.append((persona, ns, f"need_score {ns:.2f} but rejected"))

    fragile.sort(key=lambda x: x[1])
    persuadable.sort(key=lambda x: x[1])
    underrep.sort(key=lambda x: -x[1])
    high_need.sort(key=lambda x: -x[1])

    used: set[str] = set()
    selections: list[SampledPersona] = []

    def push(
        persona: Persona,
        reason: SelectionReason,
        detail: str,
        scores: dict[str, float],
    ) -> None:
        if persona.id in used:
            return
        used.add(persona.id)
        selections.append(
            SampledPersona(
                persona_id=persona.id,
                selection_reason=reason,
                reason_detail=detail,
                funnel_scores=scores,
            )
        )

    def take_from(
        items: list[tuple[Persona, float, str]],
        reason: SelectionReason,
        n: int,
    ) -> int:
        """Take up to ``n`` distinct personas; return count taken."""
        got = 0
        for persona, _metric, detail in items:
            if got >= n:
                break
            if persona.id in used:
                continue
            push(persona, reason, detail, _funnel_scores_row(decisions[persona.id]))
            got += 1
        return got

    take_from(fragile, "fragile_yes", 4)
    take_from(persuadable, "persuadable_no", 4)
    take_from(underrep, "underrepresented", 3)
    take_from(high_need, "high_need_rejecter", 4)

    cap = min(target_size, n_pop)
    need_control = cap - len(selections)
    pool = sorted(
        [p for p in personas if p.id not in used],
        key=lambda p: _hash_sort_key(seed, "control", p.id),
    )
    for persona in pool[: max(0, need_control)]:
        d = decisions.get(persona.id, {})
        push(
            persona,
            "control",
            "control sample (deterministic hash ordering)",
            _funnel_scores_row(d) if d else {},
        )

    if len(selections) < cap:
        for persona in sorted(personas, key=lambda p: _hash_sort_key(seed, "fill", p.id)):
            if len(selections) >= cap:
                break
            if persona.id in used:
                continue
            d = decisions.get(persona.id, {})
            push(
                persona,
                "control",
                "fill to target size",
                _funnel_scores_row(d) if d else {},
            )

    selections = selections[:cap]

    return SmartSample(
        selections=selections,
        population_size=n_pop,
        total_adopters=total_adopters,
        total_rejecters=total_rejecters,
        sample_seed=seed,
    )
