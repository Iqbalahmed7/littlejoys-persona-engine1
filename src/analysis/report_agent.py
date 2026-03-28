"""
ReportAgent — LLM-powered analyst that generates structured reports using ReACT.

Has access to analysis tools (segments, barriers, causal) and generates
comprehensive reports for each business problem.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field

from src.analysis.barriers import analyze_barriers
from src.analysis.causal import compute_variable_importance, generate_causal_statements
from src.analysis.segments import analyze_segments
from src.constants import (
    REPORT_AGENT_MAX_ITERATIONS,
    REPORT_AGENT_MODEL,
    REPORT_MAX_TOOL_CALLS,
    REPORT_MIN_SECTIONS,
)
from src.decision.scenarios import get_scenario
from src.simulation.counterfactual import (
    get_predefined_counterfactuals,
    run_predefined_counterfactual,
)

if TYPE_CHECKING:
    from src.generation.population import Population
    from src.utils.llm import LLMClient

logger = structlog.get_logger(__name__)

REPORT_AGENT_TOOLS = {
    "query_segment": {
        "description": "Get adoption metrics for a filtered segment",
        "function": "_tool_query_segment",
    },
    "compare_segments": {
        "description": "Compare two segments head-to-head on any metric",
        "function": "_tool_compare_segments",
    },
    "explain_persona": {
        "description": "Get full decision trace for a specific persona",
        "function": "_tool_explain_persona",
    },
    "run_counterfactual": {
        "description": "Perturb a scenario parameter and get new results",
        "function": "_tool_run_counterfactual",
    },
    "get_barrier_distribution": {
        "description": "Get distribution of rejection reasons for a segment",
        "function": "_tool_get_barriers",
    },
    "get_variable_importance": {
        "description": "Get ranked list of attributes driving adoption",
        "function": "_tool_get_importance",
    },
}
_REQUIRED_SECTION_TITLES = (
    "Executive Summary",
    "Funnel Analysis",
    "Segment Deep Dive",
    "Key Drivers",
    "Counterfactual Insights",
    "Recommendations",
)


class ReportSection(BaseModel):
    """One grounded section of the generated report."""

    model_config = ConfigDict(extra="forbid")

    title: str
    content: str
    supporting_data: dict[str, Any] = Field(default_factory=dict)


class ReportOutput(BaseModel):
    """Final structured report output."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    scenario_name: str
    sections: list[ReportSection]
    tool_calls_made: int
    raw_markdown: str


def _llm_route(model_name: str) -> Literal["reasoning", "bulk"]:
    return "reasoning" if model_name == "opus" else "bulk"


def _rows_from_results(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in results.values() if isinstance(row, dict)]


def _outcome_to_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() == "adopt"
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def validate_report_grounding(report: ReportOutput, schema_attributes: list[str]) -> list[str]:
    """Return ungrounded sentences that lack both metrics and schema references."""

    lowered_attributes = [attribute.lower() for attribute in schema_attributes]
    warnings: list[str] = []

    for section in report.sections:
        snippets = [
            snippet.strip() for snippet in re.split(r"[\n\.]", section.content) if snippet.strip()
        ]
        for snippet in snippets:
            lowered = snippet.lower()
            has_metric = any(character.isdigit() for character in snippet)
            has_attribute = any(attribute in lowered for attribute in lowered_attributes)
            if not has_metric or not has_attribute:
                warnings.append(f"{section.title}: {snippet}")

    return warnings


