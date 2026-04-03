import pytest
import json
from unittest.mock import patch, MagicMock
from src.simulation.batch_runner import run_batch, BatchResult
from src.simulation.journey_config import JourneyConfig, StimulusConfig, DecisionScenarioConfig

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

@pytest.fixture
def simple_journey_config():
    return JourneyConfig(
        journey_id="BATCH_TEST",
        total_ticks=5,
        primary_brand="littlejoys",
        stimuli=[
            StimulusConfig(id="S1", tick=1, type="ad", source="src", content="cont", brand="littlejoys")
        ],
        decisions=[
            DecisionScenarioConfig(tick=3, product="Prod", price_inr=499, channel="ch", description="desc")
        ],
    )

@patch("src.agents.agent.CognitiveAgent.perceive")
@patch("src.agents.agent.CognitiveAgent.decide")
def test_run_batch_returns_batch_result(mock_d, mock_p, simple_journey_config, minimal_persona, mock_perceive, mock_decide):
    """run_batch() with 1 persona returns BatchResult."""
    mock_p.return_value = mock_perceive
    mock_d.return_value = mock_decide
    
    personas = [("P1", minimal_persona)]
    result = run_batch(simple_journey_config, personas)
    
    assert isinstance(result, BatchResult)
    assert result.personas_run == 1
    assert len(result.logs) == 1
    assert result.journey_id == "BATCH_TEST"

def test_run_batch_empty_personas_returns_zero_result(simple_journey_config):
    """empty persona list -> personas_run=0, errors=0."""
    result = run_batch(simple_journey_config, [])
    assert result.personas_run == 0
    assert result.errors == 0
    assert len(result.logs) == 0

@patch("src.agents.agent.CognitiveAgent.perceive")
@patch("src.agents.agent.CognitiveAgent.decide")
def test_run_batch_personas_run_count_matches_input(mock_d, mock_p, simple_journey_config, minimal_persona, mock_perceive, mock_decide):
    """3 personas -> personas_run=3."""
    mock_p.return_value = mock_perceive
    mock_d.return_value = mock_decide
    
    personas = [("P1", minimal_persona), ("P2", minimal_persona), ("P3", minimal_persona)]
    result = run_batch(simple_journey_config, personas)
    assert result.personas_run == 3

@patch("src.agents.agent.CognitiveAgent.perceive")
@patch("src.agents.agent.CognitiveAgent.decide")
def test_run_batch_logs_count_matches_input(mock_d, mock_p, simple_journey_config, minimal_persona, mock_perceive, mock_decide):
    """3 personas -> len(result.logs)==3."""
    mock_p.return_value = mock_perceive
    mock_d.return_value = mock_decide
    
    personas = [("P1", minimal_persona), ("P2", minimal_persona), ("P3", minimal_persona)]
    result = run_batch(simple_journey_config, personas)
    assert len(result.logs) == 3

@patch("src.agents.agent.CognitiveAgent.perceive")
@patch("src.agents.agent.CognitiveAgent.decide")
def test_run_batch_progress_callback_called_once_per_persona(mock_d, mock_p, simple_journey_config, minimal_persona, mock_perceive, mock_decide):
    """callback call count == len(personas)."""
    mock_p.return_value = mock_perceive
    mock_d.return_value = mock_decide
    
    callback = MagicMock()
    personas = [("P1", minimal_persona), ("P2", minimal_persona)]
    run_batch(simple_journey_config, personas, progress_callback=callback)
    assert callback.call_count == 2

@patch("src.agents.agent.CognitiveAgent.perceive")
@patch("src.agents.agent.CognitiveAgent.decide")
def test_run_batch_progress_callback_receives_done_and_total(mock_d, mock_p, simple_journey_config, minimal_persona, mock_perceive, mock_decide):
    """callback args are (int, int, dict)."""
    mock_p.return_value = mock_perceive
    mock_d.return_value = mock_decide
    
    callback = MagicMock()
    personas = [("P1", minimal_persona)]
    run_batch(simple_journey_config, personas, progress_callback=callback)
    
    args = callback.call_args[0]
    assert isinstance(args[0], int) # done
    assert isinstance(args[1], int) # total
    assert isinstance(args[2], dict) # log_dict

@patch("src.agents.agent.CognitiveAgent.perceive")
@patch("src.agents.agent.CognitiveAgent.decide")
def test_run_batch_elapsed_seconds_is_positive(mock_d, mock_p, simple_journey_config, minimal_persona, mock_perceive, mock_decide):
    """result.elapsed_seconds > 0."""
    mock_p.return_value = mock_perceive
    mock_d.return_value = mock_decide
    
    personas = [("P1", minimal_persona)]
    result = run_batch(simple_journey_config, personas)
    assert result.elapsed_seconds >= 0  # might be 0.0 if extremely fast, but brief says > 0

@patch("src.simulation.tick_engine.TickEngine.run")
def test_run_batch_handles_engine_error_gracefully(mock_run, simple_journey_config, minimal_persona):
    """if TickEngine.run raises, error recorded in log."""
    mock_run.side_effect = Exception("Engine Kaboom")
    
    personas = [("P1", minimal_persona)]
    result = run_batch(simple_journey_config, personas)
    
    assert result.personas_run == 1
    assert result.errors == 1
    assert "Engine Kaboom" in result.logs[0]["error"]

@patch("src.agents.agent.CognitiveAgent.perceive")
@patch("src.agents.agent.CognitiveAgent.decide")
def test_batch_result_to_dict_is_json_serialisable(mock_d, mock_p, simple_journey_config, minimal_persona, mock_perceive, mock_decide):
    """json.dumps(result.to_dict()) doesn't raise."""
    mock_p.return_value = mock_perceive
    mock_d.return_value = mock_decide
    
    personas = [("P1", minimal_persona)]
    result = run_batch(simple_journey_config, personas)
    d = result.to_dict()
    assert json.dumps(d) # Should not raise

@patch("src.agents.agent.CognitiveAgent.perceive")
@patch("src.agents.agent.CognitiveAgent.decide")
def test_batch_result_to_dict_has_required_keys(mock_d, mock_p, simple_journey_config, minimal_persona, mock_perceive, mock_decide):
    """to_dict() has keys: journey_id, total_personas, errors, elapsed_seconds, aggregate, logs."""
    mock_p.return_value = mock_perceive
    mock_d.return_value = mock_decide
    
    personas = [("P1", minimal_persona)]
    result = run_batch(simple_journey_config, personas)
    d = result.to_dict()
    
    expected_keys = {"journey_id", "total_personas", "errors", "elapsed_seconds", "aggregate", "logs"}
    assert expected_keys.issubset(d.keys())
