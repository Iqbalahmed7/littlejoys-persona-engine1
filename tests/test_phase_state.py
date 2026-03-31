"""Tests for app/utils/phase_state.phase_complete().

Source inspection reveals:
  - phase 0: always True (no key check)
  - phase 1: checks "population" in st.session_state
  - phase 2: checks "probe_results" in st.session_state
  - phase 3: checks "core_finding" in st.session_state
  - phase 4: checks "intervention_results" in st.session_state
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.utils.phase_state import phase_complete


# ---------------------------------------------------------------------------
# Phase 0 — always unlocked
# ---------------------------------------------------------------------------

def test_phase_0_always_complete_empty_state():
    """Phase 0 returns True regardless of session state."""
    with patch("app.utils.phase_state.st") as mock_st:
        mock_st.session_state = {}
        assert phase_complete(0) is True


def test_phase_0_always_complete_populated_state():
    """Phase 0 returns True even when session state has other keys."""
    with patch("app.utils.phase_state.st") as mock_st:
        mock_st.session_state = {"population": object(), "some_other_key": 42}
        assert phase_complete(0) is True


# ---------------------------------------------------------------------------
# Phase 1 — requires "population" key
# ---------------------------------------------------------------------------

def test_phase_1_incomplete_when_key_missing():
    """Phase 1 returns False when 'population' is absent from session state."""
    with patch("app.utils.phase_state.st") as mock_st:
        mock_st.session_state = {}
        assert phase_complete(1) is False


def test_phase_1_incomplete_when_wrong_key_present():
    """Phase 1 returns False if only 'baseline_cohorts' is set (wrong key)."""
    with patch("app.utils.phase_state.st") as mock_st:
        mock_st.session_state = {"baseline_cohorts": object()}
        assert phase_complete(1) is False


def test_phase_1_complete_when_population_key_present():
    """Phase 1 returns True when 'population' is in session state."""
    with patch("app.utils.phase_state.st") as mock_st:
        mock_st.session_state = {"population": object()}
        assert phase_complete(1) is True


# ---------------------------------------------------------------------------
# Phase 2 — requires "probe_results" key
# ---------------------------------------------------------------------------

def test_phase_2_incomplete_when_key_missing():
    """Phase 2 returns False when 'probe_results' is absent."""
    with patch("app.utils.phase_state.st") as mock_st:
        mock_st.session_state = {"population": object(), "baseline_cohorts": object()}
        assert phase_complete(2) is False


def test_phase_2_complete_when_probe_results_present():
    """Phase 2 returns True when 'probe_results' is in session state."""
    with patch("app.utils.phase_state.st") as mock_st:
        mock_st.session_state = {"probe_results": []}
        assert phase_complete(2) is True


# ---------------------------------------------------------------------------
# Phase 3 — requires "core_finding" key
# ---------------------------------------------------------------------------

def test_phase_3_incomplete_when_key_missing():
    """Phase 3 returns False when 'core_finding' is absent."""
    with patch("app.utils.phase_state.st") as mock_st:
        mock_st.session_state = {}
        assert phase_complete(3) is False


def test_phase_3_complete_when_core_finding_present():
    """Phase 3 returns True when 'core_finding' is in session state."""
    with patch("app.utils.phase_state.st") as mock_st:
        mock_st.session_state = {"core_finding": "The main driver is X."}
        assert phase_complete(3) is True


# ---------------------------------------------------------------------------
# Phase 4 — requires "intervention_results" key
# ---------------------------------------------------------------------------

def test_phase_4_incomplete_when_key_missing():
    """Phase 4 returns False when 'intervention_results' is absent."""
    with patch("app.utils.phase_state.st") as mock_st:
        mock_st.session_state = {}
        assert phase_complete(4) is False


def test_phase_4_complete_when_intervention_results_present():
    """Phase 4 returns True when 'intervention_results' is in session state."""
    with patch("app.utils.phase_state.st") as mock_st:
        mock_st.session_state = {"intervention_results": {"lift": 0.12}}
        assert phase_complete(4) is True


# ---------------------------------------------------------------------------
# Unknown phase — returns False (key will be "" which is falsy)
# ---------------------------------------------------------------------------

def test_unknown_phase_returns_false():
    """An unrecognised phase number returns False."""
    with patch("app.utils.phase_state.st") as mock_st:
        mock_st.session_state = {"anything": True}
        assert phase_complete(99) is False
