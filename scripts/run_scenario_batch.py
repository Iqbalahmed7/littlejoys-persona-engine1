#!/usr/bin/env python3
"""
run_scenario_batch.py — Run 5 stimuli + purchase decision across all clean personas.

Usage:
    ANTHROPIC_API_KEY=sk-... python3 scripts/run_scenario_batch.py
    python3 scripts/run_scenario_batch.py --max 20   # test on 20 personas first
    python3 scripts/run_scenario_batch.py --concurrency 3

Output:
    data/population/scenario_results.json
    Prints running progress + final summary table
"""
import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents import CognitiveAgent
from src.taxonomy.schema import Persona

TEST_STIMULI = [
    {
        "id": "S1", "type": "ad", "source": "instagram_feed", "brand": "littlejoys",
        "content": "LittleJoys: India's first clean-label nutrition drink for kids. No artificial colours, no preservatives. Trusted by 50,000 moms.",
        "simulation_tick": 1,
    },
    {
        "id": "S2", "type": "wom", "source": "friend_whatsapp", "brand": "littlejoys",
        "content": "My friend Ritu sent me a WhatsApp: 'Yaar try karo LittleJoys, Aarav ki immunity bahut improve hui hai, no side effects'",
        "simulation_tick": 5,
    },
    {
        "id": "S3", "type": "price_change", "source": "amazon_listing", "brand": "littlejoys",
        "content": "LittleJoys 500g pack now Rs 649 (was Rs 799). Limited time offer. Subscribe & Save for additional 10% off.",
        "simulation_tick": 8,
    },
    {
        "id": "S4", "type": "product", "source": "pediatrician_office", "brand": "littlejoys",
        "content": "Pediatrician mentioned: 'I've been recommending LittleJoys to parents whose kids have low iron. The absorption rate is better than most alternatives.'",
        "simulation_tick": 12,
    },
    {
        "id": "S5", "type": "social_event", "source": "school_whatsapp_group", "brand": "horlicks",
        "content": "School WhatsApp group: 'Which health drink does everyone give? My son refuses everything except Horlicks. Thinking of switching to something cleaner.'",
        "simulation_tick": 15,
    },
]

DECISION_SCENARIO = {
    "description": "You see LittleJoys available for purchase on BigBasket. Rs 649 for 500g. You have seen ads, heard from a friend, and your pediatrician mentioned it. Do you buy?",
    "product": "LittleJoys 500g",
    "price_inr": 649,
    "channel": "bigbasket",
    "simulation_tick": 20,
}


def load_clean_personas(max_n: int | None = None) -> list[tuple[str, Persona]]:
    """
    Load only the clean personas (no hard violations) from the population.
    Uses constraint_violations_report.json to filter.
    """
    violations_path = PROJECT_ROOT / "data" / "population" / "constraint_violations_report.json"
    hard_violation_ids: set[str] = set()

    if violations_path.exists():
        report = json.loads(violations_path.read_text())
        hard_violation_ids = set(report.get("personas_with_hard_violations", []))
        print(f"Filtering out {len(hard_violation_ids)} hard-violation personas.")

    candidates = [
        PROJECT_ROOT / "data" / "population" / "personas_generated.json",
        PROJECT_ROOT / "data" / "population" / "personas.json",
    ]

    all_personas = []
    for path in candidates:
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, list):
                for i, p_dict in enumerate(data):
                    pid = str(p_dict.get("id", f"persona_{i:03d}"))
                    if pid in hard_violation_ids:
                        continue
                    try:
                        all_personas.append((pid, Persona.model_validate(p_dict)))
                    except Exception as e:
                        print(f"  [SKIP] {pid}: {e}")
            break

    print(f"Loaded {len(all_personas)} clean personas.")
    if max_n:
        all_personas = all_personas[:max_n]
        print(f"Capped at {max_n} for this run.")
    return all_personas


