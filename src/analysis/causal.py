"""
Causal inference and variable importance — which attributes drive adoption?

Uses logistic regression + SHAP values to identify causal factors and then
turns the ranked variables into grounded causal statements.
"""

from __future__ import annotations

from statistics import median
from typing import Any

import numpy as np
import shap
import structlog
from pydantic import BaseModel, ConfigDict
from sklearn.linear_model import LogisticRegression

from src.constants import (
    CAUSAL_HIGH_IMPORTANCE_MULTIPLIER,
    CAUSAL_SEGMENT_KEYS,
    CAUSAL_SEGMENT_LIFT_VARIATION_THRESHOLD,
    DEFAULT_CAUSAL_TOP_N,
    DEFAULT_SEED,
    INCOME_BRACKET_LOW_MAX_LPA,
    INCOME_BRACKET_MID_MAX_LPA,
)
from src.utils.display import display_name

logger = structlog.get_logger(__name__)


class VariableImportance(BaseModel):
    """Importance ranking for a single variable."""

    model_config = ConfigDict(extra="forbid")

    variable_name: str
    coefficient: float
    shap_mean_abs: float
    direction: str  # "positive" or "negative"
    rank: int


class CausalStatement(BaseModel):
    """A grounded causal insight referencing specific variables and thresholds."""

    model_config = ConfigDict(extra="forbid")

    statement: str
    supporting_variables: list[str]
    evidence_strength: float
    segment: str | None = None


def _rows_from_results(
    results: dict[str, dict[str, Any]] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not results:
        return []
    if isinstance(results, dict):
        return [row for row in results.values() if isinstance(row, dict)]
    return [row for row in results if isinstance(row, dict)]


def _outcome_to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"adopt", "adopted", "converted", "yes", "true", "1"}:
            return 1
        if lowered in {"reject", "rejected", "no", "false", "0"}:
            return 0
    return None


def _numeric_feature_names(first_row: dict[str, Any]) -> list[str]:
    outcome_keys = {"outcome", "adopted", "converted", "is_adopter"}
    return [
        key
        for key, value in first_row.items()
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and key not in outcome_keys
        and key not in {"id", "persona_id"}
    ]


def compute_variable_importance(
    results: dict[str, dict[str, Any]] | list[dict[str, Any]],
) -> list[VariableImportance]:
    """Rank variables by their causal impact on adoption."""

    rows = _rows_from_results(results)
    if not rows:
        return []

    first_row = rows[0]
    outcome_keys = ["outcome", "adopted", "converted", "is_adopter"]
    outcome_key = next((key for key in outcome_keys if key in first_row), None)
    if outcome_key is None:
        return []

    feature_names = _numeric_feature_names(first_row)
    if not feature_names:
        return []

    x_list: list[list[float]] = []
    y_list: list[int] = []
    for row in rows:
        outcome_value = _outcome_to_int(row.get(outcome_key))
        if outcome_value is None:
            continue
        y_list.append(outcome_value)
        x_list.append([float(row.get(feature_name, 0.0) or 0.0) for feature_name in feature_names])

    if not x_list:
        return []

    x_mat = np.array(x_list, dtype=float)
    y_mat = np.array(y_list, dtype=int)

    if len(np.unique(y_mat)) < 2:
        return []

    model = LogisticRegression(random_state=DEFAULT_SEED, max_iter=1000)
    model.fit(x_mat, y_mat)

    explainer = shap.LinearExplainer(model, x_mat)
    shap_values = explainer.shap_values(x_mat)
    if isinstance(shap_values, list):
        shap_array = np.array(shap_values[0])
    else:
        shap_array = np.array(shap_values)

    coefficients = model.coef_[0]
    shap_mean_abs = np.abs(shap_array).mean(axis=0)

    importances = [
        VariableImportance(
            variable_name=feature_name,
            coefficient=float(coefficients[index]),
            shap_mean_abs=float(shap_mean_abs[index]),
            direction="positive" if coefficients[index] >= 0 else "negative",
            rank=0,
        )
        for index, feature_name in enumerate(feature_names)
    ]
    importances.sort(key=lambda item: item.shap_mean_abs, reverse=True)

    for rank, item in enumerate(importances, start=1):
        item.rank = rank

    logger.debug("variable_importance_computed", variables=len(importances))
    return importances


