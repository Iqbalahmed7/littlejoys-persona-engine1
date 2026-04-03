# Sprint 30 — Brief: ANTIGRAVITY

**Role:** Test coverage / schema integrity
**Model:** Gemini 3 Flash
**Assignment:** `tests/test_tick_engine.py` + `tests/test_journey_result.py`
**Est. duration:** 4-5 hours
**START:** After Cursor + Codex + Goose all signal done

---

## Files to Create

| Action | File |
|---|---|
| CREATE | `tests/test_tick_engine.py` |
| CREATE | `tests/test_journey_result.py` |

## Do NOT Touch
- `src/` — any file
- `app/` — any file
- `scripts/` — any file
- `tests/conftest.py` — do NOT add `pytest_plugins` entries
- Any existing test file

---

## Critical: Run Before Signalling Done

```bash
# 1. Collect only — catches import errors before running
python3 -m pytest tests/test_tick_engine.py tests/test_journey_result.py --collect-only -q

# 2. Run your new tests
python3 -m pytest tests/test_tick_engine.py tests/test_journey_result.py -v --tb=short

# 3. Confirm no regressions in existing tests
python3 -m pytest tests/test_reflection.py tests/test_agent.py tests/test_memory.py tests/test_constraint_checker.py tests/test_schema_coherence.py -q
```

All three must pass before signalling done.

---

## Part 1: `tests/test_tick_engine.py`

≥ 12 tests. All LLM calls mocked — no real API calls.

### Fixtures

```python
import pytest
import json
from unittest.mock import MagicMock, patch
from src.simulation.tick_engine import TickEngine, TickSnapshot, TickJourneyLog, JourneySpec, JOURNEY_A, JOURNEY_B
from src.taxonomy.schema import Persona


@pytest.fixture
def engine():
    return TickEngine()


@pytest.fixture
def mock_perceive_result():
    """A mock PerceptionResult with known values."""
    mock = MagicMock()
    mock.importance = 0.6
    mock.emotional_valence = 0.4
    mock.reflection_trigger_candidate = False
    return mock


@pytest.fixture
def mock_decide_result():
    """A mock DecisionResult with known values."""
    mock = MagicMock()
    mock.decision = "buy"
    mock.confidence = 0.75
    mock.to_dict.return_value = {
        "decision": "buy",
        "confidence": 0.75,
        "reasoning_trace": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
        "key_drivers": ["pediatrician_recommendation"],
        "objections": [],
        "willingness_to_pay_inr": 649,
        "follow_up_action": "add_to_cart",
    }
    return mock
```

### Tests to write

```
test_tick_engine_instantiates
test_journey_a_defined_with_correct_total_ticks
test_journey_b_defined_with_correct_total_ticks
test_journey_a_has_primary_brand_littlejoys
test_journey_spec_stimuli_at_returns_empty_list_for_empty_tick
test_journey_spec_decision_at_returns_none_for_empty_tick
test_journey_spec_stimuli_at_tick_1_returns_stimulus
test_journey_spec_decision_at_tick_20_returns_scenario
test_run_returns_tick_journey_log
test_run_snapshots_count_equals_total_ticks
test_run_snapshot_contains_brand_trust
test_run_reordered_false_when_no_purchase
test_run_reordered_true_when_two_purchases
test_run_handles_perceive_error_gracefully
test_run_handles_decide_error_gracefully
test_tick_journey_log_to_dict_is_json_serialisable
test_run_records_reflection_in_snapshot
```

### Key test implementations

