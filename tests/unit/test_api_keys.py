"""Unit tests for shared API key utility."""

from __future__ import annotations

from src.utils.api_keys import resolve_api_key, has_api_key


def test_resolve_api_key_returns_string():
    """resolve_api_key() returns a string (may be empty in test environment)."""
    result = resolve_api_key()
    assert isinstance(result, str)


def test_has_api_key_returns_bool():
    """has_api_key() returns a boolean."""
    result = has_api_key()
    assert isinstance(result, bool)


def test_placeholder_key_rejected(monkeypatch):
    """Placeholder key 'sk-ant-REPLACE_ME' is treated as missing."""
    import src.utils.api_keys as mod

    class FakeConfig:
        anthropic_api_key = "sk-ant-REPLACE_ME"

    monkeypatch.setattr(mod, "get_config", lambda: FakeConfig())
    # Also ensure Streamlit secrets path doesn't interfere
    monkeypatch.setattr(mod, "st", type("FakeSt", (), {"secrets": {}})())
    assert resolve_api_key() == ""
    assert has_api_key() is False


def test_real_key_accepted(monkeypatch):
    """A real-looking key is accepted."""
    import src.utils.api_keys as mod

    class FakeConfig:
        anthropic_api_key = "sk-ant-abc123realkey"

    monkeypatch.setattr(mod, "get_config", lambda: FakeConfig())
    monkeypatch.setattr(mod, "st", type("FakeSt", (), {"secrets": {}})())
    assert resolve_api_key() == "sk-ant-abc123realkey"
    assert has_api_key() is True
