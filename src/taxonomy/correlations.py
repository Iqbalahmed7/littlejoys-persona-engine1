"""
Correlation enforcement via Gaussian copula and conditional rules.

See ARCHITECTURE.md §5.2 for the correlation specification.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import structlog
from scipy import stats

from src.constants import (
    ATTRIBUTE_MAX,
    ATTRIBUTE_MIN,
    CHOLESKY_DIAGONAL_JITTER,
    CONDITIONAL_SHIFT_FIRST_CHILD_ANXIETY,
    CONDITIONAL_SHIFT_HIGH_INCOME_BRAND_PREMIUM,
    CONDITIONAL_SHIFT_HIGH_INCOME_PRICE_SENSITIVITY,
    CONDITIONAL_SHIFT_JOINT_EXTENDED_FAMILY,
    CONDITIONAL_SHIFT_JOINT_FAMILY_INFLUENCE,
    CONDITIONAL_SHIFT_TIER3_AUTHORITY_BIAS,
    CONDITIONAL_SHIFT_TIER3_DIGITAL_COMFORT,
    CONDITIONAL_SHIFT_WORKING_MOTHER_TIME_SCARCITY,
    CONDITIONAL_SHIFT_WORKING_MOTHER_WORK_GUILT,
    DEMOGRAPHIC_CHILD_AGE_SHIFT,
    DEMOGRAPHIC_CHILD_CONDITIONING_CHILD_AUTONOMY_OLDEST,
    DEMOGRAPHIC_CHILD_CONDITIONING_CHILD_PESTER_OLDER,
    DEMOGRAPHIC_CHILD_CONDITIONING_CHILD_TASTE_VETO_OLDER,
    DEMOGRAPHIC_CHILD_CONDITIONING_COMPARISON_OLDER,
    DEMOGRAPHIC_CHILD_CONDITIONING_HEALTH_ANXIETY_YOUNG,
    DEMOGRAPHIC_CHILD_CONDITIONING_SUPPLEMENT_BELIEF_OLDER,
    DEMOGRAPHIC_EMPLOYMENT_SHIFT,
    DEMOGRAPHIC_FAMILY_STRUCTURE_SHIFT,
    DEMOGRAPHIC_TIER_INDICATOR_SHIFT,
    DEMOGRAPHIC_Z_SHIFT_SCALE,
    HIGH_INCOME_LPA_THRESHOLD,
    NEAR_PSD_EIGENVALUE_FLOOR,
    NEAR_PSD_MAX_ITERATIONS,
    OLDER_CHILD_AGE_GTE,
    OLDEST_CHILD_AGE_GTE_10,
    POSTGRADUATE_EDUCATION_LEVELS,
    YOUNG_CHILD_AGE_LT,
)
from src.taxonomy.schema import list_psychographic_continuous_attributes

log = structlog.get_logger(__name__)

PSYCHOGRAPHIC_CONTINUOUS_COLUMNS: tuple[str, ...] = list_psychographic_continuous_attributes()

_INCOME_Z_TARGETS: tuple[tuple[str, float], ...] = (
    ("budget_consciousness", -0.55),
    ("deal_seeking_intensity", -0.40),
    ("health_spend_priority", 0.35),
    ("indie_brand_openness", 0.25),
)

_TIER3_SHIFT_TARGETS: tuple[tuple[str, float], ...] = (
    ("medical_authority_trust", 0.50),
    ("authority_bias", 0.45),
    ("digital_payment_comfort", -0.35),
    ("elder_advice_weight", 0.40),
)
_TIER1_SHIFT_TARGETS: tuple[tuple[str, float], ...] = (
    ("online_vs_offline_preference", 0.45),
    ("subscription_comfort", 0.35),
)
_EMPLOYMENT_FULL_TIME_TARGETS: tuple[tuple[str, float], ...] = (
    ("perceived_time_scarcity", 0.55),
    ("meal_planning_habit", -0.50),
    ("convenience_food_acceptance", 0.40),
    ("guilt_driven_spending", 0.35),
)
_EMPLOYMENT_HOMEMAKER_TARGETS: tuple[tuple[str, float], ...] = (
    ("meal_planning_habit", 0.35),
    ("recipe_experimentation", 0.30),
)
_NUM_CHILDREN_GT2_BUDGET_RHO = 0.35
_NUM_CHILDREN_EQ1_TARGETS: tuple[tuple[str, float], ...] = (
    ("health_anxiety", 0.40),
    ("guilt_sensitivity", 0.35),
)
_JOINT_FAMILY_TARGETS: tuple[tuple[str, float], ...] = (("elder_advice_weight", 0.55),)
_POSTGRAD_TARGETS: tuple[tuple[str, float], ...] = (
    ("science_literacy", 0.50),
    ("label_reading_habit", 0.40),
    ("self_research_tendency", 0.45),
)


def default_psych_correlation_rules() -> dict[tuple[str, str], float]:
    """
    Default pairwise Pearson targets for Gaussian copula columns.

    Sourced from ARCHITECTURE.md §5.2 and sprint briefing pairs, using
    ``schema.py`` field names. Boolean / categorical taxonomy signals are omitted
    from the copula matrix and handled via conditioning instead.
    """
    pairs: dict[tuple[str, str], float] = {
        ("health_anxiety", "supplement_necessity_belief"): 0.55,
        ("authority_bias", "social_proof_bias"): 0.40,
        ("perceived_time_scarcity", "convenience_food_acceptance"): 0.50,
        ("online_vs_offline_preference", "digital_payment_comfort"): 0.65,
        ("deal_seeking_intensity", "budget_consciousness"): 0.70,
        ("comparison_anxiety", "research_before_purchase"): 0.35,
        ("health_anxiety", "preventive_vs_reactive_health"): 0.45,
        ("health_anxiety", "health_spend_priority"): 0.50,
        ("health_anxiety", "budget_consciousness"): -0.25,
        ("comparison_anxiety", "peer_influence_strength"): 0.50,
        ("comparison_anxiety", "social_proof_bias"): 0.45,
        ("guilt_sensitivity", "best_for_my_child_intensity"): 0.55,
        ("guilt_sensitivity", "emotional_persuasion_susceptibility"): 0.40,
        ("science_literacy", "authority_bias"): -0.30,
        ("science_literacy", "food_first_belief"): 0.25,
        ("brand_loyalty_tendency", "status_quo_bias"): 0.50,
        ("status_quo_bias", "risk_tolerance"): -0.40,
        ("simplicity_preference", "decision_speed"): -0.30,
        ("traditional_vs_modern_spectrum", "ayurveda_affinity"): -0.55,
        ("traditional_vs_modern_spectrum", "western_brand_trust"): 0.45,
        ("label_reading_habit", "transparency_importance"): 0.55,
        ("label_reading_habit", "clean_label_importance"): 0.50,
        ("research_before_purchase", "information_need"): 0.60,
        ("research_before_purchase", "decision_speed"): 0.40,
        ("online_vs_offline_preference", "subscription_comfort"): 0.40,
        ("cooking_enthusiasm", "recipe_experimentation"): 0.50,
        ("cooking_time_available", "recipe_experimentation"): 0.35,
    }
    return {_canonical_pair(a, b): rho for (a, b), rho in pairs.items()}


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def _aggregate_pairwise_rules(
    rules: dict[tuple[str, str], float],
) -> dict[tuple[str, str], float]:
    buckets: dict[tuple[str, str], list[float]] = {}
    for (a, b), rho in rules.items():
        key = _canonical_pair(a, b)
        buckets.setdefault(key, []).append(float(rho))
    return {k: float(np.mean(v)) for k, v in buckets.items()}


def _nearest_positive_semidefinite_correlation(matrix: np.ndarray) -> np.ndarray:
    x = np.asarray(matrix, dtype=np.float64)
    for _ in range(NEAR_PSD_MAX_ITERATIONS):
        x = (x + x.T) / 2.0
        vals, vecs = np.linalg.eigh(x)
        vals = np.maximum(vals, NEAR_PSD_EIGENVALUE_FLOOR)
        x = (vecs * vals) @ vecs.T
        diag = np.clip(np.diag(x), 1e-12, None)
        inv_sd = 1.0 / np.sqrt(diag)
        x = x * np.outer(inv_sd, inv_sd)
        np.fill_diagonal(x, 1.0)
    return x


def _clip_psych_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = out[col].clip(ATTRIBUTE_MIN, ATTRIBUTE_MAX)
    return out


class GaussianCopulaGenerator:
    """Gaussian copula over all ``UnitInterval`` psychographic identity fields."""

    def __init__(self, correlation_rules: dict[tuple[str, str], float] | None = None) -> None:
        merged = default_psych_correlation_rules()
        if correlation_rules:
            for (a, b), rho in correlation_rules.items():
                merged[_canonical_pair(a, b)] = float(rho)
        self.correlation_rules = _aggregate_pairwise_rules(merged)
        self._column_index: dict[str, int] = {
            name: i for i, name in enumerate(PSYCHOGRAPHIC_CONTINUOUS_COLUMNS)
        }
        self._correlation_matrix: np.ndarray | None = None

    def _build_correlation_matrix(self) -> np.ndarray:
        dim = len(PSYCHOGRAPHIC_CONTINUOUS_COLUMNS)
        sigma = np.eye(dim, dtype=np.float64)
        unknown_pairs: list[tuple[str, str]] = []
        for (a, b), rho in self.correlation_rules.items():
            if a not in self._column_index or b not in self._column_index:
                unknown_pairs.append((a, b))
                continue
            i, j = self._column_index[a], self._column_index[b]
            sigma[i, j] = sigma[j, i] = rho
        if unknown_pairs:
            log.warning("correlation_rules_skipped_unknown_attributes", pairs=unknown_pairs[:20])
        sigma = _nearest_positive_semidefinite_correlation(sigma)
        eig_min = float(np.min(np.linalg.eigvalsh(sigma)))
        log.info("correlation_matrix_ready", dimension=dim, min_eigenvalue=eig_min)
        return sigma

    def generate(
        self,
        n: int,
        demographics: pd.DataFrame,
        seed: int,
    ) -> pd.DataFrame:
        """
        Generate correlated psychographic attributes.

        Args:
            n: Number of personas (must match ``len(demographics)``).
            demographics: Pre-sampled demographic attributes used for conditioning.
            seed: Random seed for reproducibility.

        Returns:
            DataFrame with all continuous (0-1) psychographic attributes.

        Raises:
            ValueError: If ``n`` does not match demographics row count.
        """
        if len(demographics) != n:
            msg = f"n ({n}) must match demographics row count ({len(demographics)})"
            raise ValueError(msg)

        if self._correlation_matrix is None:
            self._correlation_matrix = self._build_correlation_matrix()
        corr = self._correlation_matrix

        rng = np.random.default_rng(seed)
        dim = corr.shape[0]
        try:
            chol = np.linalg.cholesky(corr)
        except np.linalg.LinAlgError:
            corr_j = corr + np.eye(dim) * CHOLESKY_DIAGONAL_JITTER
            chol = np.linalg.cholesky(corr_j)
            log.warning("cholesky_jitter_applied", jitter=CHOLESKY_DIAGONAL_JITTER)

        z = rng.standard_normal(size=(n, dim)) @ chol.T
        uniform = stats.norm.cdf(z)

        psych = pd.DataFrame(uniform, columns=list(PSYCHOGRAPHIC_CONTINUOUS_COLUMNS))
        psych = _apply_demographic_conditioning(psych, demographics)
        psych = _clip_psych_columns(psych, PSYCHOGRAPHIC_CONTINUOUS_COLUMNS)

        head_cols = [c for c in PSYCHOGRAPHIC_CONTINUOUS_COLUMNS[:3]]
        sample_corr = psych[head_cols].corr().to_numpy()
        log.info(
            "gaussian_copula_generated",
            n=n,
            seed=seed,
            preview_corr_head=float(sample_corr[0, 1]) if sample_corr.size > 1 else None,
        )
        return psych

    def correlation_matrix(self) -> np.ndarray:
        if self._correlation_matrix is None:
            self._correlation_matrix = self._build_correlation_matrix()
        return self._correlation_matrix


def _apply_demographic_conditioning(
    psychographics: pd.DataFrame,
    demographics: pd.DataFrame,
) -> pd.DataFrame:
    out = psychographics.copy()
    s = DEMOGRAPHIC_Z_SHIFT_SCALE

    inc = demographics["household_income_lpa"].astype(float).to_numpy()
    mu, sig = float(np.mean(inc)), float(np.std(inc))
    if sig < 1e-9:
        sig = 1.0
    z_inc = (inc - mu) / sig
    for col, rho in _INCOME_Z_TARGETS:
        if col in out.columns:
            out[col] = out[col] + s * rho * z_inc

    tier = demographics["city_tier"].astype(str)
    tier3 = tier.eq("Tier3").to_numpy()
    tier1 = tier.eq("Tier1").to_numpy()
    t = DEMOGRAPHIC_TIER_INDICATOR_SHIFT
    for col, w in _TIER3_SHIFT_TARGETS:
        if col in out.columns:
            out.loc[tier3, col] = out.loc[tier3, col] + t * w
    for col, w in _TIER1_SHIFT_TARGETS:
        if col in out.columns:
            out.loc[tier1, col] = out.loc[tier1, col] + t * w

    employment = demographics["employment_status"].astype(str)
    full_time = employment.eq("full_time").to_numpy()
    homemaker = employment.eq("homemaker").to_numpy()
    e = DEMOGRAPHIC_EMPLOYMENT_SHIFT
    for col, w in _EMPLOYMENT_FULL_TIME_TARGETS:
        if col in out.columns:
            out.loc[full_time, col] = out.loc[full_time, col] + e * w
    for col, w in _EMPLOYMENT_HOMEMAKER_TARGETS:
        if col in out.columns:
            out.loc[homemaker, col] = out.loc[homemaker, col] + e * w

    num_children = demographics["num_children"].astype(int).to_numpy()
    gt2 = num_children > 2
    eq1 = num_children == 1
    f = DEMOGRAPHIC_FAMILY_STRUCTURE_SHIFT
    if "budget_consciousness" in out.columns:
        out.loc[gt2, "budget_consciousness"] = (
            out.loc[gt2, "budget_consciousness"] + f * _NUM_CHILDREN_GT2_BUDGET_RHO
        )
    for col, w in _NUM_CHILDREN_EQ1_TARGETS:
        if col in out.columns:
            out.loc[eq1, col] = out.loc[eq1, col] + f * w

    joint = demographics["family_structure"].astype(str).eq("joint").to_numpy()
    for col, w in _JOINT_FAMILY_TARGETS:
        if col in out.columns:
            out.loc[joint, col] = out.loc[joint, col] + f * w

    education = demographics["education_level"].astype(str)
    postgrad = education.isin(POSTGRADUATE_EDUCATION_LEVELS).to_numpy()
    for col, w in _POSTGRAD_TARGETS:
        if col in out.columns:
            out.loc[postgrad, col] = out.loc[postgrad, col] + f * w

    youngest = demographics["youngest_child_age"].astype(int).to_numpy()
    c = DEMOGRAPHIC_CHILD_AGE_SHIFT
    young = youngest < YOUNG_CHILD_AGE_LT
    older = youngest >= OLDER_CHILD_AGE_GTE
    oldest = youngest >= OLDEST_CHILD_AGE_GTE_10
    if "health_anxiety" in out.columns:
        out.loc[young, "health_anxiety"] = (
            out.loc[young, "health_anxiety"]
            + c * DEMOGRAPHIC_CHILD_CONDITIONING_HEALTH_ANXIETY_YOUNG
        )
    if "comparison_anxiety" in out.columns:
        out.loc[older, "comparison_anxiety"] = (
            out.loc[older, "comparison_anxiety"]
            + c * DEMOGRAPHIC_CHILD_CONDITIONING_COMPARISON_OLDER
        )
    if "child_taste_veto" in out.columns:
        out.loc[older, "child_taste_veto"] = (
            out.loc[older, "child_taste_veto"]
            + c * DEMOGRAPHIC_CHILD_CONDITIONING_CHILD_TASTE_VETO_OLDER
        )
    if "child_pester_power" in out.columns:
        out.loc[older, "child_pester_power"] = (
            out.loc[older, "child_pester_power"]
            + c * DEMOGRAPHIC_CHILD_CONDITIONING_CHILD_PESTER_OLDER
        )
    if "child_autonomy_given" in out.columns:
        out.loc[oldest, "child_autonomy_given"] = (
            out.loc[oldest, "child_autonomy_given"]
            + c * DEMOGRAPHIC_CHILD_CONDITIONING_CHILD_AUTONOMY_OLDEST
        )
    if "supplement_necessity_belief" in out.columns:
        out.loc[older, "supplement_necessity_belief"] = (
            out.loc[older, "supplement_necessity_belief"]
            + c * DEMOGRAPHIC_CHILD_CONDITIONING_SUPPLEMENT_BELIEF_OLDER
        )

    return out


class ConditionalRuleEngine:
    """Sprint briefing additive shifts on a merged demographic + psychographic frame."""

    def apply(self, population: pd.DataFrame) -> pd.DataFrame:
        """
        Apply conditional rules to shift attribute values, clipping to [0, 1].

        Args:
            population: Rows with demographic columns plus psychographic UnitInterval fields.

        Returns:
            Copy with shifts applied and psychographic columns clipped.
        """
        out = population.copy()
        tier3 = out["city_tier"].astype(str).eq("Tier3")
        if "authority_bias" in out.columns:
            out.loc[tier3, "authority_bias"] = (
                out.loc[tier3, "authority_bias"] + CONDITIONAL_SHIFT_TIER3_AUTHORITY_BIAS
            )
        if "digital_payment_comfort" in out.columns:
            out.loc[tier3, "digital_payment_comfort"] = (
                out.loc[tier3, "digital_payment_comfort"] - CONDITIONAL_SHIFT_TIER3_DIGITAL_COMFORT
            )

        working_mother = out["employment_status"].astype(str).eq("full_time") & out[
            "parent_gender"
        ].astype(str).eq("female")
        if "perceived_time_scarcity" in out.columns:
            out.loc[working_mother, "perceived_time_scarcity"] = (
                out.loc[working_mother, "perceived_time_scarcity"]
                + CONDITIONAL_SHIFT_WORKING_MOTHER_TIME_SCARCITY
            )
        if "guilt_driven_spending" in out.columns:
            out.loc[working_mother, "guilt_driven_spending"] = (
                out.loc[working_mother, "guilt_driven_spending"]
                + CONDITIONAL_SHIFT_WORKING_MOTHER_WORK_GUILT
            )

        first_child = out["num_children"].astype(int).eq(1)
        if "health_anxiety" in out.columns:
            out.loc[first_child, "health_anxiety"] = (
                out.loc[first_child, "health_anxiety"] + CONDITIONAL_SHIFT_FIRST_CHILD_ANXIETY
            )

        joint = out["family_structure"].astype(str).eq("joint")
        if "elder_advice_weight" in out.columns:
            out.loc[joint, "elder_advice_weight"] = (
                out.loc[joint, "elder_advice_weight"] + CONDITIONAL_SHIFT_JOINT_EXTENDED_FAMILY
            )
        if "partner_involvement" in out.columns:
            out.loc[joint, "partner_involvement"] = (
                out.loc[joint, "partner_involvement"] + CONDITIONAL_SHIFT_JOINT_FAMILY_INFLUENCE
            )

        high_income = out["household_income_lpa"].astype(float) > HIGH_INCOME_LPA_THRESHOLD
        if "best_for_my_child_intensity" in out.columns:
            out.loc[high_income, "best_for_my_child_intensity"] = (
                out.loc[high_income, "best_for_my_child_intensity"]
                + CONDITIONAL_SHIFT_HIGH_INCOME_BRAND_PREMIUM
            )
        if "deal_seeking_intensity" in out.columns:
            out.loc[high_income, "deal_seeking_intensity"] = (
                out.loc[high_income, "deal_seeking_intensity"]
                - CONDITIONAL_SHIFT_HIGH_INCOME_PRICE_SENSITIVITY
            )

        return _clip_psych_columns(out, PSYCHOGRAPHIC_CONTINUOUS_COLUMNS)
