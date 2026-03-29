"""
Dashboard data helpers — paths, persistence, and persona/result merges.

Used by the Streamlit app (PRD-011).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.constants import (
    DASHBOARD_DEFAULT_POPULATION_PATH,
    DASHBOARD_DEFAULT_RESULTS_PATH,
    INCOME_BRACKET_LOW_MAX_LPA,
    INCOME_BRACKET_MID_MAX_LPA,
)


def project_root() -> Path:
    """Repository root (parent of ``app/``)."""

    return Path(__file__).resolve().parents[2]


def default_population_dir() -> Path:
    return project_root() / DASHBOARD_DEFAULT_POPULATION_PATH


def default_results_dir() -> Path:
    return project_root() / DASHBOARD_DEFAULT_RESULTS_PATH


def scenario_results_path() -> Path:
    default_results_dir().mkdir(parents=True, exist_ok=True)
    return default_results_dir() / "scenario_results.json"


def income_bracket_label(household_income_lpa: float) -> str:
    """Bucket household income into analysis segments."""

    if household_income_lpa <= INCOME_BRACKET_LOW_MAX_LPA:
        return "low_income"
    if household_income_lpa <= INCOME_BRACKET_MID_MAX_LPA:
        return "middle_income"
    return "high_income"


def child_age_group_label(age: int | float | None) -> str:
    """Bucket a child's age into dashboard-friendly life-stage labels."""

    if age is None or pd.isna(age):
        return "Unknown"

    numeric_age = int(age)
    if numeric_age <= 5:
        return "Toddler (2-5)"
    if numeric_age <= 10:
        return "School-age (6-10)"
    return "Pre-teen (11-14)"


def load_scenario_results_from_disk() -> dict[str, dict[str, dict[str, Any]]]:
    """Load persisted static simulation outputs keyed by scenario id."""

    path = scenario_results_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_scenario_results_to_disk(payload: dict[str, dict[str, dict[str, Any]]]) -> None:
    path = scenario_results_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def tier1_dataframe_with_results(
    population: Any,
    results_by_persona: dict[str, dict[str, Any]] | None,
) -> pd.DataFrame:
    """
    Tier 1 personas flattened and merged with simulation result columns when provided.
    """

    rows: list[dict[str, Any]] = []
    for persona in population.tier1_personas:
        flat = persona.to_flat_dict()
        flat["id"] = persona.id
        flat["tier"] = persona.tier
        flat["income_bracket"] = income_bracket_label(float(flat.get("household_income_lpa", 0.0)))
        if results_by_persona and persona.id in results_by_persona:
            res = results_by_persona[persona.id]
            for key in (
                "outcome",
                "need_score",
                "awareness_score",
                "consideration_score",
                "purchase_score",
                "rejection_stage",
                "rejection_reason",
            ):
                if key in res:
                    flat[key] = res[key]
        rows.append(flat)
    return pd.DataFrame(rows)


def adoption_heatmap_matrix(
    df: pd.DataFrame,
    row_attr: str,
    col_attr: str,
    outcome_col: str = "outcome",
) -> tuple[list[list[float]], list[str], list[str]]:
    """
    Build adoption-rate matrix for heatmap (row_attr vs col_attr).

    Returns:
        ``z_matrix``, ``row_labels``, ``col_labels`` suitable for
        :func:`src.utils.viz.create_segment_heatmap` keyword mode.
    """

    if df.empty or row_attr not in df.columns or col_attr not in df.columns:
        return [], [], []

    work = df[[row_attr, col_attr, outcome_col]].copy()
    work["_adopt"] = (work[outcome_col] == "adopt").astype(float)
    pivot = work.groupby([row_attr, col_attr], as_index=False)["_adopt"].mean()
    table = pivot.pivot(index=row_attr, columns=col_attr, values="_adopt")
    table = table.fillna(0.0)

    row_labels = [str(x) for x in table.index.tolist()]
    col_labels = [str(c) for c in table.columns.tolist()]
    z_matrix = table.values.tolist()
    return z_matrix, row_labels, col_labels
