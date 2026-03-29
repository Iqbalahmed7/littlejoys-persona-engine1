"""Heuristic behavioural clustering over temporal persona trajectories."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from src.generation.population import Population
    from src.simulation.temporal import PersonaTrajectory


class BehaviourCluster(BaseModel):
    """One behaviour cluster distilled from trajectory patterns."""

    model_config = ConfigDict(extra="forbid")

    cluster_name: str
    persona_ids: list[str]
    size: int
    pct: float
    avg_lifetime_months: float
    avg_satisfaction: float
    dominant_attributes: dict[str, float]


class TrajectoryClusterResult(BaseModel):
    """Cluster set for a full simulated population."""

    model_config = ConfigDict(extra="forbid")

    clusters: list[BehaviourCluster]
    population_size: int


def _satisfaction_slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return (values[-1] - values[0]) / (len(values) - 1)


def _dominant_attributes(
    population: Population,
    persona_ids: list[str],
) -> dict[str, float]:
    if not persona_ids:
        return {}

    cluster_rows = [population.get_persona(pid).to_flat_dict() for pid in persona_ids]
    global_rows = [persona.to_flat_dict() for persona in population.personas]

    global_means: dict[str, float] = {}
    for key in global_rows[0]:
        vals = [
            float(row[key])
            for row in global_rows
            if isinstance(row.get(key), (int, float)) and not isinstance(row.get(key), bool)
        ]
        if vals:
            global_means[key] = sum(vals) / len(vals)

    cluster_means: dict[str, float] = {}
    for key in cluster_rows[0]:
        vals = [
            float(row[key])
            for row in cluster_rows
            if isinstance(row.get(key), (int, float)) and not isinstance(row.get(key), bool)
        ]
        if vals:
            cluster_means[key] = sum(vals) / len(vals)

    ranked = sorted(
        (
            (key, cluster_means[key], abs(cluster_means[key] - global_means.get(key, 0.0)))
            for key in cluster_means
        ),
        key=lambda item: item[2],
        reverse=True,
    )
    return {key: round(mean, 3) for key, mean, _ in ranked[:5]}


def cluster_trajectories(
    trajectories: list[PersonaTrajectory],
    population: Population,
) -> TrajectoryClusterResult:
    """Cluster personas into behavioural groups using deterministic heuristic rules."""

    groups: dict[str, list[PersonaTrajectory]] = defaultdict(list)

    for trajectory in trajectories:
        states = trajectory.monthly_states
        adopted_month = next((s.month for s in states if s.adopted_this_month), None)
        churn_month = next((s.month for s in states if s.churned_this_month), None)
        ever_adopted = adopted_month is not None
        active_months = sum(1 for s in states if s.is_active)
        max_consecutive = max((s.consecutive_months for s in states), default=0)
        sat_values = [s.satisfaction for s in states if s.satisfaction > 0]
        sat_avg = sum(sat_values) / len(sat_values) if sat_values else 0.0
        sat_slope = _satisfaction_slope(sat_values)
        active_end = states[-1].is_active if states else False

        budget = float(population.get_persona(trajectory.persona_id).to_flat_dict().get("budget_consciousness", 0.5))

        if not ever_adopted:
            label = "Never Reached"
        elif adopted_month is not None and adopted_month <= 2 and churn_month is None and sat_avg >= 0.55:
            label = "Loyal Repeaters"
        elif adopted_month is not None and adopted_month >= 3:
            label = "Late Adopters"
        elif churn_month is not None and churn_month <= 4 and sat_slope < -0.03:
            label = "Taste-Fatigued Droppers"
        elif churn_month is not None and budget >= 0.7:
            label = "Price-Triggered Switchers"
        elif max_consecutive <= 2 or (not active_end and active_months <= 2):
            label = "Forgot-to-Reorder"
        else:
            label = "Loyal Repeaters"

        groups[label].append(trajectory)

    total = len(trajectories)
    clusters: list[BehaviourCluster] = []
    for name, members in groups.items():
        persona_ids = [member.persona_id for member in members]
        lifetimes = [sum(1 for s in member.monthly_states if s.is_active) for member in members]
        sat_means = []
        for member in members:
            vals = [s.satisfaction for s in member.monthly_states if s.satisfaction > 0]
            sat_means.append(sum(vals) / len(vals) if vals else 0.0)

        clusters.append(
            BehaviourCluster(
                cluster_name=name,
                persona_ids=persona_ids,
                size=len(persona_ids),
                pct=(len(persona_ids) / total) if total else 0.0,
                avg_lifetime_months=(sum(lifetimes) / len(lifetimes)) if lifetimes else 0.0,
                avg_satisfaction=(sum(sat_means) / len(sat_means)) if sat_means else 0.0,
                dominant_attributes=_dominant_attributes(population, persona_ids),
            )
        )

    clusters.sort(key=lambda c: (-c.size, c.cluster_name))
    return TrajectoryClusterResult(clusters=clusters, population_size=total)
