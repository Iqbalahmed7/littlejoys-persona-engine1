"""
Persona and population validation framework.

See ARCHITECTURE.md §6.3 for validation rules.
Full implementation in PRD-001 (Antigravity).
"""

from __future__ import annotations

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
    target: dict[str, float]
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

    def validate_persona(self, persona_id: str, flat_attrs: dict) -> ValidationResult:
        """
        Check a single persona for logical consistency.

        Hard failures: child_age > parent_age - 18, out-of-range, NaN/Inf.
        Soft warnings: unusual but possible combinations.
        """
        raise NotImplementedError("Full implementation in PRD-001")

    def validate_population(
        self,
        personas: list[dict],
        target_distributions: dict,
        target_correlations: dict,
    ) -> PopulationValidationReport:
        """Check population-level distribution and correlation compliance."""
        raise NotImplementedError("Full implementation in PRD-001")
