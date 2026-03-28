"""
Causal inference and variable importance — which attributes drive adoption?

Uses logistic regression + SHAP values to identify causal factors.
Full implementation in PRD-008 (Antigravity + Codex).
"""

from __future__ import annotations

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


def compute_variable_importance(results: dict) -> list[VariableImportance]:
    """Rank variables by their causal impact on adoption."""
    if not results:
        return []

    # Infer feature names from the first result
    first_res = next(iter(results.values())) if isinstance(results, dict) else results[0]

    # Try to find the outcome key
    outcome_keys = ["outcome", "adopted", "converted", "is_adopter"]
    outcome_key = next((k for k in outcome_keys if k in first_res), None)
    if outcome_key is None:
        return []

    # Get continuous features
    feature_names = [
        k
        for k, v in first_res.items()
        if isinstance(v, (int, float))
        and not isinstance(v, bool)
        and k not in [*outcome_keys, "id", "persona_id"]
    ]

    if not feature_names:
        return []

    # Extract X and y
    x_list = []
    y = []

    iterable = results.values() if isinstance(results, dict) else results
    for row in iterable:
        y.append(int(row.get(outcome_key, 0)))
        features = []
        for fn in feature_names:
            val = row.get(fn, 0.0)
            features.append(float(val) if val is not None else 0.0)
        x_list.append(features)

    x_mat = np.array(x_list)
    y_mat = np.array(y)

    # Note: If there's only one class in y, logistic regression will fail or just return 0s
    if len(np.unique(y_mat)) < 2:
        return []

    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(x_mat, y_mat)

    coefs = model.coef_[0]

    explainer = shap.LinearExplainer(model, x_mat)
    shap_values = explainer.shap_values(x_mat)

    shap_mean_abs = np.abs(shap_values).mean(axis=0)

    importances = []
    for i, fn in enumerate(feature_names):
        importances.append(
            VariableImportance(
                variable_name=fn,
                coefficient=float(coefs[i]),
                shap_mean_abs=float(shap_mean_abs[i]),
                direction="positive" if coefs[i] > 0 else "negative",
                rank=0,  # Set rank later
            )
        )

    # Sort descending by absolute coefficient value
    importances.sort(key=lambda x: abs(x.coefficient), reverse=True)

    # Apply ranks
    for rank, imp in enumerate(importances, start=1):
        imp.rank = rank

    return importances


def generate_causal_statements(
    importances: list[VariableImportance],
    results: dict,
) -> list[CausalStatement]:
    """Generate human-readable causal insights grounded in specific variables."""
    raise NotImplementedError("Full implementation in PRD-008")
