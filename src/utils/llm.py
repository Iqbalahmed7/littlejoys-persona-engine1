"""
Unified Claude API client with caching, routing, and mock mode.

Features:
- Dual model routing (Opus for reasoning, Sonnet for bulk generation)
- Disk-based response caching (keyed by prompt hash)
- Mock mode for unit tests
- Retry with exponential backoff
- Structured output parsing (JSON mode)
- Token usage tracking

Full implementation in PRD-000 (Codex).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from src.config import Config


@dataclass
class LLMResponse:
    """Response from an LLM call."""

    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached: bool = False
    duration_ms: float = 0.0


@dataclass
class TokenUsageTracker:
    """Tracks cumulative token usage across all LLM calls."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0
    cache_hits: int = 0
    calls_by_model: dict[str, int] = field(default_factory=dict)

    def record(self, response: LLMResponse) -> None:
        """Record token usage from a response."""
        self.total_input_tokens += response.input_tokens
        self.total_output_tokens += response.output_tokens
        self.total_calls += 1
        if response.cached:
            self.cache_hits += 1
        self.calls_by_model[response.model] = self.calls_by_model.get(response.model, 0) + 1


class LLMError(Exception):
    """Raised when an LLM API call fails after retries."""

    def __init__(self, message: str, model: str, retries: int) -> None:
        self.model = model
        self.retries = retries
        super().__init__(f"LLM error ({model}, {retries} retries): {message}")


class LLMClient:
    """
    Unified Claude API client with caching, routing, and mock mode.

    Usage:
        client = LLMClient(config)
        response = await client.generate("What is 2+2?", model="bulk")
        print(response.text)
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.usage = TokenUsageTracker()

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: Literal["reasoning", "bulk"] = "bulk",
        response_format: Literal["text", "json"] = "text",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Generate a response from the Claude API.

        Args:
            prompt: User prompt.
            system: System prompt.
            model: 'reasoning' (Opus) or 'bulk' (Sonnet).
            response_format: 'text' or 'json' for structured output.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.

        Returns:
            LLMResponse with text and usage metadata.

        Raises:
            LLMError: If all retries are exhausted.
        """
        raise NotImplementedError("Full implementation in PRD-000 (Codex)")

    async def generate_batch(
        self,
        prompts: list[str],
        system: str = "",
        model: Literal["reasoning", "bulk"] = "bulk",
        max_concurrency: int = 5,
    ) -> list[LLMResponse]:
        """Batch generation with concurrency control."""
        raise NotImplementedError("Full implementation in PRD-000 (Codex)")

    def _cache_key(self, model: str, system: str, prompt: str, temperature: float) -> str:
        """Generate a deterministic cache key."""
        content = f"{model}|{system}|{prompt}|{temperature}"
        return hashlib.sha256(content.encode()).hexdigest()
