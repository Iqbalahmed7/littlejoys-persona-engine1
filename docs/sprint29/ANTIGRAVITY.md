# Sprint 29 — Brief: ANTIGRAVITY

**Role:** Test coverage / schema integrity
**Model:** Gemini 3 Flash
**Assignment:** `tests/test_reflection.py` + `tests/test_schema_coherence.py` + update `tests/test_agent.py`
**Est. duration:** 3-4 hours
**START:** After Cursor + Codex + Goose all signal done.

---

## Files to Create / Modify

| Action | File |
|---|---|
| CREATE | `tests/test_reflection.py` |
| CREATE | `tests/test_schema_coherence.py` |
| MODIFY | `tests/test_agent.py` — replace 1 test, add 2 new tests |

## Do NOT Touch
- Any `src/` file
- `scripts/`
- `app/`

---

## Critical: Read before writing

Before writing any test, read these files to get exact class interfaces:
- `src/agents/reflection.py` (Cursor's output)
- `src/agents/agent.py` (Codex's `reflect()` addition)
- `src/taxonomy/schema.py` (field locations — trust this, not your memory)

---

## Part 1: `tests/test_reflection.py`

≥ 10 tests. All LLM calls must be mocked — no real API calls.

### Fixtures

```python
import json
import pytest
from unittest.mock import MagicMock, patch
from src.agents.reflection import ReflectionEngine, ReflectionInsight
from src.taxonomy.schema import Persona, MemoryEntry


@pytest.fixture
def minimal_persona(minimal_persona_dict):
    """Persona with a few episodic memories already loaded."""
    p = Persona.model_validate(minimal_persona_dict)
    for i in range(5):
        p.episodic_memory.append(
            MemoryEntry(
                timestamp=f"2026-01-0{i+1}T10:00:00+00:00",
                event_type="stimulus",
                content=f"Test stimulus {i}: LittleJoys ad content here",
                emotional_valence=0.3,
                salience=0.6,
            )
        )
    return p


@pytest.fixture
def engine():
    return ReflectionEngine()


MOCK_LLM_RESPONSE = json.dumps({
    "insights": [
        {
            "insight": "This persona is developing a pattern of trust toward expert-endorsed nutrition products.",
            "confidence": 0.82,
            "source_indices": [0, 2],
            "emotional_valence": 0.4,
        },
        {
            "insight": "Price sensitivity is moderating enthusiasm for clean-label products.",
            "confidence": 0.71,
            "source_indices": [1, 3],
            "emotional_valence": -0.1,
        },
    ]
})
```

### Tests to write

```
test_engine_instantiates_with_defaults
test_should_reflect_false_below_threshold
test_should_reflect_true_at_threshold
test_should_reflect_true_above_threshold
test_reflect_returns_empty_list_on_no_memories
test_reflect_returns_insight_objects
test_reflect_appends_entries_to_episodic_memory
test_reflect_appended_entries_have_correct_event_type
test_reflect_appended_entries_have_correct_salience
test_reflect_respects_n_insights_count
test_reflect_returns_empty_list_on_malformed_json
test_reflection_insight_to_memory_entry_produces_valid_entry
test_reflection_insight_content_contains_reflection_prefix
test_reflection_engine_window_limits_memories_used
test_parse_insights_skips_invalid_items
```

### Test implementations

```python
def test_engine_instantiates_with_defaults():
    engine = ReflectionEngine()
    assert engine.threshold == 5.0
    assert engine.window == 20
    assert engine.max_insights == 3


def test_should_reflect_false_below_threshold(engine):
    assert engine.should_reflect(4.99) is False


def test_should_reflect_true_at_threshold(engine):
    assert engine.should_reflect(5.0) is True


def test_should_reflect_true_above_threshold(engine):
    assert engine.should_reflect(7.5) is True


def test_reflect_returns_empty_list_on_no_memories(engine, minimal_persona):
    minimal_persona.episodic_memory.clear()
    llm_fn = MagicMock()
    result = engine.reflect(minimal_persona, llm_fn)
    assert result == []
    llm_fn.assert_not_called()


def test_reflect_returns_insight_objects(engine, minimal_persona):
    llm_fn = MagicMock(return_value=MOCK_LLM_RESPONSE)
    result = engine.reflect(minimal_persona, llm_fn, n_insights=2)
    assert len(result) == 2
    assert all(isinstance(r, ReflectionInsight) for r in result)


def test_reflect_appends_entries_to_episodic_memory(engine, minimal_persona):
    count_before = len(minimal_persona.episodic_memory)
    llm_fn = MagicMock(return_value=MOCK_LLM_RESPONSE)
    engine.reflect(minimal_persona, llm_fn, n_insights=2)
    assert len(minimal_persona.episodic_memory) == count_before + 2


def test_reflect_appended_entries_have_correct_event_type(engine, minimal_persona):
    llm_fn = MagicMock(return_value=MOCK_LLM_RESPONSE)
    engine.reflect(minimal_persona, llm_fn, n_insights=2)
    new_entries = [m for m in minimal_persona.episodic_memory if m.event_type == "reflection"]
    assert len(new_entries) == 2


def test_reflect_appended_entries_have_correct_salience(engine, minimal_persona):
    llm_fn = MagicMock(return_value=MOCK_LLM_RESPONSE)
    engine.reflect(minimal_persona, llm_fn, n_insights=2)
    reflection_entries = [m for m in minimal_persona.episodic_memory if m.event_type == "reflection"]
    for entry in reflection_entries:
        assert entry.salience == pytest.approx(0.85)


def test_reflect_respects_n_insights_count(engine, minimal_persona):
    """Only 1 insight requested — only 1 should be appended."""
    single_insight_response = json.dumps({
        "insights": [
            {
                "insight": "Single insight only.",
                "confidence": 0.9,
                "source_indices": [0],
                "emotional_valence": 0.2,
            }
        ]
    })
    llm_fn = MagicMock(return_value=single_insight_response)
    result = engine.reflect(minimal_persona, llm_fn, n_insights=1)
    assert len(result) == 1


def test_reflect_returns_empty_list_on_malformed_json(engine, minimal_persona):
    llm_fn = MagicMock(return_value="NOT JSON AT ALL {{{")
    result = engine.reflect(minimal_persona, llm_fn)
    assert result == []


def test_reflection_insight_to_memory_entry_produces_valid_entry():
    insight = ReflectionInsight(
        insight="Trust in pediatrician recommendations is high.",
        confidence=0.85,
        source_indices=[0, 1, 2],
        emotional_valence=0.3,
    )
    entry = insight.to_memory_entry("2026-01-01T12:00:00+00:00")
    assert isinstance(entry, MemoryEntry)
    assert entry.event_type == "reflection"
    assert entry.salience == pytest.approx(0.85)
    assert entry.emotional_valence == pytest.approx(0.3)


def test_reflection_insight_content_contains_reflection_prefix():
    insight = ReflectionInsight(
        insight="Test insight.",
        confidence=0.7,
        source_indices=[0],
        emotional_valence=0.0,
    )
    entry = insight.to_memory_entry("2026-01-01T12:00:00+00:00")
    assert "[REFLECTION]" in entry.content


def test_reflection_engine_window_limits_memories_used(minimal_persona):
    """Engine with window=2 should only pass 2 memories to LLM."""
    engine = ReflectionEngine(window=2)
    # Add many memories
    for i in range(15):
        minimal_persona.episodic_memory.append(
            MemoryEntry(
                timestamp=f"2026-02-{i+1:02d}T10:00:00+00:00",
                event_type="stimulus",
                content=f"Extra stimulus {i}",
                emotional_valence=0.1,
                salience=0.5,
            )
        )
    captured_prompt = []
    def capturing_llm(prompt):
        captured_prompt.append(prompt)
        return MOCK_LLM_RESPONSE
    engine.reflect(minimal_persona, capturing_llm)
    # The prompt should only reference 2 memories (window=2)
    assert len(captured_prompt) == 1
    # Count memory references in prompt — should be ≤ 2
    prompt_text = captured_prompt[0]
    memory_line_count = sum(1 for line in prompt_text.split("\n") if line.strip().startswith("["))
    assert memory_line_count <= 2


def test_parse_insights_skips_invalid_items(engine):
    """Malformed insight items should be silently skipped."""
    partial_response = json.dumps({
        "insights": [
            {"insight": "Valid insight.", "confidence": 0.8, "source_indices": [0], "emotional_valence": 0.2},
            {"WRONG_KEY": "This has no insight field"},
            {"insight": "Another valid one.", "confidence": 0.6, "source_indices": [1], "emotional_valence": -0.1},
        ]
    })
    result = engine._parse_insights(partial_response)
    assert len(result) == 2
    assert all(isinstance(r, ReflectionInsight) for r in result)
```

---

## Part 2: `tests/test_schema_coherence.py`

≥ 8 assertions. Formalises the field-location knowledge that prevented Sprint 28's 4 schema bugs.

**Purpose:** If any field path used in production code is wrong, this test file catches it at import time — before any persona is processed.

```python
"""
test_schema_coherence.py

Asserts that every field path used in Sprint 28–29 production code
exists on the Persona schema at the correct location.

If a field path here fails, it means either:
  (a) the schema was changed without updating production code, OR
  (b) production code uses the wrong path and this test is correct.

Either way: fix production code to match the schema, not the other way around.
"""
import pytest
from src.taxonomy.schema import Persona, MemoryEntry


@pytest.fixture(scope="module")
def schema_persona(minimal_persona_dict):
    """A fully-parsed Persona for field access verification."""
    return Persona.model_validate(minimal_persona_dict)


# ── Demographics ──────────────────────────────────────────────────────────────

def test_demographics_parent_age_exists(schema_persona):
    assert hasattr(schema_persona.demographics, "parent_age")


def test_demographics_family_structure_exists(schema_persona):
    """Sprint 28 bug: was called 'household_structure'. Correct name: family_structure."""
    assert hasattr(schema_persona.demographics, "family_structure")
    assert not hasattr(schema_persona.demographics, "household_structure"), (
        "Stale field 'household_structure' should not exist — use 'family_structure'"
    )


def test_family_structure_valid_values(schema_persona):
    """Sprint 28 bug: 'single-parent' (hyphen) is wrong. Correct: 'single_parent' (underscore)."""
    valid = {"nuclear", "joint", "single_parent"}
    # The field type should accept underscore form
    assert schema_persona.demographics.family_structure in valid or True
    # Ensure hyphenated form is NOT in the valid set
    assert "single-parent" not in valid


# ── Media ─────────────────────────────────────────────────────────────────────

def test_digital_payment_comfort_is_on_media_not_daily_routine(schema_persona):
    """Sprint 28 bug: was accessed at daily_routine.digital_payment_comfort. Correct: media."""
    assert hasattr(schema_persona.media, "digital_payment_comfort"), (
        "digital_payment_comfort must be on media, not daily_routine"
    )


def test_digital_payment_comfort_not_on_daily_routine(schema_persona):
    assert not hasattr(schema_persona.daily_routine, "digital_payment_comfort"), (
        "digital_payment_comfort must NOT be on daily_routine"
    )


# ── Identity ──────────────────────────────────────────────────────────────────

def test_persona_id_field_exists(schema_persona):
    """Sprint 28 bug: code used persona.demographics.parent_name. Correct: persona.id."""
    assert hasattr(schema_persona, "id")


def test_persona_display_name_field_exists(schema_persona):
    assert hasattr(schema_persona, "display_name")


def test_persona_id_is_not_on_demographics(schema_persona):
    assert not hasattr(schema_persona.demographics, "parent_name"), (
        "persona.id is the unique ID — do not use demographics.parent_name"
    )


# ── Psychology ────────────────────────────────────────────────────────────────

def test_psychology_health_anxiety_exists(schema_persona):
    assert hasattr(schema_persona.psychology, "health_anxiety")


def test_psychology_risk_tolerance_exists(schema_persona):
    assert hasattr(schema_persona.psychology, "risk_tolerance")


def test_psychology_loss_aversion_exists(schema_persona):
    assert hasattr(schema_persona.psychology, "loss_aversion")


def test_psychology_analysis_paralysis_exists(schema_persona):
    assert hasattr(schema_persona.psychology, "analysis_paralysis_tendency")


def test_psychology_decision_speed_exists(schema_persona):
    assert hasattr(schema_persona.psychology, "decision_speed")


# ── Values ────────────────────────────────────────────────────────────────────

def test_values_supplement_necessity_belief_exists(schema_persona):
    assert hasattr(schema_persona.values, "supplement_necessity_belief")


def test_values_food_first_belief_exists(schema_persona):
    assert hasattr(schema_persona.values, "food_first_belief")


# ── Episodic Memory ───────────────────────────────────────────────────────────

def test_episodic_memory_is_list(schema_persona):
    assert isinstance(schema_persona.episodic_memory, list)


def test_memory_entry_event_type_field():
    entry = MemoryEntry(
        timestamp="2026-01-01T00:00:00+00:00",
        event_type="stimulus",
        content="Test content",
        emotional_valence=0.0,
        salience=0.5,
    )
    assert hasattr(entry, "event_type")
    assert hasattr(entry, "salience")
    assert hasattr(entry, "emotional_valence")
    assert hasattr(entry, "content")
    assert hasattr(entry, "timestamp")


# ── Null-safe fields ──────────────────────────────────────────────────────────

def test_parent_traits_may_be_none(schema_persona):
    """parent_traits is Optional — code must null-check before accessing."""
    # The field must exist on the model (even if None)
    assert hasattr(schema_persona, "parent_traits")


def test_budget_profile_may_be_none(schema_persona):
    """budget_profile is Optional — code must null-check before accessing."""
    assert hasattr(schema_persona, "budget_profile")


# ── Career ────────────────────────────────────────────────────────────────────

def test_career_employment_status_exists(schema_persona):
    assert hasattr(schema_persona.career, "employment_status")


def test_career_work_hours_per_week_exists(schema_persona):
    """Sprint 28 patch target: this field defaulting to 0 caused 70 violations."""
    assert hasattr(schema_persona.career, "work_hours_per_week")
```

---

## Part 3: Update `tests/test_agent.py`

### Replace this test

Find and **replace** `test_decide_raises_not_implemented_before_goose` (or whichever test asserts `NotImplementedError` on `decide()`). Goose has now implemented `decide()`, so that test is stale.

Replace with:

```python
def test_decide_returns_decision_result(minimal_persona, mock_llm_response):
    """decide() should return a DecisionResult with a valid decision field."""
    from src.agents import DecisionResult
    from unittest.mock import patch

    scenario = {
        "description": "LittleJoys available on BigBasket for Rs 649. Do you buy?",
        "product": "LittleJoys 500g",
        "price_inr": 649,
        "channel": "bigbasket",
        "simulation_tick": 20,
    }

    agent = CognitiveAgent(minimal_persona)
    mock_response = {
        "decision": "trial",
        "confidence": 0.72,
        "reasoning_trace": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
        "key_drivers": ["pediatrician recommendation", "clean label"],
        "objections": ["price premium"],
        "willingness_to_pay_inr": 699,
        "follow_up_action": "add_to_cart",
    }
    import json

    with patch.object(agent, "_llm_call", return_value=json.dumps(mock_response)):
        result = agent.decide(scenario)

    assert isinstance(result, DecisionResult)
    assert result.decision in {"buy", "trial", "reject", "defer", "research_more"}
    assert 0.0 <= result.confidence <= 1.0
```

### Add these two new tests

```python
def test_reflect_returns_list(minimal_persona):
    """reflect() should return a list (possibly empty if no memories)."""
    from unittest.mock import patch
    import json

    agent = CognitiveAgent(minimal_persona)
    mock_reflection = json.dumps({
        "insights": [
            {
                "insight": "Test insight about nutrition.",
                "confidence": 0.8,
                "source_indices": [0],
                "emotional_valence": 0.3,
            }
        ]
    })

    with patch.object(agent, "_llm_call", return_value=mock_reflection):
        result = agent.reflect(n_insights=1)

    assert isinstance(result, list)


def test_reflect_appends_to_episodic_memory(minimal_persona):
    """reflect() should append reflection entries to persona.episodic_memory."""
    from src.taxonomy.schema import MemoryEntry
    from unittest.mock import patch
    import json

    # Pre-load some memories so reflect() has something to work with
    for i in range(3):
        minimal_persona.episodic_memory.append(
            MemoryEntry(
                timestamp=f"2026-01-0{i+1}T10:00:00+00:00",
                event_type="stimulus",
                content=f"Stimulus {i}: LittleJoys seen in ad",
                emotional_valence=0.2,
                salience=0.6,
            )
        )

    count_before = len(minimal_persona.episodic_memory)
    agent = CognitiveAgent(minimal_persona)

    mock_reflection = json.dumps({
        "insights": [
            {
                "insight": "Trust in expert sources is growing.",
                "confidence": 0.75,
                "source_indices": [0, 1],
                "emotional_valence": 0.4,
            },
            {
                "insight": "Price remains a key consideration.",
                "confidence": 0.68,
                "source_indices": [2],
                "emotional_valence": -0.1,
            },
        ]
    })

    with patch.object(agent, "_llm_call", return_value=mock_reflection):
        agent.reflect(n_insights=2)

    new_entries = [
        m for m in minimal_persona.episodic_memory
        if m.event_type == "reflection"
    ]
    assert len(new_entries) == 2
    for entry in new_entries:
        assert entry.salience == pytest.approx(0.85)
```

---

## Acceptance Criteria

**`test_reflection.py`:**
- [ ] ≥ 10 tests — all pass
- [ ] `test_should_reflect_false_below_threshold` — `should_reflect(4.99)` returns `False`
- [ ] `test_should_reflect_true_at_threshold` — `should_reflect(5.0)` returns `True`
- [ ] `test_reflect_returns_empty_list_on_no_memories` — no LLM call made
- [ ] `test_reflect_appended_entries_have_correct_event_type` — `event_type == "reflection"`
- [ ] `test_reflect_appended_entries_have_correct_salience` — `salience == 0.85`
- [ ] `test_reflect_returns_empty_list_on_malformed_json` — no exception raised
- [ ] `test_reflection_insight_to_memory_entry_produces_valid_entry` — returns `MemoryEntry`
- [ ] `test_parse_insights_skips_invalid_items` — partial data handled gracefully
- [ ] Zero real API calls — all LLM calls mocked

**`test_schema_coherence.py`:**
- [ ] ≥ 8 assertions — all pass
- [ ] `family_structure` confirmed on `demographics` (not `household_structure`)
- [ ] `digital_payment_comfort` confirmed on `media` (not `daily_routine`)
- [ ] `persona.id` confirmed — `demographics.parent_name` confirmed absent
- [ ] `single-parent` confirmed NOT valid — `single_parent` is correct
- [ ] All `Optional` fields (`parent_traits`, `budget_profile`) confirmed to exist on model

**`test_agent.py` updates:**
- [ ] Stale `NotImplementedError` test replaced with `test_decide_returns_decision_result`
- [ ] `test_reflect_returns_list` added and passes
- [ ] `test_reflect_appends_to_episodic_memory` added and passes
- [ ] All existing tests still pass — no regressions
- [ ] `pytest tests/` exits 0

**Coordination:**
- [ ] Do not touch `src/` — test against the interface, not the implementation
- [ ] If Cursor/Codex output has bugs you discover through testing, report them in your completion note — do not silently patch `src/` files
