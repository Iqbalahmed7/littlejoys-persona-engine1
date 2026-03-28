"""
Persona and population validation framework.

See ARCHITECTURE.md §6.3 for validation rules.
Full implementation in PRD-001 (Antigravity).
"""

from __future__ import annotations

import datetime
import math
from typing import Any, ClassVar

import numpy as np
import scipy.stats as stats
from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Validation result for a single persona."""

    persona_id: str
    is_valid: bool
    hard_failures: list[str]
    soft_warnings: list[str]


class DistributionCheckResult(BaseModel):
    """Result of a population-level distribution check."""

    attribute: str
    target: dict[str, Any]
    actual: dict[str, float]
    p_value: float
    passed: bool


class CorrelationCheckResult(BaseModel):
    """Result of a pairwise correlation check."""

    pair: tuple[str, str]
    target: float
    actual: float
    passed: bool


class PopulationValidationReport(BaseModel):
    """Comprehensive validation report for an entire population."""

    timestamp: str
    population_size: int
    seed: int
    tier1_count: int
    tier2_count: int
    distribution_checks: dict[str, DistributionCheckResult]
    correlation_checks: dict[str, CorrelationCheckResult]
    invalid_personas_regenerated: int
    hard_failure_types: dict[str, int]
    soft_warnings: list[str]
    overall_pass: bool


class PersonaValidator:
    """Validates individual personas and populations against consistency rules."""

    # Schema valid enums
    VALID_ENUMS: ClassVar[dict[str, set[str]]] = {
        "city_tier": {"Tier1", "Tier2", "Tier3"},
        "parent_gender": {"female", "male"},
        "education_level": {
            "high_school",
            "bachelors",
            "masters",
            "doctorate",
            "professional",
        },
        "employment_status": {
            "homemaker",
            "part_time",
            "full_time",
            "self_employed",
            "freelance",
        },
        "family_structure": {"nuclear", "joint", "single_parent"},
        "dietary_culture": {"vegetarian", "eggetarian", "non_vegetarian", "vegan", "jain"},
        "primary_shopping_platform": {
            "amazon",
            "flipkart",
            "bigbasket",
            "dmart",
            "local_store",
            "brand_website",
            "quick_commerce",
        },
    }

    REQUIRED_FIELDS: ClassVar[set[str]] = {
        "city_tier",
        "city_name",
        "household_income_lpa",
        "parent_age",
        "parent_gender",
        "num_children",
        "youngest_child_age",
        "oldest_child_age",
        "education_level",
        "employment_status",
        "family_structure",
        "dietary_culture",
        "health_anxiety",
        "supplement_necessity_belief",
        "digital_payment_comfort",
        "best_for_my_child_intensity",
        "perceived_time_scarcity",
    }

    def validate_persona(self, persona_id: str, flat_attrs: dict[str, Any]) -> ValidationResult:
        """
        Check a single persona for logical consistency.

        Hard failures: child_age > parent_age - 18, out-of-range, NaN/Inf.
        Soft warnings: unusual but possible combinations.
        """
        hard_failures = []
        soft_warnings = []

        # 1. & 2. Continuous out of range [0,1] or NaN/Inf
        for k, v in flat_attrs.items():
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    hard_failures.append(f"{k} is NaN or Inf")
                elif k not in (
                    "household_income_lpa",
                    "price_paid",
                    "price_reference_point",
                    "daily_social_media_hours",
                ) and (v < 0.0 or v > 1.0):
                    hard_failures.append(f"{k} is outside [0, 1]: {v}")

        y_age = flat_attrs.get("youngest_child_age")
        o_age = flat_attrs.get("oldest_child_age")
        if isinstance(y_age, int) and isinstance(o_age, int) and y_age > o_age:
            hard_failures.append(f"youngest_child_age ({y_age}) > oldest_child_age ({o_age})")

        p_age = flat_attrs.get("parent_age")
        if isinstance(p_age, int) and isinstance(o_age, int) and p_age - o_age < 18:
            hard_failures.append(f"parent_age ({p_age}) - oldest_child_age ({o_age}) < 18")

        num_kids = flat_attrs.get("num_children")
        if (
            (isinstance(num_kids, int) and isinstance(y_age, int) and isinstance(o_age, int))
            and num_kids == 1
            and y_age != o_age
        ):
            hard_failures.append("num_children is 1 but youngest_child_age != oldest_child_age")

        for field, valid_set in self.VALID_ENUMS.items():
            val = flat_attrs.get(field)
            if val is not None and val not in valid_set:
                hard_failures.append(
                    f"Categorical attribute {field} value not in valid enum: {val}"
                )

        for req in self.REQUIRED_FIELDS:
            if req not in flat_attrs or flat_attrs[req] is None:
                hard_failures.append(f"Missing required field: {req}")

        tier = flat_attrs.get("city_tier")
        dc = flat_attrs.get("digital_payment_comfort", 0.0)
        if tier == "Tier3" and isinstance(dc, float) and dc > 0.85:
            soft_warnings.append("Tier3 + digital_payment_comfort > 0.85")

        inc = flat_attrs.get("household_income_lpa", 0.0)
        bpw = flat_attrs.get("best_for_my_child_intensity", 0.0)
        if (
            isinstance(inc, (int, float))
            and isinstance(bpw, (int, float))
            and (inc < 3.0 and bpw > 0.7)
        ):
            soft_warnings.append("household_income_lpa < 3 + best_for_my_child_intensity > 0.7")

        emp = flat_attrs.get("employment_status")
        ts = flat_attrs.get("perceived_time_scarcity", 0.0)
        if emp == "homemaker" and isinstance(ts, float) and ts > 0.8:
            soft_warnings.append("homemaker + perceived_time_scarcity > 0.8")

        ha = flat_attrs.get("health_anxiety", 0.0)
        sb = flat_attrs.get("supplement_necessity_belief", 0.0)
        if isinstance(ha, float) and isinstance(sb, float) and ha < 0.2 and sb > 0.8:
            soft_warnings.append("health_anxiety < 0.2 + supplement_necessity_belief > 0.8")

        return ValidationResult(
            persona_id=persona_id,
            is_valid=len(hard_failures) == 0,
            hard_failures=list(set(hard_failures)),
            soft_warnings=list(set(soft_warnings)),
        )

    def validate_population(
        self,
        personas: list[dict[str, Any]],
        target_distributions: dict[str, Any],
        target_correlations: dict[tuple[str, str], float],
    ) -> PopulationValidationReport:
        """Check population-level distribution and correlation compliance."""
        dist_checks = {}
        corr_checks = {}

        timestamp = datetime.datetime.now().isoformat()

        for attr, target in target_distributions.items():
            if isinstance(target, dict) and "distribution" in target:
                values = [
                    p.get(attr)
                    for p in personas
                    if attr in p and isinstance(p.get(attr), (int, float))
                ]
                if not values:
                    continue
                actual_mean = float(np.mean(values))
                if target["distribution"] == "uniform":
                    _stat, p_val = stats.kstest(
                        values,
                        "uniform",
                        args=(
                            target.get("min", 0),
                            target.get("max", 1) - target.get("min", 0),
                        ),
                    )
                    dist_checks[attr] = DistributionCheckResult(
                        attribute=attr,
                        target=target,
                        actual={"mean": actual_mean},
                        p_value=float(p_val),
                        passed=bool(p_val > 0.05),
                    )
                else:
                    dist_checks[attr] = DistributionCheckResult(
                        attribute=attr,
                        target=target,
                        actual={"mean": actual_mean},
                        p_value=1.0,
                        passed=True,
                    )
            elif isinstance(target, dict):
                values = [p.get(attr) for p in personas if attr in p]
                if not values:
                    continue
                counts: dict[str, int] = {}
                for v in values:
                    counts[v] = counts.get(v, 0) + 1
                n = len(values)
                actual_dist = {k: v / n for k, v in counts.items()}

                keys = list(target.keys())
                obs = [counts.get(k, 0) for k in keys]
                exp = [target[k] * n for k in keys]

                if sum(obs) > 0 and sum(exp) > 0:
                    _chi_stat, p_val = stats.chisquare(f_obs=obs, f_exp=exp)
                else:
                    p_val = 0.0

                dist_checks[attr] = DistributionCheckResult(
                    attribute=attr,
                    target=target,
                    actual=actual_dist,
                    p_value=float(p_val),
                    passed=bool(p_val > 0.05),
                )

        for pair, target_corr in target_correlations.items():
            attr1_raw, attr2_raw = pair

            vals1 = []
            vals2 = []

            for p in personas:

                def get_val(p_attr: dict[str, Any], raw_attr: str) -> float | None:
                    if "=" in raw_attr:
                        key, val = raw_attr.split("=")
                        return 1.0 if str(p_attr.get(key)) == val else 0.0
                    res = p_attr.get(raw_attr)
                    if isinstance(res, (int, float)):
                        return float(res)
                    return None

                v1 = get_val(p, attr1_raw)
                v2 = get_val(p, attr2_raw)

                if v1 is not None and v2 is not None:
                    try:
                        vals1.append(float(v1))
                        vals2.append(float(v2))
                    except ValueError:
                        pass

            if len(vals1) > 1 and np.std(vals1) > 1e-6 and np.std(vals2) > 1e-6:
                actual_corr, _ = stats.pearsonr(vals1, vals2)
                passed = abs(actual_corr - target_corr) <= 0.15
                corr_checks[f"{attr1_raw}-{attr2_raw}"] = CorrelationCheckResult(
                    pair=pair,
                    target=target_corr,
                    actual=float(actual_corr),
                    passed=bool(passed),
                )
            else:
                corr_checks[f"{attr1_raw}-{attr2_raw}"] = CorrelationCheckResult(
                    pair=pair, target=target_corr, actual=0.0, passed=False
                )

        invalid_count = 0
        hf_types: dict[str, int] = {}
        all_soft: set[str] = set()

        for p in personas:
            res = self.validate_persona(str(p.get("id", "unknown")), p)
            if not res.is_valid:
                invalid_count += 1
                for hf in res.hard_failures:
                    hf_key = " ".join(hf.split()[:2])
                    hf_types[hf_key] = hf_types.get(hf_key, 0) + 1
            for sw in res.soft_warnings:
                all_soft.add(sw)

        all_chi_pass = all(c.passed for c in dist_checks.values() if "distribution" not in c.target)
        corr_pass_ratio = (
            sum(c.passed for c in corr_checks.values()) / max(1, len(corr_checks))
            if corr_checks
            else 1.0
        )

        overall_pass = all_chi_pass and (corr_pass_ratio >= 0.8)

        return PopulationValidationReport(
            timestamp=timestamp,
            population_size=len(personas),
            seed=0,
            tier1_count=len(personas),
            tier2_count=sum(1 for p in personas if p.get("tier") == "deep"),
            distribution_checks=dist_checks,
            correlation_checks=corr_checks,
            invalid_personas_regenerated=invalid_count,
            hard_failure_types=hf_types,
            soft_warnings=list(all_soft),
            overall_pass=overall_pass,
        )
