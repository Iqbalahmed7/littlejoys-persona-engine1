"""Tests for Sprint 9 interview prompt assembly."""

from __future__ import annotations

import pytest

from src.analysis.interview_prompts import (
    BELIEF_CONVERTERS,
    assemble_system_prompt,
    build_decision_narrative,
    build_identity_anchor,
    build_lived_experience,
)
from src.decision.scenarios import get_scenario


@pytest.mark.parametrize(
    ("score", "must_contain"),
    [
        (0.9, "Every rupee matters"),
        (0.6, "thoughtful"),
        (0.4, "first thing"),
        (0.1, "don't think twice"),
    ],
)
def test_budget_belief_four_tiers(score: float, must_contain: str) -> None:
    text = BELIEF_CONVERTERS["budget_consciousness"](score)
    assert must_contain.lower() in text.lower()


def test_belief_converter_handles_nan() -> None:
    t = BELIEF_CONVERTERS["health_anxiety"](float("nan"))
    assert len(t) > 10


def test_identity_anchor_uses_city_not_persona_id(sample_persona) -> None:
    text = build_identity_anchor(sample_persona)
    assert sample_persona.id not in text
    assert "Mumbai" in text
    assert "simulation" in text.lower()


def test_lived_experience_groups_categories(sample_persona) -> None:
    text = build_lived_experience(sample_persona)
    assert "beliefs" in text.lower() or "think" in text.lower()


def test_decision_narrative_adopt(sample_persona) -> None:
    sc = get_scenario("nutrimix_2_6")
    dr = {"outcome": "adopt"}
    t = build_decision_narrative(sample_persona, dr, sc)
    assert "Nutrimix" in t


def test_decision_narrative_awareness(sample_persona) -> None:
    sc = get_scenario("nutrimix_2_6")
    dr = {"outcome": "reject", "rejection_stage": "awareness"}
    t = build_decision_narrative(sample_persona, dr, sc)
    assert "never came across" in t.lower() or "simply never" in t.lower()


def test_decision_narrative_need(sample_persona) -> None:
    sc = get_scenario("nutrimix_2_6")
    dr = {"outcome": "reject", "rejection_stage": "need_recognition"}
    t = build_decision_narrative(sample_persona, dr, sc)
    assert "never felt" in t.lower()


def test_assemble_contains_all_layers(sample_persona) -> None:
    prompt = assemble_system_prompt(
        sample_persona,
        "nutrimix_2_6",
        {"outcome": "reject", "rejection_stage": "purchase", "rejection_reason": "price_too_high"},
    )
    assert prompt.count("---") >= 4
    assert "BEHAVIORAL RULES" in prompt
    assert "Nutrimix" in prompt
