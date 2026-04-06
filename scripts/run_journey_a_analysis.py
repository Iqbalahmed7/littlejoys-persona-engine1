#!/usr/bin/env python3
"""
run_journey_a_analysis.py — Full Journey A analysis pipeline.

Steps:
  1. Load Journey A results + build hypothesis tree
  2. Run probes on lapse cohort (81 lapsers)
  3. Synthesise insights
  4. Run intervention journey (baseline + intervention on lapse cohort)
  5. Run counterfactual (intervention vs baseline)
  6. Save all outputs

Outputs:
  data/population/probe_results_A.json
  data/population/journey_A_intervention_results.json
  data/population/journey_A_counterfactual.json

Usage:
    source .env && PYTHONPATH=. .venv/bin/python3 scripts/run_journey_a_analysis.py
"""

from __future__ import annotations

import json
import os
import sys
import random
import time
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.agent import CognitiveAgent          # noqa: E402
from src.taxonomy.schema import Persona              # noqa: E402
from src.simulation.batch_runner import run_batch    # noqa: E402
from src.simulation.journey_config import JourneyConfig, StimulusConfig  # noqa: E402
from src.simulation.journey_presets import PRESET_JOURNEY_A  # noqa: E402

OUT_DIR = PROJECT_ROOT / "data" / "population"


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
    print(f"Loaded {len(personas)} personas")
    return personas


def load_journey_a_results() -> list[dict]:
    path = OUT_DIR / "journey_A_results.json"
    with path.open() as f:
        data = json.load(f)
    return data["logs"]


def get_lapse_cohort(logs: list[dict]) -> list[str]:
    return [l["persona_id"] for l in logs if not l.get("error") and not l.get("reordered")]


def get_reorder_cohort(logs: list[dict]) -> list[str]:
    return [l["persona_id"] for l in logs if not l.get("error") and l.get("reordered")]


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
    print(f"\n  Probe: {probe_id} ({len(personas)} personas)")
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
    positive = sum(outcome_counts.get(k, 0) for k in {"buy", "trial"})
    return {
        "total": total,
        "outcome_counts": outcome_counts,
        "positive_pct": round(100 * positive / total, 1) if total else 0,
        "top_drivers": Counter(all_drivers).most_common(5),
        "top_objections": Counter(all_objections).most_common(5),
    }


# ── Step 1: Hypothesis Tree ────────────────────────────────────────────────────

def build_hypothesis_tree(lapse_count: int, reorder_count: int, top_lapse_reasons: list) -> dict:
    """Build a structured hypothesis tree grounded in Journey A results."""
    tree = {
        "problem": "Why do 39.6% of Nutrimix first-time buyers not reorder?",
        "reorder_rate": 60.4,
        "lapse_rate": 39.6,
        "lapse_n": lapse_count,
        "hypotheses": [
            {
                "id": "H1",
                "hypothesis": "Price friction: no reorder discount removes the trigger to act",
                "evidence": "Top lapse reason across runs: no_discount_available_this_time (7/81 lapsers explicitly cited)",
                "confidence": "HIGH",
                "probe": "A-P1",
                "sub_hypotheses": [
                    {"id": "H1a", "text": "Rs 649 feels acceptable with a discount, not without"},
                    {"id": "H1b", "text": "Initial purchase was discount-driven; full-price repeat feels like overpaying"},
                    {"id": "H1c", "text": "Price-sensitive Tier 2/3 parents defer without a clear save trigger"},
                ]
            },
            {
                "id": "H2",
                "hypothesis": "Outcome uncertainty: no measurable benefit makes Rs 649 feel unjustified",
                "evidence": "insufficient_proof_of_tangible_benefit_in_own_child cited in lapse reasons",
                "confidence": "HIGH",
                "probe": "A-P3",
                "sub_hypotheses": [
                    {"id": "H2a", "text": "5 weeks is too short to see visible nutritional change"},
                    {"id": "H2b", "text": "Parents expect appetite/energy signals but see none in 30 days"},
                    {"id": "H2c", "text": "Without pediatrician follow-up, there's no external validation"},
                ]
            },
            {
                "id": "H3",
                "hypothesis": "Social proof deficit: no community reorder signal leaves habitual parents without reinforcement",
                "evidence": "prior_peer_validation is top reorder DRIVER — its absence predicts lapse",
                "confidence": "MEDIUM",
                "probe": "A-P2",
                "sub_hypotheses": [
                    {"id": "H3a", "text": "Parents who reorder are motivated by peer confirmation, not self-assessment"},
                    {"id": "H3b", "text": "Lapsers lack WhatsApp/peer group reinforcement at the reorder moment"},
                ]
            },
            {
                "id": "H4",
                "hypothesis": "Competitive displacement: Horlicks/Complan reclaim attention at the reorder window",
                "evidence": "Horlicks retargeting ad at tick 32 was in stimulus schedule",
                "confidence": "MEDIUM",
                "probe": "A-P4",
                "sub_hypotheses": [
                    {"id": "H4a", "text": "Established brands are recalled at 'time to reorder' moment"},
                    {"id": "H4b", "text": "Without a counter-stimulus, default brand preference reasserts"},
                ]
            },
        ]
    }
    return tree


