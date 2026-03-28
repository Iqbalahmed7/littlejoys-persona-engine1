"""Unit tests for the deep persona interview system."""

from __future__ import annotations

import pytest

from src.analysis.interviews import (
    InterviewTurn,
    PersonaInterviewer,
    check_interview_quality,
)
from src.config import Config
from src.taxonomy.schema import (
    DailyRoutineAttributes,
    HealthAttributes,
    Persona,
    PsychologyAttributes,
)
from src.utils.llm import LLMClient


def _decision_result(outcome: str = "reject") -> dict[str, object]:
    return {
        "scenario_id": "nutrimix_2_6",
        "product_name": "Nutrimix",
        "outcome": outcome,
        "need_score": 0.62,
        "awareness_score": 0.58,
        "consideration_score": 0.44,
        "purchase_score": 0.31,
        "rejection_reason": "price_too_high" if outcome == "reject" else None,
    }


def _mock_interviewer() -> PersonaInterviewer:
    client = LLMClient(Config(llm_mock_enabled=True, llm_cache_enabled=False, anthropic_api_key=""))
    return PersonaInterviewer(client)


def test_system_prompt_includes_persona_demographics(sample_persona: Persona) -> None:
    prompt = _mock_interviewer().build_system_prompt(
        sample_persona,
        "nutrimix_2_6",
        _decision_result(),
    )

    assert "Mumbai" in prompt
    assert "Tier1" in prompt
    assert "full time" in prompt
    assert "masters" in prompt
    assert "15.0 LPA" in prompt


def test_system_prompt_includes_decision_outcome(sample_persona: Persona) -> None:
    prompt = _mock_interviewer().build_system_prompt(
        sample_persona,
        "nutrimix_2_6",
        _decision_result("reject"),
    )

    assert "Outcome: reject" in prompt
    assert "Rejection reason: price_too_high" in prompt
    assert "Nutrimix" in prompt


def test_system_prompt_includes_psychographic_highlights(sample_persona: Persona) -> None:
    tuned = sample_persona.model_copy(
        update={
            "psychology": PsychologyAttributes(health_anxiety=0.92, simplicity_preference=0.12),
            "daily_routine": DailyRoutineAttributes(budget_consciousness=0.91),
            "health": HealthAttributes(medical_authority_trust=0.88),
        },
        deep=True,
    )
    prompt = _mock_interviewer().build_system_prompt(
        tuned,
        "nutrimix_2_6",
        _decision_result(),
    )

    assert "health_anxiety = 0.92" in prompt
    assert "budget_consciousness = 0.91" in prompt
    assert "medical_authority_trust = 0.88" in prompt


@pytest.mark.asyncio
async def test_interview_returns_interview_turn(sample_persona: Persona) -> None:
    turn = await _mock_interviewer().interview(
        sample_persona,
        "How do you think about the price?",
        "nutrimix_2_6",
        _decision_result(),
    )

    assert isinstance(turn, InterviewTurn)
    assert turn.role == "persona"
    assert len(turn.content.split()) >= 50


@pytest.mark.asyncio
async def test_interview_maintains_conversation_history(sample_persona: Persona) -> None:
    history = [
        InterviewTurn(
            role="user", content="Tell me about your mornings.", timestamp="2026-03-28T00:00:00Z"
        ),
        InterviewTurn(
            role="persona", content="Our mornings are rushed.", timestamp="2026-03-28T00:00:10Z"
        ),
    ]
    turn = await _mock_interviewer().interview(
        sample_persona,
        "And what about price?",
        "nutrimix_2_6",
        _decision_result(),
        conversation_history=history,
    )

    assert "As I mentioned earlier" in turn.content


@pytest.mark.asyncio
async def test_interview_works_in_mock_mode(sample_persona: Persona) -> None:
    interviewer = _mock_interviewer()
    turn = await interviewer.interview(
        sample_persona,
        "Who do you trust when it comes to supplements?",
        "nutrimix_2_6",
        _decision_result(),
    )

    assert "pediatrician" in turn.content.lower() or "doctor" in turn.content.lower()


def test_quality_check_catches_ai_disclosure(sample_persona: Persona) -> None:
    quality = check_interview_quality(
        "As an AI, I do not have feelings about this purchase decision.",
        sample_persona,
        _decision_result(),
    )

    assert quality.no_ai_disclosure is False


def test_quality_check_validates_response_length(sample_persona: Persona) -> None:
    too_short = check_interview_quality("Too short.", sample_persona, _decision_result())
    too_long = check_interview_quality(
        "word " * 301 + "Mumbai price trust",
        sample_persona,
        _decision_result(),
    )

    assert too_short.appropriate_length is False
    assert too_long.appropriate_length is False


def test_quality_check_rejects_inconsistent_sentiment(sample_persona: Persona) -> None:
    quality = check_interview_quality(
        "I absolutely love this product and would buy it every month because it is perfect for us in Mumbai.",
        sample_persona,
        _decision_result("reject"),
    )

    assert quality.in_character is False
    assert "response_sentiment_inconsistent_with_rejection" in quality.warnings
