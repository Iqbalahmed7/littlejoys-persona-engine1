from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.simulation.tick_engine import TickJourneyLog


@dataclass
class JourneyAggregate:
    """Summary statistics across all persona journeys for one journey type."""

    journey_id: str
    total_personas: int
    errors: int

    # First decision (tick 20 for Journey A, tick 35 for Journey B)
    first_decision_distribution: dict[str, dict]
    first_decision_drivers: dict[str, int]
    first_decision_objections: dict[str, int]

    # Second decision (tick 60 for all journeys A, B, C)
    second_decision_distribution: dict[str, dict]
    second_decision_drivers: dict[str, int]
    second_decision_objections: dict[str, int]

    # Reorder / continuation rate
    reorder_rate_pct: float
    avg_trust_at_first_decision: float
    avg_trust_at_second_decision: float

    # Trust trajectory
    trust_by_tick: dict[int, float]

    def to_dict(self) -> dict:
        return {
            "journey_id": self.journey_id,
            "total_personas": self.total_personas,
            "errors": self.errors,
            "first_decision_distribution": self.first_decision_distribution,
            "first_decision_drivers": self.first_decision_drivers,
            "first_decision_objections": self.first_decision_objections,
            "second_decision_distribution": self.second_decision_distribution,
            "second_decision_drivers": self.second_decision_drivers,
            "second_decision_objections": self.second_decision_objections,
            "reorder_rate_pct": self.reorder_rate_pct,
            "avg_trust_at_first_decision": self.avg_trust_at_first_decision,
            "avg_trust_at_second_decision": self.avg_trust_at_second_decision,
            "trust_by_tick": self.trust_by_tick,
        }


_PURCHASE_DECISIONS = {"buy", "trial", "reorder"}


def _as_dict(log: TickJourneyLog | dict[str, Any]) -> dict[str, Any]:
    if isinstance(log, dict):
        return log
    if hasattr(log, "to_dict"):
        try:
            payload = log.to_dict()
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
    if hasattr(log, "model_dump"):
        try:
            payload = log.model_dump()
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
    return dict(getattr(log, "__dict__", {}))


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        try:
            payload = value.to_dict()
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
    if hasattr(value, "model_dump"):
        try:
            payload = value.model_dump()
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
    return dict(getattr(value, "__dict__", {}))


def _extract_decision(payload: dict[str, Any], decision_number: int) -> dict[str, Any]:
    if decision_number == 1:
        candidates = [
            "first_decision",
            "tick20_decision",
            "tick28_decision",
            "tick35_decision",
            "decision_tick_20",
            "decision_tick_28",
            "decision_tick_35",
        ]
        snapshot_ticks = {20, 28, 35}
    else:
        candidates = [
            "second_decision",
            "final_decision",   # TickJourneyLog stores last decision here (tick 60 for all journeys)
            "tick60_decision",
            "decision_tick_60",
        ]
        snapshot_ticks = {60}

    # NOTE: "final_decision" in the TickJourneyLog is always the LAST decision
    # made (e.g. tick 60), so it must NOT be used as a fallback for the first
    # decision. The snapshot scan below handles the correct tick lookup.

    for key in candidates:
        if key in payload:
            return _to_dict(payload.get(key))

    # Fallback: scan snapshots for a decision_result at the expected tick
    for snap in payload.get("snapshots", []):
        if snap.get("tick") in snapshot_ticks and snap.get("decision_result"):
            dr = snap["decision_result"]
            if isinstance(dr, dict) and "error" not in dr:
                return dr

    # Final fallback: pick the first decision-bearing snapshot
    all_decision_snaps = [
        s for s in payload.get("snapshots", [])
        if s.get("decision_result") and isinstance(s.get("decision_result"), dict)
        and "error" not in s["decision_result"]
    ]
    all_decision_snaps.sort(key=lambda s: s.get("tick", 0))
    if all_decision_snaps:
        idx = 0 if decision_number == 1 else -1
        if len(all_decision_snaps) > idx or decision_number == 2:
            try:
                return all_decision_snaps[idx if decision_number == 2 else 0]["decision_result"]
            except IndexError:
                pass

    return {}


