# Antigravity — Sprint 9 Track D: Tests for Interview Prompts, Guardrails & Tree Viz

**Branch:** `sprint-9-track-d-tests`
**Base:** `main`

## Context

Sprint 9 introduces three new modules:
- `src/analysis/interview_prompts.py` (Track A) — 5-layer system prompt builder
- `src/analysis/interview_guardrails.py` (Track B) — post-response validation
- `app/components/probing_tree_viz.py` (Track C) — McKinsey tree visualization

This track writes tests for all three. Since implementation may not be merged yet, structure tests to import expected modules and validate expected behavior.

## Deliverables

### 1. Interview Prompt Tests

**File:** `tests/test_interview_prompts.py` (NEW)

```python
"""Tests for the 5-layer interview prompt system."""

import pytest
from src.analysis.interview_prompts import (
    BELIEF_CONVERTERS,
    BELIEF_CATEGORIES,
    build_identity_anchor,
    build_lived_experience,
    build_decision_narrative,
    build_scope_guardrails,
    BEHAVIORAL_DIRECTIVES,
    assemble_system_prompt,
)
```

**Test classes:**

#### TestBeliefConverters (~20 tests)

```python
class TestBeliefConverters:
    """Each belief converter must produce valid text for all score ranges."""

    @pytest.mark.parametrize("score", [0.0, 0.15, 0.25, 0.50, 0.75, 0.90, 1.0])
    def test_budget_consciousness_all_tiers(self, score):
        result = BELIEF_CONVERTERS["budget_consciousness"](score)
        assert isinstance(result, str)
        assert len(result) > 20  # non-trivial text

    @pytest.mark.parametrize("score", [0.0, 0.25, 0.50, 0.75, 1.0])
    def test_health_anxiety_all_tiers(self, score):
        result = BELIEF_CONVERTERS["health_anxiety"](score)
        assert isinstance(result, str)
        assert len(result) > 20

    def test_all_converters_exist_for_categories(self):
        """Every attribute listed in BELIEF_CATEGORIES must have a converter."""
        for category, attrs in BELIEF_CATEGORIES.items():
            for attr in attrs:
                assert attr in BELIEF_CONVERTERS, (
                    f"Missing converter for {attr} in category {category}"
                )

    def test_minimum_converter_count(self):
        """Must have at least 15 converters."""
        assert len(BELIEF_CONVERTERS) >= 15

    def test_converters_produce_different_text_for_extremes(self):
        """High and low scores should produce different belief statements."""
        for attr, converter in BELIEF_CONVERTERS.items():
            high = converter(0.9)
            low = converter(0.1)
            assert high != low, f"Converter for {attr} returns same text for 0.9 and 0.1"

    def test_all_categories_non_empty(self):
        """Each belief category must contain at least one attribute."""
        for category, attrs in BELIEF_CATEGORIES.items():
            assert len(attrs) >= 1, f"Category {category} is empty"
```

#### TestIdentityAnchor (~5 tests)

Use a mock/fixture persona. Test that output:
- Contains the persona's city name
- Contains the persona's age
- Contains a children description
- Contains employment description
- Contains the "You are NOT role-playing" anchor text
- Does NOT contain the raw persona ID (e.g., "Priya-Mumbai-Mom-32")

**Fixture:**

```python
@pytest.fixture
def sample_persona():
    """Create a minimal persona for testing.

    Load from disk if available, otherwise skip.
    """
    from pathlib import Path
    from src.generation.population import Population

    pop_path = Path("data/population")
    if not pop_path.exists():
        pytest.skip("Population data not generated")
    pop = Population.load(pop_path)
    return pop.tier1_personas[0]

@pytest.fixture
def sample_decision_result():
    return {
        "outcome": "reject",
        "need_score": 0.65,
        "awareness_score": 0.22,
        "consideration_score": 0.0,
        "purchase_score": 0.0,
        "rejection_stage": "awareness",
        "rejection_reason": "low_awareness",
    }
```

