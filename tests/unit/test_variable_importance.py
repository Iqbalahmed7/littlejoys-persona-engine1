import numpy as np
import pytest

from src.analysis.causal import compute_variable_importance


@pytest.fixture
def mock_results():
    # Make a synthetic logic where F1 is highly positively correlated with outcome,
    # F2 is moderately negatively correlated,
    # F3 is random noise.
    rng = np.random.default_rng(42)
    res = {}
    for i in range(200):
        f1 = rng.random()
        f2 = rng.random()
        f3 = rng.random()

        # Outcome logic: largely driven by F1 and inversely by F2
        logit = -2.0 + 5.0 * f1 - 3.0 * f2
        prob = 1.0 / (1.0 + np.exp(-logit))
        outcome = 1 if rng.random() < prob else 0

        res[f"p{i}"] = {"outcome": outcome, "feature1": f1, "feature2": f2, "feature3": f3}
    return res


def test_variable_importance_returns_ranked_list(mock_results):
    importances = compute_variable_importance(mock_results)
    assert len(importances) == 3

    # Ranks should be 1, 2, 3
    ranks = [imp.rank for imp in importances]
    assert ranks == [1, 2, 3]

    # Check that they are sorted by absolute coefficient
    abs_coefs = [abs(imp.coefficient) for imp in importances]
    assert abs_coefs[0] >= abs_coefs[1]
    assert abs_coefs[1] >= abs_coefs[2]


def test_top_variable_has_highest_coefficient(mock_results):
    importances = compute_variable_importance(mock_results)
    assert len(importances) > 0
    top = importances[0]

    # feature1 has the highest synthetic coefficient (5.0 vs -3.0 vs 0.0)
    assert top.variable_name == "feature1"
    assert top.direction == "positive"

    # feature2 should be second
    second = importances[1]
    assert second.variable_name == "feature2"
    assert second.direction == "negative"


def test_variable_importance_reproducible(mock_results):
    imp1 = compute_variable_importance(mock_results)
    imp2 = compute_variable_importance(mock_results)

    for a, b in zip(imp1, imp2, strict=True):
        assert a.variable_name == b.variable_name
        assert a.coefficient == b.coefficient
        assert a.shap_mean_abs == b.shap_mean_abs
        assert a.rank == b.rank
