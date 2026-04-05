#!/usr/bin/env python3
"""Re-run Problem B and C probes with correct API key."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.agent import CognitiveAgent  # noqa: E402
from src.taxonomy.schema import Persona  # noqa: E402


def load_personas() -> dict[str, Persona]:
    path = PROJECT_ROOT / "data" / "population" / "personas_generated.json"
    with path.open() as f:
        data = json.load(f)
    personas: dict[str, Persona] = {}
    for i, p_dict in enumerate(data):
        pid = str(p_dict.get("id", f"persona_{i:03d}"))
        try:
            personas[pid] = Persona.model_validate(p_dict)
        except Exception:
            pass
    print(f"Loaded {len(personas)} personas")
    return personas


def run_probe(persona: Persona, scenario: dict, probe_id: str) -> dict:
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


def run_probe_batch(probe_id: str, scenario: dict, personas: list, concurrency: int = 3) -> list:
    results = []
    print(f"\n  Probe: {probe_id} ({len(personas)} personas)", flush=True)
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(run_probe, p, scenario, probe_id): p for p in personas}
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            name = result.get("display_name", "?")
            dec = result.get("decision", "?")
            print(f"    [{i:>2}/{len(personas)}] {name:<28} => {dec}", flush=True)
    return results


def summarize(results: list) -> dict:
    outcome_counts: dict[str, int] = {}
    all_drivers: list = []
    all_objections: list = []
    for r in results:
        if r.get("error") and r.get("decision") == "error":
            continue
        dec = r.get("decision", "unknown")
        outcome_counts[dec] = outcome_counts.get(dec, 0) + 1
        all_drivers.extend(r.get("key_drivers") or [])
        all_objections.extend(r.get("objections") or [])
    total = sum(outcome_counts.values())
    positive = outcome_counts.get("buy", 0) + outcome_counts.get("trial", 0)
    pos_pct = round(100 * positive / total, 1) if total else 0
    return {
        "total": total,
        "outcome_counts": outcome_counts,
        "positive_pct": pos_pct,
        "top_drivers": Counter(all_drivers).most_common(5),
        "top_objections": Counter(all_objections).most_common(5),
    }


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        return 1

    all_personas = load_personas()

    # --- PROBLEM B ---
    with open(PROJECT_ROOT / "data" / "population" / "journey_B_results.json") as f:
        b_data = json.load(f)
    b_non = [log["persona_id"] for log in b_data["logs"] if not log.get("error") and not log.get("reordered")]
    b_ids = b_non + [log["persona_id"] for log in b_data["logs"] if log.get("reordered")][:25]
    b_ids = b_ids[:30]
    b_personas = [all_personas[pid] for pid in b_ids if pid in all_personas]

    print(f"\nPROBLEM B PROBES ({len(b_personas)} personas)")
    probe_b: dict = {}

    r_b1 = run_probe_batch("B-P1", {
        "description": (
            "LittleJoys app prompts: 'Track your child's sleep this week — 3 quick questions "
            "each morning. We'll show you what changed at Day 10.' You just started Magnesium "
            "Gummies. Unsure if they work. Would this tracking feature make you more confident "
            "and likely to continue the gummies?"
        ),
        "product": "LittleJoys Magnesium Gummies 30-day pack",
        "price_inr": 499,
        "simulation_tick": 5,
    }, b_personas)
    probe_b["B-P1"] = {
        "hypothesis": "Outcome tracking increases perceived efficacy and reorder",
        "results": r_b1,
        "summary": summarize(r_b1),
    }

    r_b2 = run_probe_batch("B-P2", {
        "description": (
            "Push notification: '1,200 parents completed their first Magnesium Gummies pack. "
            "Average bedtime moved 22 minutes earlier. Here's the data.' "
            "You've been giving gummies for 8 days and are unsure if it's working. "
            "Does seeing this community data make you more likely to reorder?"
        ),
        "product": "LittleJoys Magnesium Gummies 30-day pack",
        "price_inr": 499,
        "simulation_tick": 30,
    }, b_personas)
    probe_b["B-P2"] = {
        "hypothesis": "Community outcome data resolves uncertainty and drives reorder",
        "results": r_b2,
        "summary": summarize(r_b2),
    }

    r_b3 = run_probe_batch("B-P3", {
        "description": (
            "Your pediatrician confirms: 'Magnesium supplementation at the right dose is safe "
            "and can support sleep in children who are picky eaters with low dietary variety.' "
            "Child has been on Gummies 10 days. Pack finishes in 5 days. Rs 499 to reorder. "
            "Does this professional validation make you reorder?"
        ),
        "product": "LittleJoys Magnesium Gummies 30-day pack",
        "price_inr": 499,
        "simulation_tick": 40,
    }, b_personas)
    probe_b["B-P3"] = {
        "hypothesis": "Pediatrician validation is the missing confidence signal",
        "results": r_b3,
        "summary": summarize(r_b3),
    }

    r_b4 = run_probe_batch("B-P4", {
        "description": (
            "You've been giving your child Magnesium Gummies for only 10 days. Some sleep "
            "improvement noticed but unsure if real. Pack finishes in 5 days. Rs 499 to reorder. "
            "Your main concern: 10 days is not enough to tell if it's working. What do you do?"
        ),
        "product": "LittleJoys Magnesium Gummies 30-day pack",
        "price_inr": 499,
        "simulation_tick": 45,
    }, b_personas)
    probe_b["B-P4"] = {
        "hypothesis": "10-day trial window insufficient to prove efficacy",
        "results": r_b4,
        "summary": summarize(r_b4),
    }

    with open(PROJECT_ROOT / "data" / "population" / "probe_results_B.json", "w") as f:
        json.dump(probe_b, f, indent=2)
    print("\nSaved probe_results_B.json")

    # Print B summary
    print("\n=== PROBLEM B SUMMARY ===")
    for pid, pd in probe_b.items():
        s = pd["summary"]
        print(f"  {pid}: positive={s['positive_pct']}% | outcomes={s['outcome_counts']}")

    # --- PROBLEM C ---
    with open(PROJECT_ROOT / "data" / "population" / "journey_C_results.json") as f:
        c_data = json.load(f)
    c_non = [log["persona_id"] for log in c_data["logs"] if not log.get("error") and not log.get("reordered")]
    c_ids = c_non[:20] + [log["persona_id"] for log in c_data["logs"] if log.get("reordered")][:10]
    c_ids = c_ids[:30]
    c_personas = [all_personas[pid] for pid in c_ids if pid in all_personas]

    print(f"\nPROBLEM C PROBES ({len(c_personas)} personas)")
    probe_c: dict = {}

    r_c1 = run_probe_batch("C-P1", {
        "description": (
            "LittleJoys push: 'Nutrimix has 3x the iron of Bournvita and zero added sugar. "
            "That's your Rs 250 explained.' With comparison infographic. Your child has been "
            "on Nutrimix 4 weeks, pack running low. Rs 649 vs Bournvita Rs 399. "
            "Does this nutritional comparison make you reorder Nutrimix?"
        ),
        "product": "LittleJoys Nutrimix 500g",
        "price_inr": 649,
        "simulation_tick": 55,
    }, c_personas)
    probe_c["C-P1"] = {
        "hypothesis": "Nutritional comparison closes Rs 250 price gap",
        "results": r_c1,
        "summary": summarize(r_c1),
    }

    r_c2 = run_probe_batch("C-P2", {
        "description": (
            "BigBasket offer: 2 x 500g Nutrimix for Rs 1,099 (Rs 549 each — Rs 100 saving). "
            "Valid this week. Child using Nutrimix a month, pack running low. "
            "Does this family pack deal make you reorder Nutrimix instead of switching to Bournvita?"
        ),
        "product": "LittleJoys Nutrimix 500g x2 Family Pack",
        "price_inr": 1099,
        "simulation_tick": 55,
    }, c_personas)
    probe_c["C-P2"] = {
        "hypothesis": "Multi-pack deal reduces effective price and increases loyalty",
        "results": r_c2,
        "summary": summarize(r_c2),
    }

    r_c3 = run_probe_batch("C-P3", {
        "description": (
            "Time to reorder. Nutrimix is Rs 649. Bournvita is Rs 399 — trusted by your "
            "family for years. Saw a Bournvita ad yesterday. Child seems more alert since "
            "Nutrimix but hard to be sure. Do you reorder Nutrimix or switch back to Bournvita?"
        ),
        "product": "LittleJoys Nutrimix 500g",
        "price_inr": 649,
        "simulation_tick": 60,
    }, c_personas)
    probe_c["C-P3"] = {
        "hypothesis": "Bournvita brand inertia reasserts pull at reorder moment",
        "results": r_c3,
        "summary": summarize(r_c3),
    }

    r_c4 = run_probe_batch("C-P4", {
        "description": (
            "Your 9-year-old child says: 'I like the brown milk drink. Can we keep getting it?' "
            "They mean Nutrimix. Pack running low. Rs 649. "
            "Does your child's explicit preference make you reorder?"
        ),
        "product": "LittleJoys Nutrimix 500g",
        "price_inr": 649,
        "simulation_tick": 58,
    }, c_personas)
    probe_c["C-P4"] = {
        "hypothesis": "Child's explicit preference is a strong reorder driver",
        "results": r_c4,
        "summary": summarize(r_c4),
    }

    with open(PROJECT_ROOT / "data" / "population" / "probe_results_C.json", "w") as f:
        json.dump(probe_c, f, indent=2)
    print("\nSaved probe_results_C.json")

    # Print C summary
    print("\n=== PROBLEM C SUMMARY ===")
    for pid, pd in probe_c.items():
        s = pd["summary"]
        print(f"  {pid}: positive={s['positive_pct']}% | outcomes={s['outcome_counts']}")

    print("\nAll B and C probes complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
