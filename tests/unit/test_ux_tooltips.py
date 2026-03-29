"""Structural tests for PRD-014a UX copy and tooltip source data."""

from __future__ import annotations

from src.constants import SCENARIO_IDS
from src.simulation.counterfactual import get_predefined_counterfactuals
from src.utils.display import (
    CHANNEL_HELP,
    INTERVENTION_RATIONALE,
    SCATTER_PURCHASE_OUTCOME_LABELS,
    scatter_purchase_outcome_label,
)


def test_intervention_rationale_covers_all_scenarios() -> None:
    """Every scenario's predefined interventions have rationale text."""

    for scenario_id in SCENARIO_IDS:
        predefined = get_predefined_counterfactuals(scenario_id)
        for cf_name in predefined:
            rationale = INTERVENTION_RATIONALE.get(scenario_id, {}).get(cf_name, "")
            assert rationale, f"Missing rationale for {scenario_id}/{cf_name}"


def test_channel_help_covers_all_channels() -> None:
    """Every default channel has help text."""

    for ch in ["instagram", "youtube", "whatsapp"]:
        assert ch in CHANNEL_HELP
        assert len(CHANNEL_HELP[ch]) > 10


def test_scatter_outcome_labels_avoid_raw_codes() -> None:
    """Scatter legend uses executive-friendly terms, not adopt/reject."""

    assert "adopt" not in SCATTER_PURCHASE_OUTCOME_LABELS["adopt"].lower()
    assert "reject" not in SCATTER_PURCHASE_OUTCOME_LABELS["reject"].lower()


def test_scatter_purchase_outcome_label_none() -> None:
    assert scatter_purchase_outcome_label(None) == "No simulation"


def test_scatter_purchase_outcome_label_known() -> None:
    assert scatter_purchase_outcome_label("adopt") == "Would buy"
    assert scatter_purchase_outcome_label("reject") == "Wouldn't buy"
