#!/usr/bin/env python3
"""
run_probe_lj_pass.py — Run Probe A-P5: LJ Pass (D2C loyalty bundle).

Tests whether the LittleJoys Pass (5% cashback + free delivery + expert
consultation + surprise gift, exclusive to ourlittlejoys.com) converts
Journey A lapsers — and measures the D2C channel-switch friction.

Appends A-P5 results to probe_results_A.json and updates hypothesis tree.

Usage:
    source .env && PYTHONPATH=. .venv/bin/python3 scripts/run_probe_lj_pass.py
"""
from __future__ import annotations

import json
import os
import sys
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.agent import CognitiveAgent       # noqa: E402
from src.taxonomy.schema import Persona           # noqa: E402

OUT_DIR = PROJECT_ROOT / "data" / "population"

# ── Probe scenario ─────────────────────────────────────────────────────────────

LJ_PASS_SCENARIO = {
    "description": (
        "Your first Nutrimix pack is finished. You've seen some possible improvement "
        "but can't be certain. You receive a push notification from the LittleJoys app: "
        "'Reorder with LJ Pass — 5% cashback on every order (Rs 32 back on Rs 649), "
        "zero delivery charges, a free surprise gift, and one FREE 10-minute nutritionist "
        "consultation to track your child's progress. 90-day pass, exclusive to "
        "ourlittlejoys.com (not available on BigBasket). Add to your next order.' "
        "Effective net price with cashback + saved delivery: ~Rs 540–557 for this order. "
        "However, you'd need to switch from BigBasket to the LittleJoys website/app. "
        "Do you reorder Nutrimix with LJ Pass on the D2C site?"
    ),
    "product": "LittleJoys Nutrimix 500g + LJ Pass",
    "price_inr": 649,
    "simulation_tick": 65,
}

# Two sub-probes to isolate what drives/blocks conversion
LJ_PASS_CONSULTATION_ONLY = {
    "description": (
        "First Nutrimix pack finished. Outcome is unclear — possible appetite improvement "
        "but hard to confirm. LittleJoys offers a FREE 10-minute online nutritionist "
        "consultation (book on their app) to review your child's progress and advise "
        "whether to continue. No purchase required to book the consultation. "
        "Does the free expert consultation make you more confident about reordering Nutrimix?"
    ),
    "product": "LittleJoys Nutrimix 500g",
    "price_inr": 649,
    "simulation_tick": 65,
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_personas() -> dict[str, Persona]:
    path = OUT_DIR / "personas_generated.json"
    with path.open() as f:
        data = json.load(f)
    personas: dict[str, Persona] = {}
    for i, p_dict in enumerate(data):
        pid = str(p_dict.get("id", f"persona_{i:03d}"))
        try:
            personas[pid] = Persona.model_validate(p_dict)
        except Exception:
            pass
    return personas


def run_probe_for_persona(persona: Persona, scenario: dict, probe_id: str) -> dict:
    agent = CognitiveAgent(persona)
    try:
        result = agent.decide(scenario)
        return {
            "persona_id": getattr(persona, "id", "unknown"),
            "display_name": getattr(persona, "display_name", "unknown"),
            "probe_id": probe_id,
            "decision": result.decision,
            "confidence": result.confidence,
            "reasoning_trace": result.reasoning_trace,
            "key_drivers": result.key_drivers,
            "objections": result.objections,
            "follow_up_action": result.follow_up_action,
            "error": None,
        }
    except Exception as exc:
        return {
            "persona_id": getattr(persona, "id", "unknown"),
            "display_name": getattr(persona, "display_name", "unknown"),
            "probe_id": probe_id,
            "decision": "error",
            "error": str(exc),
        }


def run_probe_batch(probe_id: str, scenario: dict, personas: list[Persona], concurrency: int = 3) -> list[dict]:
    results = []
    print(f"\n  [{probe_id}] Running on {len(personas)} personas...")
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(run_probe_for_persona, p, scenario, probe_id): p for p in personas}
        for i, future in enumerate(as_completed(futures), 1):
            r = future.result()
            results.append(r)
            print(f"    [{i:>2}/{len(personas)}] {r.get('display_name','?'):<28} => {r.get('decision','?')}")
    return results


def summarize_probe(results: list[dict]) -> dict:
    outcome_counts: dict[str, int] = {}
    all_drivers: list[str] = []
    all_objections: list[str] = []
    for r in results:
        if r.get("error") and r.get("decision") == "error":
            continue
        dec = r.get("decision", "unknown")
        outcome_counts[dec] = outcome_counts.get(dec, 0) + 1
        all_drivers.extend(r.get("key_drivers") or [])
        all_objections.extend(r.get("objections") or [])
    total = sum(outcome_counts.values())
    positive = sum(outcome_counts.get(k, 0) for k in {"buy", "trial", "reorder"})
    return {
        "total": total,
        "outcome_counts": outcome_counts,
        "positive_pct": round(100 * positive / total, 1) if total else 0,
        "top_drivers": Counter(all_drivers).most_common(5),
        "top_objections": Counter(all_objections).most_common(5),
    }


