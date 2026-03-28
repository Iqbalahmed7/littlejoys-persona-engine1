"""Causal inference and variable importance — which attributes drive adoption.

This module uses a lightweight logistic regression model and SHAP values to
estimate the impact of continuous features on adoption outcomes.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import shap
from pydantic import BaseModel
from sklearn.linear_model import LogisticRegression


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


def compute_variable_importance(results: dict[str, dict[str, Any]]) -> list[VariableImportance]:
    """Rank variables by their causal impact on adoption.

    Args:
        results: Mapping of persona_id to a flat dict containing an adoption-like
            outcome key (typically ``outcome``) plus numeric feature values.

    Returns:
        List of variable importance entries, sorted by absolute coefficient
        magnitude (highest impact first).
    """

    if not results:
        return []

    first_res = next(iter(results.values()))

    # Try to find the outcome key.
    outcome_keys = ["outcome", "adopted", "converted", "is_adopter"]
    outcome_key = next((k for k in outcome_keys if k in first_res), None)
    if outcome_key is None:
        return []

    feature_names = [
        k
        for k, v in first_res.items()
        if isinstance(v, (int, float))
        and not isinstance(v, bool)
        and k not in [*outcome_keys, "id", "persona_id"]
    ]
    if not feature_names:
        return []

    x_list: list[list[float]] = []
    y: list[int] = []
    for row in results.values():
        y.append(int(row.get(outcome_key, 0)))
        features: list[float] = []
        for fn in feature_names:
            val = row.get(fn, 0.0)
            features.append(float(val) if val is not None else 0.0)
        x_list.append(features)

    x_mat = np.array(x_list)
    y_mat = np.array(y)

    # If there's only one class, logistic regression is not meaningful.
    if len(np.unique(y_mat)) < 2:
        return []

    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(x_mat, y_mat)

    coefs = model.coef_[0]

    explainer = shap.LinearExplainer(model, x_mat)
    shap_values = explainer.shap_values(x_mat)
    shap_mean_abs = np.abs(shap_values).mean(axis=0)

    importances: list[VariableImportance] = []
    for i, fn in enumerate(feature_names):
        importances.append(
            VariableImportance(
                variable_name=fn,
                coefficient=float(coefs[i]),
                shap_mean_abs=float(shap_mean_abs[i]),
                direction="positive" if coefs[i] > 0 else "negative",
                rank=0,  # Set later.
            )
        )

    importances.sort(key=lambda x: abs(x.coefficient), reverse=True)
    for rank, imp in enumerate(importances, start=1):
        imp.rank = rank

    return importances


def generate_causal_statements(
    importances: list[VariableImportance],
    results: dict[str, dict[str, Any]],
) -> list[CausalStatement]:
    """Generate human-readable causal insights grounded in specific variables."""

    raise NotImplementedError("Full implementation in PRD-008")