def _derive_segment_value(segment_key: str, row: dict[str, Any]) -> str | None:
    if segment_key == "income_bracket":
        income = row.get("household_income_lpa")
        if not isinstance(income, (int, float)) or isinstance(income, bool):
            return None
        if income <= INCOME_BRACKET_LOW_MAX_LPA:
            return "low_income"
        if income <= INCOME_BRACKET_MID_MAX_LPA:
            return "middle_income"
        return "high_income"

    value = row.get(segment_key)
    if value is None:
        return None
    return str(value)


def _adoption_rate(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    adopted = sum(_outcome_to_int(row.get("outcome")) == 1 for row in rows)
    return adopted / len(rows)


def _lift_ratio(above_rate: float, below_rate: float) -> float:
    if above_rate <= 0.0 and below_rate <= 0.0:
        return 1.0
    if below_rate <= 0.0:
        return float("inf")
    return above_rate / below_rate


def _format_lift_text(ratio: float) -> str:
    if ratio == float("inf"):
        return "materially more likely"
    if ratio >= 1.0:
        return f"{ratio:.2f}x more likely"
    if ratio <= 0.0:
        return "materially less likely"
    return f"{1.0 / ratio:.2f}x less likely"


def _mechanism_phrase(variable_name: str, direction: str) -> str:
    label = display_name(variable_name)
    mechanisms = {
        "budget_consciousness": f"higher {label} makes price friction show up faster at purchase",
        "health_anxiety": f"higher {label} increases need recognition earlier in the funnel",
        "medical_authority_trust": f"higher {label} makes expert signals carry more weight",
        "ad_receptivity": f"higher {label} lifts awareness faster",
        "price_reference_point": f"a higher {label} softens price shock at checkout",
        "supplement_necessity_belief": f"stronger {label} makes the category feel more necessary",
        "perceived_time_scarcity": f"higher {label} makes convenience matter more",
    }
    if variable_name in mechanisms:
        return mechanisms[variable_name]
    if direction == "positive":
        return f"higher {label} pushes the modeled decision scores upward"
    return f"higher {label} creates a stronger modeled barrier to adoption"


def _supporting_variables(
    importances: list[VariableImportance],
    primary_variable: str,
    extra: str | None = None,
) -> list[str]:
    support = [primary_variable]
    if extra is not None:
        support.append(extra)
    for item in importances:
        if item.variable_name not in support:
            support.append(item.variable_name)
        if len(support) == 3:
            break
    return support


def _statement_for_split(
    variable_name: str,
    threshold: float,
    above_rate: float,
    below_rate: float,
    importances: list[VariableImportance],
    evidence_strength: float,
    direction_hint: str,
    segment: str | None = None,
    segment_key: str | None = None,
) -> CausalStatement:
    ratio = _lift_ratio(above_rate, below_rate)
    direction_text = _format_lift_text(ratio)
    mechanism = _mechanism_phrase(variable_name, direction_hint)
    label = display_name(variable_name)

    if segment is None:
        statement = (
            f"Personas with {label} above {threshold:.2f} are {direction_text} to adopt "
            f"than those below {threshold:.2f}, because {mechanism}."
        )
    else:
        segment_label = display_name(segment_key) if segment_key else segment_key
        segment_value = display_name(segment) if segment else segment
        statement = (
            f"Within {segment_label} = {segment_value}, personas with {label} above {threshold:.2f} are "
            f"{direction_text} to adopt than peers below {threshold:.2f}, because {mechanism}."
        )

    return CausalStatement(
        statement=statement,
        supporting_variables=_supporting_variables(importances, variable_name, segment_key),
        evidence_strength=evidence_strength,
        segment=segment,
    )


def generate_causal_statements(
    importances: list[VariableImportance],
    results: dict[str, dict[str, Any]] | list[dict[str, Any]],
    scenario_id: str | None = None,
    top_n: int = DEFAULT_CAUSAL_TOP_N,
) -> list[CausalStatement]:
    """Generate human-readable causal insights grounded in specific variables."""

    rows = _rows_from_results(results)
    if not importances or not rows:
        return []

    sorted_importances = sorted(importances, key=lambda item: item.shap_mean_abs, reverse=True)[
        :top_n
    ]
    max_shap = max((item.shap_mean_abs for item in sorted_importances), default=0.0)
    mean_shap = sum(item.shap_mean_abs for item in sorted_importances) / len(sorted_importances)
    statements: list[CausalStatement] = []

    for importance in sorted_importances:
        variable_rows = [
            row
            for row in rows
            if isinstance(row.get(importance.variable_name), (int, float))
            and not isinstance(row.get(importance.variable_name), bool)
            and _outcome_to_int(row.get("outcome")) is not None
        ]
        if len(variable_rows) < 2:
            continue

        threshold = float(median(float(row[importance.variable_name]) for row in variable_rows))
        above_rows = [
            row for row in variable_rows if float(row[importance.variable_name]) >= threshold
        ]
        below_rows = [
            row for row in variable_rows if float(row[importance.variable_name]) < threshold
        ]
        if not above_rows or not below_rows:
            continue

        evidence_strength = 0.0 if max_shap <= 0 else importance.shap_mean_abs / max_shap
        above_rate = _adoption_rate(above_rows)
        below_rate = _adoption_rate(below_rows)
        statements.append(
            _statement_for_split(
                variable_name=importance.variable_name,
                threshold=threshold,
                above_rate=above_rate,
                below_rate=below_rate,
                importances=sorted_importances,
                evidence_strength=evidence_strength,
                direction_hint=importance.direction,
            )
        )

        if importance.shap_mean_abs <= mean_shap * CAUSAL_HIGH_IMPORTANCE_MULTIPLIER:
            continue

        for segment_key in CAUSAL_SEGMENT_KEYS:
            segment_lifts: list[tuple[str, float, float, float]] = []
            segment_values = {
                value
                for row in variable_rows
                if (value := _derive_segment_value(segment_key, row)) is not None
            }
            for segment_value in segment_values:
                segment_rows = [
                    row
                    for row in variable_rows
                    if _derive_segment_value(segment_key, row) == segment_value
                ]
                if len(segment_rows) < 2:
                    continue
                segment_above = [
                    row for row in segment_rows if float(row[importance.variable_name]) >= threshold
                ]
                segment_below = [
                    row for row in segment_rows if float(row[importance.variable_name]) < threshold
                ]
                if not segment_above or not segment_below:
                    continue
                segment_lifts.append(
                    (
                        segment_value,
                        _lift_ratio(_adoption_rate(segment_above), _adoption_rate(segment_below)),
                        _adoption_rate(segment_above),
                        _adoption_rate(segment_below),
                    )
                )

            finite_lifts = [
                lift if lift != float("inf") else CAUSAL_SEGMENT_LIFT_VARIATION_THRESHOLD + 1.0
                for _, lift, _, _ in segment_lifts
                if lift > 0.0
            ]
            if len(finite_lifts) < 2:
                continue
            if (
                max(finite_lifts) / max(min(finite_lifts), 1e-6)
                <= CAUSAL_SEGMENT_LIFT_VARIATION_THRESHOLD
            ):
                continue

            strongest_segment, _, strongest_above, strongest_below = max(
                segment_lifts,
                key=lambda item: item[1],
            )
            statements.append(
                _statement_for_split(
                    variable_name=importance.variable_name,
                    threshold=threshold,
                    above_rate=strongest_above,
                    below_rate=strongest_below,
                    importances=sorted_importances,
                    evidence_strength=max(0.0, min(1.0, evidence_strength * 0.95)),
                    direction_hint=importance.direction,
                    segment=strongest_segment,
                    segment_key=segment_key,
                )
            )

    statements.sort(key=lambda item: item.evidence_strength, reverse=True)
    logger.info(
        "causal_statements_generated",
        scenario_id=scenario_id,
        statements=len(statements),
        variables_considered=len(sorted_importances),
    )
    return statements
