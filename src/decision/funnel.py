"""
Purchase funnel decision functions — Layer 0 through Layer 3.

Layer 0: Need Recognition (does the parent recognize a nutrition need?)
Layer 1: Awareness (has the parent heard of this product?)
Layer 2: Consideration (does the parent seriously consider purchasing?)
Layer 3: Purchase (does the parent actually buy?)

Each layer is a function of persona attributes and scenario parameters.
See ARCHITECTURE.md §8 for the full decision model.
Full implementation in PRD-004 (Cursor).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


class DecisionResult:
    """Result of running a persona through the purchase funnel."""

    def __init__(
        self,
        persona_id: str,
        need_score: float,
        awareness_score: float,
        consideration_score: float,
        purchase_score: float,
        outcome: str,
        rejection_stage: str | None,
        rejection_reason: str | None,
    ) -> None:
        self.persona_id = persona_id
        self.need_score = need_score
        self.awareness_score = awareness_score
        self.consideration_score = consideration_score
        self.purchase_score = purchase_score
        self.outcome = outcome
        self.rejection_stage = rejection_stage
        self.rejection_reason = rejection_reason


def compute_need_recognition(persona: Persona, scenario: dict) -> float:
    """Layer 0: Compute need recognition score (0-1)."""
    raise NotImplementedError("Full implementation in PRD-004")


def compute_awareness(persona: Persona, scenario: dict) -> float:
    """Layer 1: Compute awareness score (0-1)."""
    raise NotImplementedError("Full implementation in PRD-004")


def compute_consideration(persona: Persona, scenario: dict, awareness: float) -> float:
    """Layer 2: Compute consideration score (0-1), conditioned on awareness."""
    raise NotImplementedError("Full implementation in PRD-004")


def compute_purchase(persona: Persona, scenario: dict, consideration: float) -> float:
    """Layer 3: Compute purchase probability (0-1), conditioned on consideration."""
    raise NotImplementedError("Full implementation in PRD-004")


def run_funnel(persona: Persona, scenario: dict) -> DecisionResult:
    """Run a persona through the complete purchase funnel."""
    raise NotImplementedError("Full implementation in PRD-004")