```python
def test_journey_a_defined_with_correct_total_ticks():
    assert JOURNEY_A.total_ticks == 60


def test_journey_b_defined_with_correct_total_ticks():
    assert JOURNEY_B.total_ticks == 45


def test_journey_a_has_primary_brand_littlejoys():
    assert JOURNEY_A.primary_brand == "littlejoys"


def test_journey_spec_stimuli_at_returns_empty_list_for_empty_tick(engine):
    stimuli = JOURNEY_A.stimuli_at(999)
    assert stimuli == []


def test_journey_spec_decision_at_returns_none_for_empty_tick():
    assert JOURNEY_A.decision_at(999) is None


def test_journey_spec_stimuli_at_tick_1_returns_stimulus():
    stimuli = JOURNEY_A.stimuli_at(1)
    assert len(stimuli) >= 1
    assert "content" in stimuli[0]


def test_journey_spec_decision_at_tick_20_returns_scenario():
    scenario = JOURNEY_A.decision_at(20)
    assert scenario is not None
    assert "description" in scenario
    assert "price_inr" in scenario


def test_run_returns_tick_journey_log(minimal_persona, mock_perceive_result, mock_decide_result):
    engine = TickEngine()
    with patch("src.agents.agent.CognitiveAgent.perceive", return_value=mock_perceive_result), \
         patch("src.agents.agent.CognitiveAgent.decide", return_value=mock_decide_result), \
         patch("src.agents.agent.CognitiveAgent.reflect", return_value=[]):
        log = engine.run(minimal_persona, JOURNEY_A)
    assert isinstance(log, TickJourneyLog)
    assert log.persona_id == minimal_persona.id


def test_run_snapshots_count_equals_total_ticks(minimal_persona, mock_perceive_result, mock_decide_result):
    engine = TickEngine()
    with patch("src.agents.agent.CognitiveAgent.perceive", return_value=mock_perceive_result), \
         patch("src.agents.agent.CognitiveAgent.decide", return_value=mock_decide_result), \
         patch("src.agents.agent.CognitiveAgent.reflect", return_value=[]):
        log = engine.run(minimal_persona, JOURNEY_A)
    assert len(log.snapshots) == JOURNEY_A.total_ticks


def test_run_reordered_false_when_no_purchase(minimal_persona, mock_perceive_result):
    """If decide() always returns 'reject', reordered should be False."""
    mock_reject = MagicMock()
    mock_reject.decision = "reject"
    mock_reject.to_dict.return_value = {"decision": "reject", "confidence": 0.8,
        "reasoning_trace": [], "key_drivers": [], "objections": ["too_expensive"],
        "willingness_to_pay_inr": None, "follow_up_action": ""}
    engine = TickEngine()
    with patch("src.agents.agent.CognitiveAgent.perceive", return_value=mock_perceive_result), \
         patch("src.agents.agent.CognitiveAgent.decide", return_value=mock_reject), \
         patch("src.agents.agent.CognitiveAgent.reflect", return_value=[]):
        log = engine.run(minimal_persona, JOURNEY_A)
    assert log.reordered is False


def test_run_handles_perceive_error_gracefully(minimal_persona):
    """If perceive() raises, the engine should catch it and continue."""
    engine = TickEngine()
    mock_decide = MagicMock()
    mock_decide.decision = "defer"
    mock_decide.to_dict.return_value = {"decision": "defer", "confidence": 0.5,
        "reasoning_trace": [], "key_drivers": [], "objections": [],
        "willingness_to_pay_inr": None, "follow_up_action": ""}
    with patch("src.agents.agent.CognitiveAgent.perceive", side_effect=RuntimeError("mock error")), \
         patch("src.agents.agent.CognitiveAgent.decide", return_value=mock_decide), \
         patch("src.agents.agent.CognitiveAgent.reflect", return_value=[]):
        log = engine.run(minimal_persona, JOURNEY_A)
    # Should not raise — error is recorded in snapshot
    assert isinstance(log, TickJourneyLog)


def test_tick_journey_log_to_dict_is_json_serialisable(minimal_persona, mock_perceive_result, mock_decide_result):
    import json as json_module
    engine = TickEngine()
    with patch("src.agents.agent.CognitiveAgent.perceive", return_value=mock_perceive_result), \
         patch("src.agents.agent.CognitiveAgent.decide", return_value=mock_decide_result), \
         patch("src.agents.agent.CognitiveAgent.reflect", return_value=[]):
        log = engine.run(minimal_persona, JOURNEY_A)
    d = log.to_dict()
    # Should not raise
    serialised = json_module.dumps(d)
    assert len(serialised) > 0


def test_run_records_reflection_in_snapshot(minimal_persona, mock_decide_result):
    """When cumulative salience > 5.0, reflected=True should appear in a snapshot."""
    # High importance score to quickly cross threshold
    mock_high_importance = MagicMock()
    mock_high_importance.importance = 0.9  # 0.9 × 6 stimuli = 5.4 > threshold
    mock_high_importance.emotional_valence = 0.5
    mock_high_importance.reflection_trigger_candidate = True

    engine = TickEngine()
    with patch("src.agents.agent.CognitiveAgent.perceive", return_value=mock_high_importance), \
         patch("src.agents.agent.CognitiveAgent.decide", return_value=mock_decide_result), \
         patch("src.agents.agent.CognitiveAgent.reflect", return_value=[]):
        log = engine.run(minimal_persona, JOURNEY_A)

    reflected_ticks = [s for s in log.snapshots if s.reflected]
    assert len(reflected_ticks) >= 1
```

---

## Part 2: `tests/test_journey_result.py`

≥ 8 tests.

