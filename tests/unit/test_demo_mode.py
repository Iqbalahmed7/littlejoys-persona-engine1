from unittest.mock import MagicMock, patch

import pytest

from app.utils.demo_mode import DEMO_POPULATION_SIZE, DEMO_SCENARIO_ID, ensure_demo_data


class _SessionState(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(name)
    def __setattr__(self, name, value):
        self[name] = value

@pytest.fixture
def mock_st():
    with patch("app.utils.demo_mode.st") as mock:
        mock.session_state = _SessionState()
        mock.spinner.return_value.__enter__ = MagicMock()
        mock.spinner.return_value.__exit__ = MagicMock()
        yield mock

def test_ensure_demo_data_populates_population(mock_st):
    ensure_demo_data()
    assert "population" in mock_st.session_state
    assert len(mock_st.session_state.population.personas) == DEMO_POPULATION_SIZE
    assert mock_st.session_state.demo_preloaded is True

def test_ensure_demo_data_populates_phase_a(mock_st):
    ensure_demo_data()
    assert "phase_a_insights" in mock_st.session_state
    assert "phase_a_quadrant" in mock_st.session_state
    assert mock_st.session_state.phase_a_insights["scenario_id"] == DEMO_SCENARIO_ID

def test_ensure_demo_data_populates_phase_c(mock_st):
    ensure_demo_data()
    assert "phase_c_run_result" in mock_st.session_state
    assert "phase_c_analysis" in mock_st.session_state
    assert mock_st.session_state.phase_c_run_result.scenario_id == DEMO_SCENARIO_ID

def test_demo_cohort_cache_key(mock_st):
    ensure_demo_data()
    expected_key = f"phase_a_cohorts_{DEMO_SCENARIO_ID}"
    assert expected_key in mock_st.session_state

def test_ensure_demo_data_idempotent(mock_st):
    # Call 1
    ensure_demo_data()
    pop_id_1 = id(mock_st.session_state.population)

    # Call 2
    ensure_demo_data()
    pop_id_2 = id(mock_st.session_state.population)

    assert pop_id_1 == pop_id_2
    assert mock_st.session_state.demo_preloaded is True

@pytest.mark.parametrize("prefilled_key", [
    "population",
    "phase_a_insights",
    "phase_c_analysis",
    "research_result"
])
def test_ensure_demo_data_with_partial_state(mock_st, prefilled_key):
    # This shouldn't block the logic if demo_preloaded is False
    mock_st.session_state[prefilled_key] = "existing"
    ensure_demo_data()
    # It should overwrite or at least finish without error
    assert mock_st.session_state.demo_preloaded is True
    assert mock_st.session_state[prefilled_key] != "existing"

@pytest.mark.parametrize("scenario_override", [DEMO_SCENARIO_ID])
def test_demo_scenario_consistency(mock_st, scenario_override):
    ensure_demo_data()
    assert mock_st.session_state.phase_a_insights["scenario_id"] == scenario_override
    assert mock_st.session_state.phase_c_run_result.scenario_id == scenario_override

def test_demo_mode_forces_mock_llm(mock_st):
    with patch("app.utils.demo_mode.LLMClient") as mock_llm:
        ensure_demo_data()
        # Verify LLMClient was initialized with mock_enabled=True
        args, _kwargs = mock_llm.call_args
        config = args[0]
        assert config.llm_mock_enabled is True
