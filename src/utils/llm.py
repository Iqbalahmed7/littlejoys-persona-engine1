"""
Unified Claude API client with caching, routing, retries, and mock mode.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import structlog

from src.constants import LLM_CACHE_DIR, LLM_MAX_RETRIES, LLM_RETRY_BASE_DELAY

if TYPE_CHECKING:
    from pydantic import BaseModel

    from src.config import Config

logger = structlog.get_logger(__name__)


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

    The client uses a disk cache keyed by ``model + system + prompt + temperature``.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.usage = TokenUsageTracker()
        self._cache_dir = Path(LLM_CACHE_DIR)
        self._anthropic_client: Any | None = None

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: Literal["reasoning", "bulk"] = "bulk",
        response_format: Literal["text", "json"] = "text",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        """
        Generate a response from Anthropic or from deterministic mock fixtures.

        Args:
            prompt: User prompt.
            system: Optional system prompt.
            model: ``reasoning`` or ``bulk`` routing alias.
            response_format: ``text`` or ``json``.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.
            schema: Optional Pydantic model used to validate JSON responses.

        Returns:
            Normalized response text plus usage metadata.

        Raises:
            LLMError: If all retries are exhausted or structured parsing fails.
        """

        model_name = self._resolve_model_name(model)
        cache_key = self._cache_key(model_name, system, prompt, temperature)

        if self.config.llm_cache_enabled:
            cached_response = self._read_cached_response(cache_key)
            if cached_response is not None:
                cached_response.cached = True
                self.usage.record(cached_response)
                logger.debug("llm_cache_hit", model=model_name, cache_key=cache_key)
                return cached_response

        if self.config.llm_mock_enabled:
            response = self._build_mock_response(
                prompt=prompt,
                system=system,
                model_name=model_name,
                response_format=response_format,
                temperature=temperature,
                schema=schema,
            )
            self._persist_response(cache_key, response)
            self.usage.record(response)
            try:
                from src.utils.spend_tracker import record_llm_response

                record_llm_response(response)
            except Exception:
                pass
            return response

        last_error: Exception | None = None
        for attempt in range(LLM_MAX_RETRIES):
            start = time.perf_counter()
            try:
                payload = await self._call_anthropic(
                    prompt=prompt,
                    system=system,
                    model_name=model_name,
                    response_format=response_format,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                text = self._normalize_response_text(payload["text"], response_format, schema)
                response = LLMResponse(
                    text=text,
                    model=model_name,
                    input_tokens=payload["input_tokens"],
                    output_tokens=payload["output_tokens"],
                    duration_ms=(time.perf_counter() - start) * 1000.0,
                )
                self._persist_response(cache_key, response)
                self.usage.record(response)
                try:
                    from src.utils.spend_tracker import record_llm_response

                    record_llm_response(response)
                except Exception:
                    pass
                logger.info("llm_generate_success", model=model_name, cached=False)
                return response
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "llm_generate_retry",
                    model=model_name,
                    attempt=attempt + 1,
                    retries=LLM_MAX_RETRIES,
                    error=str(exc),
                )
                if attempt + 1 == LLM_MAX_RETRIES:
                    break
                await asyncio.sleep(LLM_RETRY_BASE_DELAY * (2**attempt))

        raise LLMError(str(last_error), model_name, LLM_MAX_RETRIES)

    async def generate_batch(
        self,
        prompts: list[str],
        system: str = "",
        model: Literal["reasoning", "bulk"] = "bulk",
        max_concurrency: int = 5,
    ) -> list[LLMResponse]:
        """
        Generate multiple responses concurrently with a semaphore.

        Args:
            prompts: Prompts to send.
            system: Shared system prompt.
            model: ``reasoning`` or ``bulk`` routing alias.
            max_concurrency: Maximum in-flight requests.

        Returns:
            Responses in the same order as ``prompts``.
        """

        semaphore = asyncio.Semaphore(max_concurrency)

        async def _generate_single(prompt: str) -> LLMResponse:
            async with semaphore:
                return await self.generate(prompt=prompt, system=system, model=model)

        return await asyncio.gather(*(_generate_single(prompt) for prompt in prompts))

    def _cache_key(self, model: str, system: str, prompt: str, temperature: float) -> str:
        """Generate a deterministic cache key."""

        content = f"{model}|{system}|{prompt}|{temperature}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _resolve_model_name(self, model: Literal["reasoning", "bulk"]) -> str:
        if model == "reasoning":
            return self.config.llm_model_reasoning
        return self.config.llm_model_bulk

    def _read_cached_response(self, cache_key: str) -> LLMResponse | None:
        cache_path = self._cache_dir / f"{cache_key}.json"
        if not cache_path.exists():
            return None

        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return LLMResponse(
            text=str(payload["text"]),
            model=str(payload["model"]),
            input_tokens=int(payload.get("input_tokens", 0)),
            output_tokens=int(payload.get("output_tokens", 0)),
            cached=bool(payload.get("cached", False)),
            duration_ms=float(payload.get("duration_ms", 0.0)),
        )

    def _persist_response(self, cache_key: str, response: LLMResponse) -> None:
        if not self.config.llm_cache_enabled:
            return

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self._cache_dir / f"{cache_key}.json"
        cache_payload = {
            "text": response.text,
            "model": response.model,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cached": response.cached,
            "duration_ms": response.duration_ms,
        }
        cache_path.write_text(json.dumps(cache_payload, sort_keys=True), encoding="utf-8")

    async def _call_anthropic(
        self,
        prompt: str,
        system: str,
        model_name: str,
        response_format: Literal["text", "json"],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        if self._anthropic_client is None:
            from anthropic import AsyncAnthropic

            self._anthropic_client = AsyncAnthropic(api_key=self.config.anthropic_api_key)

        formatted_system = system.strip()
        if response_format == "json":
            json_instruction = "Return valid JSON only."
            formatted_system = (
                f"{formatted_system}\n\n{json_instruction}"
                if formatted_system
                else json_instruction
            )

        request_kwargs: dict[str, Any] = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if formatted_system:
            request_kwargs["system"] = formatted_system

        message = await self._anthropic_client.messages.create(**request_kwargs)

        text_blocks = [block.text for block in message.content if hasattr(block, "text")]
        return {
            "text": "\n".join(text_blocks).strip(),
            "input_tokens": int(getattr(message.usage, "input_tokens", 0)),
            "output_tokens": int(getattr(message.usage, "output_tokens", 0)),
        }

    def _normalize_response_text(
        self,
        raw_text: str,
        response_format: Literal["text", "json"],
        schema: type[BaseModel] | None,
    ) -> str:
        if response_format == "text" and schema is None:
            return raw_text

        parsed = json.loads(raw_text)
        if schema is None:
            return json.dumps(parsed, sort_keys=True)

        validated = schema.model_validate(parsed)
        return json.dumps(validated.model_dump(mode="json"), sort_keys=True)

    def _build_mock_response(
        self,
        prompt: str,
        system: str,
        model_name: str,
        response_format: Literal["text", "json"],
        temperature: float,
        schema: type[BaseModel] | None,
    ) -> LLMResponse:
        cache_key = self._cache_key(model_name, system, prompt, temperature)
        input_tokens = max(1, (len(system) + len(prompt)) // 4)

        if response_format == "json":
            payload: dict[str, Any] = {
                "cache_key": cache_key[:12],
                "message": "mock-json-response",
                "model": model_name,
            }
            if schema is not None:
                validated = schema.model_validate(payload)
                text = json.dumps(validated.model_dump(mode="json"), sort_keys=True)
            else:
                text = json.dumps(payload, sort_keys=True)
        else:
            text = f"[mock:{model_name}] {cache_key[:16]}"

        output_tokens = max(1, len(text) // 4)
        return LLMResponse(
            text=text,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached=False,
            duration_ms=0.0,
        )