def _decision_label(decision_payload: dict[str, Any]) -> str:
    return str(
        decision_payload.get("decision")
        or decision_payload.get("outcome")
        or decision_payload.get("action")
        or "unknown"
    )


def _decision_drivers(decision_payload: dict[str, Any]) -> list[str]:
    values = decision_payload.get("key_drivers") or decision_payload.get("drivers") or []
    if not isinstance(values, list):
        return []
    return [str(v) for v in values if str(v).strip()]


def _decision_objections(decision_payload: dict[str, Any]) -> list[str]:
    values = decision_payload.get("objections") or []
    if not isinstance(values, list):
        return []
    return [str(v) for v in values if str(v).strip()]


def _decision_trust(
    payload: dict[str, Any],
    decision_payload: dict[str, Any],
    tick: int,
) -> float | None:
    if "trust_level" in decision_payload:
        try:
            return float(decision_payload["trust_level"])
        except Exception:
            return None

    trust_by_tick = payload.get("trust_by_tick") or payload.get("brand_trust_by_tick") or {}
    if isinstance(trust_by_tick, dict):
        if tick in trust_by_tick:
            try:
                return float(trust_by_tick[tick])
            except Exception:
                return None
        if str(tick) in trust_by_tick:
            try:
                return float(trust_by_tick[str(tick)])
            except Exception:
                return None
    return None


def _journey_ticks(journey_id: str) -> tuple[int, int]:
    # All journeys now have their reorder decision at tick 60.
    # First-buy ticks: A=20, B=35, C=28
    first_tick = 35 if journey_id.upper() == "B" else (28 if journey_id.upper() == "C" else 20)
    return first_tick, 60


def _distribution(counter: Counter[str], denominator: int) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for key, count in counter.most_common():
        pct = (count / denominator * 100.0) if denominator else 0.0
        out[key] = {"count": count, "pct": round(pct, 1)}
    return out


def aggregate_journeys(logs: list[TickJourneyLog]) -> JourneyAggregate:
    """
    Compute summary statistics from a list of TickJourneyLog objects.

    Handles errors gracefully — skips logs with errors in the aggregate.
    """

    if not logs:
        return JourneyAggregate(
            journey_id="unknown",
            total_personas=0,
            errors=0,
            first_decision_distribution={},
            first_decision_drivers={},
            first_decision_objections={},
            second_decision_distribution={},
            second_decision_drivers={},
            second_decision_objections={},
            reorder_rate_pct=0.0,
            avg_trust_at_first_decision=0.0,
            avg_trust_at_second_decision=0.0,
            trust_by_tick={},
        )

    payloads = [_as_dict(log) for log in logs]
    journey_id = str(payloads[0].get("journey_id", "unknown"))
    first_tick, second_tick = _journey_ticks(journey_id)

    first_decisions: Counter[str] = Counter()
    second_decisions: Counter[str] = Counter()
    first_drivers: Counter[str] = Counter()
    first_objections: Counter[str] = Counter()
    second_drivers: Counter[str] = Counter()
    second_objections: Counter[str] = Counter()
    trust_points: dict[int, list[float]] = defaultdict(list)
    first_trust_values: list[float] = []
    second_trust_values: list[float] = []

    errors = 0
    valid_payloads: list[dict[str, Any]] = []
    for payload in payloads:
        if payload.get("error"):
            errors += 1
            continue
        valid_payloads.append(payload)

    reorderers, lapsers = segment_by_reorder(valid_payloads).values()
    total_first_buyers = len(reorderers) + len(lapsers)
    reorder_rate_pct = (len(reorderers) / total_first_buyers * 100.0) if total_first_buyers else 0.0

    for payload in valid_payloads:
        first_payload = _extract_decision(payload, 1)
        second_payload = _extract_decision(payload, 2)

        first_label = _decision_label(first_payload)
        second_label = _decision_label(second_payload)
        first_decisions[first_label] += 1
        second_decisions[second_label] += 1

        for d in _decision_drivers(first_payload):
            first_drivers[d] += 1
        for o in _decision_objections(first_payload):
            first_objections[o] += 1
        for d in _decision_drivers(second_payload):
            second_drivers[d] += 1
        for o in _decision_objections(second_payload):
            second_objections[o] += 1

        first_trust = _decision_trust(payload, first_payload, first_tick)
        second_trust = _decision_trust(payload, second_payload, second_tick)
        if first_trust is not None:
            first_trust_values.append(first_trust)
        if second_trust is not None:
            second_trust_values.append(second_trust)

        per_tick = payload.get("trust_by_tick") or payload.get("brand_trust_by_tick") or {}
        if isinstance(per_tick, dict):
            for tick_key, value in per_tick.items():
                try:
                    tick_int = int(tick_key)
                    trust_points[tick_int].append(float(value))
                except Exception:
                    continue

    trust_by_tick = {
        tick: round(sum(values) / len(values), 4)
        for tick, values in sorted(trust_points.items())
        if values
    }

    avg_first_trust = round(sum(first_trust_values) / len(first_trust_values), 4) if first_trust_values else 0.0
    avg_second_trust = round(sum(second_trust_values) / len(second_trust_values), 4) if second_trust_values else 0.0

    return JourneyAggregate(
        journey_id=journey_id,
        total_personas=len(payloads),
        errors=errors,
        first_decision_distribution=_distribution(first_decisions, len(valid_payloads)),
        first_decision_drivers=dict(first_drivers.most_common(10)),
        first_decision_objections=dict(first_objections.most_common(10)),
        second_decision_distribution=_distribution(second_decisions, len(valid_payloads)),
        second_decision_drivers=dict(second_drivers.most_common(10)),
        second_decision_objections=dict(second_objections.most_common(10)),
        reorder_rate_pct=round(reorder_rate_pct, 2),
        avg_trust_at_first_decision=avg_first_trust,
        avg_trust_at_second_decision=avg_second_trust,
        trust_by_tick=trust_by_tick,
    )