def verdict(positive_pct: float) -> str:
    if positive_pct >= 60:
        return "CONFIRMED"
    if positive_pct >= 35:
        return "PARTIAL"
    return "NOT CONFIRMED"


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set"); return 1

    # Load existing probe results
    probe_path = OUT_DIR / "probe_results_A.json"
    with probe_path.open() as f:
        all_results = json.load(f)

    # Load personas and lapse cohort
    all_personas = load_personas()
    print(f"Loaded {len(all_personas)} personas")

    with open(OUT_DIR / "journey_A_results.json") as f:
        d = json.load(f)
    logs = d["logs"]
    lapse_ids = [l["persona_id"] for l in logs if not l.get("error") and not l.get("reordered")]
    reorder_ids = [l["persona_id"] for l in logs if not l.get("error") and l.get("reordered")]
    print(f"Lapsers: {len(lapse_ids)}, Reorderers: {len(reorder_ids)}")

    # Same 30-persona cohort as A-P1 through A-P4
    random.seed(42)
    probe_ids = lapse_ids[:30]
    remaining = 30 - len(probe_ids)
    probe_ids += reorder_ids[:remaining]
    probe_personas = [all_personas[pid] for pid in probe_ids if pid in all_personas]
    print(f"Probe cohort: {len(probe_personas)} personas ({min(30, len(lapse_ids))} lapsers + {remaining} reorderers)")

    # ── A-P5a: LJ Pass full bundle (D2C channel switch required) ───────────────
    print("\n=== A-P5a: LJ Pass — Full Bundle (D2C) ===")
    p5a_results = run_probe_batch("A-P5a", LJ_PASS_SCENARIO, probe_personas, concurrency=3)
    p5a_summary = summarize_probe(p5a_results)
    all_results["A-P5a"] = {
        "hypothesis": "H1+H2: LJ Pass addresses price friction (cashback+free delivery) AND outcome uncertainty (expert consultation) — but requires D2C channel switch from BigBasket",
        "scenario": LJ_PASS_SCENARIO,
        "results": p5a_results,
        "summary": p5a_summary,
    }
    print(f"\n  A-P5a result: {p5a_summary['positive_pct']}% positive — {verdict(p5a_summary['positive_pct'])}")
    print(f"  Outcomes: {p5a_summary['outcome_counts']}")

    # ── A-P5b: Consultation only (no channel switch required) ──────────────────
    print("\n=== A-P5b: Expert Consultation Only (no purchase required) ===")
    p5b_results = run_probe_batch("A-P5b", LJ_PASS_CONSULTATION_ONLY, probe_personas, concurrency=3)
    p5b_summary = summarize_probe(p5b_results)
    all_results["A-P5b"] = {
        "hypothesis": "H2 isolation: Does the expert consultation alone (without price incentive) unlock reorder confidence for outcome-uncertain lapsers?",
        "scenario": LJ_PASS_CONSULTATION_ONLY,
        "results": p5b_results,
        "summary": p5b_summary,
    }
    print(f"\n  A-P5b result: {p5b_summary['positive_pct']}% positive — {verdict(p5b_summary['positive_pct'])}")
    print(f"  Outcomes: {p5b_summary['outcome_counts']}")

    # Save updated probe results
    with probe_path.open("w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nProbe results saved: {probe_path}")

    # Print comparison
    print("\n" + "=" * 60)
    print("PROBE A-P5 SUMMARY vs PRIOR PROBES")
    print("=" * 60)
    for pid in ["A-P1", "A-P2", "A-P3", "A-P4", "A-P5a", "A-P5b"]:
        if pid in all_results:
            s = all_results[pid].get("summary", {})
            pct = s.get("positive_pct", 0)
            v = verdict(pct)
            hyp = all_results[pid].get("hypothesis", "")[:60]
            print(f"  {pid}: {pct:>5.1f}% positive  [{v:<14}]  {hyp}")

    print("\n  Key insight:")
    p5a_pct = p5a_summary["positive_pct"]
    p5b_pct = p5b_summary["positive_pct"]
    p1_pct = all_results.get("A-P1", {}).get("summary", {}).get("positive_pct", 50)

    if p5a_pct > p1_pct:
        print(f"  LJ Pass ({p5a_pct}%) OUTPERFORMS BigBasket discount ({p1_pct}%) — "
              "D2C bundle value exceeds channel-switch friction.")
    elif p5a_pct >= p1_pct * 0.8:
        print(f"  LJ Pass ({p5a_pct}%) is COMPARABLE to BigBasket discount ({p1_pct}%) — "
              "channel switch is manageable for the savings offered.")
    else:
        print(f"  LJ Pass ({p5a_pct}%) UNDERPERFORMS BigBasket discount ({p1_pct}%) — "
              "D2C channel-switch friction cancels some of the bundle advantage.")

    if p5b_pct > p5a_pct:
        print(f"  Consultation alone ({p5b_pct}%) outperforms full LJ Pass ({p5a_pct}%) — "
              "H2 (outcome uncertainty) is the primary lever; price is secondary.")
    elif p5b_pct < p5a_pct * 0.5:
        print(f"  Consultation alone ({p5b_pct}%) much weaker than full bundle ({p5a_pct}%) — "
              "price benefit (cashback + free delivery) is doing the heavy lifting.")
    else:
        print(f"  Consultation + price bundle work together — neither alone is sufficient.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
