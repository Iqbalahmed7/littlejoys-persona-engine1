"""Unit tests for the LLM client."""

from __future__ import annotations

import pytest

from src.config import Config
from src.utils import llm as llm_module


@pytest.mark.asyncio
async def test_mock_mode_returns_deterministic_response(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mock mode returns deterministic output for the same prompt."""

    monkeypatch.setattr(llm_module, "LLM_CACHE_DIR", str(tmp_path / "cache"))
    client = llm_module.LLMClient(
        Config(llm_mock_enabled=True, llm_cache_enabled=False, anthropic_api_key="")
    )

    first = await client.generate(prompt="hello world", model="bulk")
    second = await client.generate(prompt="hello world", model="bulk")

    assert first.text == second.text
    assert first.model == second.model


def test_cache_key_deterministic() -> None:
    """Cache keys should be stable for the same payload."""

    client = llm_module.LLMClient(
        Config(llm_mock_enabled=True, llm_cache_enabled=False, anthropic_api_key="")
    )

    first = client._cache_key("bulk-model", "system", "prompt", 0.2)
    second = client._cache_key("bulk-model", "system", "prompt", 0.2)

    assert first == second


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_response(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated prompts should hit the disk cache on subsequent reads."""

    monkeypatch.setattr(llm_module, "LLM_CACHE_DIR", str(tmp_path / "cache"))
    client = llm_module.LLMClient(
        Config(llm_mock_enabled=True, llm_cache_enabled=True, anthropic_api_key="")
    )

    first = await client.generate(prompt="cached prompt", system="system", model="bulk")
    second = await client.generate(prompt="cached prompt", system="system", model="bulk")

    assert first.cached is False
    assert second.cached is True
    assert client.usage.cache_hits == 1


@pytest.mark.asyncio
async def test_token_usage_tracking(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Token usage tracker accumulates counts across calls."""

    monkeypatch.setattr(llm_module, "LLM_CACHE_DIR", str(tmp_path / "cache"))
    client = llm_module.LLMClient(
        Config(llm_mock_enabled=True, llm_cache_enabled=False, anthropic_api_key="")
    )

    await client.generate(prompt="first prompt", model="bulk")
    await client.generate(prompt="second prompt", model="bulk")

    assert client.usage.total_calls == 2
    assert client.usage.total_input_tokens > 0
    assert client.usage.total_output_tokens > 0
    assert client.usage.calls_by_model[client.config.llm_model_bulk] == 2