# ── Step 2: Probes ─────────────────────────────────────────────────────────────

def run_all_probes(all_personas: dict[str, Persona], lapse_ids: list[str], reorder_ids: list[str]) -> dict:
    # 30 personas: all lapsers up to 30, then fill with reorderers
    probe_ids = lapse_ids[:30]
    remaining = 30 - len(probe_ids)
    probe_ids += reorder_ids[:remaining]
    probe_personas = [all_personas[pid] for pid in probe_ids if pid in all_personas]
    print(f"\n  Probe cohort: {len(probe_personas)} personas ({min(30, len(lapse_ids))} lapsers + {remaining} reorderers)")

    all_results = {}

    # A-P1: Loyalty discount
    all_results["A-P1"] = {
        "hypothesis": "H1: Price friction — a loyalty discount removes reorder barrier",
        "scenario": {
            "description": (
                "BigBasket sends a loyalty price notification — Rs 599 on your second Nutrimix pack "
                "(Rs 50 off, valid 48 hours). You finished your first pack and your child liked it. "
                "Would this discounted price prompt you to reorder now?"
            ),
            "product": "LittleJoys Nutrimix 500g",
            "price_inr": 599,
            "simulation_tick": 65,
        },
        "results": run_probe_batch("A-P1", {
            "description": "BigBasket loyalty notification: Rs 599 (Rs 50 off), 48 hours, child liked the product. Reorder?",
            "product": "LittleJoys Nutrimix 500g", "price_inr": 599, "simulation_tick": 65,
        }, probe_personas, concurrency=3),
    }
    all_results["A-P1"]["summary"] = summarize_probe(all_results["A-P1"]["results"])

    # A-P2: Social proof WOM
    all_results["A-P2"] = {
        "hypothesis": "H3: Social proof deficit — WOM reorder data reinforces habit",
        "scenario": {
            "description": (
                "WhatsApp message from parenting group: '3,400 parents reordered Nutrimix this month — "
                "here's why they kept going.' Short quotes about appetite improvement and energy. "
                "Does this make you more likely to reorder?"
            ),
            "product": "LittleJoys Nutrimix 500g",
            "price_inr": 649,
            "simulation_tick": 62,
        },
        "results": run_probe_batch("A-P2", {
            "description": "WhatsApp: 3,400 parents reordered Nutrimix this month, quotes about appetite/energy. Reorder prompted?",
            "product": "LittleJoys Nutrimix 500g", "price_inr": 649, "simulation_tick": 62,
        }, probe_personas, concurrency=3),
    }
    all_results["A-P2"]["summary"] = summarize_probe(all_results["A-P2"]["results"])

    # A-P3: Outcome uncertainty
    all_results["A-P3"] = {
        "hypothesis": "H2: Outcome uncertainty — unclear results make Rs 649 feel risky",
        "scenario": {
            "description": (
                "First Nutrimix pack finished. 5 weeks in. You think there might be some appetite improvement "
                "but it's hard to tell. On BigBasket: Rs 649, no discount. "
                "Weighing whether it's worth it given you can't clearly see results. What do you do?"
            ),
            "product": "LittleJoys Nutrimix 500g",
            "price_inr": 649,
            "simulation_tick": 60,
        },
        "results": run_probe_batch("A-P3", {
            "description": "Pack finished, 5 weeks, unclear appetite improvement, Rs 649 no discount. Worth reordering?",
            "product": "LittleJoys Nutrimix 500g", "price_inr": 649, "simulation_tick": 60,
        }, probe_personas, concurrency=3),
    }
    all_results["A-P3"]["summary"] = summarize_probe(all_results["A-P3"]["results"])

    # A-P4: Competitive switch
    all_results["A-P4"] = {
        "hypothesis": "H4: Competitive displacement — pharmacist Complan suggestion at reorder window",
        "scenario": {
            "description": (
                "Pharmacist suggested Complan as a 'safe default' for children — Rs 420 for 500g "
                "(Rs 229 cheaper than Nutrimix). Your first Nutrimix pack just finished. Switch to save?"
            ),
            "product": "LittleJoys Nutrimix 500g",
            "price_inr": 649,
            "simulation_tick": 60,
        },
        "results": run_probe_batch("A-P4", {
            "description": "Pharmacist suggested Complan at Rs 420 (Rs 229 cheaper). First Nutrimix pack done. Switch?",
            "product": "LittleJoys Nutrimix 500g", "price_inr": 649, "simulation_tick": 60,
        }, probe_personas, concurrency=3),
    }
    all_results["A-P4"]["summary"] = summarize_probe(all_results["A-P4"]["results"])

    return all_results


