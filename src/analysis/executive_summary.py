"""LLM-generated executive narrative for consolidated research reports."""

from __future__ import annotations

import asyncio
import json
import threading
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from src.analysis.research_consolidator import ConsolidatedReport
    from src.decision.scenarios import ScenarioConfig
    from src.utils.llm import LLMClient

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
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if errors:
        raise errors[0]
    return result[0]


class ExecutiveSummary(BaseModel):
    """LLM-generated narrative summary of simulation results."""

    model_config = ConfigDict(extra="forbid")

    headline: str
    trajectory_summary: str
    key_drivers: list[str]
    recommendations: list[str]
    risk_factors: list[str]
    raw_llm_response: str
    mock_mode: bool


class _ExecutiveSummaryJSON(BaseModel):
    """JSON payload from the model (subset of ExecutiveSummary)."""

    model_config = ConfigDict(extra="ignore")

    headline: str
    trajectory_summary: str
    key_drivers: list[str]
    recommendations: list[str]
    risk_factors: list[str]


def _format_monthly_rows(report: ConsolidatedReport) -> str:
    rows = report.event_monthly_rollup or report.temporal_snapshots
    if not rows:
        return "(no monthly trajectory available)"
    lines: list[str] = []
    for row in rows[:14]:
        m = row.get("month")
        active = row.get("total_active", row.get("active"))
        lines.append(f"Month {m}: total_active={active}")
    return "\n".join(lines)


def _format_clusters(report: ConsolidatedReport) -> str:
    clusters = report.event_clusters or report.behaviour_clusters or []
    if not clusters:
        return "(no cluster breakdown)"
    parts = []
    for c in clusters[:6]:
        parts.append(
            f"- {c.get('cluster_name')}: n={c.get('size')} ({float(c.get('pct', 0)):.0%} of sample)"
        )
    return "\n".join(parts)


def _format_decision_drivers(report: ConsolidatedReport) -> str:
    dr = report.decision_rationale_summary or []
    if not dr:
        return "(no decision-driver aggregates)"
    ordered = sorted(dr, key=lambda x: float(x.get("fraction", 0)), reverse=True)[:6]
    lines = [
        f"- {x.get('variable')}: {float(x.get('fraction', 0)):.0%} of churn/switch decisions"
        for x in ordered
    ]
    return "\n".join(lines)


def _top_counterfactual_line(report: ConsolidatedReport) -> str:
    cf = report.counterfactual_results or []
    if len(cf) == 0:
        return "(no counterfactual analysis)"
    best = max(cf, key=lambda r: r.lift_pct if r.lift_pct is not None else 0.0)
    label = best.label or best.counterfactual_name
    pct = best.lift_pct if best.lift_pct is not None else 0.0
    return f"Top intervention: {label} ({pct:+.1f}% vs baseline active rate)"


def _build_user_prompt(report: ConsolidatedReport, scenario: ScenarioConfig) -> str:
    return f"""You are a senior product strategist writing for a PM audience.

Scenario: {scenario.name} ({scenario.id})
Product: {scenario.product.name}, price ₹{scenario.product.price_inr}, age range {scenario.product.age_range}

Month-by-month active counts:
{_format_monthly_rows(report)}

Behavioural / trajectory clusters:
{_format_clusters(report)}

Top decision drivers (event model, if present):
{_format_decision_drivers(report)}

{_top_counterfactual_line(report)}

Funnel trial rate: {report.funnel.adoption_rate:.1%}
Month-12 / final active rate (if available): {report.month_12_active_rate}

Respond with JSON only (no markdown), using this exact schema:
{{
  "headline": "<one sentence>",
  "trajectory_summary": "<2-3 sentences>",
  "key_drivers": ["<3 short strings>"],
  "recommendations": ["<3 actionable strings>"],
  "risk_factors": ["<2 risk strings>"]
}}

Rules:
- key_drivers must have exactly 3 items; recommendations exactly 3; risk_factors exactly 2.
- Be specific to this scenario; avoid generic filler."""


def generate_executive_summary(
    report: ConsolidatedReport,
    scenario: ScenarioConfig,
    llm_client: LLMClient | None = None,
    mock_mode: bool = False,
) -> ExecutiveSummary:
    """Produce a PM-ready narrative; mock_mode returns fixtures without calling the API."""

    if mock_mode:
        return ExecutiveSummary(
            headline=(
                f"{scenario.product.name}: retention hinges on taste and repeat-use friction"
            ),
            trajectory_summary=(
                "Over the simulated year, active households ramp through trial and early "
                "repurchase, then plateau as churn and switching pressures build."
            ),
            key_drivers=[
                "Price vs. perceived value for the target age band awareness and trust signals",
                "Household routine fit (effort to prepare and remind children)",
                "Competitive alternatives and proof points (pediatrician / school / social proof)",
            ],
            recommendations=[
                'Run a timed price-value test with a clear "per-day" cost anchor.',
                "Bundle onboarding that reduces effort in the first 30 days post-trial.",
                "Target high-trust channels tied to the dominant barriers surfaced in interviews.",
            ],
            risk_factors=[
                "If awareness stays flat, the funnel never reaches scale despite a strong product.",
                "If churn drivers from the event model are unaddressed, LTV stays below acquisition cost.",
            ],
            raw_llm_response="[mock executive summary - LLM not invoked]",
            mock_mode=True,
        )

    if llm_client is None:
        raise ValueError("llm_client is required when mock_mode is False")

    from src.utils.llm import LLMClient as _LLMClient

    if not isinstance(llm_client, _LLMClient):
        raise TypeError("llm_client must be an LLMClient instance")

    system = (
        "You output only valid JSON objects. No prose outside JSON. "
        "Follow the user's field counts exactly."
    )
    prompt = _build_user_prompt(report, scenario)

    response = _run_async(
        llm_client.generate(
            prompt=prompt,
            system=system,
            model="bulk",
            response_format="json",
            temperature=0.4,
            max_tokens=900,
            schema=_ExecutiveSummaryJSON,
        )
    )

    payload = _ExecutiveSummaryJSON.model_validate(json.loads(response.text))
    return ExecutiveSummary(
        headline=payload.headline,
        trajectory_summary=payload.trajectory_summary,
        key_drivers=list(payload.key_drivers)[:3],
        recommendations=list(payload.recommendations)[:3],
        risk_factors=list(payload.risk_factors)[:2],
        raw_llm_response=response.text,
        mock_mode=False,
    )
