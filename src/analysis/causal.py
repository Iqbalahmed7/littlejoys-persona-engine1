"""
Causal inference and variable importance — which attributes drive adoption?

Uses logistic regression + SHAP values to identify causal factors.
Full implementation in PRD-008 (Antigravity + Codex).
"""

from __future__ import annotations

from pydantic import BaseModel


class VariableImportance(BaseModel):
    """Importance ranking for a single variable."""

    variable_name: str
    coefficient: float
    shap_mean_abs: float
    direction: str  # "positive" or "negative"
    rank: int


class CausalStatement(BaseModel):
    """A grounded causal insight referencing specific variables and thresholds."""

    statement: str
    supporting_variables: list[str]
    evidence_strength: float
    segment: str | None = None


def compute_variable_importance(results: dict) -> list[VariableImportance]:
    """Rank variables by their causal impact on adoption."""
    raise NotImplementedError("Full implementation in PRD-008")


def generate_causal_statements(
    importances: list[VariableImportance],
    results: dict,
) -> list[CausalStatement]:
    """Generate human-readable causal insights grounded in specific variables."""
    raise NotImplementedError("Full implementation in PRD-008")
