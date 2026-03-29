"""Hybrid research orchestration: funnel, smart sample, interviews, alternatives."""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar

import structlog
from pydantic import BaseModel, ConfigDict, Field

from src.analysis.interviews import InterviewTurn, PersonaInterviewer
from src.constants import INTERVIEW_COST_PER_1K_INPUT_USD, INTERVIEW_COST_PER_1K_OUTPUT_USD
from src.probing.models import ProbeType
from src.probing.question_bank import BusinessQuestion, get_tree_for_question
from src.probing.smart_sample import SampledPersona, SmartSample, select_smart_sample
from src.simulation.explorer import VariantStrategy, generate_variants
from src.simulation.static import StaticSimulationResult, run_static_simulation

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.decision.scenarios import ScenarioConfig
    from src.generation.population import Population
    from src.taxonomy.schema import Persona
    from src.utils.llm import LLMClient

logger = structlog.get_logger(__name__)
_T = TypeVar("_T")


def _run_async(coro: Any) -> _T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: list[_T] = []
    errors: list[BaseException] = []

    def _runner() -> None:
        try:
            result.append(asyncio.run(coro))
        except BaseException as exc:  # pragma: no cover - surfaced through callers
            errors.append(exc)

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]
    return result[0]


def _iso_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class AlternativeRunSummary(BaseModel):
    """Summary of one alternative scenario run (funnel-only)."""

    model_config = ConfigDict(extra="forbid")

    variant_id: str
    parameter_changes: dict[str, Any]
    business_rationale: str
    adoption_count: int
    adoption_rate: float
    delta_vs_primary: float


class ResearchMetadata(BaseModel):
    """Metadata about the research run."""

    model_config = ConfigDict(extra="forbid")

    timestamp: str
    duration_seconds: float
    scenario_id: str
    question_id: str
    population_size: int
    sample_size: int
    alternative_count: int
    llm_calls_made: int
    estimated_cost_usd: float
    mock_mode: bool


class InterviewResult(BaseModel):
    """One persona's interview responses."""

    model_config = ConfigDict(extra="forbid")

    persona_id: str
    persona_name: str
    selection_reason: str
    responses: list[dict[str, str]] = Field(default_factory=list)


class ResearchResult(BaseModel):
    """Complete output of a hybrid research run."""

    model_config = ConfigDict(extra="forbid")

    primary_funnel: StaticSimulationResult
    smart_sample: SmartSample
    interview_results: list[InterviewResult]
    alternative_runs: list[AlternativeRunSummary]
    metadata: ResearchMetadata


