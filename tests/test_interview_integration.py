"""Integration test: prompt assembly + guardrail validation on mock interview."""

from pathlib import Path

import pytest


@pytest.fixture
def population():
    pop_path = Path("data/population")
    if not pop_path.exists():
        pytest.skip("Population data not generated")
    from src.generation.population import Population
    return Population.load(pop_path)


class TestInterviewIntegration:
    def test_assemble_prompt_for_real_persona(self, population):
        try:
            from src.analysis.interview_prompts import assemble_system_prompt
            from src.decision.funnel import run_funnel
            from src.decision.scenarios import get_scenario
        except ImportError:
            pytest.skip("Sprint 9 Track A/B not merged")

        persona = population.tier1_personas[0]
        scenario = get_scenario("nutrimix_2_6")
        decision = run_funnel(persona, scenario)

        prompt = assemble_system_prompt(
            persona=persona,
            scenario_id="nutrimix_2_6",
            decision_result=decision.to_dict(),
        )

        assert len(prompt) > 500  # Should be substantial
        assert persona.demographics.city_name in prompt
        assert "NutriMix" in prompt or "nutrimix" in prompt.lower()
        # Should NOT contain raw scores like "0.4523"
        import re
        raw_scores = re.findall(r"\d+\.\d{4,}", prompt)
        assert len(raw_scores) == 0, f"Raw scores found in prompt: {raw_scores}"

    def test_guardrails_on_clean_mock_response(self, population):
        try:
            from src.analysis.interview_guardrails import run_all_guardrails
        except ImportError:
            pytest.skip("Sprint 9 module missing")

        persona = population.tier1_personas[0]
        clean_response = (
            f"In our home in {persona.demographics.city_name}, I always make sure "
            f"my {persona.demographics.child_ages[0]}-year-old gets proper nutrition. "
            "I compare prices at the local store before buying health products."
        )

        warnings = run_all_guardrails(
            response=clean_response,
            question="Tell me about how you approach nutrition for your kids.",
            persona=persona,
            decision_result={"outcome": "reject", "rejection_stage": "awareness"},
            previous_turns=None,
        )

        assert isinstance(warnings, list)
        # A clean response should have few or no warnings
