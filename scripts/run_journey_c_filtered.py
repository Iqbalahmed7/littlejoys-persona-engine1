#!/usr/bin/env python3
"""
run_journey_c_filtered.py — Run Journey C on 148 personas with children aged 7-14.

Filters the full 200-persona cohort to only those with at least one child
aged 7-14 (per demographics.child_ages) — the relevant audience for the
Nutrimix 7-14 expansion journey.

Usage:
    source .env && PYTHONPATH=. .venv/bin/python3 scripts/run_journey_c_filtered.py
    source .env && PYTHONPATH=. .venv/bin/python3 scripts/run_journey_c_filtered.py --max 20
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation.batch_runner import BatchResult, run_batch   # noqa: E402
from src.simulation.journey_presets import list_presets          # noqa: E402
from src.simulation.journey_result import segment_by_reorder     # noqa: E402
from src.taxonomy.schema import Persona                           # noqa: E402

OUT_DIR = PROJECT_ROOT / "data" / "population"


def load_filtered_personas(max_n: int | None = None) -> list[tuple[str, Persona]]:
    path = OUT_DIR / "personas_generated.json"
    with path.open() as f:
        raw = json.load(f)

    filtered: list[tuple[str, Persona]] = []
    skipped = 0
    for i, p_dict in enumerate(raw):
        pid = str(p_dict.get("id", f"persona_{i:03d}"))
        child_ages = p_dict.get("demographics", {}).get("child_ages", [])
        has_714 = any(7 <= int(a) <= 14 for a in child_ages if str(a).isdigit())
        if not has_714:
            skipped += 1
            continue
        try:
            filtered.append((pid, Persona.model_validate(p_dict)))
        except Exception as exc:
            print(f"  [SKIP] {pid}: {exc}")

    print(f"Filtered: {len(filtered)} personas with 7-14 age children "
          f"({skipped} skipped — no children in 7-14 range)")

    if max_n is not None:
        filtered = filtered[:max(0, max_n)]
        print(f"Capped at {len(filtered)} personas (--max {max_n})")

    return filtered


def _decision_label(value) -> str:
    if isinstance(value, dict):
        return str(value.get("decision") or value.get("outcome") or "unknown")
    return "unknown"


def _get_second_decision(log_dict: dict, journey_id: str) -> dict:
    if "second_decision" in log_dict and isinstance(log_dict["second_decision"], dict):
        return log_dict["second_decision"]
    key = "tick60_decision"
    if key in log_dict and isinstance(log_dict[key], dict):
        return log_dict[key]
    for snap in log_dict.get("snapshots", []):
        if snap.get("tick") == 60 and snap.get("decision_result"):
            dr = snap["decision_result"]
            if isinstance(dr, dict) and "error" not in dr:
                return dr
    return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=None, help="Cap personas (default: all 148)")
    parser.add_argument("--concurrency", type=int, default=3, help="Thread pool size")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set."); return 1

    personas = load_filtered_personas(max_n=args.max)
    if not personas:
        print("ERROR: No eligible personas found."); return 1

    presets = list_presets()
    journey_config = presets["C"]
    total = len(personas)
    print(f"\nRunning Journey C for {total} personas (concurrency={args.concurrency})...")

    def progress_cb(done: int, total: int, log_dict: dict) -> None:
        name = str(log_dict.get("display_name") or log_dict.get("persona_id") or "?")
        second = _get_second_decision(log_dict, "C")
        second_decision = _decision_label(second)
        reordered = log_dict.get("reordered") or second_decision in {"buy", "trial", "reorder"}
        print(
            f"  [{done:>3}/{total}] {name:<28} "
            f"tick28={_decision_label({}):<14} "
            f"tick60={second_decision:<14} reordered={bool(reordered)}"
        )

    result: BatchResult = run_batch(
        journey_config=journey_config,
        personas=personas,
        concurrency=args.concurrency,
        progress_callback=progress_cb,
    )

    # Summary
    logs = result.logs
    agg = result.aggregate
    errors = sum(1 for l in logs if l.get("error"))

    print("\n" + "=" * 59)
    print("JOURNEY C — NUTRIMIX 7-14 EXPANSION — SUMMARY")
    print("=" * 59)
    print(f"Personas run:    {agg.total_personas}")
    print(f"Errors:          {errors}")
    print()
    print("FIRST PURCHASE (tick 28):")
    for decision, data in agg.first_decision_distribution.items():
        pct = float(data.get("pct", 0))
        bar = "#" * int(pct / 2)
        print(f"  {decision:<14} {data.get('count', 0):>4} ({pct:>5.1f}%)  {bar}")

    reorder_split = segment_by_reorder(logs)
    reorderers = len(reorder_split["reorderers"])
    lapsers = len(reorder_split["lapsers"])
    total_buyers = reorderers + lapsers
    reorder_pct = (reorderers / total_buyers * 100) if total_buyers else 0
    print(f"\nREORDER RATE (among first-time buyers):")
    print(f"  Reordered:    {reorder_pct:.1f}%")
    print(f"  Lapsed:       {100 - reorder_pct:.1f}%")

    print(f"\nBRAND TRUST TRAJECTORY (mean across personas):")
    for tick in sorted(agg.trust_by_tick)[:10]:
        marker = "  ← first decision" if tick == 28 else ("  ← reorder decision" if tick == 60 else "")
        print(f"  Tick {tick:<2}: {agg.trust_by_tick[tick]:.2f}{marker}")

    print("\nTOP LAPSE REASONS (objections from non-reorderers):")
    lapse_objs: Counter = Counter()
    reorderer_ids = set(reorder_split["reorderers"])
    for log in logs:
        if log.get("error") or log.get("persona_id") in reorderer_ids:
            continue
        second = _get_second_decision(log, "C")
        for o in (second.get("objections") or []):
            lapse_objs[str(o)] += 1
    for idx, (name, count) in enumerate(lapse_objs.most_common(5), 1):
        print(f"  {idx}. {name}: {count}")

    print("=" * 59)

    # Save
    output = result.to_dict()
    out_path = OUT_DIR / "journey_C_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(output, f, indent=2)
    print(f"\nFull results written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
