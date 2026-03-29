"""Calibration diagnostic for event-engine behavioural realism.

Run with:
    .venv/bin/python scripts/calibrate_event_params.py
"""

from __future__ import annotations

from dataclasses import dataclass

from src.analysis.trajectory_clustering import cluster_trajectories
from src.decision.scenarios import get_scenario
from src.generation.population import PopulationGenerator
from src.simulation.event_engine import EventSimulationResult, run_event_simulation
from src.simulation.temporal import MonthState, PersonaTrajectory


@dataclass(frozen=True)
class MetricCheck:
    name: str
    value: float
    low: float
    high: float
    units: str = ""

    @property
    def passed(self) -> bool:
        return self.low <= self.value <= self.high

    def render(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        suffix = self.units if self.units else ""
        return (
            f"[{status}] {self.name}: {self.value:.2f}{suffix} "
            f"(target {self.low:.2f}-{self.high:.2f}{suffix})"
        )


def _to_monthly_trajectories(result: EventSimulationResult) -> list[PersonaTrajectory]:
    out: list[PersonaTrajectory] = []
    for trajectory in result.trajectories:
        monthly_states: list[MonthState] = []
        months = result.duration_days // 30
        for month in range(1, months + 1):
            start_day = (month - 1) * 30 + 1
            end_day = month * 30
            end_snap = trajectory.days[end_day - 1]
            month_snaps = trajectory.days[start_day - 1 : end_day]
            monthly_states.append(
                MonthState(
                    month=month,
                    is_active=end_snap.is_active,
                    satisfaction=end_snap.state.get("perceived_value", 0.0),
                    consecutive_months=round(end_snap.state.get("habit_strength", 0.0) * 10),
                    has_lj_pass=end_snap.has_lj_pass,
                    churned_this_month=any(
                        snap.decision in {"churn", "switch"} for snap in month_snaps
                    ),
                    adopted_this_month=any(
                        snap.decision in {"purchase", "reorder", "subscribe"}
                        for snap in month_snaps
                    ),
                )
            )
        out.append(PersonaTrajectory(persona_id=trajectory.persona_id, monthly_states=monthly_states))
    return out


def _print_suggestions(checks: list[MetricCheck], populated_clusters: int, churn_peak_month: int) -> None:
    print("\nSuggestions")
    print("-----------")
    if not checks[0].passed:
        print("- Trial is low/high: tune awareness decay or ad exposure intensity.")
    if not checks[1].passed:
        print("- Repeat rate is off: tune habit boost and fatigue growth rates.")
    if not checks[2].passed:
        print("- Month-12 active rate is off: adjust churn/switch thresholds.")
    if not checks[3].passed:
        print("- Purchases per adopter are off: tune pack duration or reorder urgency ramp.")
    if populated_clusters < 4:
        print("- Behaviour diversity is low: increase event heterogeneity.")
    if churn_peak_month < 3 or churn_peak_month > 5:
        print("- Churn timing is unrealistic: slow early fatigue or raise early trust.")
    if not checks[4].passed:
        print("- Revenue per adopter is off: tune price point or repeat dynamics.")


def main() -> None:
    population = PopulationGenerator().generate(size=200, seed=42, deep_persona_count=30)
    scenario = get_scenario("nutrimix_2_6")
    result = run_event_simulation(population, scenario, duration_days=360, seed=42)

    month3 = result.aggregate_monthly[min(2, len(result.aggregate_monthly) - 1)]
    adopters_month3 = int(month3["cumulative_adopters"])
    trial_rate_month3 = adopters_month3 / len(population.personas)

    adopters = [trajectory for trajectory in result.trajectories if trajectory.first_purchase_day]
    adopter_count = len(adopters)
    repeaters = [trajectory for trajectory in adopters if trajectory.total_purchases >= 2]
    repeat_rate = (len(repeaters) / adopter_count) if adopter_count else 0.0
    mean_purchases_per_adopter = (
        sum(trajectory.total_purchases for trajectory in adopters) / adopter_count
        if adopter_count
        else 0.0
    )
    revenue_per_adopter = (result.total_revenue_estimate / adopter_count) if adopter_count else 0.0

    peak_churn = max(
        result.aggregate_monthly,
        key=lambda row: int(row.get("churned", 0)),
    )
    churn_peak_month = int(peak_churn["month"])

    trajectories = _to_monthly_trajectories(result)
    clusters = cluster_trajectories(trajectories, population).clusters
    populated_clusters = sum(1 for cluster in clusters if cluster.size > 0)

    checks = [
        MetricCheck("Trial rate by month 3", trial_rate_month3, 0.15, 0.30),
        MetricCheck("Repeat rate of adopters", repeat_rate, 0.40, 0.60),
        MetricCheck("Month-12 active rate", result.final_active_rate, 0.10, 0.20),
        MetricCheck("Mean purchases per adopter", mean_purchases_per_adopter, 3.0, 6.0),
        MetricCheck("Revenue per adopter (INR)", revenue_per_adopter, 2000.0, 4000.0),
    ]

    print("Event Engine Calibration Report")
    print("===============================")
    for check in checks:
        print(check.render())

    cluster_status = "PASS" if populated_clusters >= 4 else "FAIL"
    churn_status = "PASS" if 3 <= churn_peak_month <= 5 else "FAIL"
    print(
        f"[{cluster_status}] Behaviour clusters populated: {populated_clusters} "
        "(target >= 4)"
    )
    print(
        f"[{churn_status}] Churn peak month: {churn_peak_month} "
        "(target month 3-5)"
    )

    _print_suggestions(checks, populated_clusters, churn_peak_month)


if __name__ == "__main__":
    main()