```python
import pytest
from src.simulation.journey_result import aggregate_journeys, segment_by_reorder, find_conversion_tick, JourneyAggregate
from src.simulation.tick_engine import TickJourneyLog, TickSnapshot


def make_mock_log(persona_id, reordered, first_decision="buy", second_decision="buy", error=None):
    """Helper to create a minimal TickJourneyLog dict (as returned by to_dict())."""
    return {
        "persona_id": persona_id,
        "display_name": persona_id,
        "journey_id": "A",
        "total_ticks": 60,
        "reordered": reordered,
        "error": error,
        "final_decision": {"decision": second_decision, "confidence": 0.7,
                           "key_drivers": ["pediatrician"], "objections": [],
                           "willingness_to_pay_inr": 649} if not error else None,
        "snapshots": [
            {
                "tick": 20,
                "brand_trust": {"littlejoys": 0.6},
                "memories_count": 5,
                "cumulative_salience": 0.0,
                "reflected": False,
                "perception_results": [],
                "decision_result": {"decision": first_decision, "confidence": 0.8,
                                    "key_drivers": ["pediatrician"], "objections": [],
                                    "willingness_to_pay_inr": 649},
            },
            {
                "tick": 60,
                "brand_trust": {"littlejoys": 0.75},
                "memories_count": 12,
                "cumulative_salience": 0.0,
                "reflected": True,
                "perception_results": [],
                "decision_result": {"decision": second_decision, "confidence": 0.7,
                                    "key_drivers": ["habit"], "objections": [],
                                    "willingness_to_pay_inr": 649},
            },
        ],
    }
```

### Tests to write

```
test_aggregate_journeys_empty_list
test_aggregate_journeys_all_errors
test_aggregate_journeys_computes_reorder_rate
test_aggregate_journeys_returns_journey_aggregate
test_segment_by_reorder_empty_list
test_segment_by_reorder_splits_correctly
test_segment_by_reorder_excludes_errors
test_find_conversion_tick_empty_list
test_aggregate_trust_by_tick_computed
```

### Key implementations

```python
def test_aggregate_journeys_empty_list():
    result = aggregate_journeys([])
    assert isinstance(result, JourneyAggregate)
    assert result.total_personas == 0
    assert result.reorder_rate_pct == 0.0


def test_aggregate_journeys_all_errors():
    logs = [make_mock_log(f"p{i}", False, error="some error") for i in range(5)]
    result = aggregate_journeys(logs)
    assert result.errors == 5
    assert result.reorder_rate_pct == 0.0


def test_aggregate_journeys_computes_reorder_rate():
    logs = [
        make_mock_log("p1", reordered=True, first_decision="buy", second_decision="buy"),
        make_mock_log("p2", reordered=True, first_decision="buy", second_decision="buy"),
        make_mock_log("p3", reordered=False, first_decision="buy", second_decision="defer"),
        make_mock_log("p4", reordered=False, first_decision="trial", second_decision="reject"),
    ]
    result = aggregate_journeys(logs)
    # 2 reordered out of 4 = 50%
    assert result.reorder_rate_pct == pytest.approx(50.0)


def test_segment_by_reorder_empty_list():
    result = segment_by_reorder([])
    assert result == {"reorderers": [], "lapsers": []}


def test_segment_by_reorder_splits_correctly():
    logs = [
        make_mock_log("p1", reordered=True),
        make_mock_log("p2", reordered=False),
        make_mock_log("p3", reordered=True),
        make_mock_log("p4", reordered=False, error="crash"),  # errors excluded
    ]
    result = segment_by_reorder(logs)
    assert set(result["reorderers"]) == {"p1", "p3"}
    assert set(result["lapsers"]) == {"p2"}  # p4 excluded (error)


def test_find_conversion_tick_empty_list():
    result = find_conversion_tick([])
    assert isinstance(result, dict)
    assert len(result) == 0
```

---

## Acceptance Criteria

- [ ] `python3 -m pytest tests/test_tick_engine.py tests/test_journey_result.py --collect-only -q` — no import errors
- [ ] ≥ 12 tests in `test_tick_engine.py` — all pass
- [ ] ≥ 8 tests in `test_journey_result.py` — all pass
- [ ] Zero real API calls — all LLM calls mocked
- [ ] `test_run_snapshots_count_equals_total_ticks` passes (60 for Journey A)
- [ ] `test_run_reordered_false_when_no_purchase` passes
- [ ] `test_aggregate_journeys_computes_reorder_rate` passes
- [ ] `test_segment_by_reorder_splits_correctly` passes
- [ ] Existing tests unaffected — `pytest tests/test_reflection.py tests/test_agent.py tests/test_memory.py` still green
- [ ] Do NOT add anything to `conftest.py`
