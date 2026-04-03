"""
runner.py — Runs intervention simulations against the persona population.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

from src.simulation.journey_config import JourneyConfig, StimulusConfig

if TYPE_CHECKING:
    from src.interventions.proposer import InterventionProposal
    from src.taxonomy.schema import Persona

logger = logging.getLogger(__name__)

# ── Data model ─────────────────────────────────────────────────────────────────


@dataclass
class InterventionRun:
    intervention_id: str
    intervention_title: str
    status: str                       # "queued" | "running" | "complete" | "failed"
    started_at: str | None
    completed_at: str | None
    baseline_metric: float | None
    intervention_metric: float | None
    lift_pct: float | None
    personas_run: int
    result_dict: dict[str, Any] | None
    error: str | None = None


# ── Helpers ────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _extract_primary_metric(batch_result: Any) -> float:
    """
    Extract buy+trial rate for the first decision from a BatchResult.

    Looks at aggregate.first_decision_distribution and sums the counts
    for any decision label in {buy, trial, reorder}.
    """
    _PURCHASE_LABELS = {"buy", "trial", "reorder"}

    try:
        dist: dict = batch_result.aggregate.first_decision_distribution
        total = batch_result.aggregate.total_personas - batch_result.aggregate.errors
        if total <= 0:
            return 0.0
        purchase_count = sum(
            v.get("count", 0)
            for label, v in dist.items()
            if label.lower() in _PURCHASE_LABELS
        )
        return round(purchase_count / total, 4)
    except Exception as exc:
        logger.warning("Could not extract primary metric: %s", exc)
        return 0.0


# ── Core functions ─────────────────────────────────────────────────────────────


def apply_intervention(
    base_config: JourneyConfig,
    modifications: dict[str, Any],
) -> JourneyConfig:
    """
    Return a modified copy of base_config with the given modifications applied.

    Recognised keys:
      - ``price_inr``: update all decision price_inr values.
      - ``add_stimuli``: list of dicts → appended as StimulusConfig objects,
        re-sorted by tick.
      - ``marketing.*`` flat keys: logged as warning, not applied directly
        (JourneyConfig has no marketing sub-model).
    """
    # Pydantic deep-copy via model serialisation (avoids shared mutable state)
    updated = base_config.model_copy(deep=True)

    new_decisions = list(updated.decisions)
    new_stimuli = list(updated.stimuli)

    for key, value in modifications.items():
        if key == "price_inr":
            price = float(value)
            new_decisions = [d.model_copy(update={"price_inr": price}) for d in new_decisions]

        elif key == "add_stimuli":
            existing_ids = {s.id for s in new_stimuli}
            for i, raw in enumerate(value):
                raw = dict(raw)  # copy so we don't mutate caller's data
                # Auto-generate a deterministic id if not supplied
                s_id = raw.pop("id", None) or f"iv-stim-{i:02d}-t{raw.get('tick', 0)}"
                # Avoid duplicate ids
                if s_id in existing_ids:
                    s_id = f"{s_id}-x"
                existing_ids.add(s_id)
                new_stimuli.append(
                    StimulusConfig(
                        id=s_id,
                        tick=int(raw.get("tick", 1)),
                        type=str(raw.get("type", "social_event")),
                        source=str(raw.get("source", "intervention")),
                        content=str(raw.get("content", "")),
                        brand=str(raw.get("brand", "")),
                    )
                )
            # Re-sort by tick after appending
            new_stimuli.sort(key=lambda s: s.tick)

        elif key.startswith("marketing."):
            logger.warning(
                "apply_intervention: key '%s' not applied — JourneyConfig has no "
                "marketing sub-model. Ignoring.",
                key,
            )

        else:
            logger.warning(
                "apply_intervention: unrecognised modification key '%s'. Ignoring.",
                key,
            )

    return updated.model_copy(
        update={"decisions": new_decisions, "stimuli": new_stimuli}
    )


def run_intervention(
    proposal: InterventionProposal,
    base_config: JourneyConfig,
    personas: list[tuple[str, Persona]],
    baseline_metric: float,
    progress_callback: Callable[[int, int, dict], None] | None = None,
) -> InterventionRun:
    """
    Apply modifications, run the full persona batch, and return an InterventionRun.
    """
    from src.simulation.batch_runner import run_batch

    run = InterventionRun(
        intervention_id=proposal.id,
        intervention_title=proposal.title,
        status="running",
        started_at=_now_iso(),
        completed_at=None,
        baseline_metric=baseline_metric,
        intervention_metric=None,
        lift_pct=None,
        personas_run=len(personas),
        result_dict=None,
        error=None,
    )

    try:
        intervention_config = apply_intervention(base_config, proposal.journey_modifications)

        batch_result = run_batch(
            journey_config=intervention_config,
            personas=personas,
            concurrency=3,
            progress_callback=progress_callback,
        )

        intervention_metric = _extract_primary_metric(batch_result)
        lift_pct = (
            (intervention_metric - baseline_metric) / max(baseline_metric, 0.01)
        ) * 100.0

        run.intervention_metric = round(intervention_metric, 4)
        run.lift_pct = round(lift_pct, 2)
        run.personas_run = batch_result.personas_run
        run.result_dict = batch_result.to_dict()
        run.status = "complete"
        run.completed_at = _now_iso()

    except Exception as exc:
        logger.exception("run_intervention failed for '%s': %s", proposal.id, exc)
        run.status = "failed"
        run.error = str(exc)
        run.completed_at = _now_iso()

    return run


def run_intervention_queue(
    proposals: list[InterventionProposal],
    base_config: JourneyConfig,
    personas: list[tuple[str, Persona]],
    baseline_metric: float,
    on_run_complete: Callable[[InterventionRun], None] | None = None,
) -> list[InterventionRun]:
    """
    Run proposals sequentially (not parallel — avoids LLM rate limits).

    Calls on_run_complete after each run regardless of success/failure.
    Returns all InterventionRun objects.
    """
    results: list[InterventionRun] = []

    for proposal in proposals:
        run = run_intervention(
            proposal=proposal,
            base_config=base_config,
            personas=personas,
            baseline_metric=baseline_metric,
        )
        results.append(run)
        if on_run_complete is not None:
            try:
                on_run_complete(run)
            except Exception as cb_exc:
                logger.warning(
                    "on_run_complete callback raised for '%s': %s",
                    proposal.id,
                    cb_exc,
                )

    return results
