"""Probing tree execution engine."""

from __future__ import annotations

import asyncio
import math
import threading
from typing import TYPE_CHECKING, Any, TypeVar

import structlog

from src.analysis.interviews import PersonaInterviewer
from src.constants import DEFAULT_SEED
from src.decision.funnel import run_funnel
from src.decision.scenarios import get_scenario
from src.probing.clustering import cluster_responses_mock
from src.probing.confidence import (
    classify_hypothesis,
    compute_attribute_confidence,
    compute_hypothesis_confidence,
    compute_interview_confidence,
    compute_simulation_confidence,
)
from src.probing.models import (
    AttributeSplit,
    Hypothesis,
    HypothesisVerdict,
    InterviewResponse,
    Probe,
    ProbeResult,
    ProbeType,
    ProblemStatement,
    TreeSynthesis,
)
from src.probing.sampling import PROBE_SAMPLE_SIZE, sample_personas_for_probe
from src.utils.display import display_name

if TYPE_CHECKING:
    from src.generation.population import Population
    from src.probing.models import ResponseCluster
    from src.taxonomy.schema import Persona
    from src.utils.llm import LLMClient

log = structlog.get_logger(__name__)
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


class ProbingTreeEngine:
    """Orchestrates probe execution across a persona population."""

    def __init__(
        self,
        population: Population,
        scenario_id: str,
        llm_client: LLMClient,
    ) -> None:
        self.population = population
        self.scenario = get_scenario(scenario_id)
        self.llm = llm_client
        self.interviewer = PersonaInterviewer(llm_client)
        self._decisions: dict[str, Any] = {}
        self._outcomes: dict[str, str] = {}
        self.verdicts: dict[str, HypothesisVerdict] = {}
        self.synthesis: TreeSynthesis | None = None
        self._precompute_outcomes()

    @property
    def _personas(self) -> list[Persona]:
        return self.population.personas

    def _precompute_outcomes(self) -> None:
        """Run the funnel once for all personas and cache the results."""

        for persona in self._personas:
            decision = run_funnel(persona, self.scenario)
            self._decisions[persona.id] = decision
            self._outcomes[persona.id] = decision.outcome

    def execute_tree(
        self,
        problem: ProblemStatement,
        hypotheses: list[Hypothesis],
        probes: list[Probe],
    ) -> TreeSynthesis:
        """Run all probes for enabled hypotheses and return a tree synthesis."""

        self.verdicts = {}
        for hypothesis in sorted(hypotheses, key=lambda item: (item.order, item.id)):
            if not hypothesis.enabled:
                log.info("probing_hypothesis_skipped", hypothesis_id=hypothesis.id)
                continue

            hypothesis_probes = sorted(
                [probe for probe in probes if probe.hypothesis_id == hypothesis.id],
                key=lambda item: (item.order, item.id),
            )
            for probe in hypothesis_probes:
                self.execute_probe(probe)

            self.verdicts[hypothesis.id] = self._build_hypothesis_verdict(
                hypothesis,
                hypothesis_probes,
            )

        self.synthesis = self._build_tree_synthesis(problem, hypotheses, probes)
        return self.synthesis

    def execute_probe(self, probe: Probe) -> ProbeResult:
        """Dispatch a probe to the appropriate execution path."""

        probe.status = "running"
        if probe.probe_type == ProbeType.INTERVIEW:
            result = _run_async(self._run_interview_probe(probe))
        elif probe.probe_type == ProbeType.SIMULATION:
            result = self._run_simulation_probe(probe)
        elif probe.probe_type == ProbeType.ATTRIBUTE:
            result = self._run_attribute_probe(probe)
        else:  # pragma: no cover - enum guards this in normal flows
            raise ValueError(f"Unsupported probe type: {probe.probe_type}")

        probe.result = result
        probe.status = "complete"
        log.info(
            "probing_probe_complete",
            probe_id=probe.id,
            probe_type=probe.probe_type.value,
            confidence=result.confidence,
        )
        return result

    async def _run_interview_probe(self, probe: Probe) -> ProbeResult:
        if not probe.question_template:
            raise ValueError(f"Interview probe '{probe.id}' is missing question_template")

        personas = list(self._personas)
        sampled = sample_personas_for_probe(
            personas=personas,
            outcomes=self._outcomes,
            target_outcome=probe.target_outcome,
            sample_size=PROBE_SAMPLE_SIZE,
            seed=DEFAULT_SEED,
        )

        responses: list[tuple[Persona, str]] = []
        interview_responses: list[InterviewResponse] = []
        for persona in sampled:
            decision = self._decisions[persona.id]
            turn = await self.interviewer.interview(
                persona=persona,
                question=probe.question_template,
                scenario_id=self.scenario.id,
                decision_result=decision.to_dict(),
            )
            responses.append((persona, turn.content))
            interview_responses.append(
                InterviewResponse(
                    persona_id=persona.id,
                    persona_name=persona.display_name or persona.id,
                    outcome=decision.outcome,
                    content=turn.content,
                )
            )

        clusters = cluster_responses_mock(responses)
        confidence = compute_interview_confidence(clusters)
        return ProbeResult(
            probe_id=probe.id,
            confidence=confidence,
            evidence_summary=_summarize_clusters(clusters),
            sample_size=len(responses),
            population_size=len(personas),
            clustering_method="keyword",
            interview_responses=interview_responses,
            response_clusters=clusters,
        )

    def _run_simulation_probe(self, probe: Probe) -> ProbeResult:
        if not probe.scenario_modifications:
            raise ValueError(f"Simulation probe '{probe.id}' is missing scenario_modifications")

        from src.simulation.counterfactual import run_counterfactual

        result = run_counterfactual(
            population=self.population,
            baseline_scenario=self.scenario,
            modifications=probe.scenario_modifications,
            counterfactual_name=probe.id,
            seed=DEFAULT_SEED,
        )
        confidence = compute_simulation_confidence(
            result.baseline_adoption_rate,
            result.counterfactual_adoption_rate,
            len(self._personas),
        )
        return ProbeResult(
            probe_id=probe.id,
            confidence=confidence,
            evidence_summary=_format_simulation_summary(probe, result),
            sample_size=len(self._personas),
            baseline_metric=result.baseline_adoption_rate,
            modified_metric=result.counterfactual_adoption_rate,
            lift=result.absolute_lift,
        )

    def _run_attribute_probe(self, probe: Probe) -> ProbeResult:
        if not probe.analysis_attributes:
            raise ValueError(f"Attribute probe '{probe.id}' is missing analysis_attributes")

        rows: list[dict[str, Any]] = []
        for persona in self._personas:
            flat = persona.to_flat_dict()
            flat["_outcome"] = self._outcomes.get(persona.id, "reject")
            rows.append(flat)

        splits: list[AttributeSplit] = []
        for attribute in probe.analysis_attributes:
            adopter_vals = [
                float(row[attribute])
                for row in rows
                if row["_outcome"] == "adopt"
                and attribute in row
                and isinstance(row[attribute], (int, float))
                and not isinstance(row[attribute], bool)
            ]
            rejector_vals = [
                float(row[attribute])
                for row in rows
                if row["_outcome"] == "reject"
                and attribute in row
                and isinstance(row[attribute], (int, float))
                and not isinstance(row[attribute], bool)
            ]
            if not adopter_vals or not rejector_vals:
                continue

            adopter_mean = sum(adopter_vals) / len(adopter_vals)
            rejector_mean = sum(rejector_vals) / len(rejector_vals)
            pooled_std = _pooled_std(adopter_vals, rejector_vals)
            effect_size = (adopter_mean - rejector_mean) / pooled_std if pooled_std > 0 else 0.0
            splits.append(
                AttributeSplit(
                    attribute=attribute,
                    adopter_mean=adopter_mean,
                    rejector_mean=rejector_mean,
                    effect_size=effect_size,
                    significant=abs(effect_size) > 0.3,
                )
            )

        splits.sort(key=lambda split: abs(split.effect_size), reverse=True)
        confidence = compute_attribute_confidence(splits)
        return ProbeResult(
            probe_id=probe.id,
            confidence=confidence,
            evidence_summary=_format_attribute_summary(splits),
            sample_size=len(rows),
            attribute_splits=splits,
        )

    def _build_hypothesis_verdict(
        self,
        hypothesis: Hypothesis,
        probes: list[Probe],
    ) -> HypothesisVerdict:
        results = [probe.result for probe in probes if probe.result is not None]
        confidences = [result.confidence for result in results]
        final_confidence, consistency = compute_hypothesis_confidence(confidences)
        status = classify_hypothesis(final_confidence)
        return HypothesisVerdict(
            hypothesis_id=hypothesis.id,
            confidence=final_confidence,
            status=status,
            evidence_summary=_format_hypothesis_summary(
                hypothesis_title=hypothesis.title,
                status=status,
                confidence=final_confidence,
                results=results,
            ),
            key_persona_segments=_extract_key_segments(results),
            recommended_actions=_recommend_actions(hypothesis),
            consistency_score=consistency,
        )

    def _build_tree_synthesis(
        self,
        problem: ProblemStatement,
        hypotheses: list[Hypothesis],
        probes: list[Probe],
    ) -> TreeSynthesis:
        enabled_ids = {hypothesis.id for hypothesis in hypotheses if hypothesis.enabled}
        disabled_ids = [hypothesis.id for hypothesis in hypotheses if not hypothesis.enabled]
        ranking = sorted(
            (
                (hypothesis_id, verdict.confidence)
                for hypothesis_id, verdict in self.verdicts.items()
                if hypothesis_id in enabled_ids
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        dominant_hypothesis = ranking[0][0] if ranking else ""
        overall_confidence = ranking[0][1] if ranking else 0.0
        hypotheses_confirmed = sum(
            1
            for verdict in self.verdicts.values()
            if verdict.status in {"confirmed", "partially_confirmed"}
        )

        disabled_confidences = [
            self.verdicts[hypothesis_id].confidence
            for hypothesis_id in disabled_ids
            if hypothesis_id in self.verdicts
        ]
        full_confidence = max([*disabled_confidences, overall_confidence], default=0.0)
        disabled_impact = (
            max(0.0, full_confidence - overall_confidence) if disabled_confidences else 0.0
        )

        hypothesis_lookup = {hypothesis.id: hypothesis for hypothesis in hypotheses}
        recommended_actions: list[str] = []
        for hypothesis_id, _confidence in ranking:
            for action in self.verdicts[hypothesis_id].recommended_actions:
                if action not in recommended_actions:
                    recommended_actions.append(action)

        return TreeSynthesis(
            problem_id=problem.id,
            hypotheses_tested=len(ranking),
            hypotheses_confirmed=hypotheses_confirmed,
            dominant_hypothesis=dominant_hypothesis,
            confidence_ranking=ranking,
            synthesis_narrative=_format_tree_narrative(
                problem_title=problem.title,
                ranking=ranking,
                verdicts=self.verdicts,
                hypothesis_lookup=hypothesis_lookup,
                disabled_count=len(disabled_ids),
            ),
            recommended_actions=recommended_actions[:5],
            overall_confidence=overall_confidence,
            disabled_hypotheses=disabled_ids,
            confidence_impact_of_disabled=disabled_impact,
            total_cost_estimate=_estimate_run_cost(
                enabled_probes=[probe for probe in probes if probe.hypothesis_id in enabled_ids],
                verdict_count=len(ranking),
                mock_mode=self.llm.config.llm_mock_enabled,
            ),
        )


def _pooled_std(first: list[float], second: list[float]) -> float:
    if len(first) < 2 or len(second) < 2:
        return 0.0

    first_mean = sum(first) / len(first)
    second_mean = sum(second) / len(second)
    first_var = sum((value - first_mean) ** 2 for value in first) / (len(first) - 1)
    second_var = sum((value - second_mean) ** 2 for value in second) / (len(second) - 1)
    pooled_variance = (
        ((len(first) - 1) * first_var) + ((len(second) - 1) * second_var)
    ) / (len(first) + len(second) - 2)
    return math.sqrt(max(0.0, pooled_variance))


def _summarize_clusters(clusters: list[ResponseCluster]) -> str:
    if not clusters:
        return "No clear interview theme emerged in the sampled responses."

    dominant = clusters[0]
    summary = (
        f"The dominant interview theme was {dominant.description.lower()}, appearing in "
        f"{dominant.percentage:.0%} of sampled responses."
    )
    if len(clusters) > 1:
        summary += (
            f" A secondary theme was {clusters[1].description.lower()} "
            f"({clusters[1].percentage:.0%})."
        )
    return summary


def _metric_label(metric: str | None) -> str:
    if not metric:
        return "adoption rate"
    if metric == "repeat_rate":
        return "modeled repeat rate proxy"
    return metric.replace("_", " ")


def _parameter_label(path: str) -> str:
    leaf = path.split(".")[-1]
    labels = {
        "price_inr": "price",
        "taste_appeal": "taste appeal",
        "form_factor": "format",
        "awareness_budget": "awareness investment",
        "pediatrician_endorsement": "pediatrician endorsement",
        "school_partnership": "school partnerships",
        "effort_to_acquire": "ease of trial",
        "cooking_required": "cooking effort",
        "lj_pass_available": "LittleJoys Pass access",
    }
    return labels.get(leaf, display_name(leaf))


def _format_parameter_value(path: str, value: Any) -> str:
    leaf = path.split(".")[-1]
    if isinstance(value, bool):
        return "enabled" if value else "disabled"
    if leaf == "price_inr" and isinstance(value, (int, float)):
        return f"Rs {value:.0f}"
    if isinstance(value, float) and 0.0 <= value <= 1.0:
        return f"{value:.0%}"
    return str(value).replace("_", " ")


def _format_modifications(modifications: dict[str, Any]) -> str:
    phrases = [
        f"{_parameter_label(path)} set to {_format_parameter_value(path, value)}"
        for path, value in modifications.items()
    ]
    return ", ".join(phrases)


def _format_simulation_summary(probe: Probe, result: Any) -> str:
    modifications = probe.scenario_modifications or {}
    metric_label = _metric_label(probe.comparison_metric)
    return (
        f"Testing {_format_modifications(modifications)} moved the {metric_label} from "
        f"{result.baseline_adoption_rate:.0%} to {result.counterfactual_adoption_rate:.0%} "
        f"(lift {result.absolute_lift:+.1%})."
    )


def _format_attribute_summary(splits: list[AttributeSplit]) -> str:
    if not splits:
        return "No meaningful attribute differences emerged between adopters and rejectors."

    highlights = []
    for split in splits[:2]:
        label = display_name(split.attribute)
        higher_group = "adopters" if split.adopter_mean >= split.rejector_mean else "rejectors"
        highlights.append(
            f"{label} was higher among {higher_group} "
            f"({split.adopter_mean:.2f} vs {split.rejector_mean:.2f}, effect {split.effect_size:.2f})."
        )

    prefix = (
        "Clear separation emerged between adopters and rejectors. "
        if any(split.significant for split in splits)
        else "Attribute differences were weak overall. "
    )
    return prefix + " ".join(highlights)


def _format_hypothesis_summary(
    *,
    hypothesis_title: str,
    status: str,
    confidence: float,
    results: list[ProbeResult],
) -> str:
    if not results:
        return f"{hypothesis_title} remains untested."

    strongest = max(results, key=lambda result: result.confidence)
    status_text = status.replace("_", " ")
    return (
        f"{hypothesis_title} is {status_text} at {confidence:.0%} confidence. "
        f"Strongest evidence: {strongest.evidence_summary}"
    )


def _extract_key_segments(results: list[ProbeResult]) -> list[str]:
    segments: list[str] = []
    for result in results:
        if result.response_clusters:
            cluster = result.response_clusters[0]
            segments.append(cluster.description)
            for attribute, value in list(cluster.dominant_attributes.items())[:2]:
                direction = "high" if value >= 0.5 else "low"
                segments.append(f"Parents with {direction} {display_name(attribute).lower()}")
        for split in result.attribute_splits:
            if split.significant:
                group = "adopters" if split.adopter_mean >= split.rejector_mean else "rejectors"
                segments.append(f"{group.title()} with higher {display_name(split.attribute)}")

    deduped: list[str] = []
    for segment in segments:
        if segment not in deduped:
            deduped.append(segment)
    return deduped[:3]


def _recommend_actions(hypothesis: Hypothesis) -> list[str]:
    title = hypothesis.title.lower()
    if "price" in title or "value" in title:
        return [
            "Test sharper value messaging and lower-friction price offers.",
            "Prioritize segments that show stronger sensitivity to cost comparisons.",
        ]
    if "taste" in title or "format" in title:
        return [
            "Improve taste cues and widen serving-format options for the child.",
            "Use messaging that helps parents vary the routine instead of repeating one format.",
        ]
    if "re-engagement" in title or "automatic" in title or "reminder" in title:
        return [
            "Add reorder reminders through channels that fit busy parent routines.",
            "Make subscription or auto-reorder the easiest next step after first purchase.",
        ]
    if "competitor" in title or "alternative" in title:
        return [
            "Clarify why LittleJoys is easier or more trustworthy than familiar alternatives.",
            "Arm parents with simple comparison points they can explain at home.",
        ]
    if "school" in title or "peer" in title:
        return [
            "Invest in school and community recommendation channels ahead of pure social reach.",
        ]
    if "irrelevance" in title or "need" in title or "unfamiliarity" in title:
        return [
            "Strengthen parent education on the need gap before pushing conversion tactics.",
        ]
    if "effort" in title or "cooking" in title:
        return [
            "Reduce prep effort and make the first-use routine feel easy on busy mornings.",
        ]
    return ["Run a focused follow-up test to sharpen the strongest signal."]


def _format_tree_narrative(
    *,
    problem_title: str,
    ranking: list[tuple[str, float]],
    verdicts: dict[str, HypothesisVerdict],
    hypothesis_lookup: dict[str, Hypothesis],
    disabled_count: int,
) -> str:
    if not ranking:
        return f"No enabled hypotheses were executed for {problem_title.lower()}."

    top_id, top_confidence = ranking[0]
    top_title = hypothesis_lookup[top_id].title
    narrative = (
        f"The strongest explanation is {top_title} with {top_confidence:.0%} confidence."
    )
    if len(ranking) > 1:
        second_id, second_confidence = ranking[1]
        second_title = hypothesis_lookup[second_id].title
        narrative += (
            f" The next best-supported branch is {second_title} at {second_confidence:.0%} confidence."
        )
    narrative += f" Overall tree confidence sits at {ranking[0][1]:.0%}."
    if disabled_count:
        narrative += f" {disabled_count} hypothesis branches were left disabled."
    top_verdict = verdicts.get(top_id)
    if top_verdict and top_verdict.key_persona_segments:
        narrative += f" Key segments include {', '.join(top_verdict.key_persona_segments[:2])}."
    return narrative


def _estimate_run_cost(
    *,
    enabled_probes: list[Probe],
    verdict_count: int,
    mock_mode: bool,
) -> float:
    if mock_mode:
        return 0.0

    interview_probe_count = sum(
        1 for probe in enabled_probes if probe.probe_type == ProbeType.INTERVIEW
    )
    estimated_cost = (
        (interview_probe_count * PROBE_SAMPLE_SIZE * 0.0007)
        + (interview_probe_count * 0.015)
        + (verdict_count * 0.015)
        + (0.02 if verdict_count else 0.0)
    )
    return round(estimated_cost, 2)
