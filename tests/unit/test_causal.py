"""Unit tests for causal statement generation."""

from __future__ import annotations

import re

from src.analysis.causal import CausalStatement, VariableImportance, generate_causal_statements


def _causal_importances() -> list[VariableImportance]:
    return [
        VariableImportance(
            variable_name="feature1",
            coefficient=1.8,
            shap_mean_abs=1.0,
            direction="positive",
            rank=1,
        ),
        VariableImportance(
            variable_name="feature2",
            coefficient=-0.8,
            shap_mean_abs=0.25,
            direction="negative",
            rank=2,
        ),
        VariableImportance(
            variable_name="feature3",
            coefficient=0.2,
            shap_mean_abs=0.10,
            direction="positive",
            rank=3,
        ),
    ]


def _causal_results() -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}

    for index in range(24):
        tier = "Tier1" if index < 12 else "Tier3"
        feature1 = 0.85 if index % 2 == 0 else 0.20
        if tier == "Tier1":
            outcome = "adopt" if feature1 >= 0.50 else "reject"
        else:
            outcome = "adopt" if index in {12, 16, 19, 21} else "reject"

        results[f"p{index:02d}"] = {
            "outcome": outcome,
            "feature1": feature1,
            "feature2": 0.90 if outcome == "reject" else 0.15,
            "feature3": 0.50,
            "city_tier": tier,
            "household_income_lpa": 18.0 if tier == "Tier1" else 6.0,
        }

    return results


def test_causal_statements_reference_specific_variables() -> None:
    statements = generate_causal_statements(_causal_importances(), _causal_results(), top_n=3)

    assert statements
    assert any("feature1" in statement.statement for statement in statements)


def test_causal_statements_sorted_by_evidence_strength() -> None:
    statements = generate_causal_statements(_causal_importances(), _causal_results(), top_n=3)
    strengths = [statement.evidence_strength for statement in statements]

    assert strengths == sorted(strengths, reverse=True)


def test_causal_statements_include_threshold_values() -> None:
    statements = generate_causal_statements(_causal_importances(), _causal_results(), top_n=3)

    assert any(re.search(r"\d+\.\d{2}", statement.statement) for statement in statements)


def test_causal_statements_empty_input_returns_empty() -> None:
    assert generate_causal_statements([], {}) == []


def test_segment_specific_statements_generated_when_lift_differs() -> None:
    statements = generate_causal_statements(_causal_importances(), _causal_results(), top_n=3)

    assert any(
        isinstance(statement, CausalStatement)
        and statement.segment is not None
        and "city_tier" in statement.statement
        for statement in statements
    )
