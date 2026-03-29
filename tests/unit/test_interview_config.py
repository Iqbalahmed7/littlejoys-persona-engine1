"""Unit tests for interview configuration and API key resolution."""

from __future__ import annotations

from src.config import Config


def test_config_defaults_to_mock_enabled(monkeypatch) -> None:
    """Default config should have mock mode enabled when no env override."""
    monkeypatch.delenv("LLM_MOCK_ENABLED", raising=False)
    config = Config(_env_file=None)
    assert config.llm_mock_enabled is True


def test_config_accepts_empty_api_key() -> None:
    """Config should accept empty string as API key (for mock mode)."""
    config = Config(anthropic_api_key="", llm_mock_enabled=True)
    assert config.anthropic_api_key == ""
    assert config.llm_mock_enabled is True
