"""Structural tests for Probing Tree UI helpers (PRD-014b)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.components.probing_tree_helpers import (
    probe_icon,
    probe_label,
    verdict_status_display,
)
from src.probing.models import Probe, ProbeType


def test_probe_icon_all_types() -> None:
    """Every ProbeType has an icon."""

    for pt in ProbeType:
        icon = probe_icon(pt)
        assert len(icon) > 0


def test_probe_label_interview() -> None:
    p = Probe(
        id="test",
        hypothesis_id="h1",
        probe_type=ProbeType.INTERVIEW,
        question_template="What made you hesitate?",
    )
    label = probe_label(p)
    assert "hesitate" in label


def test_probe_label_simulation() -> None:
    p = Probe(
        id="test",
        hypothesis_id="h1",
        probe_type=ProbeType.SIMULATION,
        scenario_modifications={"product.price_inr": 479},
        comparison_metric="adoption_rate",
    )
    label = probe_label(p)
    assert "479" in label


def test_probe_label_attribute() -> None:
    p = Probe(
        id="test",
        hypothesis_id="h1",
        probe_type=ProbeType.ATTRIBUTE,
        analysis_attributes=["budget_consciousness"],
        split_by="outcome",
    )
    label = probe_label(p)
    assert "Price Sensitivity" in label or "budget" in label.lower()


def test_verdict_status_display() -> None:
    assert verdict_status_display("partially_confirmed") == "Partially Confirmed"


def test_load_population_returns_none_when_missing(monkeypatch) -> None:
    import streamlit as st

    from app.components import probing_tree_helpers as h

    if "population" in st.session_state:
        del st.session_state["population"]

    monkeypatch.setattr(Path, "exists", lambda self: False)

    assert h.load_population_for_probing() is None


def test_load_population_from_session(monkeypatch) -> None:
    import streamlit as st

    from app.components import probing_tree_helpers as h

    pop = MagicMock()
    st.session_state["population"] = pop
    monkeypatch.setattr(Path, "exists", lambda self: False)
    try:
        assert h.load_population_for_probing() is pop
    finally:
        del st.session_state["population"]
