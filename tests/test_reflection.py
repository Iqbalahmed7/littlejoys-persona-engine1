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
