"""Unit tests for repeat purchase, satisfaction, and churn helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.decision.repeat import (
    compute_churn_probability,
    compute_repeat_probability,
    compute_satisfaction,
)
from src.decision.scenarios import ProductConfig

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


def test_satisfaction_increases_repeat_probability(sample_persona: Persona) -> None:
    """Higher satisfaction should weakly increase repeat propensity (habit held fixed)."""

    product = ProductConfig(
        name="LittleJoys Repeat",
        category="nutrition",
        price_inr=400.0,
        age_range=(3, 10),
        key_benefits=["nutrition"],
        form_factor="powder",
        taste_appeal=0.8,
    )
    low_sat = compute_satisfaction(sample_persona, product, month=1)

    tuned = sample_persona.model_copy(
        update={
            "education_learning": sample_persona.education_learning.model_copy(
                update={"science_literacy": 0.95}
            ),
            "lifestyle": sample_persona.lifestyle.model_copy(
                update={"wellness_trend_follower": 0.95}
            ),
        }
    )
    high_sat = compute_satisfaction(tuned, product, month=1)
    assert high_sat >= low_sat
    r_low = compute_repeat_probability(
        sample_persona, low_sat, consecutive_months=2, has_lj_pass=False
    )
    r_high = compute_repeat_probability(
        sample_persona, high_sat, consecutive_months=2, has_lj_pass=False
    )
    assert r_high >= r_low


def test_lj_pass_increases_repeat_rate(sample_persona: Persona) -> None:
    """LJ Pass applies the configured uplift multiplier to repeat probability."""

    product = ProductConfig(
        name="LittleJoys Pass",
        category="nutrition",
        price_inr=380.0,
        age_range=(3, 10),
        key_benefits=["nutrition"],
        form_factor="powder",
    )
    sat = compute_satisfaction(sample_persona, product, month=2)
    base = compute_repeat_probability(sample_persona, sat, consecutive_months=3, has_lj_pass=False)
    boosted = compute_repeat_probability(
        sample_persona, sat, consecutive_months=3, has_lj_pass=True
    )
    assert boosted >= base


def test_habit_formation_increases_with_months(sample_persona: Persona) -> None:
    """Longer consecutive streaks increase habit strength up to the unit cap."""

    sat = 0.75
    r1 = compute_repeat_probability(sample_persona, sat, consecutive_months=1, has_lj_pass=False)
    r4 = compute_repeat_probability(sample_persona, sat, consecutive_months=4, has_lj_pass=False)
    assert r4 >= r1


def test_churn_increases_with_low_satisfaction(sample_persona: Persona) -> None:
    """Lower trailing satisfaction lifts churn probability."""

    high_hist = [0.85, 0.88, 0.9]
    low_hist = [0.25, 0.28, 0.22]
    c_high = compute_churn_probability(sample_persona, high_hist, has_lj_pass=False)
    c_low = compute_churn_probability(sample_persona, low_hist, has_lj_pass=False)
    assert c_low > c_high


def test_churn_lower_with_lj_pass(sample_persona: Persona) -> None:
    """Pass holders use the dampened churn factor on the same history."""

    hist = [0.35, 0.38, 0.36]
    without = compute_churn_probability(sample_persona, hist, has_lj_pass=False)
    with_pass = compute_churn_probability(sample_persona, hist, has_lj_pass=True)
    assert with_pass < without