def run_persona(pid: str, persona: Persona) -> dict:
    """
    Run the full scenario (5 stimuli + 1 decision) for a single persona.
    Returns a result dict. Catches and records errors without crashing.
    """
    result = {
        "persona_id": pid,
        "display_name": persona.display_name or pid,
        "age": persona.demographics.parent_age,
        "decision_style": persona.parent_traits.decision_style if persona.parent_traits else "unknown",
        "trust_anchor": persona.parent_traits.trust_anchor if persona.parent_traits else "unknown",
        "price_sensitivity": persona.budget_profile.price_sensitivity if persona.budget_profile else "unknown",
        "perception_results": [],
        "decision_result": None,
        "error": None,
    }

    try:
        agent = CognitiveAgent(persona)

        # Phase 1: run all 5 stimuli through perceive()
        for stimulus in TEST_STIMULI:
            try:
                pr = agent.perceive(stimulus)
                result["perception_results"].append({
                    "stimulus_id": stimulus["id"],
                    "importance": pr.importance,
                    "emotional_valence": pr.emotional_valence,
                    "reflection_trigger": pr.reflection_trigger_candidate,
                })
            except Exception as e:
                result["perception_results"].append({
                    "stimulus_id": stimulus["id"],
                    "error": str(e),
                })

        # Phase 2: run the purchase decision
        dr = agent.decide(DECISION_SCENARIO)
        result["decision_result"] = dr.to_dict()

    except Exception as e:
        result["error"] = str(e)

    return result


def aggregate_results(results: list[dict]) -> dict:
    """Compute summary statistics across all persona results."""
    decisions = Counter()
    wtp_values = []
    all_drivers = Counter()
    all_objections = Counter()
    errors = 0

    for r in results:
        if r.get("error"):
            errors += 1
            continue
        dr = r.get("decision_result")
        if not dr:
            continue
        decisions[dr.get("decision", "unknown")] += 1
        wtp = dr.get("willingness_to_pay_inr")
        if wtp is not None:
            wtp_values.append(wtp)
        for d in dr.get("key_drivers", []):
            all_drivers[d] += 1
        for o in dr.get("objections", []):
            all_objections[o] += 1

    total = len(results) - errors

    summary = {
        "total_personas": len(results),
        "errors": errors,
        "decision_distribution": {
            k: {"count": v, "pct": round(v / max(total, 1) * 100, 1)}
            for k, v in decisions.most_common()
        },
        "wtp_stats": {},
        "top_drivers": dict(all_drivers.most_common(10)),
        "top_objections": dict(all_objections.most_common(10)),
    }

    if wtp_values:
        import statistics
        summary["wtp_stats"] = {
            "mean": round(statistics.mean(wtp_values)),
            "median": round(statistics.median(wtp_values)),
            "stdev": round(statistics.stdev(wtp_values) if len(wtp_values) > 1 else 0),
            "min": min(wtp_values),
            "max": max(wtp_values),
            "n": len(wtp_values),
        }

    return summary


def print_summary(summary: dict) -> None:
    print("\n" + "=" * 55)
    print("SCENARIO BATCH — RESULTS SUMMARY")
    print("=" * 55)
    print(f"Personas run:  {summary['total_personas']}")
    print(f"Errors:        {summary['errors']}")
    print()

    print("Decision distribution:")
    for decision, data in summary["decision_distribution"].items():
        bar = "#" * int(data["pct"] / 2)
        print(f"  {decision:<15} {data['count']:>4}  ({data['pct']:>5.1f}%)  {bar}")

    if summary.get("wtp_stats"):
        w = summary["wtp_stats"]
        print(f"\nWillingness to pay (n={w['n']}):")
        print(f"  Mean:   Rs {w['mean']}")
        print(f"  Median: Rs {w['median']}")
        print(f"  Range:  Rs {w['min']} \u2013 Rs {w['max']}")

    print("\nTop drivers:")
    for d, count in list(summary["top_drivers"].items())[:5]:
        print(f"  {d}: {count}")

    print("\nTop objections:")
    for o, count in list(summary["top_objections"].items())[:5]:
        print(f"  {o}: {count}")

    print("=" * 55)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=None,
                        help="Max personas to run (default: all clean)")
    parser.add_argument("--concurrency", type=int, default=3,
                        help="Parallel workers (default 3)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    personas = load_clean_personas(max_n=args.max)
    if not personas:
        print("No clean personas found.")
        sys.exit(1)

    print(f"\nRunning scenario batch: {len(personas)} personas, "
          f"concurrency={args.concurrency}...")

    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(run_persona, pid, persona): pid
            for pid, persona in personas
        }
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            status = "ERROR" if result.get("error") else result.get("decision_result", {}).get("decision", "?")
            print(f"  [{i:>3}/{len(personas)}] {result['persona_id']:<40} -> {status}")

    elapsed = round(time.time() - start_time, 1)
    print(f"\nCompleted in {elapsed}s")

    summary = aggregate_results(results)
    print_summary(summary)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_personas": len(personas),
        "elapsed_seconds": elapsed,
        "summary": summary,
        "results": results,
    }

    out_path = PROJECT_ROOT / "data" / "population" / "scenario_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nFull results written: {out_path}")


if __name__ == "__main__":
    main()
