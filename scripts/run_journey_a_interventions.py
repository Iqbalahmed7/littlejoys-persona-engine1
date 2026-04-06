#!/usr/bin/env python3
"""
run_journey_a_interventions.py — Run intervention + counterfactual for Journey A.
Skips probes (already done). Uses existing probe_results_A.json.

Usage:
    source .env && PYTHONPATH=. .venv/bin/python3 scripts/run_journey_a_interventions.py
"""
from __future__ import annotations
import json, os, sys, random, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.taxonomy.schema import Persona
from src.simulation.batch_runner import run_batch
from src.simulation.journey_config import JourneyConfig, StimulusConfig
from src.simulation.journey_presets import PRESET_JOURNEY_A

OUT_DIR = PROJECT_ROOT / "data" / "population"


def load_personas() -> dict[str, Persona]:
    path = OUT_DIR / "personas_generated.json"
    with path.open() as f:
        data = json.load(f)
    personas: dict[str, Persona] = {}
    for i, p in enumerate(data):
        pid = str(p.get("id", f"persona_{i:03d}"))
        try:
            personas[pid] = Persona.model_validate(p)
        except Exception:
            pass
    print(f"Loaded {len(personas)} personas")
    return personas


def create_intervention_journey() -> JourneyConfig:
    intervention_stimuli = [
        StimulusConfig(
            id="A-INT-S50", tick=50, type="wom", source="whatsapp_group",
            content=(
                "WhatsApp message from parenting group: '3,400 parents reordered "
                "Nutrimix this month — here's why they kept going.' "
                "Includes quotes about appetite improvement and energy levels."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="A-INT-S55", tick=55, type="price_change", source="bigbasket_app",
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


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set"); return 1

    all_personas = load_personas()

    # Load lapsers
    with open(OUT_DIR / "journey_A_results.json") as f:
        d = json.load(f)
    logs = d["logs"]
    lapse_ids = [l["persona_id"] for l in logs if not l.get("error") and not l.get("reordered")]
    reorder_ids = [l["persona_id"] for l in logs if not l.get("error") and l.get("reordered")]
    print(f"Lapsers: {len(lapse_ids)}, Reorderers: {len(reorder_ids)}")

    # Build 50-persona sample: all lapsers (capped at 50) + fill with reorderers
    random.seed(42)
    sample_ids = lapse_ids[:50]
    remaining = 50 - len(sample_ids)
    if remaining > 0:
        sample_ids += random.sample(reorder_ids, min(remaining, len(reorder_ids)))
    sample_personas = [(pid, all_personas[pid]) for pid in sample_ids if pid in all_personas]
    print(f"Intervention sample: {len(sample_personas)} personas "
          f"({min(50, len(lapse_ids))} lapsers + {len(sample_personas)-min(50,len(lapse_ids))} reorderers)")

    intervention_journey = create_intervention_journey()

    # ── Intervention run ──────────────────────────────────────────────────────
    print(f"\n[4/5] Running intervention (loyalty discount + WOM) on {len(sample_personas)} personas...")
    int_result = run_batch(
        journey_config=intervention_journey,
        personas=sample_personas,
        concurrency=3,
        progress_callback=lambda done, total, log: print(
            f"  [{done:>2}/{total}] {log.get('display_name','?'):<28} reordered={log.get('reordered','?')}"
        ),
    )

    def agg_dict(agg):
        return {
            "total_personas": agg.total_personas,
            "reorder_rate_pct": agg.reorder_rate_pct,
            "first_decision_distribution": {
                k: {"count": v["count"], "pct": v["pct"]} if isinstance(v, dict) else {"count": v.count, "pct": v.pct}
                for k, v in agg.first_decision_distribution.items()
            },
            "second_decision_distribution": {
                k: {"count": v["count"], "pct": v["pct"]} if isinstance(v, dict) else {"count": v.count, "pct": v.pct}
                for k, v in agg.second_decision_distribution.items()
            },
            "second_decision_objections": agg.second_decision_objections,
            "second_decision_drivers": agg.second_decision_drivers,
        }

    int_out = {
        "journey_id": "A_intervention",
        "total_personas": int_result.personas_run,
        "errors": sum(1 for l in int_result.logs if l.get("error")),
        "elapsed_seconds": int_result.elapsed_seconds,
        "aggregate": agg_dict(int_result.aggregate),
        "logs": int_result.logs,
    }
    with open(OUT_DIR / "journey_A_intervention_results.json", "w") as f:
        json.dump(int_out, f, indent=2)
    print(f"\n  Intervention reorder rate: {int_result.aggregate.reorder_rate_pct:.1f}%")

    # ── Counterfactual (baseline on same sample) ──────────────────────────────
    print(f"\n[4b] Running counterfactual baseline on same {len(sample_personas)} personas...")
    cf_result = run_batch(
        journey_config=PRESET_JOURNEY_A,
        personas=sample_personas,
        concurrency=3,
        progress_callback=lambda done, total, log: print(
            f"  [{done:>2}/{total}] {log.get('display_name','?'):<28} reordered={log.get('reordered','?')}"
        ),
    )

    baseline_rr = cf_result.aggregate.reorder_rate_pct
    intervention_rr = int_result.aggregate.reorder_rate_pct
    lift_pp = intervention_rr - baseline_rr

    cf_out = {
        "journey_id": "A_counterfactual_baseline",
        "total_personas": cf_result.personas_run,
        "errors": sum(1 for l in cf_result.logs if l.get("error")),
        "elapsed_seconds": cf_result.elapsed_seconds,
        "aggregate": agg_dict(cf_result.aggregate),
        "counterfactual_comparison": {
            "baseline_reorder_rate_pct": baseline_rr,
            "intervention_reorder_rate_pct": intervention_rr,
            "lift_pp": lift_pp,
            "lift_pct_relative": round(100 * lift_pp / baseline_rr, 1) if baseline_rr else 0,
            "interventions_applied": [
                "A-INT-S50: WOM social proof at tick 50 (3,400 parents reordered)",
                "A-INT-S55: Loyalty discount Rs 599 (-Rs 50) at tick 55 via BigBasket",
            ],
        },
        "logs": cf_result.logs,
    }
    with open(OUT_DIR / "journey_A_counterfactual.json", "w") as f:
        json.dump(cf_out, f, indent=2)

    print(f"\n  === COUNTERFACTUAL RESULTS ===")
    print(f"  Baseline reorder rate (same 50-persona sample): {baseline_rr:.1f}%")
    print(f"  Intervention reorder rate:                      {intervention_rr:.1f}%")
    print(f"  Lift:                                           +{lift_pp:.1f}pp ({cf_out['counterfactual_comparison']['lift_pct_relative']:+.1f}% relative)")
    print(f"\n  Files saved:")
    print(f"    data/population/journey_A_intervention_results.json")
    print(f"    data/population/journey_A_counterfactual.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
