import pytest
from src.simulation.journey_config import JourneyConfig, StimulusConfig, DecisionScenarioConfig
from src.simulation.tick_engine import JourneySpec

@pytest.fixture
def simple_journey_config():
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

def test_stimulus_config_instantiates():
    """StimulusConfig with all fields, no error."""
    s = StimulusConfig(id="S1", tick=1, type="ad", source="src", content="cont", brand="br")
    assert s.id == "S1"
    assert s.tick == 1
    assert s.brand == "br"

def test_decision_scenario_config_instantiates():
    """DecisionScenarioConfig with all fields."""
    d = DecisionScenarioConfig(tick=10, description="desc", product="prod", price_inr=100.0, channel="ch")
    assert d.tick == 10
    assert d.price_inr == 100.0

def test_journey_config_instantiates(simple_journey_config):
    """JourneyConfig with 2 stimuli and 1 decision."""
    assert len(simple_journey_config.stimuli) == 2
    assert len(simple_journey_config.decisions) == 1
    assert simple_journey_config.journey_id == "TEST"

def test_to_journey_spec_returns_journey_spec(simple_journey_config):
    """config.to_journey_spec() returns a JourneySpec."""
    spec = simple_journey_config.to_journey_spec()
    assert isinstance(spec, JourneySpec)

def test_to_journey_spec_total_ticks_preserved(simple_journey_config):
    """spec.total_ticks == config.total_ticks."""
    spec = simple_journey_config.to_journey_spec()
    assert spec.total_ticks == simple_journey_config.total_ticks

def test_to_journey_spec_stimuli_at_correct_tick(simple_journey_config):
    """stimuli_at(tick) returns the right stimulus."""
    spec = simple_journey_config.to_journey_spec()
    stimuli_5 = spec.stimuli_at(5)
    assert len(stimuli_5) == 1
    assert stimuli_5[0]["id"] == "T-S01"
    assert stimuli_5[0]["content"] == "Test ad content"
    
    stimuli_10 = spec.stimuli_at(10)
    assert len(stimuli_10) == 1
    assert stimuli_10[0]["id"] == "T-S10"

def test_to_journey_spec_decision_at_correct_tick(simple_journey_config):
    """decision_at(tick) returns the right scenario."""
    spec = simple_journey_config.to_journey_spec()
    decision_20 = spec.decision_at(20)
    assert decision_20 is not None
    assert decision_20["product"] == "Test Product"
    assert decision_20["price_inr"] == 499

    assert spec.decision_at(5) is None

def test_with_price_returns_new_config(simple_journey_config):
    """with_price(549) returns a new JourneyConfig."""
    new_config = simple_journey_config.with_price(549)
    assert isinstance(new_config, JourneyConfig)
    assert new_config.decisions[0].price_inr == 549
    assert new_config is not simple_journey_config

def test_with_price_does_not_mutate_original(simple_journey_config):
    """original price unchanged after with_price()."""
    original_price = simple_journey_config.decisions[0].price_inr
    simple_journey_config.with_price(original_price + 100)
    assert simple_journey_config.decisions[0].price_inr == original_price

def test_preset_journey_a_round_trips():
    """PRESET_JOURNEY_A.to_journey_spec().total_ticks == 61."""
    from src.simulation.journey_presets import PRESET_JOURNEY_A
    spec = PRESET_JOURNEY_A.to_journey_spec()
    assert spec.total_ticks == 61
    assert spec.journey_id == "A"

def test_preset_journey_b_round_trips():
    """PRESET_JOURNEY_B.to_journey_spec().total_ticks == 46."""
    from src.simulation.journey_presets import PRESET_JOURNEY_B
    spec = PRESET_JOURNEY_B.to_journey_spec()
    assert spec.total_ticks == 46
    assert spec.journey_id == "B"

def test_list_presets_returns_a_and_b():
    """list_presets() returns dict with keys "A" and "B"."""
    from src.simulation.journey_presets import list_presets
    presets = list_presets()
    assert "A" in presets
    assert "B" in presets
    assert isinstance(presets["A"], JourneyConfig)