#### TestDecisionNarrative (~8 tests)

Test that:
- Adopter narrative contains the product name
- Adopter narrative contains positive language
- Rejector narrative matches rejection stage:
  - `need_recognition` → mentions "need" or "didn't feel"
  - `awareness` → mentions "never heard" or "never came across"
  - `consideration` → mentions "looked into" or "didn't click"
  - `purchase` → mentions "considered" or "price" or "didn't pull"
- Narrative does NOT contain raw score values like "0.45"

#### TestScopeGuardrails (~3 tests)

- Output contains "WILL answer" section
- Output contains "WILL NOT answer" section
- Output contains the product name from the scenario

#### TestAssembly (~3 tests)

- `assemble_system_prompt()` returns a non-empty string
- Output contains the "---" layer separators
- Output contains text from all 5 layers

### 2. Interview Guardrail Tests

**File:** `tests/test_interview_guardrails.py` (NEW)

```python
"""Tests for interview post-response guardrails."""

import pytest
from src.analysis.interview_guardrails import (
    check_scope_violation,
    check_sec_coherence,
    check_reframing_susceptibility,
    check_cross_turn_consistency,
    run_all_guardrails,
)
```

#### TestScopeViolation (~8 tests)

```python
class TestScopeViolation:
    def test_clean_response_no_violations(self):
        result = check_scope_violation(
            "I buy Horlicks from the local store for my children."
        )
        assert result == []

    def test_political_reference_flagged(self):
        result = check_scope_violation(
            "I think the election results will affect product prices."
        )
        assert any("scope_violation" in w for w in result)

    def test_sports_reference_flagged(self):
        result = check_scope_violation(
            "I was watching the IPL match instead of shopping."
        )
        assert any("scope_violation" in w for w in result)

    def test_child_cricket_not_flagged(self):
        """Child activities mentioning cricket should NOT be flagged."""
        result = check_scope_violation(
            "My son has cricket practice after school so mornings are hectic."
        )
        # This is about child's routine — should ideally not flag
        # Accept either behavior but document

    def test_stock_market_flagged(self):
        result = check_scope_violation(
            "I invest in mutual funds and the stock market is down."
        )
        assert any("scope_violation" in w for w in result)

    def test_nutrition_discussion_clean(self):
        result = check_scope_violation(
            "I give my daughter calcium supplements and she takes vitamins daily."
        )
        assert result == []

    def test_religion_flagged(self):
        result = check_scope_violation(
            "Our religion forbids certain foods."
        )
        assert any("scope_violation" in w for w in result)

    def test_dietary_culture_clean(self):
        """Vegetarian/non-veg discussion is in-scope."""
        result = check_scope_violation(
            "We are a vegetarian family so protein sources are limited."
        )
        assert result == []
```

#### TestSECCoherence (~6 tests)

Create a mock persona helper:

```python
class _MockDemographics:
    def __init__(self, sec, income, platform="local_store"):
        self.socioeconomic_class = sec
        self.household_income_lpa = income
        self.city_name = "Mumbai"
        self.city_tier = "Tier1"

class _MockDailyRoutine:
    def __init__(self, platform="local_store"):
        self.primary_shopping_platform = platform

class _MockPersona:
    def __init__(self, sec="C1", income=4.0, platform="local_store"):
        self.demographics = _MockDemographics(sec, income, platform)
        self.daily_routine = _MockDailyRoutine(platform)
```

Tests:
- C1 persona mentioning "organic harvest" → flagged
- C2 persona mentioning "Horlicks" → clean
- A1 persona mentioning "can't afford" → flagged
- A1 persona mentioning premium brands → clean
- B1 persona → no flags for mass market brands
- C1 persona mentioning "Blinkit" shopping → flagged

#### TestAntiReframing (~5 tests)

