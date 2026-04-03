# Sprint 31 — ANTIGRAVITY Brief: Tests for JourneyConfig + BatchRunner

## Context
Sprint 31 introduces two new modules: `src/simulation/journey_config.py` (JourneyConfig,
StimulusConfig, DecisionScenarioConfig) and `src/simulation/batch_runner.py` (run_batch,
BatchResult). Write tests for both.

## Dependencies
Requires CURSOR and CODEX deliverables to be present before running tests.

## Working directory
`/Users/admin/Documents/Simulatte Projects/1. LittleJoys`

## Task 1 — `tests/test_journey_config.py` (12 tests)

```python
"""Tests for JourneyConfig, StimulusConfig, DecisionScenarioConfig, and presets."""
```

Tests to write:

1. `test_stimulus_config_instantiates` — StimulusConfig with all fields, no error
2. `test_decision_scenario_config_instantiates` — DecisionScenarioConfig with all fields
3. `test_journey_config_instantiates` — JourneyConfig with 2 stimuli and 1 decision
4. `test_to_journey_spec_returns_journey_spec` — `config.to_journey_spec()` returns a `JourneySpec`
5. `test_to_journey_spec_total_ticks_preserved` — `spec.total_ticks == config.total_ticks`
6. `test_to_journey_spec_stimuli_at_correct_tick` — stimuli_at(tick) returns the right stimulus
7. `test_to_journey_spec_decision_at_correct_tick` — decision_at(tick) returns the right scenario
8. `test_with_price_returns_new_config` — `with_price(549)` returns a new JourneyConfig
9. `test_with_price_does_not_mutate_original` — original price unchanged after with_price()
10. `test_preset_journey_a_round_trips` — PRESET_JOURNEY_A.to_journey_spec().total_ticks == 61
11. `test_preset_journey_b_round_trips` — PRESET_JOURNEY_B.to_journey_spec().total_ticks == 46
12. `test_list_presets_returns_a_and_b` — list_presets() returns dict with keys "A" and "B"

### Fixture to use
```python
@pytest.fixture
def simple_journey_config():
    from src.simulation.journey_config import JourneyConfig, StimulusConfig, DecisionScenarioConfig
    return JourneyConfig(
        journey_id="TEST",
        total_ticks=25,
        primary_brand="testbrand",
        stimuli=[
            StimulusConfig(id="T-S01", tick=5, type="ad", source="instagram",
                           content="Test ad content", brand="testbrand"),
            StimulusConfig(id="T-S10", tick=10, type="wom", source="friend",
                           content="Friend recommendation", brand="testbrand"),
        ],
        decisions=[
            DecisionScenarioConfig(tick=20, product="Test Product", price_inr=499,
                                   channel="bigbasket",
                                   description="Do you buy Test Product for Rs 499?"),
        ],
    )
```

## Task 2 — `tests/test_batch_runner.py` (10 tests)

```python
"""Tests for run_batch() and BatchResult. All LLM calls are mocked."""
```

Tests to write:

1. `test_run_batch_returns_batch_result` — run_batch() with 1 persona returns BatchResult
2. `test_run_batch_empty_personas_returns_zero_result` — empty persona list → personas_run=0, errors=0
3. `test_run_batch_personas_run_count_matches_input` — 3 personas → personas_run=3
4. `test_run_batch_logs_count_matches_input` — 3 personas → len(result.logs)==3
5. `test_run_batch_progress_callback_called_once_per_persona` — callback call count == len(personas)
6. `test_run_batch_progress_callback_receives_done_and_total` — callback args are (int, int, dict)
7. `test_run_batch_elapsed_seconds_is_positive` — result.elapsed_seconds > 0
8. `test_run_batch_handles_engine_error_gracefully` — if TickEngine.run raises, error recorded in log
9. `test_batch_result_to_dict_is_json_serialisable` — json.dumps(result.to_dict()) doesn't raise
10. `test_batch_result_to_dict_has_required_keys` — to_dict() has keys: journey_id, total_personas,
    errors, elapsed_seconds, aggregate, logs

### Mock pattern to use
```python
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_perceive():
    m = MagicMock()
    m.importance = 0.5
    m.emotional_valence = 0.3
    m.reflection_trigger_candidate = False
    return m

@pytest.fixture
def mock_decide():
    m = MagicMock()
    m.decision = "buy"
    m.to_dict.return_value = {
        "decision": "buy", "confidence": 0.8,
        "reasoning_trace": [], "key_drivers": [], "objections": [],
        "willingness_to_pay_inr": 499, "follow_up_action": "",
    }
    return m

# Use minimal_persona fixture from conftest.py (already available)
# Use simple_journey_config fixture from test_journey_config.py or define locally
```

## Verification
```bash
python3 -m pytest tests/test_journey_config.py tests/test_batch_runner.py -v --tb=short
```

All 22 new tests must pass.
Existing suite must still pass: `python3 -m pytest tests/ -q --ignore=tests/integration`
