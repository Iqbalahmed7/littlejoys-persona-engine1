"""Simulation-based cohort classification for research decomposition."""

from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from src.decision.calibration import evaluate_scenario_adoption
from src.simulation.event_engine import run_event_simulation

if TYPE_CHECKING:
    from src.decision.scenarios import ScenarioConfig
    from src.generation.population import Population


class CohortClassification(BaseModel):
    """One persona's final cohort assignment with rationale."""

    model_config = ConfigDict(extra="forbid")

    persona_id: str
    cohort_id: str
    cohort_name: str
    classification_reason: str


class PopulationCohorts(BaseModel):
    """Cohort assignment output for a full population."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    cohorts: dict[str, list[str]]
    classifications: list[CohortClassification] = Field(default_factory=list)
    summary: dict[str, int]


_COHORT_NAMES = {
    "never_aware": "Never Aware",
    "aware_not_tried": "Aware But Not Tried",
    "first_time_buyer": "First-Time Buyer",
    "current_user": "Current User",
    "lapsed_user": "Lapsed User",
}


def _static_reject_cohort(rejection_stage: str | None) -> str:
    if rejection_stage in {"need_recognition", "awareness"}:
        return "never_aware"
    return "aware_not_tried"


def _static_reason(rejection_stage: str | None, rejection_reason: str | None) -> str:
    if rejection_stage in {"need_recognition", "awareness"}:
        return "Never passed awareness stage - brand salience too low"
    hint = (rejection_reason or "insufficient conversion signals").replace("_", " ")
    return f"Aware but did not purchase - blocked at {rejection_stage or 'purchase'} ({hint})"


def _dominant_churn_signal(rationale: dict[str, float] | None) -> str | None:
    if not rationale:
        return None
    signal = max(rationale.items(), key=lambda item: item[1])[0]
    if signal == "child_acceptance":
        return "child_acceptance < 0.2"
    if signal == "fatigue":
        return "fatigue > 0.7"
    if signal == "trust":
        return "trust < 0.3"
    return signal


def classify_population(
    population: Population,
    scenario: ScenarioConfig,
    seed: int = 42,
) -> PopulationCohorts:
    """Run baseline simulations and classify personas into research cohorts."""

    cohorts: dict[str, list[str]] = {
        "never_aware": [],
        "aware_not_tried": [],
        "first_time_buyer": [],
        "current_user": [],
        "lapsed_user": [],
    }
    classifications: list[CohortClassification] = []

    static_result = evaluate_scenario_adoption(population=population, scenario=scenario, seed=seed)
    adopted_ids: list[str] = []

    for persona_id, result in static_result.results_by_persona.items():
        if result.get("outcome") == "adopt":
            adopted_ids.append(persona_id)
            continue

        stage = result.get("rejection_stage")
        reject_reason = result.get("rejection_reason")
        cohort_id = _static_reject_cohort(stage)
        cohorts[cohort_id].append(persona_id)
        population.get_persona(persona_id).product_relationship = cohort_id
        classifications.append(
            CohortClassification(
                persona_id=persona_id,
                cohort_id=cohort_id,
                cohort_name=_COHORT_NAMES[cohort_id],
                classification_reason=_static_reason(stage, reject_reason),
            )
        )

    if adopted_ids:
        adopter_population = population.model_copy(
            update={"tier1_personas": [population.get_persona(pid) for pid in adopted_ids]},
            deep=True,
        )
        duration_days = max(1, int(scenario.months) * 30)
        event_result = run_event_simulation(
            population=adopter_population,
            scenario=scenario,
            duration_days=duration_days,
            seed=seed,
        )

        for trajectory in event_result.trajectories:
            final_snapshot = trajectory.days[-1] if trajectory.days else None
            if final_snapshot and final_snapshot.is_active:
                cohort_id = "current_user"
                cohorts[cohort_id].append(trajectory.persona_id)
                population.get_persona(trajectory.persona_id).product_relationship = cohort_id
                classifications.append(
                    CohortClassification(
                        persona_id=trajectory.persona_id,
                        cohort_id=cohort_id,
                        cohort_name=_COHORT_NAMES[cohort_id],
                        classification_reason="Adopted in month 1 and remained active through final month",
                    )
                )
                continue

            # Use total_purchases to distinguish a one-time buyer from someone
            # who repeated at least once and then lapsed.
            # first_time_buyer = exactly 1 purchase (tried once, never came back)
            # lapsed_user      = 2+ purchases (was a repeat buyer) but no longer active
            total_purchases = trajectory.total_purchases or 1
            cohort_id = "first_time_buyer" if total_purchases <= 1 else "lapsed_user"
            cohorts[cohort_id].append(trajectory.persona_id)
            population.get_persona(trajectory.persona_id).product_relationship = cohort_id

            churn_day = trajectory.churned_day or duration_days
            churn_month = max(1, ceil(churn_day / 30))
            churn_snapshot = trajectory.days[churn_day - 1] if trajectory.days else None
            driver = _dominant_churn_signal(
                churn_snapshot.decision_rationale if churn_snapshot else None
            )
            purchase_label = f"{total_purchases} purchase{'s' if total_purchases != 1 else ''}"
            if driver:
                reason = (
                    f"{'One-time buyer' if cohort_id == 'first_time_buyer' else 'Repeat buyer'} "
                    f"({purchase_label}), churned in month {churn_month} due to {driver}"
                )
            else:
                reason = (
                    f"{'One-time buyer' if cohort_id == 'first_time_buyer' else 'Repeat buyer'} "
                    f"({purchase_label}), churned in month {churn_month}"
                )
            classifications.append(
                CohortClassification(
                    persona_id=trajectory.persona_id,
                    cohort_id=cohort_id,
                    cohort_name=_COHORT_NAMES[cohort_id],
                    classification_reason=reason,
                )
            )

    summary = {cohort_id: len(persona_ids) for cohort_id, persona_ids in cohorts.items()}
    return PopulationCohorts(
        scenario_id=scenario.id,
        cohorts=cohorts,
        classifications=classifications,
        summary=summary,
    )
