"""
Layer 4: Repeat purchase and habit formation model.

Models satisfaction → repeat probability → habit strengthening → churn.
Used in temporal simulation (Mode B).
See ARCHITECTURE.md §8.5.
"""

from __future__ import annotations

import math
import statistics
from typing import TYPE_CHECKING

from src.constants import (
    ATTRIBUTE_MAX,
    ATTRIBUTE_MIN,
    REPEAT_CHURN_LJ_PASS_FACTOR,
    REPEAT_HABIT_BASE,
    REPEAT_HABIT_PER_MONTH,
    REPEAT_LJ_PASS_MULTIPLIER,
    REPEAT_SATISFACTION_HISTORY_MONTHS,
)

if TYPE_CHECKING:
    from src.decision.scenarios import ProductConfig
    from src.taxonomy.schema import Persona


def _clip_unit(x: float) -> float:
    if not math.isfinite(x):
        return ATTRIBUTE_MIN
    return max(ATTRIBUTE_MIN, min(ATTRIBUTE_MAX, x))


def compute_satisfaction(persona: Persona, product: ProductConfig, month: int) -> float:
    """
    Post-purchase satisfaction from taste fit, perceived efficacy, and price-value.

    Args:
        persona: Purchaser persona.
        product: Product configuration.
        month: Simulation month index (1-based); modulates mild habit smoothing.

    Returns:
        Satisfaction in ``[0, 1]``.
    """

    _ = month  # reserved for future seasonality / fatigue
    taste_alignment = _clip_unit(
        product.taste_appeal * (1.0 - persona.relationships.child_taste_veto * 0.5)
    )
    perceived_effectiveness = _clip_unit(
        product.taste_appeal * 0.45 + persona.education_learning.science_literacy * 0.55
    )
    ref = max(persona.daily_routine.price_reference_point, 1.0)
    price_ratio = min(3.0, product.price_inr / ref)
    price_value = _clip_unit(1.0 - (price_ratio - 1.0) * 0.35)

    raw = taste_alignment * 0.35 + perceived_effectiveness * 0.40 + price_value * 0.25
    return _clip_unit(raw)


def compute_repeat_probability(
    persona: Persona,
    satisfaction: float,
    consecutive_months: int,
    has_lj_pass: bool,
) -> float:
    """
    Repeat purchase probability given satisfaction, habit, and LJ Pass uplift.

    Habit strength increases with consecutive active months, capped at 1.0.
    """

    sat = _clip_unit(satisfaction)
    habit = min(
        ATTRIBUTE_MAX,
        REPEAT_HABIT_BASE + REPEAT_HABIT_PER_MONTH * max(0, consecutive_months),
    )
    repeat = sat * habit * (REPEAT_LJ_PASS_MULTIPLIER if has_lj_pass else 1.0)
    _ = persona  # reserved for future heterogeneity
    return _clip_unit(repeat)


def compute_churn_probability(
    persona: Persona,
    satisfaction_trajectory: list[float],
    has_lj_pass: bool,
) -> float:
    """
    Churn probability from recent satisfaction mean; LJ Pass dampens churn.

    Args:
        persona: Active customer persona.
        satisfaction_trajectory: Historical monthly satisfaction values (most recent last).
        has_lj_pass: Whether the persona holds LittleJoys Pass benefits.

    Returns:
        Churn probability in ``[0, 1]``.
    """

    _ = persona
    window = satisfaction_trajectory[-REPEAT_SATISFACTION_HISTORY_MONTHS:]
    mean_sat = ATTRIBUTE_MAX / 2 if not window else float(statistics.mean(window))
    mean_sat = _clip_unit(mean_sat)
    base = 1.0 - mean_sat
    factor = REPEAT_CHURN_LJ_PASS_FACTOR if has_lj_pass else 1.0
    return _clip_unit(base * factor)
