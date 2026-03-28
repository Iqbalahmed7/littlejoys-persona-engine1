"""
Layer 4: Repeat purchase and habit formation model.

Models satisfaction → repeat probability → habit strengthening → churn.
Used in temporal simulation (Mode B).
See ARCHITECTURE.md §8.5.
Full implementation in PRD-004 (Cursor).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


def compute_satisfaction(persona: Persona, product: dict, month: int) -> float:
    """Compute satisfaction score after a purchase event."""
    raise NotImplementedError("Full implementation in PRD-004")


def compute_repeat_probability(
    persona: Persona,
    satisfaction: float,
    consecutive_months: int,
    has_lj_pass: bool,
) -> float:
    """Compute probability of repeat purchase given satisfaction and habit strength."""
    raise NotImplementedError("Full implementation in PRD-004")


def compute_churn_probability(
    persona: Persona,
    satisfaction_trajectory: list[float],
    has_lj_pass: bool,
) -> float:
    """Compute probability of churning (stopping purchases)."""
    raise NotImplementedError("Full implementation in PRD-004")