class ReportAgent:
    """
    LLM-powered report generator using ReACT (Reason + Act) pattern.

    Tools available to the agent:
    - analyze_segments(group_by) → segment analysis
    - analyze_barriers() → barrier distribution
    - compute_importance() → variable importance ranking
    - query_population(filter) → filtered persona data
    - compare_scenarios(a, b) → counterfactual comparison
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client
        self.max_iterations = REPORT_AGENT_MAX_ITERATIONS
        self.tools = {
            tool_name: getattr(self, spec["function"])
            for tool_name, spec in REPORT_AGENT_TOOLS.items()
        }
        self._scenario_id = ""
        self._scenario_name = ""
        self._population: Population | None = None
        self._working_results: dict[str, dict[str, Any]] = {}

    def _merge_results_with_population(
        self,
        results: dict[str, dict[str, Any]],
        population: Population | None,
    ) -> dict[str, dict[str, Any]]:
        if population is None:
            return {persona_id: dict(row) for persona_id, row in results.items()}

        merged: dict[str, dict[str, Any]] = {}
        for persona_id, row in results.items():
            try:
                persona = population.get_persona(persona_id)
                merged[persona_id] = persona.to_flat_dict() | dict(row) | {"persona_id": persona_id}
            except KeyError:
                merged[persona_id] = dict(row) | {"persona_id": persona_id}
        return merged

    def _available_segment_key(self) -> str | None:
        rows = _rows_from_results(self._working_results)
        for candidate in ("city_tier", "income_bracket", "employment_status"):
            if any(candidate in row for row in rows):
                return candidate
        return None

    def _available_segment_values(self, group_by: str) -> list[str]:
        values = sorted(
            {
                str(row[group_by])
                for row in _rows_from_results(self._working_results)
                if row.get(group_by) is not None
            }
        )
        return values

    async def _maybe_reason_about_next_tool(
        self,
        iteration: int,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> None:
        if self.llm.config.llm_mock_enabled:
            return

        prompt = (
            f"Scenario: {self._scenario_name}\n"
            f"Iteration: {iteration}\n"
            f"Next tool: {tool_name}\n"
            f"Tool args: {json.dumps(tool_args, sort_keys=True)}\n"
            "Briefly reason about why this tool is useful before running it."
        )
        await self.llm.generate(
            prompt=prompt,
            system="You are planning the next grounded analysis step.",
            model=_llm_route(REPORT_AGENT_MODEL),
        )

    def _plan_tool_sequence(self) -> list[tuple[str, dict[str, Any]]]:
        if not self._working_results:
            return []

        plan: list[tuple[str, dict[str, Any]]] = [
            ("get_variable_importance", {"scenario_id": self._scenario_id}),
            ("get_barrier_distribution", {"scenario_id": self._scenario_id}),
        ]

        segment_key = self._available_segment_key()
        if segment_key is not None:
            values = self._available_segment_values(segment_key)
            if values:
                plan.append(("query_segment", {"group_by": segment_key, "value": values[0]}))
            if len(values) >= 2:
                plan.append(
                    (
                        "compare_segments",
                        {"group_by": segment_key, "value_a": values[0], "value_b": values[-1]},
                    )
                )

        persona_id = next(iter(self._working_results.keys()), None)
        if persona_id is not None:
            plan.append(("explain_persona", {"persona_id": persona_id}))

        if self._population is not None:
            try:
                counterfactuals = get_predefined_counterfactuals(self._scenario_id)
                first_name = next(iter(counterfactuals.keys()))
                plan.append(("run_counterfactual", {"counterfactual_name": first_name}))
            except (KeyError, StopIteration):
                pass

        return plan[:REPORT_MAX_TOOL_CALLS]

    async def _execute_tool(self, tool_name: str, **tool_args: Any) -> dict[str, Any]:
        raw = self.tools[tool_name](**tool_args)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}

    def _tool_query_segment(self, group_by: str, value: str) -> str:
        segments = analyze_segments(self._working_results, group_by=group_by)
        match = next((segment for segment in segments if segment.segment_value == value), None)
        if match is None:
            return json.dumps(
                {"group_by": group_by, "value": value, "found": False}, sort_keys=True
            )
        return json.dumps(match.model_dump(mode="json"), sort_keys=True)

    def _tool_compare_segments(self, group_by: str, value_a: str, value_b: str) -> str:
        segments = analyze_segments(self._working_results, group_by=group_by)
        match_a = next((segment for segment in segments if segment.segment_value == value_a), None)
        match_b = next((segment for segment in segments if segment.segment_value == value_b), None)
        return json.dumps(
            {
                "group_by": group_by,
                "value_a": match_a.model_dump(mode="json") if match_a else None,
                "value_b": match_b.model_dump(mode="json") if match_b else None,
            },
            sort_keys=True,
        )

    def _tool_explain_persona(self, persona_id: str) -> str:
        row = self._working_results.get(persona_id, {})
        if not row:
            return json.dumps({"persona_id": persona_id, "found": False}, sort_keys=True)
        return json.dumps(
            {
                "persona_id": persona_id,
                "outcome": row.get("outcome"),
                "need_score": row.get("need_score"),
                "awareness_score": row.get("awareness_score"),
                "consideration_score": row.get("consideration_score"),
                "purchase_score": row.get("purchase_score"),
                "rejection_reason": row.get("rejection_reason"),
                "city_tier": row.get("city_tier"),
                "income_bracket": row.get("income_bracket"),
            },
            sort_keys=True,
        )

    def _tool_run_counterfactual(self, counterfactual_name: str | None = None) -> str:
        if self._population is None:
            return json.dumps({"available": False, "reason": "population_required"}, sort_keys=True)

        catalog = get_predefined_counterfactuals(self._scenario_id)
        selected_name = counterfactual_name or next(iter(catalog.keys()))
        result = run_predefined_counterfactual(
            population=self._population,
            scenario_id=self._scenario_id,
            counterfactual_name=selected_name,
        )
        return json.dumps(
            {
                "counterfactual_name": result.counterfactual_name,
                "baseline_adoption_rate": result.baseline_adoption_rate,
                "counterfactual_adoption_rate": result.counterfactual_adoption_rate,
                "absolute_lift": result.absolute_lift,
                "relative_lift_percent": result.relative_lift_percent,
                "top_segment": (
                    result.most_affected_segments[0].model_dump(mode="json")
                    if result.most_affected_segments
                    else None
                ),
            },
            sort_keys=True,
        )

    def _tool_get_barriers(self, scenario_id: str | None = None) -> str:
        del scenario_id
        barriers = analyze_barriers(self._working_results)
        return json.dumps(
            {"barriers": [barrier.model_dump(mode="json") for barrier in barriers]},
            sort_keys=True,
        )

    def _tool_get_importance(self, scenario_id: str | None = None) -> str:
        importances = compute_variable_importance(self._working_results)
        causal_statements = generate_causal_statements(
            importances,
            self._working_results,
            scenario_id=scenario_id,
        )
        return json.dumps(
            {
                "importances": [item.model_dump(mode="json") for item in importances[:10]],
                "causal_statements": [
                    item.model_dump(mode="json") for item in causal_statements[:5]
                ],
            },
            sort_keys=True,
        )

    def _overall_metrics(self) -> tuple[int, int, float]:
        rows = _rows_from_results(self._working_results)
        total = len(rows)
        adopted = sum(_outcome_to_bool(row.get("outcome")) for row in rows)
        rate = adopted / total if total else 0.0
        return total, adopted, rate

    def _build_sections(self, evidence: dict[str, dict[str, Any]]) -> list[ReportSection]:
        total, adopted, adoption_rate = self._overall_metrics()
        barriers = evidence.get("get_barrier_distribution", {}).get("barriers", [])
        importance_blob = evidence.get("get_variable_importance", {})
        importances = importance_blob.get("importances", [])
        causal_statements = importance_blob.get("causal_statements", [])
        segment_key = self._available_segment_key()
        segment_analysis = (
            analyze_segments(self._working_results, group_by=segment_key)
            if segment_key is not None
            else []
        )
        best_segment = segment_analysis[0] if segment_analysis else None
        worst_segment = segment_analysis[-1] if len(segment_analysis) >= 2 else best_segment
        counterfactual = evidence.get("run_counterfactual", {})

        top_barrier = barriers[0] if barriers else None
        top_importance = importances[0] if importances else None
        top_causal = causal_statements[0] if causal_statements else None

        executive_lines = [
            f"- scenario adoption_rate is {adoption_rate * 100:.1f}% ({adopted}/{total} personas).",
        ]
        if best_segment is not None and worst_segment is not None:
            executive_lines.append(
                f"- {segment_key}={best_segment.segment_value} adopts at {best_segment.adoption_rate * 100:.1f}% "
                f"vs {segment_key}={worst_segment.segment_value} at {worst_segment.adoption_rate * 100:.1f}%."
            )
        if top_importance is not None:
            executive_lines.append(
                f"- {top_importance['variable_name']} leads the model with SHAP {top_importance['shap_mean_abs']:.3f}."
            )
        if top_barrier is not None:
            executive_lines.append(
                f"- The main rejection barrier is {top_barrier['barrier']} at the {top_barrier['stage']} stage "
                f"({top_barrier['percentage'] * 100:.1f}% of all personas)."
            )

        funnel_content = (
            f"Out of {total} personas, {adopted} adopt and {total - adopted} reject, leaving an adoption_rate of "
            f"{adoption_rate * 100:.1f}%. "
        )
        if top_barrier is not None:
            funnel_content += (
                f"The largest measurable drop is {top_barrier['barrier']} in {top_barrier['stage']}, with "
                f"{top_barrier['count']} personas affected."
            )
        else:
            funnel_content += "No rejection barriers were recorded in the supplied results."

        if best_segment is not None:
            segment_content = (
                f"{segment_key}={best_segment.segment_value} is the strongest segment at "
                f"{best_segment.adoption_rate * 100:.1f}% adoption across n={best_segment.count}, while "
                f"{segment_key}={worst_segment.segment_value} sits at {worst_segment.adoption_rate * 100:.1f}% across "
                f"n={worst_segment.count}."
            )
        else:
            segment_content = "No segment attributes were available, so segment-level adoption remains at 0 analyzable groups."

        key_driver_lines = []
        if top_causal is not None:
            key_driver_lines.append(top_causal["statement"])
        for item in importances[1:3]:
            key_driver_lines.append(
                f"{item['variable_name']} carries SHAP {item['shap_mean_abs']:.3f} with a {item['direction']} coefficient of "
                f"{item['coefficient']:.3f}."
            )
        if not key_driver_lines:
            key_driver_lines.append(
                "No numeric predictors were available, so variable importance remains at 0 ranked drivers."
            )

        if counterfactual.get("available") is False:
            counterfactual_content = "Counterfactual analysis requires a linked population, so the current lift estimate is 0.0."
        elif counterfactual:
            counterfactual_content = (
                f"{counterfactual['counterfactual_name']} moves adoption from "
                f"{counterfactual['baseline_adoption_rate'] * 100:.1f}% to "
                f"{counterfactual['counterfactual_adoption_rate'] * 100:.1f}%, a lift of "
                f"{counterfactual['absolute_lift'] * 100:.1f} points."
            )
        else:
            counterfactual_content = (
                "No counterfactual evidence was gathered, so the modeled lift remains at 0.0."
            )

        recommendation_lines = []
        if top_importance is not None:
            recommendation_lines.append(
                f"1. Build messaging around {top_importance['variable_name']} because its SHAP signal is "
                f"{top_importance['shap_mean_abs']:.3f}."
            )
        if top_barrier is not None:
            recommendation_lines.append(
                f"2. Reduce {top_barrier['barrier']} at the {top_barrier['stage']} stage, where "
                f"{top_barrier['count']} personas currently stall."
            )
        if counterfactual and counterfactual.get("available") is not False:
            recommendation_lines.append(
                f"3. Prioritize the {counterfactual['counterfactual_name']} counterfactual because it adds "
                f"{counterfactual['absolute_lift'] * 100:.1f} adoption points."
            )
        if not recommendation_lines:
            recommendation_lines.append(
                "1. Gather richer persona-level numeric fields before making recommendations."
            )

        sections = [
            ReportSection(
                title="Executive Summary",
                content="\n".join(executive_lines),
                supporting_data={"adoption_rate": adoption_rate, "persona_count": total},
            ),
            ReportSection(
                title="Funnel Analysis",
                content=funnel_content,
                supporting_data={"barriers": barriers[:3]},
            ),
            ReportSection(
                title="Segment Deep Dive",
                content=segment_content,
                supporting_data={
                    "segments": [
                        segment.model_dump(mode="json") for segment in segment_analysis[:3]
                    ]
                },
            ),
            ReportSection(
                title="Key Drivers",
                content="\n".join(key_driver_lines),
                supporting_data={
                    "importances": importances[:3],
                    "causal_statements": causal_statements[:3],
                },
            ),
            ReportSection(
                title="Counterfactual Insights",
                content=counterfactual_content,
                supporting_data=counterfactual,
            ),
            ReportSection(
                title="Recommendations",
                content="\n".join(recommendation_lines),
                supporting_data={"top_importance": top_importance, "top_barrier": top_barrier},
            ),
        ]

        return sections[:REPORT_MIN_SECTIONS]

    def _build_raw_markdown(self, sections: list[ReportSection]) -> str:
        blocks = [f"# {self._scenario_name}"]
        for section in sections:
            blocks.append(f"## {section.title}\n{section.content}")
        return "\n\n".join(blocks)

    async def generate_report(
        self,
        scenario_id: str,
        results: dict[str, dict[str, Any]],
        population: Population | None = None,
    ) -> ReportOutput:
        """Generate a comprehensive analysis report for a scenario."""

        scenario = get_scenario(scenario_id)
        self._scenario_id = scenario_id
        self._scenario_name = scenario.name
        self._population = population
        self._working_results = self._merge_results_with_population(results, population)

        evidence: dict[str, dict[str, Any]] = {}
        tool_calls = 0
        plan = self._plan_tool_sequence()

        for iteration, (tool_name, tool_args) in enumerate(plan, start=1):
            if iteration > self.max_iterations or tool_calls >= REPORT_MAX_TOOL_CALLS:
                break
            await self._maybe_reason_about_next_tool(iteration, tool_name, tool_args)
            logger.info(
                "report_agent_iteration",
                scenario_id=scenario_id,
                iteration=iteration,
                tool_name=tool_name,
                tool_args=tool_args,
            )
            evidence[tool_name] = await self._execute_tool(tool_name, **tool_args)
            tool_calls += 1

        sections = self._build_sections(evidence)
        raw_markdown = self._build_raw_markdown(sections)
        report = ReportOutput(
            scenario_id=scenario_id,
            scenario_name=scenario.name,
            sections=sections,
            tool_calls_made=tool_calls,
            raw_markdown=raw_markdown,
        )

        grounding_warnings = validate_report_grounding(
            report,
            list(_rows_from_results(self._working_results)[0].keys())
            if self._working_results
            else [],
        )
        if grounding_warnings:
            logger.info(
                "report_grounding_warnings",
                scenario_id=scenario_id,
                warnings=grounding_warnings,
            )

        return report
