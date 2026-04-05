#!/usr/bin/env python3
"""
run_probes.py — Run interview probes on non-reordering cohorts for problems A, B, C.

Usage:
    ANTHROPIC_API_KEY=sk-... python3 scripts/run_probes.py

Output:
    data/population/probe_results_A.json
    data/population/probe_results_B.json
    data/population/probe_results_C.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.agent import CognitiveAgent  # noqa: E402
from src.taxonomy.schema import Persona  # noqa: E402


def load_personas(max_n: int | None = None) -> dict[str, Persona]:
    """Load all personas into a dict keyed by persona_id."""
    path = PROJECT_ROOT / "data" / "population" / "personas_generated.json"
    with path.open() as f:
        data = json.load(f)
    personas: dict[str, Persona] = {}
    for i, p_dict in enumerate(data):
        pid = str(p_dict.get("id", f"persona_{i:03d}"))
        try:
            personas[pid] = Persona.model_validate(p_dict)
        except Exception as exc:
            print(f"  [SKIP] {pid}: {exc}")
    if max_n:
        personas = dict(list(personas.items())[:max_n])
    print(f"Loaded {len(personas)} personas")
    return personas


def load_journey_results(journey_id: str) -> list[dict]:
    path = PROJECT_ROOT / "data" / "population" / f"journey_{journey_id}_results.json"
    with path.open() as f:
        data = json.load(f)
    return data["logs"]


def get_non_reorderers(logs: list[dict]) -> list[str]:
    return [log["persona_id"] for log in logs if not log.get("error") and not log.get("reordered")]


def run_probe_for_persona(persona: Persona, scenario: dict, probe_id: str) -> dict:
    """Run a single probe scenario for one persona."""
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


def run_probe_batch(
    probe_id: str,
    scenario: dict,
    personas: list[Persona],
    concurrency: int = 3,
) -> list[dict]:
    """Run a probe scenario for a batch of personas."""
    results = []
    print(f"\n  Running probe: {probe_id} ({len(personas)} personas)")

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(run_probe_for_persona, p, scenario, probe_id): p
            for p in personas
        }
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            name = result.get("display_name", "?")
            dec = result.get("decision", "?")
            print(f"    [{i:>2}/{len(personas)}] {name:<28} => {dec}")

    return results


def summarize_probe(results: list[dict]) -> dict:
    """Summarize outcomes from a probe batch."""
    outcome_counts: dict[str, int] = {}
    all_drivers: list[str] = []
    all_objections: list[str] = []
    positive_outcomes = {"buy", "trial"}

    for r in results:
        if r.get("error") and r.get("decision") == "error":
            continue
        dec = r.get("decision", "unknown")
        outcome_counts[dec] = outcome_counts.get(dec, 0) + 1
        drivers = r.get("key_drivers") or []
        objections = r.get("objections") or []
        all_drivers.extend(drivers)
        all_objections.extend(objections)

    total = sum(outcome_counts.values())
    positive = sum(outcome_counts.get(k, 0) for k in positive_outcomes)
    positive_pct = round(100 * positive / total, 1) if total else 0

    # Top drivers/objections
    from collections import Counter
    driver_counter = Counter(all_drivers)
    objection_counter = Counter(all_objections)

    return {
        "total": total,
        "outcome_counts": outcome_counts,
        "positive_pct": positive_pct,
        "top_drivers": driver_counter.most_common(5),
        "top_objections": objection_counter.most_common(5),
    }


def run_problem_a_probes(
    all_personas: dict[str, Persona],
    non_reorderer_ids: list[str],
) -> dict:
    """Run probes for Problem A: Nutrimix repeat purchase."""
    print("\n" + "=" * 60)
    print("PROBLEM A PROBES: Nutrimix Repeat Purchase")
    print("=" * 60)

    # Use non-reorderers + sample reorderers, cap at 30
    probe_persona_ids = non_reorderer_ids.copy()
    # Add some reorderers for comparison
    all_ids = list(all_personas.keys())
    reorderers = [pid for pid in all_ids if pid not in non_reorderer_ids][:26]
    probe_persona_ids = probe_persona_ids + reorderers
    probe_persona_ids = probe_persona_ids[:30]

    probe_personas = [all_personas[pid] for pid in probe_persona_ids if pid in all_personas]

    all_probe_results = {}

    # Probe A1: Price sensitivity — loyalty discount
    scenario_a1 = {
        "description": (
            "BigBasket sends a loyalty price notification — Rs 599 on your second Nutrimix pack "
            "(Rs 50 off). Valid for 48 hours. You finished your first pack and your child liked it. "
            "Would this discounted price prompt you to reorder Nutrimix now?"
        ),
        "product": "LittleJoys Nutrimix 500g",
        "price_inr": 599,
        "simulation_tick": 65,
    }
    results_a1 = run_probe_batch("A-P1-price-loyalty-discount", scenario_a1, probe_personas)
    all_probe_results["A-P1"] = {
        "hypothesis": "Price re-evaluation at reorder: a loyalty discount removes price friction",
        "scenario": scenario_a1,
        "results": results_a1,
        "summary": summarize_probe(results_a1),
    }

    # Probe A2: Social proof — WOM nudge
    scenario_a2 = {
        "description": (
            "You receive a WhatsApp message from your parenting group: "
            "'3,400 parents reordered Nutrimix this month — here's why they kept going.' "
            "It includes short quotes from parents about appetite improvement and energy levels. "
            "Does this message make you more likely to reorder Nutrimix?"
        ),
        "product": "LittleJoys Nutrimix 500g",
        "price_inr": 649,
        "simulation_tick": 62,
    }
    results_a2 = run_probe_batch("A-P2-social-proof-wom", scenario_a2, probe_personas)
    all_probe_results["A-P2"] = {
        "hypothesis": "Social proof deficit: peer reorder data would reinforce the habit",
        "scenario": scenario_a2,
        "results": results_a2,
        "summary": summarize_probe(results_a2),
    }

    # Probe A3: Habit formation — no visible outcome doubt
    scenario_a3 = {
        "description": (
            "Your first Nutrimix pack is finished. Your child had it for 5 weeks. "
            "You think there might be some improvement in appetite — but it's hard to tell. "
            "You're on BigBasket. Rs 649 — same price as before, no discount. "
            "You are weighing whether the Rs 649 is worth it given you can't clearly see results. "
            "What do you do?"
        ),
        "product": "LittleJoys Nutrimix 500g",
        "price_inr": 649,
        "simulation_tick": 60,
    }
    results_a3 = run_probe_batch("A-P3-outcome-uncertainty", scenario_a3, probe_personas)
    all_probe_results["A-P3"] = {
        "hypothesis": "Outcome uncertainty: unclear results make reordering feel risky",
        "scenario": scenario_a3,
        "results": results_a3,
        "summary": summarize_probe(results_a3),
    }

    # Probe A4: Competitive switch — pharmacist complan suggestion
    scenario_a4 = {
        "description": (
            "Your pharmacist suggested Complan as a 'safe default' for children. "
            "Complan is Rs 420 for 500g — Rs 229 cheaper than Nutrimix. "
            "Your first Nutrimix pack just finished. Would you switch to Complan to save money?"
        ),
        "product": "LittleJoys Nutrimix 500g",
        "price_inr": 649,
        "simulation_tick": 60,
    }
    results_a4 = run_probe_batch("A-P4-competitive-switch", scenario_a4, probe_personas)
    all_probe_results["A-P4"] = {
        "hypothesis": "Competitive switch: established brand suggestions displace reorder",
        "scenario": scenario_a4,
        "results": results_a4,
        "summary": summarize_probe(results_a4),
    }

    return all_probe_results


def run_problem_b_probes(
    all_personas: dict[str, Persona],
    non_reorderer_ids: list[str],
) -> dict:
    """Run probes for Problem B: Magnesium Gummies sales growth."""
    print("\n" + "=" * 60)
    print("PROBLEM B PROBES: Magnesium Gummies Growth")
    print("=" * 60)

    probe_persona_ids = non_reorderer_ids.copy()
    all_ids = list(all_personas.keys())
    reorderers = [pid for pid in all_ids if pid not in non_reorderer_ids][:25]
    probe_persona_ids = probe_persona_ids + reorderers
    probe_persona_ids = probe_persona_ids[:30]

    probe_personas = [all_personas[pid] for pid in probe_persona_ids if pid in all_personas]

    all_probe_results = {}

    # Probe B1: Placebo uncertainty — measurement removes doubt
    scenario_b1 = {
        "description": (
            "LittleJoys app prompts: 'Track your child's sleep this week — 3 quick questions "
            "each morning. We'll show you what changed at Day 10.' "
            "You just started giving your child Magnesium Gummies. "
            "You're unsure if they will really work. "
            "Would this tracking feature make you more confident and likely to continue with the gummies?"
        ),
        "product": "LittleJoys Magnesium Gummies 30-day pack",
        "price_inr": 499,
        "simulation_tick": 5,
    }
    results_b1 = run_probe_batch("B-P1-tracking-reduces-placebo-doubt", scenario_b1, probe_personas)
    all_probe_results["B-P1"] = {
        "hypothesis": "Placebo uncertainty: outcome tracking increases perceived efficacy and reorder",
        "scenario": scenario_b1,
        "results": results_b1,
        "summary": summarize_probe(results_b1),
    }

    # Probe B2: Social proof — peer outcome data
    scenario_b2 = {
        "description": (
            "Push notification: '1,200 parents completed their first Magnesium Gummies pack. "
            "Average bedtime moved 22 minutes earlier. Here's the data.' "
            "You've been giving your child gummies for 8 days and are unsure if it's working. "
            "Does seeing this community data make you more likely to reorder?"
        ),
        "product": "LittleJoys Magnesium Gummies 30-day pack",
        "price_inr": 499,
        "simulation_tick": 30,
    }
    results_b2 = run_probe_batch("B-P2-community-outcome-data", scenario_b2, probe_personas)
    all_probe_results["B-P2"] = {
        "hypothesis": "Social proof of outcomes: community data resolves uncertainty and drives reorder",
        "scenario": scenario_b2,
        "results": results_b2,
        "summary": summarize_probe(results_b2),
    }

    # Probe B3: Pediatrician validation
    scenario_b3 = {
        "description": (
            "Your pediatrician confirms: 'Magnesium supplementation at the right dose is safe "
            "and can support sleep in children who are picky eaters with low dietary variety.' "
            "Your child has been on Magnesium Gummies for 10 days. Pack finishes in 5 days. "
            "Rs 499 to reorder. Does this professional validation make you reorder?"
        ),
        "product": "LittleJoys Magnesium Gummies 30-day pack",
        "price_inr": 499,
        "simulation_tick": 40,
    }
    results_b3 = run_probe_batch("B-P3-ped-validation", scenario_b3, probe_personas)
    all_probe_results["B-P3"] = {
        "hypothesis": "Authority deficit: pediatrician validation is the missing confidence signal",
        "scenario": scenario_b3,
        "results": results_b3,
        "summary": summarize_probe(results_b3),
    }

    # Probe B4: Trial window was too short
    scenario_b4 = {
        "description": (
            "You've been giving your child LittleJoys Magnesium Gummies for only 10 days. "
            "You notice some improvement in sleep but you're not sure if it's real. "
            "The pack finishes in 5 days. Rs 499 to reorder. "
            "Your main concern: 10 days is not long enough to tell if it's working. "
            "What do you do?"
        ),
        "product": "LittleJoys Magnesium Gummies 30-day pack",
        "price_inr": 499,
        "simulation_tick": 45,
    }
    results_b4 = run_probe_batch("B-P4-short-trial-window", scenario_b4, probe_personas)
    all_probe_results["B-P4"] = {
        "hypothesis": "Trial window too short: 10-day window insufficient to prove efficacy",
        "scenario": scenario_b4,
        "results": results_b4,
        "summary": summarize_probe(results_b4),
    }

    return all_probe_results


def run_problem_c_probes(
    all_personas: dict[str, Persona],
    non_reorderer_ids: list[str],
) -> dict:
    """Run probes for Problem C: Nutrimix 7-14 expansion."""
    print("\n" + "=" * 60)
    print("PROBLEM C PROBES: Nutrimix 7-14 Expansion (vs Bournvita)")
    print("=" * 60)

    # C has more non-reorderers (25), use them all + some reorderers
    probe_persona_ids = non_reorderer_ids[:20].copy()
    all_ids = list(all_personas.keys())
    reorderers = [pid for pid in all_ids if pid not in non_reorderer_ids][:10]
    probe_persona_ids = probe_persona_ids + reorderers
    probe_persona_ids = probe_persona_ids[:30]

    probe_personas = [all_personas[pid] for pid in probe_persona_ids if pid in all_personas]

    all_probe_results = {}

    # Probe C1: Price justification — nutritional comparison
    scenario_c1 = {
        "description": (
            "LittleJoys push notification: 'Nutrimix has 3x the iron of Bournvita and zero "
            "added sugar. That's your Rs 250 explained.' With a comparison infographic showing "
            "micronutrient levels side-by-side. "
            "Your child has been on Nutrimix for 4 weeks. Pack running low. "
            "Rs 649 to reorder vs Bournvita at Rs 399. Does this comparison make you reorder Nutrimix?"
        ),
        "product": "LittleJoys Nutrimix 500g",
        "price_inr": 649,
        "simulation_tick": 55,
    }
    results_c1 = run_probe_batch("C-P1-nutrition-price-justification", scenario_c1, probe_personas)
    all_probe_results["C-P1"] = {
        "hypothesis": "Price premium not justified: clear nutritional comparison closes Rs 250 gap",
        "scenario": scenario_c1,
        "results": results_c1,
        "summary": summarize_probe(results_c1),
    }

    # Probe C2: Family pack reduces per-unit cost
    scenario_c2 = {
        "description": (
            "BigBasket offer: 2 x 500g Nutrimix packs for Rs 1,099 (Rs 549.50 each — Rs 100 "
            "saving vs buying two individually). Valid this week. "
            "Your child has been using Nutrimix for a month. Pack running low. "
            "Does this family pack deal make you reorder Nutrimix instead of switching to Bournvita?"
        ),
        "product": "LittleJoys Nutrimix 500g x2 Family Pack",
        "price_inr": 1099,
        "simulation_tick": 55,
    }
    results_c2 = run_probe_batch("C-P2-family-pack-deal", scenario_c2, probe_personas)
    all_probe_results["C-P2"] = {
        "hypothesis": "Price architecture: multi-pack deal reduces effective price and increases loyalty",
        "scenario": scenario_c2,
        "results": results_c2,
        "summary": summarize_probe(results_c2),
    }

    # Probe C3: Bournvita brand inertia
    scenario_c3 = {
        "description": (
            "It's time to reorder your child's drink mix. Nutrimix is Rs 649. "
            "Bournvita is Rs 399 — a brand your family has trusted for years. "
            "You saw a Bournvita 'Junior Champion' ad yesterday. "
            "Your child seems more alert since starting Nutrimix but it's hard to be sure. "
            "What do you do: reorder Nutrimix or switch back to Bournvita?"
        ),
        "product": "LittleJoys Nutrimix 500g",
        "price_inr": 649,
        "simulation_tick": 60,
    }
    results_c3 = run_probe_batch("C-P3-bournvita-brand-inertia", scenario_c3, probe_personas)
    all_probe_results["C-P3"] = {
        "hypothesis": "Bournvita brand inertia: legacy brand reasserts pull at reorder moment",
        "scenario": scenario_c3,
        "results": results_c3,
        "summary": summarize_probe(results_c3),
    }

    # Probe C4: Child preference (school-ager involvement)
    scenario_c4 = {
        "description": (
            "Your 9-year-old child says: 'I like the brown milk drink. Can we keep getting it?' "
            "They are referring to Nutrimix. Pack is running low. Rs 649 on BigBasket. "
            "Your child's preference influences your decision. Do you reorder?"
        ),
        "product": "LittleJoys Nutrimix 500g",
        "price_inr": 649,
        "simulation_tick": 58,
    }
    results_c4 = run_probe_batch("C-P4-child-preference-pull", scenario_c4, probe_personas)
    all_probe_results["C-P4"] = {
        "hypothesis": "Child preference: older child's explicit preference is a strong reorder driver",
        "scenario": scenario_c4,
        "results": results_c4,
        "summary": summarize_probe(results_c4),
    }

    return all_probe_results


def print_probe_summary(problem: str, probe_results: dict) -> None:
    print(f"\n{'='*60}")
    print(f"PROBE SUMMARY — PROBLEM {problem}")
    print(f"{'='*60}")
    for probe_id, probe_data in probe_results.items():
        summary = probe_data.get("summary", {})
        hyp = probe_data.get("hypothesis", "")
        pos_pct = summary.get("positive_pct", 0)
        outcome_counts = summary.get("outcome_counts", {})
        print(f"\n  {probe_id}: {hyp[:60]}")
        print(f"    Positive response (buy/trial): {pos_pct:.1f}%")
        print(f"    Outcomes: {outcome_counts}")
        top_obj = summary.get("top_objections", [])
        if top_obj:
            print(f"    Top objections: {top_obj[:3]}")


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        return 1

    # Load all personas
    all_personas = load_personas()

    # Load journey results and get non-reorderers
    logs_a = load_journey_results("A")
    logs_b = load_journey_results("B")
    logs_c = load_journey_results("C")

    non_reorderers_a = get_non_reorderers(logs_a)
    non_reorderers_b = get_non_reorderers(logs_b)
    non_reorderers_c = get_non_reorderers(logs_c)

    print(f"\nNon-reorderers — A: {len(non_reorderers_a)}, B: {len(non_reorderers_b)}, C: {len(non_reorderers_c)}")

    out_dir = PROJECT_ROOT / "data" / "population"

    # Run Problem A probes
    print("\nStarting Problem A probes...")
    try:
        probe_results_a = run_problem_a_probes(all_personas, non_reorderers_a)
        print_probe_summary("A", probe_results_a)
        out_path = out_dir / "probe_results_A.json"
        with out_path.open("w") as f:
            json.dump(probe_results_a, f, indent=2)
        print(f"\nSaved: {out_path}")
    except Exception as exc:
        print(f"ERROR in Problem A probes: {exc}")
        import traceback; traceback.print_exc()

    # Run Problem B probes
    print("\nStarting Problem B probes...")
    try:
        probe_results_b = run_problem_b_probes(all_personas, non_reorderers_b)
        print_probe_summary("B", probe_results_b)
        out_path = out_dir / "probe_results_B.json"
        with out_path.open("w") as f:
            json.dump(probe_results_b, f, indent=2)
        print(f"\nSaved: {out_path}")
    except Exception as exc:
        print(f"ERROR in Problem B probes: {exc}")
        import traceback; traceback.print_exc()

    # Run Problem C probes
    print("\nStarting Problem C probes...")
    try:
        probe_results_c = run_problem_c_probes(all_personas, non_reorderers_c)
        print_probe_summary("C", probe_results_c)
        out_path = out_dir / "probe_results_C.json"
        with out_path.open("w") as f:
            json.dump(probe_results_c, f, indent=2)
        print(f"\nSaved: {out_path}")
    except Exception as exc:
        print(f"ERROR in Problem C probes: {exc}")
        import traceback; traceback.print_exc()

    print("\n\nAll probes complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