def print_probe_summary(probe_results: dict) -> None:
    print("\n" + "=" * 60)
    print("PROBE SUMMARY")
    print("=" * 60)
    for probe_id, data in probe_results.items():
        s = data.get("summary", {})
        print(f"\n  {probe_id}: {data.get('hypothesis','')[:70]}")
        print(f"    Positive (buy/trial): {s.get('positive_pct', 0):.1f}%  |  outcomes: {s.get('outcome_counts', {})}")
        if s.get("top_objections"):
            print(f"    Top objections: {s['top_objections'][:3]}")


# ── Step 3: Interventions ──────────────────────────────────────────────────────

def create_intervention_journey() -> JourneyConfig:
    """Journey A + loyalty discount trigger + WOM social proof."""
    intervention_stimuli = [
        StimulusConfig(
            id="A-INT-S50",
            tick=50,
            type="wom",
            source="whatsapp_group",
            content=(
                "WhatsApp message from parenting group: '3,400 parents reordered "
                "Nutrimix this month — here's why they kept going.' "
                "Includes quotes about appetite improvement and energy levels."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="A-INT-S55",
            tick=55,
            type="price_change",
            source="bigbasket_app",
            content=(
                "BigBasket loyalty notification: Rs 599 on your second Nutrimix pack "
                "(Rs 50 off the regular Rs 649). Valid for 48 hours."
            ),
            brand="littlejoys",
        ),
    ]
    all_stimuli = sorted(list(PRESET_JOURNEY_A.stimuli) + intervention_stimuli, key=lambda s: s.tick)
    return JourneyConfig(
        journey_id="A_intervention",
        total_ticks=PRESET_JOURNEY_A.total_ticks,
        primary_brand=PRESET_JOURNEY_A.primary_brand,
        stimuli=all_stimuli,
        decisions=PRESET_JOURNEY_A.decisions,
    )


def get_intervention_sample(
    all_personas: dict[str, Persona],
    lapse_ids: list[str],
    reorder_ids: list[str],
    sample_size: int = 50,
    seed: int = 42,
) -> list[tuple[str, Persona]]:
    random.seed(seed)
    # All lapsers + fill with reorderers
    sample_ids = lapse_ids.copy()
    remaining = sample_size - len(sample_ids)
    if remaining > 0:
        sample_ids += random.sample(reorder_ids, min(remaining, len(reorder_ids)))
    sample_ids = sample_ids[:sample_size]
    result = [(pid, all_personas[pid]) for pid in sample_ids if pid in all_personas]
    print(f"  Intervention sample: {len(result)} personas ({len(lapse_ids)} lapsers + {len(result)-len(lapse_ids)} reorderers)")
    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        return 1

    t0 = time.time()

    # ── Load data ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("JOURNEY A ANALYSIS PIPELINE")
    print("=" * 60)

    all_personas = load_personas()
    logs_a = load_journey_a_results()
    lapse_ids = get_lapse_cohort(logs_a)
    reorder_ids = get_reorder_cohort(logs_a)
    print(f"Journey A: {len(lapse_ids)} lapsers, {len(reorder_ids)} reorderers")

    # Load top lapse reasons from aggregate
    with open(OUT_DIR / "journey_A_results.json") as f:
        a_data = json.load(f)
    top_lapse = a_data.get("aggregate", {}).get("second_decision_objections", {})

    # ── Step 1: Hypothesis Tree ────────────────────────────────────────────────
    print("\n[1/5] Building hypothesis tree...")
    htree = build_hypothesis_tree(len(lapse_ids), len(reorder_ids), list(top_lapse.items())[:5])
    out_path = OUT_DIR / "journey_A_hypothesis_tree.json"
    with out_path.open("w") as f:
        json.dump(htree, f, indent=2)
    print(f"  Saved: {out_path}")
    print(f"  Hypotheses: {[h['id'] for h in htree['hypotheses']]}")

    # ── Step 2: Probes ─────────────────────────────────────────────────────────
    print("\n[2/5] Running probes on lapse cohort...")
    probe_results = run_all_probes(all_personas, lapse_ids, reorder_ids)
    print_probe_summary(probe_results)
    out_path = OUT_DIR / "probe_results_A.json"
    with out_path.open("w") as f:
        json.dump(probe_results, f, indent=2)
    print(f"\n  Saved: {out_path}")

    # ── Step 3: Synthesise insights ────────────────────────────────────────────
    print("\n[3/5] Synthesising probe insights...")
    insights = {}
    for pid, data in probe_results.items():
        s = data["summary"]
        insights[pid] = {
            "hypothesis": data["hypothesis"],
            "positive_pct": s["positive_pct"],
            "outcome_counts": s["outcome_counts"],
            "top_drivers": s["top_drivers"],
            "top_objections": s["top_objections"],
            "verdict": (
                "CONFIRMED" if s["positive_pct"] >= 60 else
                "PARTIAL" if s["positive_pct"] >= 35 else
                "NOT CONFIRMED"
            ),
        }
        print(f"  {pid}: {insights[pid]['verdict']} ({s['positive_pct']:.1f}% positive)")

    # Determine which hypotheses to act on
    confirmed = [pid for pid, ins in insights.items() if ins["verdict"] in ("CONFIRMED", "PARTIAL")]
    print(f"  Hypotheses confirmed/partial: {confirmed}")

    # ── Step 4a: Intervention run ──────────────────────────────────────────────
    print("\n[4/5] Running intervention journey (A + loyalty discount + WOM)...")
    intervention_journey = create_intervention_journey()
    sample_personas = get_intervention_sample(all_personas, lapse_ids, reorder_ids, sample_size=50)

    int_result = run_batch(
        journey_config=intervention_journey,
        personas=sample_personas,
        concurrency=3,
        progress_callback=lambda done, total, log: print(
            f"  [{done:>2}/{total}] {log.get('display_name','?'):<28} reordered={log.get('reordered', '?')}"
        ),
    )

    int_out = {
        "journey_id": "A_intervention",
        "total_personas": int_result.personas_run,
        "errors": sum(1 for l in int_result.logs if l.get("error")),
        "elapsed_seconds": int_result.elapsed_seconds,
        "aggregate": {
            "total_personas": int_result.aggregate.total_personas,
            "reorder_rate_pct": int_result.aggregate.reorder_rate_pct,
            "first_decision_distribution": {
                k: {"count": v.count, "pct": v.pct}
                for k, v in int_result.aggregate.first_decision_distribution.items()
            },
            "second_decision_distribution": {
                k: {"count": v.count, "pct": v.pct}
                for k, v in int_result.aggregate.second_decision_distribution.items()
            },
            "second_decision_objections": int_result.aggregate.second_decision_objections,
            "second_decision_drivers": int_result.aggregate.second_decision_drivers,
        },
        "logs": int_result.logs,
    }
    out_path = OUT_DIR / "journey_A_intervention_results.json"
    with out_path.open("w") as f:
        json.dump(int_out, f, indent=2)
    print(f"\n  Intervention reorder rate: {int_result.aggregate.reorder_rate_pct:.1f}%")
    print(f"  Saved: {out_path}")

    # ── Step 4b: Counterfactual (baseline on same sample) ─────────────────────
    print("\n[4b] Running counterfactual (baseline journey on same sample)...")
    cf_result = run_batch(
        journey_config=PRESET_JOURNEY_A,
        personas=sample_personas,
        concurrency=3,
        progress_callback=lambda done, total, log: print(
            f"  [{done:>2}/{total}] {log.get('display_name','?'):<28} reordered={log.get('reordered', '?')}"
        ),
    )

    cf_out = {
        "journey_id": "A_counterfactual_baseline",
        "total_personas": cf_result.personas_run,
        "errors": sum(1 for l in cf_result.logs if l.get("error")),
        "elapsed_seconds": cf_result.elapsed_seconds,
        "aggregate": {
            "total_personas": cf_result.aggregate.total_personas,
            "reorder_rate_pct": cf_result.aggregate.reorder_rate_pct,
            "first_decision_distribution": {
                k: {"count": v.count, "pct": v.pct}
                for k, v in cf_result.aggregate.first_decision_distribution.items()
            },
            "second_decision_distribution": {
                k: {"count": v.count, "pct": v.pct}
                for k, v in cf_result.aggregate.second_decision_distribution.items()
            },
        },
        "logs": cf_result.logs,
    }

    # Compute lift
    baseline_rr = cf_result.aggregate.reorder_rate_pct
    intervention_rr = int_result.aggregate.reorder_rate_pct
    lift_pp = intervention_rr - baseline_rr
    cf_out["counterfactual_comparison"] = {
        "baseline_reorder_rate_pct": baseline_rr,
        "intervention_reorder_rate_pct": intervention_rr,
        "lift_pp": lift_pp,
        "lift_pct_relative": round(100 * lift_pp / baseline_rr, 1) if baseline_rr else 0,
        "interventions_applied": ["A-INT-S50 (WOM social proof tick 50)", "A-INT-S55 (Rs 50 loyalty discount tick 55)"],
    }

    out_path = OUT_DIR / "journey_A_counterfactual.json"
    with out_path.open("w") as f:
        json.dump(cf_out, f, indent=2)
    print(f"\n  Baseline reorder rate (same sample): {baseline_rr:.1f}%")
    print(f"  Intervention reorder rate: {intervention_rr:.1f}%")
    print(f"  Lift: +{lift_pp:.1f}pp  ({cf_out['counterfactual_comparison']['lift_pct_relative']:+.1f}% relative)")
    print(f"  Saved: {out_path}")

    # ── Step 5: Summary ────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print(f"\n[5/5] Pipeline complete in {elapsed/60:.1f} min")
    print("\n  === JOURNEY A FINDINGS ===")
    print(f"  Baseline reorder rate (200 personas):  60.4%")
    print(f"  Counterfactual baseline (50 personas): {baseline_rr:.1f}%")
    print(f"  Intervention reorder rate:             {intervention_rr:.1f}%")
    print(f"  Intervention lift:                     +{lift_pp:.1f}pp")
    for pid, ins in insights.items():
        print(f"  {pid}: {ins['verdict']} — {ins['positive_pct']:.1f}% responded positively")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