def find_conversion_tick(logs: list[TickJourneyLog]) -> dict:
    """
    For Journey B (Gummies): find which tick was the most common
    first-awareness-to-decision conversion point.

    Returns: {tick: count_of_first_purchase_decisions}
    """

    counts: Counter[int] = Counter()
    for log in logs:
        payload = _as_dict(log)
        if payload.get("error"):
            continue
        tick_value = payload.get("first_purchase_tick") or payload.get("conversion_tick")
        if tick_value is None:
            events = payload.get("decision_events") or payload.get("tick_logs") or []
            if isinstance(events, list):
                for event in events:
                    event_payload = _to_dict(event)
                    decision = str(event_payload.get("decision") or event_payload.get("outcome") or "")
                    if decision in _PURCHASE_DECISIONS:
                        tick_value = event_payload.get("tick")
                        break
        try:
            if tick_value is not None:
                counts[int(tick_value)] += 1
        except Exception:
            continue
    return dict(sorted(counts.items()))


def segment_by_reorder(logs: list[TickJourneyLog]) -> dict:
    """
    Split personas into reorderers vs lapsers.
    Return two lists of persona_ids for downstream analysis.

    Returns: {"reorderers": [...], "lapsers": [...]}
    """

    reorderers: list[str] = []
    lapsers: list[str] = []
    for log in logs:
        payload = _as_dict(log)
        if payload.get("error"):
            continue

        persona_id = str(payload.get("persona_id", "unknown"))
        first_payload = _extract_decision(payload, 1)
        second_payload = _extract_decision(payload, 2)

        first_decision = _decision_label(first_payload)
        if first_decision not in _PURCHASE_DECISIONS:
            continue

        reordered_flag = payload.get("reordered")
        if reordered_flag is None:
            second_decision = _decision_label(second_payload)
            reordered_flag = second_decision in _PURCHASE_DECISIONS

        if bool(reordered_flag):
            reorderers.append(persona_id)
        else:
            lapsers.append(persona_id)

    return {"reorderers": reorderers, "lapsers": lapsers}