- Non-leading question + agreement → clean (no flag)
- Leading question ("Don't you think...") + agreement ("you're absolutely right") → flagged
- Leading question + disagreement → clean
- Normal question + normal response → clean
- Leading question with partial agreement → depends on exact markers

#### TestCrossTurnConsistency (~5 tests)

```python
from src.analysis.interviews import InterviewTurn

def _make_turn(role, content):
    return InterviewTurn(role=role, content=content, timestamp="2026-01-01T00:00:00Z")
```

- No prior turns → clean
- Prior positive, current negative → flagged
- Prior negative, current negative → clean (consistent)
- Prior mentions using Horlicks, current says never used Horlicks → flagged

#### TestRunAllGuardrails (~3 tests)

- Clean response → empty list
- Response with scope + SEC issues → both warnings present
- None previous_turns → no crash

### 3. Probing Tree Visualization Tests

**File:** `tests/test_probing_tree_viz.py` (NEW)

```python
"""Tests for McKinsey decision tree visualization components."""

import pytest
from app.components.probing_tree_viz import (
    VERDICT_STYLES,
    PROBE_TYPE_CONFIG,
)
```

#### TestVerdictStyles (~4 tests)

- All 4 statuses covered: confirmed, partially_confirmed, rejected, inconclusive
- Each style has icon, color, label keys
- Icons are non-empty strings
- Colors are valid hex codes (start with #)

#### TestProbeTypeConfig (~3 tests)

- All 3 probe types covered: interview, simulation, attribute
- Each config has icon, label, color keys
- Labels match expected values

#### TestConfidenceColors (~4 tests)

If there's a `_confidence_to_color` or similar helper:
- ≥0.70 → green
- ≥0.50 → amber/orange
- ≥0.30 → orange
- <0.30 → red

#### TestResultsTable (~3 tests)

Create synthetic data and verify table structure:
- Table has correct column headers
- Handles empty probes gracefully
- Handles hypotheses with no verdicts

### 4. Integration Smoke Test

**File:** `tests/test_interview_integration.py` (NEW)

```python
"""Integration test: prompt assembly + guardrail validation on mock interview."""

import pytest
from pathlib import Path


@pytest.fixture
def population():
    pop_path = Path("data/population")
    if not pop_path.exists():
        pytest.skip("Population data not generated")
    from src.generation.population import Population
    return Population.load(pop_path)


class TestInterviewIntegration:
    def test_assemble_prompt_for_real_persona(self, population):
        from src.analysis.interview_prompts import assemble_system_prompt
        from src.decision.funnel import run_funnel
        from src.decision.scenarios import get_scenario

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
        from src.analysis.interview_guardrails import run_all_guardrails

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
```

## Files to Read Before Starting

1. `src/analysis/interviews.py` — InterviewTurn model, existing quality checks
2. `docs/designs/INTERVIEW-PROMPT-ARCHITECTURE.md` — design spec for prompts + guardrails
3. `docs/designs/PROBING-TREE-VISUALIZATION.md` — design spec for tree viz
4. `tests/unit/test_interviews.py` — existing test patterns
5. `src/probing/models.py` — probing data models for viz tests

## Constraints

- Python 3.11+, pytest
- Tests that depend on population data: use `pytest.skip` if `data/population/` not available
- Pure data/logic tests: use synthetic fixtures (mock personas, mock turns)
- Do NOT mock Streamlit rendering — test data logic only
- Each test file independently runnable
- Aim for ~70 tests total across all files

## Acceptance Criteria

- [ ] 4 test files created
- [ ] ~70 tests total
- [ ] Belief converter tests cover all score ranges via parametrize
- [ ] Guardrail tests cover all 4 check types with positive and negative cases
- [ ] Tree viz tests validate style constants and data structures
- [ ] Integration test verifies prompt assembly on real persona
- [ ] No Streamlit rendering in tests
- [ ] All tests that don't depend on Sprint 9 code pass (fixture tests, pattern tests)
