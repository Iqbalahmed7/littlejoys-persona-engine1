"""Tests for ``app.components.persona_card`` (PRD-012 Sprint 5)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.components.persona_card import render_persona_card


def _context_mock() -> MagicMock:
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=None)
    cm.__exit__ = MagicMock(return_value=None)
    return cm


@pytest.fixture
def mock_st() -> MagicMock:
    with patch("app.components.persona_card.st") as m:
        m.container.return_value = _context_mock()
        m.columns.return_value = (_context_mock(), _context_mock())
        yield m


def test_render_persona_card_without_decision(mock_st: MagicMock, sample_persona) -> None:
    render_persona_card(sample_persona, None)
    mock_st.subheader.assert_called_once()
    mock_st.success.assert_not_called()
    mock_st.error.assert_not_called()


def test_render_persona_card_adopt(mock_st: MagicMock, sample_persona) -> None:
    render_persona_card(sample_persona, {"outcome": "adopt"})
    mock_st.success.assert_called_once()
    mock_st.error.assert_not_called()


def test_render_persona_card_reject(mock_st: MagicMock, sample_persona) -> None:
    render_persona_card(
        sample_persona,
        {
            "outcome": "reject",
            "rejection_stage": "purchase",
            "rejection_reason": "price_too_high",
        },
    )
    mock_st.error.assert_called_once()
    mock_st.success.assert_not_called()