class ResearchRunner:
    """Orchestrates the full hybrid research flow."""

    def __init__(
        self,
        population: Population,
        scenario: ScenarioConfig,
        question: BusinessQuestion,
        llm_client: LLMClient,
        *,
        mock_mode: bool = True,
        alternative_count: int = 50,
        sample_size: int = 18,
        seed: int = 42,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> None:
        self.population = population
        self.scenario = scenario
        self.question = question
        self.llm_client = llm_client
        self.mock_mode = mock_mode
        self.alternative_count = alternative_count
        self.sample_size = sample_size
        self.seed = seed
        self.progress_callback = progress_callback

    def _progress(self, message: str, progress: float) -> None:
        if self.progress_callback:
            self.progress_callback(message, progress)

    def _interview_persona(
        self,
        interviewer: PersonaInterviewer,
        persona: Persona,
        sampled: SampledPersona,
        decision_result: dict[str, Any],
        interview_questions: list[str],
    ) -> tuple[InterviewResult, int, int, int]:
        history: list[InterviewTurn] = []
        responses: list[dict[str, str]] = []
        llm_calls = 0
        total_input_tokens = 0
        total_output_tokens = 0

        for prompt in interview_questions:
            turn = _run_async(
                interviewer.interview(
                    persona=persona,
                    question=prompt,
                    scenario_id=self.scenario.id,
                    decision_result=decision_result,
                    conversation_history=history,
                )
            )
            responses.append({"question": prompt, "answer": turn.content})
            history.append(InterviewTurn(role="user", content=prompt, timestamp=_iso_timestamp()))
            history.append(turn)

            # Count only real-model calls for spend/cost tracking.
            if interviewer.last_input_tokens > 0 or interviewer.last_output_tokens > 0:
                llm_calls += 1
                total_input_tokens += interviewer.last_input_tokens
                total_output_tokens += interviewer.last_output_tokens

        return (
            InterviewResult(
                persona_id=persona.id,
                persona_name=persona.display_name or persona.id,
                selection_reason=sampled.selection_reason,
                responses=responses,
            ),
            llm_calls,
            total_input_tokens,
            total_output_tokens,
        )

    def _variant_rationale(self, variant_name: str, modifications: dict[str, Any]) -> str:
        if not modifications:
            return "Baseline configuration."

        parts = [f"{path}={value}" for path, value in sorted(modifications.items())[:3]]
        joined = ", ".join(parts)
        return f"{variant_name}: tests {joined}."

    def run(self) -> ResearchResult:
        """Execute the full research pipeline."""

        started = time.monotonic()
        self.llm_client.config.llm_mock_enabled = self.mock_mode

        self._progress("Running decision pathway on all personas...", 0.1)
        primary = run_static_simulation(
            population=self.population,
            scenario=self.scenario,
            seed=self.seed,
        )

        self._progress("Selecting personas for deep interviews...", 0.2)
        smart_sample = select_smart_sample(
            personas=self.population.personas,
            decisions=primary.results_by_persona,
            target_size=self.sample_size,
            seed=self.seed,
        )

        interviewer = PersonaInterviewer(self.llm_client)
        tree = get_tree_for_question(self.question.id)
        interview_questions = [
            probe.question_template
            for probe in tree.probes
            if probe.probe_type == ProbeType.INTERVIEW
            and probe.status != "disabled"
            and probe.question_template
        ]

        interview_results: list[InterviewResult] = []
        llm_calls_made = 0
        total_input_tokens = 0
        total_output_tokens = 0

        sample_n = max(1, len(smart_sample.selections))
        for idx, sampled in enumerate(smart_sample.selections):
            persona = self.population.get_persona(sampled.persona_id)
            self._progress(
                f"Interviewing persona {persona.display_name or persona.id}...",
                0.2 + ((idx + 1) / sample_n) * 0.5,
            )
            decision_result = primary.results_by_persona.get(
                persona.id, {"scenario_id": self.scenario.id, "outcome": "reject"}
            )
            try:
                (
                    persona_result,
                    calls,
                    input_tokens,
                    output_tokens,
                ) = self._interview_persona(
                    interviewer=interviewer,
                    persona=persona,
                    sampled=sampled,
                    decision_result=decision_result,
                    interview_questions=interview_questions,
                )
                interview_results.append(persona_result)
                llm_calls_made += calls
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
            except Exception as exc:  # pragma: no cover - defensive continuation path
                logger.exception(
                    "research_interview_failed",
                    persona_id=persona.id,
                    question_id=self.question.id,
                    error=str(exc),
                )
                continue

        self._progress("Generating alternative scenarios...", 0.75)
        generated = generate_variants(
            base=self.scenario,
            strategy=VariantStrategy.SMART,
            n_variants=self.alternative_count,
            base_result=primary,
            seed=self.seed,
        )
        alternatives = [variant for variant in generated if not variant.is_baseline][
            : self.alternative_count
        ]

        alternative_runs: list[AlternativeRunSummary] = []
        alt_n = max(1, len(alternatives))
        for idx, variant in enumerate(alternatives):
            self._progress(
                "Evaluating alternatives...",
                0.75 + ((idx + 1) / alt_n) * 0.2,
            )
            sim = run_static_simulation(
                population=self.population,
                scenario=variant.scenario_config,
                seed=self.seed,
            )
            alternative_runs.append(
                AlternativeRunSummary(
                    variant_id=variant.variant_id,
                    parameter_changes=dict(variant.modifications),
                    business_rationale=self._variant_rationale(
                        variant_name=variant.variant_name,
                        modifications=variant.modifications,
                    ),
                    adoption_count=sim.adoption_count,
                    adoption_rate=sim.adoption_rate,
                    delta_vs_primary=sim.adoption_rate - primary.adoption_rate,
                )
            )

        # Sort alternatives by impact delta descending (best results first)
        alternative_runs.sort(key=lambda x: x.delta_vs_primary, reverse=True)

        self._progress("Compiling results...", 0.98)
        elapsed = time.monotonic() - started
        estimated_cost = (
            (total_input_tokens / 1000) * INTERVIEW_COST_PER_1K_INPUT_USD
            + (total_output_tokens / 1000) * INTERVIEW_COST_PER_1K_OUTPUT_USD
        )
        metadata = ResearchMetadata(
            timestamp=_iso_timestamp(),
            duration_seconds=round(elapsed, 2),
            scenario_id=self.scenario.id,
            question_id=self.question.id,
            population_size=len(self.population.personas),
            sample_size=len(smart_sample.selections),
            alternative_count=len(alternative_runs),
            llm_calls_made=0 if self.mock_mode else llm_calls_made,
            estimated_cost_usd=0.0 if self.mock_mode else round(estimated_cost, 4),
            mock_mode=self.mock_mode,
        )

        return ResearchResult(
            primary_funnel=primary,
            smart_sample=smart_sample,
            interview_results=interview_results,
            alternative_runs=alternative_runs,
            metadata=metadata,
        )

