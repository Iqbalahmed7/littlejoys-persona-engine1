"""Unit tests for Gaussian copula and conditional rule engine."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from src.constants import ATTRIBUTE_MAX, ATTRIBUTE_MIN, CORRELATION_TOLERANCE
from src.taxonomy.correlations import (
    PSYCHOGRAPHIC_CONTINUOUS_COLUMNS,
    ConditionalRuleEngine,
    GaussianCopulaGenerator,
    _apply_demographic_conditioning,
    default_psych_correlation_rules,
)


def _minimal_demographics(n: int, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tiers = rng.choice(["Tier1", "Tier2", "Tier3"], size=n, p=[0.45, 0.35, 0.20])
    return pd.DataFrame(
        {
            "city_tier": tiers,
            "city_name": ["Mumbai"] * n,
            "household_income_lpa": rng.uniform(4.0, 25.0, size=n),
            "parent_age": rng.integers(25, 41, size=n),
            "parent_gender": rng.choice(["female", "male"], size=n, p=[0.85, 0.15]),
            "num_children": rng.integers(1, 4, size=n),
            "youngest_child_age": rng.integers(2, 15, size=n),
            "oldest_child_age": rng.integers(2, 15, size=n),
            "education_level": rng.choice(
                ["high_school", "bachelors", "masters", "doctorate", "professional"],
                size=n,
            ),
            "employment_status": rng.choice(
                ["homemaker", "part_time", "full_time", "self_employed", "freelance"],
                size=n,
                p=[0.40, 0.10, 0.35, 0.08, 0.07],
            ),
            "family_structure": rng.choice(["nuclear", "joint", "single_parent"], size=n, p=[0.6, 0.3, 0.1]),
            "dietary_culture": rng.choice(
                ["vegetarian", "eggetarian", "non_vegetarian", "vegan"],
                size=n,
            ),
        }
    )


def test_correlation_matrix_is_positive_semi_definite() -> None:
    gen = GaussianCopulaGenerator()
    corr = gen.correlation_matrix()
    eig = np.linalg.eigvalsh(corr)
    assert np.min(eig) >= -1e-6
    assert corr.shape[0] == len(PSYCHOGRAPHIC_CONTINUOUS_COLUMNS)
    np.testing.assert_allclose(np.diag(corr), 1.0, atol=1e-5)


def test_copula_output_all_values_in_0_1() -> None:
    n = 50
    demo = _minimal_demographics(n, seed=1)
    gen = GaussianCopulaGenerator()
    psych = gen.generate(n, demo, seed=123)
    assert psych.shape == (n, len(PSYCHOGRAPHIC_CONTINUOUS_COLUMNS))
    assert psych.to_numpy().min() >= ATTRIBUTE_MIN
    assert psych.to_numpy().max() <= ATTRIBUTE_MAX


def test_target_correlations_achieved_within_tolerance(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.taxonomy.correlations._apply_demographic_conditioning",
        lambda psych, demo: psych,
    )
    n = 5000
    demo = _minimal_demographics(n, seed=2)
    gen = GaussianCopulaGenerator()
    psych = gen.generate(n, demo, seed=99)
    a, b = "deal_seeking_intensity", "budget_consciousness"
    rho_tgt = default_psych_correlation_rules()[_canonical(a, b)]
    expected_spearman = (6.0 / np.pi) * np.arcsin(np.clip(rho_tgt / 2.0, -1.0, 1.0))
    spearman_hat = psych[a].corr(psych[b], method="spearman")
    assert abs(spearman_hat - expected_spearman) <= CORRELATION_TOLERANCE + 0.08


def _canonical(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def test_deterministic_with_same_seed() -> None:
    n = 30
    demo = _minimal_demographics(n, seed=3)
    gen = GaussianCopulaGenerator()
    first = gen.generate(n, demo, seed=7)
    second = gen.generate(n, demo, seed=7)
    pd.testing.assert_frame_equal(first, second)


def test_different_seed_produces_different_output() -> None:
    n = 40
    demo = _minimal_demographics(n, seed=4)
    gen = GaussianCopulaGenerator()
    a_df = gen.generate(n, demo, seed=11)
    b_df = gen.generate(n, demo, seed=12)
    assert not np.allclose(a_df.to_numpy(), b_df.to_numpy())


def test_conditional_rules_shift_tier3_authority_bias() -> None:
    engine = ConditionalRuleEngine()
    base = pd.DataFrame(
        {
            "city_tier": ["Tier3"],
            "employment_status": ["homemaker"],
            "parent_gender": ["female"],
            "num_children": [2],
            "family_structure": ["nuclear"],
            "household_income_lpa": [8.0],
            "authority_bias": [0.40],
            "digital_payment_comfort": [0.50],
        }
    )
    out = engine.apply(base)
    assert float(out.loc[0, "authority_bias"]) > 0.40 + 1e-6


def test_conditional_rules_shift_working_mother_time_scarcity() -> None:
    engine = ConditionalRuleEngine()
    base = pd.DataFrame(
        {
            "city_tier": ["Tier1"],
            "employment_status": ["full_time"],
            "parent_gender": ["female"],
            "num_children": [2],
            "family_structure": ["nuclear"],
            "household_income_lpa": [12.0],
            "perceived_time_scarcity": [0.30],
            "guilt_driven_spending": [0.20],
        }
    )
    out = engine.apply(base)
    assert float(out.loc[0, "perceived_time_scarcity"]) > 0.30
    assert float(out.loc[0, "guilt_driven_spending"]) > 0.20


def test_conditional_rules_clip_to_valid_range() -> None:
    engine = ConditionalRuleEngine()
    base = pd.DataFrame(
        {
            "city_tier": ["Tier3"],
            "employment_status": ["homemaker"],
            "parent_gender": ["female"],
            "num_children": [2],
            "family_structure": ["nuclear"],
            "household_income_lpa": [8.0],
            "authority_bias": [0.98],
            "digital_payment_comfort": [0.02],
        }
    )
    out = engine.apply(base)
    assert ATTRIBUTE_MIN <= float(out.loc[0, "authority_bias"]) <= ATTRIBUTE_MAX
    assert ATTRIBUTE_MIN <= float(out.loc[0, "digital_payment_comfort"]) <= ATTRIBUTE_MAX


def test_demographic_conditioning_changes_income_budget_relationship() -> None:
    n = 2000
    rng = np.random.default_rng(0)
    demo = _minimal_demographics(n, seed=5)
    demo["household_income_lpa"] = rng.uniform(3.0, 30.0, size=n)
    z = np.random.default_rng(42).standard_normal(size=(n, len(PSYCHOGRAPHIC_CONTINUOUS_COLUMNS)))
    u = scipy_stats.norm.cdf(z)
    psych = pd.DataFrame(u, columns=list(PSYCHOGRAPHIC_CONTINUOUS_COLUMNS))
    adjusted = _apply_demographic_conditioning(psych, demo)
    rho_after = adjusted["budget_consciousness"].corr(pd.Series(demo["household_income_lpa"].values))
    assert rho_after < -0.08
