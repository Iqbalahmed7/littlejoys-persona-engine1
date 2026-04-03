#!/usr/bin/env python3
"""
run_journey_batch.py — Run multi-tick journeys across all 200 personas.

Usage:
    ANTHROPIC_API_KEY=sk-... python3 scripts/run_journey_batch.py --journey A
    ANTHROPIC_API_KEY=sk-... python3 scripts/run_journey_batch.py --journey B
    python3 scripts/run_journey_batch.py --journey A --max 10 --concurrency 3

Arguments:
    --journey   A (Nutrimix repeat purchase, 60 ticks) or B (Gummies, 45 ticks)
    --max       Cap number of personas (default: all 200)
    --concurrency  Thread pool size (default: 3)

Output:
    data/population/journey_A_results.json  (or journey_B_results.json)
    Prints progress + final summary table
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation.batch_runner import BatchResult, run_batch  # noqa: E402
from src.simulation.journey_presets import list_presets  # noqa: E402
from src.simulation.journey_result import segment_by_reorder  # noqa: E402
from src.taxonomy.schema import Persona  # noqa: E402


def load_all_personas(max_n: int | None = None) -> list[tuple[str, Persona]]:
    candidates = [
        PROJECT_ROOT / "data" / "population" / "personas_generated.json",
        PROJECT_ROOT / "data" / "population" / "personas.json",
    ]
    all_personas: list[tuple[str, Persona]] = []
    for path in candidates:
        if not path.exists():
            continue
        with path.open() as f:
            data = json.load(f)
        if isinstance(data, list):
            for i, p_dict in enumerate(data):
                pid = str(p_dict.get("id", f"persona_{i:03d}"))
                try:
                    all_personas.append((pid, Persona.model_validate(p_dict)))
                except Exception as exc:
                    print(f"  [SKIP] {pid}: {exc}")
        break
    if max_n is not None:
        all_personas = all_personas[: max(0, max_n)]
    print(f"Loaded {len(all_personas)} personas.")
    return all_personas


def _decision_label(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("decision") or value.get("outcome") or "unknown")
    return "unknown"


def _get_decision_at_tick(log_dict: dict[str, Any], tick: int) -> dict[str, Any]:
    """Extract decision_result from snapshots at the given tick."""
    for snap in log_dict.get("snapshots", []):
        if snap.get("tick") == tick and snap.get("decision_result"):
            dr = snap["decision_result"]
            if isinstance(dr, dict) and "error" not in dr:
                return dr
    return {}


def _get_second_decision(log_dict: dict[str, Any], journey_id: str) -> dict[str, Any]:
    if "second_decision" in log_dict and isinstance(log_dict["second_decision"], dict):
        return log_dict["second_decision"]
    key = "tick60_decision" if journey_id == "A" else "tick45_decision"
    if key in log_dict and isinstance(log_dict[key], dict):
        return log_dict[key]
    # Fallback: scan snapshots
    tick = 60 if journey_id == "A" else 45
    return _get_decision_at_tick(log_dict, tick)


def _print_summary(journey_id: str, logs: list[dict[str, Any]], aggregate) -> None:
    title = (
        "JOURNEY A — NUTRIMIX REPEAT PURCHASE — SUMMARY"
        if journey_id == "A"
        else "JOURNEY B — GUMMIES — SUMMARY"
    )
    print("\n" + "=" * 59)
    print(title)
    print("=" * 59)
    print(f"Personas run:    {aggregate.total_personas}")
    print(f"Errors:          {aggregate.errors}")
    print()

    first_tick = 20 if journey_id == "A" else 35
    second_tick = 60 if journey_id == "A" else 45
    print(f"FIRST PURCHASE (tick {first_tick}):")
    for decision, data in aggregate.first_decision_distribution.items():
        pct = float(data.get("pct", 0.0))
        bar = "#" * int(pct / 2)
        print(f"  {decision:<12} {data.get('count', 0):>4} ({pct:>5.1f}%)  {bar}")
    if not aggregate.first_decision_distribution:
        print("  (no valid first-decision data)")

    print("\nREORDER RATE (among first-time buyers):")
    reorder_split = segment_by_reorder(logs)
    reorderers = len(reorder_split["reorderers"])
    lapsers = len(reorder_split["lapsers"])
    total = reorderers + lapsers
    reordered_pct = (reorderers / total * 100.0) if total else 0.0
    lapsed_pct = (lapsers / total * 100.0) if total else 0.0
    print(f"  Reordered:    {reordered_pct:.1f}%")
    print(f"  Lapsed:       {lapsed_pct:.1f}%")

    print("\nBRAND TRUST TRAJECTORY (mean across personas):")
    for tick in sorted(aggregate.trust_by_tick):
        marker = ""
        if tick == first_tick:
            marker = "  ← first decision"
        elif tick == second_tick:
            marker = "  ← reorder decision"
        print(f"  Tick {tick:<2}: {aggregate.trust_by_tick[tick]:.2f}{marker}")
    if not aggregate.trust_by_tick:
        print("  (no trust trajectory available)")

    reorder_driver_counter: Counter[str] = Counter()
    lapse_objection_counter: Counter[str] = Counter()
    reorderer_ids = set(reorder_split["reorderers"])
    for log in logs:
        if log.get("error"):
            continue
        pid = str(log.get("persona_id", ""))
        second_decision = _get_second_decision(log, journey_id)
        drivers = second_decision.get("key_drivers") or second_decision.get("drivers") or []
        objections = second_decision.get("objections") or []
        if pid in reorderer_ids:
            for d in drivers:
                reorder_driver_counter[str(d)] += 1
        else:
            for o in objections:
                lapse_objection_counter[str(o)] += 1

    print("\nTOP REORDER DRIVERS:")
    top_reorder = reorder_driver_counter.most_common(5)
    if top_reorder:
        for idx, (name, count) in enumerate(top_reorder, start=1):
            print(f"  {idx}. {name}: {count}")
    else:
        print("  (none)")

    print("\nTOP LAPSE REASONS (objections from non-reorderers):")
    top_lapse = lapse_objection_counter.most_common(5)
    if top_lapse:
        for idx, (name, count) in enumerate(top_lapse, start=1):
            print(f"  {idx}. {name}: {count}")
    else:
        print("  (none)")
    print("=" * 59)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--journey",
        required=True,
        choices=["A", "B", "C"],
        help="A (Nutrimix repeat purchase) or B (Gummies) or C (Nutrimix 7-14 expansion)",
    )
    parser.add_argument("--max", type=int, default=None, help="Cap personas")
    parser.add_argument("--concurrency", type=int, default=3, help="Thread pool size")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set.")
        return 1

    personas = load_all_personas(max_n=args.max)
    if not personas:
        print("ERROR: No personas found.")
        return 1

    journey_id = str(args.journey).upper()
    presets = list_presets()
    if journey_id not in presets:
        print(f"Unknown journey: {journey_id}")
        return 1

    total = len(personas)
    print(f"Running journey {journey_id} for {total} personas (concurrency={args.concurrency})...")

    def progress_cb(done: int, total: int, log_dict: dict) -> None:
        name = str(log_dict.get("display_name") or log_dict.get("persona_id") or "?")
        second = _get_second_decision(log_dict, journey_id)
        second_decision = _decision_label(second)
        reordered = log_dict.get("reordered") or second_decision in {"buy", "trial", "reorder"}
        tick_label = "tick60_decision" if journey_id == "A" else "tick45_decision"
        print(
            f"  [{done:>3}/{total}] {name:<28} journey={journey_id}  "
            f"{tick_label}={second_decision:<6} reordered={bool(reordered)}"
        )

    result: BatchResult = run_batch(
        journey_config=presets[journey_id],
        personas=personas,
        concurrency=args.concurrency,
        progress_callback=progress_cb,
    )

    _print_summary(journey_id, result.logs, result.aggregate)

    output = result.to_dict()
    out_name = f"journey_{journey_id}_results.json"
    out_path = PROJECT_ROOT / "data" / "population" / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(output, f, indent=2)
    print(f"Full results written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
