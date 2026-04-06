#!/usr/bin/env python3
"""
rerun_journey_c_errors.py — Re-run the 10 Journey C personas that got API 400 errors.
Patches results back into journey_C_results.json and re-aggregates.

Usage:
    source .env && PYTHONPATH=. .venv/bin/python3 scripts/rerun_journey_c_errors.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation.batch_runner import run_batch          # noqa: E402
from src.simulation.journey_presets import list_presets    # noqa: E402
from src.simulation.journey_result import aggregate_journeys  # noqa: E402
from src.taxonomy.schema import Persona                    # noqa: E402

OUT_DIR = PROJECT_ROOT / "data" / "population"

ERROR_PERSONA_IDS = [
    "Preeti-Chandigarh-Mom-29",
    "Parveen-Hyderabad-Mom-35",
    "Sakshi-Guwahati-Mom-29",
    "Champa-Bangalore-Mom-30",
    "Rekha-Udaipur-Mom-33",
    "Vivek-Chennai-Dad-35",
    "Jyoti-Mumbai-Mom-31",
    "Shweta-Pune-Mom-31",
    "Nasreen-Hyderabad-Mom-26",
    "Rahul-Udaipur-Dad-35",
]


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set"); return 1

    # Load full persona pool
    with (OUT_DIR / "personas_generated.json").open() as f:
        raw = json.load(f)

    persona_map: dict[str, Persona] = {}
    for i, p_dict in enumerate(raw):
        pid = str(p_dict.get("id", f"persona_{i:03d}"))
        # Filter to 7-14 age range (Journey C requirement)
        child_ages = p_dict.get("demographics", {}).get("child_ages", [])
        has_714 = any(7 <= int(a) <= 14 for a in child_ages if str(a).isdigit())
        if not has_714:
            continue
        try:
            persona_map[pid] = Persona.model_validate(p_dict)
        except Exception:
            pass

    # Select only the 10 error personas
    error_personas = [
        (pid, persona_map[pid])
        for pid in ERROR_PERSONA_IDS
        if pid in persona_map
    ]
    print(f"Found {len(error_personas)}/{len(ERROR_PERSONA_IDS)} error personas in 7-14 filtered pool")
    if len(error_personas) < len(ERROR_PERSONA_IDS):
        missing = [pid for pid in ERROR_PERSONA_IDS if pid not in persona_map]
        print(f"  Missing (not in 7-14 pool): {missing}")

    # Load Journey C config
    presets = list_presets()
    journey_config = presets["C"]

    # Re-run the error personas
    print(f"\nRe-running {len(error_personas)} personas through Journey C (concurrency=2)...")
    def progress_cb(done: int, total: int, log_dict: dict) -> None:
        name = str(log_dict.get("display_name") or log_dict.get("persona_id") or "?")
        err = log_dict.get("error")
        reordered = log_dict.get("reordered", False)
        print(f"  [{done:>2}/{total}] {name:<30} reordered={reordered}  {'ERROR: ' + str(err)[:60] if err else 'OK'}")

    result = run_batch(
        journey_config=journey_config,
        personas=error_personas,
        concurrency=2,
        progress_callback=progress_cb,
    )

    new_logs = result.logs
    successes = [l for l in new_logs if not l.get("error")]
    errors = [l for l in new_logs if l.get("error")]
    print(f"\nRe-run complete: {len(successes)} success, {len(errors)} still errored")

    # Load existing full results
    results_path = OUT_DIR / "journey_C_results.json"
    with results_path.open() as f:
        existing = json.load(f)

    # Build lookup of new results by persona_id
    new_by_pid = {l["persona_id"]: l for l in new_logs if not l.get("error")}

    # Patch into existing logs
    patched = 0
    for i, log in enumerate(existing["logs"]):
        pid = log.get("persona_id", "")
        if pid in new_by_pid:
            existing["logs"][i] = new_by_pid[pid]
            patched += 1
            print(f"  Patched: {pid}")

    print(f"\nPatched {patched} logs in journey_C_results.json")

    # Re-aggregate
    print("\nRe-aggregating...")
    all_logs = existing["logs"]
    agg = aggregate_journeys(all_logs)
    existing["aggregate"] = agg.to_dict()

    # Update top-level counts
    valid_logs = [l for l in all_logs if not l.get("error")]
    existing["total_personas"] = len(valid_logs)
    existing["errors"] = sum(1 for l in all_logs if l.get("error"))

    # Save
    with results_path.open("w") as f:
        json.dump(existing, f, indent=2)
    print(f"Saved: {results_path}")

    # Summary
    fdd = agg.first_decision_distribution
    print(f"\n=== UPDATED JOURNEY C SUMMARY ===")
    print(f"Total personas:  {agg.total_personas}")
    print(f"Errors:          {existing['errors']}")
    print(f"Reorder rate:    {agg.reorder_rate_pct:.1f}%")
    print(f"Avg trust first: {agg.avg_trust_at_first_decision:.4f}")
    print(f"\nFirst decision distribution:")
    for k, v in fdd.items():
        count = v.get("count", 0) if isinstance(v, dict) else 0
        pct = v.get("pct", 0) if isinstance(v, dict) else 0
        bar = "#" * int(pct / 3)
        print(f"  {k:<16} {count:>4} ({pct:>5.1f}%)  {bar}")
    unknown_count = fdd.get("unknown", {}).get("count", 0) if isinstance(fdd.get("unknown"), dict) else 0
    if unknown_count == 0:
        print("\n✅ No more 'unknown' decisions — all 148 personas have valid tick-28 decisions")
    else:
        print(f"\n⚠️  Still {unknown_count} unknown decisions remaining")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
