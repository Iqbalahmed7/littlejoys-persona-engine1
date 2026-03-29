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
from src.simulation.counterfactual import (
    CounterfactualReport,
    generate_default_counterfactuals,
    run_counterfactual_analysis,
)
from src.simulation.event_engine import EventSimulationResult, run_event_simulation
from src.simulation.explorer import VariantStrategy, generate_variants
from src.simulation.static import StaticSimulationResult, run_static_simulation
from src.simulation.temporal import TemporalSimulationResult, run_temporal_simulation

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
    temporal_adoption_rate: float | None = None
    temporal_active_rate: float | None = None
    event_active_rate: float | None = None
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
    temporal_result: TemporalSimulationResult | None = None
    event_result: EventSimulationResult | None = None
    smart_sample: SmartSample
    interview_results: list[InterviewResult]
    alternative_runs: list[AlternativeRunSummary]
    metadata: ResearchMetadata
    counterfactual_report: CounterfactualReport | None = None


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
        event_primary: EventSimulationResult | None = None
        temporal_primary: TemporalSimulationResult | None = None
        if self.scenario.mode == "temporal":
            duration_days = max(1, int(self.scenario.months) * 30)

            def _event_progress(p: float) -> None:
                self._progress("Running day-level event simulation...", 0.12 + 0.08 * min(p, 1.0))

            event_primary = run_event_simulation(
                population=self.population,
                scenario=self.scenario,
                duration_days=duration_days,
                seed=self.seed,
                progress_callback=_event_progress,
            )
            self._progress("Running temporal simulation (monthly)...", 0.22)
            temporal_primary = run_temporal_simulation(
                population=self.population,
                scenario=self.scenario,
                thresholds=self.scenario.funnel_thresholds,
                months=self.scenario.months,
                seed=self.seed,
            )

        self._progress("Selecting personas for deep interviews...", 0.26)
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
                0.26 + ((idx + 1) / sample_n) * 0.48,
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

        alternative_rows: list[tuple[Any, StaticSimulationResult]] = []
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
            alternative_rows.append((variant, sim))

        temporal_by_variant: dict[str, TemporalSimulationResult] = {}
        event_by_variant: dict[str, EventSimulationResult] = {}
        if self.scenario.mode == "temporal":
            top_for_temporal = sorted(
                alternative_rows,
                key=lambda row: row[1].adoption_rate,
                reverse=True,
            )[:10]
            top_n = max(1, len(top_for_temporal))
            for idx, (variant, _sim) in enumerate(top_for_temporal):
                self._progress(
                    "Running temporal alternatives...",
                    0.95 + ((idx + 1) / top_n) * 0.03,
                )
                temporal_by_variant[variant.variant_id] = run_temporal_simulation(
                    population=self.population,
                    scenario=variant.scenario_config,
                    thresholds=variant.scenario_config.funnel_thresholds,
                    months=variant.scenario_config.months,
                    seed=self.seed,
                )

            if event_primary is not None:
                top_for_event = sorted(
                    alternative_rows,
                    key=lambda row: row[1].adoption_rate,
                    reverse=True,
                )[:5]
                ev_n = max(1, len(top_for_event))
                alt_duration = max(1, int(self.scenario.months) * 30)
                # Stay strictly above the temporal-alternatives band (ends at 0.98);
                # leave headroom before compile (1.0) for counterfactual analysis.
                for idx, (variant, _sim) in enumerate(top_for_event):
                    self._progress(
                        "Running day-level event alternatives...",
                        0.98 + ((idx + 1) / ev_n) * 0.015,
                    )
                    # Do not forward engine progress here: it maps p→[0.12,0.20] and would
                    # rewind the overall progress bar after higher phases.
                    event_by_variant[variant.variant_id] = run_event_simulation(
                        population=self.population,
                        scenario=variant.scenario_config,
                        duration_days=alt_duration,
                        seed=self.seed,
                        progress_callback=None,
                    )

        alternative_runs: list[AlternativeRunSummary] = []
        for variant, sim in alternative_rows:
            temporal_alt = temporal_by_variant.get(variant.variant_id)
            event_alt = event_by_variant.get(variant.variant_id)
            evt_rate = event_alt.final_active_rate if event_alt is not None else None

            base_delta = sim.adoption_rate - primary.adoption_rate
            if event_primary is not None and evt_rate is not None:
                base_delta = evt_rate - event_primary.final_active_rate
            elif temporal_alt is not None and temporal_primary is not None:
                base_delta = temporal_alt.final_active_rate - temporal_primary.final_active_rate
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
                    temporal_adoption_rate=(
                        temporal_alt.final_adoption_rate if temporal_alt is not None else None
                    ),
                    temporal_active_rate=(
                        temporal_alt.final_active_rate if temporal_alt is not None else None
                    ),
                    event_active_rate=evt_rate,
                    delta_vs_primary=base_delta,
                )
            )

        if event_by_variant:
            alternative_runs.sort(
                key=lambda x: (
                    x.event_active_rate is not None,
                    x.event_active_rate if x.event_active_rate is not None else -1.0,
                    x.delta_vs_primary,
                ),
                reverse=True,
            )
        elif temporal_by_variant:
            alternative_runs.sort(
                key=lambda x: (
                    x.temporal_active_rate is not None,
                    x.temporal_active_rate if x.temporal_active_rate is not None else -1.0,
                    x.delta_vs_primary,
                ),
                reverse=True,
            )
        else:
            alternative_runs.sort(key=lambda x: x.delta_vs_primary, reverse=True)

        counterfactual_report: CounterfactualReport | None = None
        if self.scenario.mode == "temporal" and event_primary is not None:
            self._progress("Running counterfactual analysis...", 0.997)
            counterfactual_report = run_counterfactual_analysis(
                population=self.population,
                baseline_scenario=self.scenario,
                counterfactuals=generate_default_counterfactuals(self.scenario),
                duration_days=max(1, int(self.scenario.months) * 30),
                seed=self.seed,
                progress_callback=None,
                baseline_event_result=event_primary,
            )

        self._progress("Compiling results...", 1.0)
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
            temporal_result=temporal_primary,
            event_result=event_primary,
            smart_sample=smart_sample,
            interview_results=interview_results,
            alternative_runs=alternative_runs,
            metadata=metadata,
            counterfactual_report=counterfactual_report,
        )
