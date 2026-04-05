"""
Demographic distribution tables for Indian urban parents.

The distribution values come from the Sprint 1 briefing and are sampled with a
seeded NumPy RNG for deterministic outputs.
"""

from __future__ import annotations

from typing import ClassVar

import numpy as np
import pandas as pd
import structlog
from scipy.stats import truncnorm

from src.constants import (
    CHILD_AGE_MAX,
    CHILD_AGE_MIN,
    MIN_PARENT_CHILD_AGE_GAP,
    MIN_POPULATION_SIZE,
    PARENT_AGE_MAX,
    PARENT_AGE_MIN,
)

logger = structlog.get_logger(__name__)


class DistributionTables:
    """
    Real-world demographic distributions for Indian urban parents.

    Provides sampling methods that produce seeded, tier-conditional
    demographic samples for the Tier 1 pipeline.
    """

    CITY_TIER: ClassVar[dict[str, float]] = {"Tier1": 0.45, "Tier2": 0.35, "Tier3": 0.20}
    INCOME_PARAMS: ClassVar[dict[str, dict[str, float]]] = {
        "Tier1": {"mean": 18.0, "std": 8.0, "min": 5.0, "max": 80.0},
        "Tier2": {"mean": 12.0, "std": 6.0, "min": 3.0, "max": 50.0},
        "Tier3": {"mean": 7.0, "std": 4.0, "min": 2.0, "max": 30.0},
    }
    PARENT_AGE: ClassVar[dict[str, float]] = {
        "mean": 32.0,
        "std": 4.0,
        "min": float(PARENT_AGE_MIN),
        "max": float(PARENT_AGE_MAX),
    }
    CHILD_AGE: ClassVar[dict[str, float]] = {
        "min": float(CHILD_AGE_MIN),
        "max": float(CHILD_AGE_MAX),
    }
    NUM_CHILDREN: ClassVar[dict[int, float]] = {1: 0.35, 2: 0.45, 3: 0.15, 4: 0.04, 5: 0.01}
    EDUCATION: ClassVar[dict[str, dict[str, float]]] = {
        "Tier1": {
            "high_school": 0.05,
            "bachelors": 0.35,
            "masters": 0.40,
            "doctorate": 0.10,
            "professional": 0.10,
        },
        "Tier2": {
            "high_school": 0.15,
            "bachelors": 0.40,
            "masters": 0.30,
            "doctorate": 0.08,
            "professional": 0.07,
        },
        "Tier3": {
            "high_school": 0.30,
            "bachelors": 0.40,
            "masters": 0.20,
            "doctorate": 0.05,
            "professional": 0.05,
        },
    }
    EMPLOYMENT: ClassVar[dict[str, float]] = {
        "homemaker": 0.30,
        "full_time": 0.35,
        "part_time": 0.15,
        "self_employed": 0.12,
        "freelance": 0.08,
    }
    FAMILY_STRUCTURE: ClassVar[dict[str, dict[str, float]]] = {
        "Tier1": {"nuclear": 0.65, "joint": 0.25, "single_parent": 0.10},
        "Tier2": {"nuclear": 0.50, "joint": 0.40, "single_parent": 0.10},
        "Tier3": {"nuclear": 0.35, "joint": 0.55, "single_parent": 0.10},
    }
    DIETARY: ClassVar[dict[str, dict[str, float]]] = {
        "Tier1": {"vegetarian": 0.30, "eggetarian": 0.15, "non_vegetarian": 0.50, "vegan": 0.05},
        "Tier2": {"vegetarian": 0.35, "eggetarian": 0.15, "non_vegetarian": 0.45, "vegan": 0.05},
        "Tier3": {"vegetarian": 0.40, "eggetarian": 0.15, "non_vegetarian": 0.40, "vegan": 0.05},
    }
    CITY_NAMES: ClassVar[dict[str, tuple[str, ...]]] = {
        "Tier1": (
            "Mumbai",
            "Delhi",
            "Bangalore",
            "Hyderabad",
            "Chennai",
            "Pune",
            "Kolkata",
            "Ahmedabad",
        ),
        "Tier2": (
            "Jaipur",
            "Lucknow",
            "Chandigarh",
            "Kochi",
            "Indore",
            "Bhopal",
            "Nagpur",
            "Coimbatore",
            "Visakhapatnam",
            "Surat",
        ),
        "Tier3": (
            "Mangalore",
            "Mysore",
            "Dehradun",
            "Udaipur",
            "Raipur",
            "Ranchi",
            "Bhubaneswar",
            "Guwahati",
        ),
    }
    CITY_REGION: ClassVar[dict[str, str]] = {
        "Mumbai": "West",
        "Delhi": "North",
        "Bangalore": "South",
        "Hyderabad": "South",
        "Chennai": "South",
        "Pune": "West",
        "Kolkata": "East",
        "Ahmedabad": "West",
        "Jaipur": "North",
        "Lucknow": "North",
        "Chandigarh": "North",
        "Kochi": "South",
        "Indore": "West",
        "Bhopal": "West",
        "Nagpur": "West",
        "Coimbatore": "South",
        "Visakhapatnam": "East",
        "Surat": "West",
        "Mangalore": "South",
        "Mysore": "South",
        "Dehradun": "North",
        "Udaipur": "West",
        "Raipur": "East",
        "Ranchi": "East",
        "Bhubaneswar": "East",
        "Guwahati": "NE",
    }
    PARENT_GENDER: ClassVar[dict[str, float]] = {"female": 0.82, "male": 0.18}

    # Bug 2 fix: work hours by employment status (lo, hi inclusive)
    WORK_HOURS_BY_STATUS: ClassVar[dict[str, tuple[int, int]]] = {
        "homemaker":      (0,   0),
        "part_time":     (15,  25),
        "full_time":     (40,  55),
        "self_employed": (45,  70),
        "freelance":     (20,  40),
    }

    # Bug 1 fix: primary shopping platform weights by city tier
    SHOPPING_PLATFORM_BY_TIER: ClassVar[dict[str, dict[str, float]]] = {
        "Tier1": {
            "amazon":         0.30,
            "bigbasket":      0.25,
            "quick_commerce": 0.20,
            "brand_website":  0.10,
            "flipkart":       0.10,
            "local_store":    0.05,
        },
        "Tier2": {
            "amazon":         0.35,
            "flipkart":       0.20,
            "bigbasket":      0.15,
            "local_store":    0.15,
            "quick_commerce": 0.10,
            "brand_website":  0.05,
        },
        "Tier3": {
            "amazon":         0.30,
            "flipkart":       0.25,
            "local_store":    0.30,
            "bigbasket":      0.08,
            "quick_commerce": 0.04,
            "brand_website":  0.03,
        },
    }

    def sample_demographics(self, n: int, seed: int) -> pd.DataFrame:
        """
        Sample baseline persona demographics.

        Args:
            n: Number of personas to sample.
            seed: Random seed used for deterministic sampling.

        Returns:
            A DataFrame with one row per persona and sampled demographic columns.

        Raises:
            ValueError: If ``n`` is below the supported minimum.
        """

        if n < MIN_POPULATION_SIZE:
            raise ValueError("n must be at least 1")

        rng = np.random.default_rng(seed)
        rows: list[dict[str, object]] = []
        # Bug 3 fix: enforce uniqueness on (city_name, parent_age, num_children)
        seen_signatures: set[tuple[str, int, int]] = set()

        for _ in range(n):
            for attempt in range(11):  # 1 initial attempt + 10 retries
                row = self._sample_one_row(rng)
                sig = (str(row["city_name"]), int(row["parent_age"]), int(row["num_children"]))
                if sig not in seen_signatures or attempt == 10:
                    if attempt == 10 and sig in seen_signatures:
                        logger.warning(
                            "demographic_uniqueness_fallback",
                            signature=sig,
                        )
                    seen_signatures.add(sig)
                    rows.append(row)
                    break

        demographics = pd.DataFrame(rows)
        logger.info("sampled_demographics", count=n, seed=seed)
        return demographics

    def _sample_one_row(self, rng: np.random.Generator) -> dict[str, object]:
        """Sample one complete demographic row from the current RNG state."""
        city_tier = str(self._weighted_choice(rng, self.CITY_TIER))
        city_name = str(self._sample_city_name(rng, city_tier))
        region = self.CITY_REGION[city_name]
        num_children = self._weighted_choice(rng, self.NUM_CHILDREN)
        parent_age = self._sample_parent_age(rng)
        child_ages = self._sample_child_ages(rng, parent_age, int(num_children))
        employment_status = str(self._weighted_choice(rng, self.EMPLOYMENT))
        family_structure = str(self._weighted_choice(rng, self.FAMILY_STRUCTURE[city_tier]))
        household_income_lpa = self._sample_income(rng, city_tier)

        # Bug 2 fix: sample realistic work hours based on employment status
        wh_lo, wh_hi = self.WORK_HOURS_BY_STATUS[employment_status]
        work_hours_per_week = int(rng.integers(wh_lo, wh_hi + 1))

        # Bug 1 fix: sample primary shopping platform from tier-weighted distribution
        primary_shopping_platform = str(
            self._weighted_choice(rng, self.SHOPPING_PLATFORM_BY_TIER[city_tier])
        )

        return {
            "city_tier": city_tier,
            "city_name": city_name,
            "region": region,
            "urban_vs_periurban": self._sample_urbanicity(rng, city_tier),
            "household_income_lpa": household_income_lpa,
            "parent_age": parent_age,
            "parent_gender": self._weighted_choice(rng, self.PARENT_GENDER),
            "marital_status": self._sample_marital_status(rng, family_structure),
            "birth_order": self._sample_birth_order(rng),
            "num_children": int(num_children),
            "child_ages": child_ages,
            "child_genders": self._sample_child_genders(rng, int(num_children)),
            "youngest_child_age": min(child_ages),
            "oldest_child_age": max(child_ages),
            "education_level": self._weighted_choice(rng, self.EDUCATION[city_tier]),
            "employment_status": employment_status,
            "work_hours_per_week": work_hours_per_week,
            "primary_shopping_platform": primary_shopping_platform,
            "family_structure": family_structure,
            "dietary_culture": self._weighted_choice(rng, self.DIETARY[city_tier]),
            "elder_influence": self._sample_elder_influence(rng, family_structure),
            "spouse_involvement_in_purchases": self._sample_spouse_involvement(
                rng, family_structure
            ),
            "income_stability": self._sample_income_stability(rng, employment_status),
            "socioeconomic_class": self._derive_sec_class(household_income_lpa),
            "dual_income_household": self._sample_dual_income_household(
                rng, employment_status, family_structure
            ),
        }

    def _weighted_choice(self, rng: np.random.Generator, weights: dict[object, float]) -> object:
        labels = tuple(weights.keys())
        probabilities = np.array(tuple(weights.values()), dtype=float)
        return rng.choice(labels, p=probabilities / probabilities.sum())

    def _sample_city_name(self, rng: np.random.Generator, city_tier: str) -> str:
        return str(rng.choice(self.CITY_NAMES[city_tier]))

    def _sample_parent_age(self, rng: np.random.Generator) -> int:
        mean = self.PARENT_AGE["mean"]
        std = self.PARENT_AGE["std"]
        lower = (self.PARENT_AGE["min"] - mean) / std
        upper = (self.PARENT_AGE["max"] - mean) / std
        return round(truncnorm.rvs(lower, upper, loc=mean, scale=std, random_state=rng))

    def _sample_income(self, rng: np.random.Generator, city_tier: str) -> float:
        params = self.INCOME_PARAMS[city_tier]
        mean = params["mean"]
        std = params["std"]
        sigma_sq = np.log(1.0 + ((std * std) / (mean * mean)))
        sigma = np.sqrt(sigma_sq)
        mu = np.log(mean) - (sigma_sq / 2.0)

        sample = float(rng.lognormal(mean=mu, sigma=sigma))
        return float(np.clip(sample, params["min"], params["max"]))

    def _sample_child_ages(
        self, rng: np.random.Generator, parent_age: int, num_children: int
    ) -> list[int]:
        max_child_age = min(CHILD_AGE_MAX, parent_age - MIN_PARENT_CHILD_AGE_GAP)
        bounded_max = max(CHILD_AGE_MIN, max_child_age)
        sampled = rng.integers(CHILD_AGE_MIN, bounded_max + 1, size=num_children)
        return sorted(int(age) for age in sampled.tolist())

    def _sample_child_genders(self, rng: np.random.Generator, num_children: int) -> list[str]:
        return [str(rng.choice(("female", "male"), p=(0.48, 0.52))) for _ in range(num_children)]

    def _sample_urbanicity(self, rng: np.random.Generator, city_tier: str) -> str:
        urban_probability = {"Tier1": 0.95, "Tier2": 0.80, "Tier3": 0.60}[city_tier]
        return "urban" if bool(rng.random() < urban_probability) else "periurban"

    def _sample_marital_status(self, rng: np.random.Generator, family_structure: str) -> str:
        if family_structure == "single_parent":
            return str(
                rng.choice(
                    ("divorced", "widowed", "separated", "single"), p=(0.45, 0.15, 0.25, 0.15)
                )
            )
        return "married"

    def _sample_birth_order(self, rng: np.random.Generator) -> str:
        return "firstborn_parent" if bool(rng.random() < 0.45) else "experienced_parent"

    def _sample_elder_influence(self, rng: np.random.Generator, family_structure: str) -> float:
        center = {"nuclear": 0.35, "joint": 0.78, "single_parent": 0.50}[family_structure]
        return float(np.clip(rng.normal(loc=center, scale=0.10), 0.0, 1.0))

    def _sample_spouse_involvement(self, rng: np.random.Generator, family_structure: str) -> float:
        if family_structure == "single_parent":
            return 0.0
        center = {"nuclear": 0.62, "joint": 0.55}[family_structure]
        return float(np.clip(rng.normal(loc=center, scale=0.12), 0.0, 1.0))

    def _sample_income_stability(self, rng: np.random.Generator, employment_status: str) -> str:
        if employment_status == "full_time":
            return str(rng.choice(("salaried", "business"), p=(0.85, 0.15)))
        if employment_status == "part_time":
            return str(rng.choice(("salaried", "freelance", "gig"), p=(0.45, 0.40, 0.15)))
        if employment_status == "self_employed":
            return "business"
        if employment_status == "freelance":
            return "freelance"
        return str(rng.choice(("salaried", "business", "gig"), p=(0.60, 0.25, 0.15)))

    def _derive_sec_class(self, income_lpa: float) -> str:
        if income_lpa >= 30.0:
            return "A1"
        if income_lpa >= 20.0:
            return "A2"
        if income_lpa >= 12.0:
            return "B1"
        if income_lpa >= 7.0:
            return "B2"
        if income_lpa >= 4.0:
            return "C1"
        return "C2"

    def _sample_dual_income_household(
        self, rng: np.random.Generator, employment_status: str, family_structure: str
    ) -> bool:
        if family_structure == "single_parent":
            return False
        probability = 0.68 if employment_status != "homemaker" else 0.32
        return bool(rng.random() < probability)
