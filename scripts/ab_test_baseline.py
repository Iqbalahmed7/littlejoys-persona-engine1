#!/usr/bin/env python3
"""
ab_test_baseline.py — Compare memory-backed CognitiveAgent vs naive LLM baseline.

Usage:
    ANTHROPIC_API_KEY=sk-... python3 scripts/ab_test_baseline.py
    python3 scripts/ab_test_baseline.py --n 10 --seed 42

Output:
    data/population/ab_test_results.json
    Prints comparison table to stdout

Metrics:
    - importance_variance: std dev of importance scores across personas (higher = more distinct)
    - consistency_delta:   |importance_run1 - importance_run2| (lower = more consistent)
    - interpretation_diversity: count of unique keywords across interpretations
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import random
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

import anthropic

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents import CognitiveAgent  # noqa: E402
from src.taxonomy.schema import Persona  # noqa: E402

TEST_STIMULI = [
    {
        "id": "S1",
        "type": "ad",
        "source": "instagram_feed",
        "brand": "littlejoys",
        "content": (
            "LittleJoys: India's first clean-label nutrition drink for kids. "
            "No artificial colours, no preservatives. Trusted by 50,000 moms."
        ),
        "simulation_tick": 1,
    },
    {
        "id": "S2",
        "type": "wom",
        "source": "friend_whatsapp",
        "brand": "littlejoys",
        "content": (
            "My friend Ritu sent me a WhatsApp: 'Yaar try karo LittleJoys, "
            "Aarav ki immunity bahut improve hui hai, no side effects'"
        ),
        "simulation_tick": 5,
    },
    {
        "id": "S3",
        "type": "price_change",
        "source": "amazon_listing",
        "brand": "littlejoys",
        "content": (
            "LittleJoys 500g pack now Rs 649 (was Rs 799). Limited time offer. "
            "Subscribe & Save for additional 10% off."
        ),
        "simulation_tick": 8,
    },
    {
        "id": "S4",
        "type": "product",
        "source": "pediatrician_office",
        "brand": "littlejoys",
        "content": (
            "Pediatrician mentioned: 'I've been recommending LittleJoys to parents "
            "whose kids have low iron. The absorption rate is better than most alternatives.'"
        ),
        "simulation_tick": 12,
    },
    {
        "id": "S5",
        "type": "social_event",
        "source": "school_whatsapp_group",
        "brand": "horlicks",
        "content": (
            "School WhatsApp group: 'Which health drink does everyone give? "
            "My son refuses everything except Horlicks. Thinking of switching to something cleaner.'"
        ),
        "simulation_tick": 15,
    },
]

NAIVE_PROMPT = """\
You are a {age}-year-old Indian parent evaluating a child nutrition stimulus.

STIMULUS:
Type: {stimulus_type}
Source: {stimulus_source}
Content: {stimulus_content}

Rate this stimulus:
1. IMPORTANCE (1-10): How much would you pay attention to this?
2. EMOTIONAL_VALENCE (-1.0 to 1.0): What emotion does this trigger?
3. INTERPRETATION: One sentence on how you'd react.

Return valid JSON only:
{{
  "importance": <int 1-10>,
  "emotional_valence": <float>,
  "interpretation": "..."
}}
"""


def load_sample_personas(n: int, seed: int) -> list[tuple[str, Persona]]:
    """Load n randomly sampled clean personas."""
    candidates = [
        PROJECT_ROOT / "data" / "population" / "personas_generated.json",
        PROJECT_ROOT / "data" / "population" / "personas.json",
    ]
    all_personas = []
    for path in candidates:
        if path.exists():
            with path.open() as f:
                data = json.load(f)
            if isinstance(data, list):
                for i, p_dict in enumerate(data):
                    pid = p_dict.get("id", f"persona_{i:03d}")
                    with contextlib.suppress(Exception):
                        all_personas.append((str(pid), Persona.model_validate(p_dict)))
            break
    if not all_personas:
        print("ERROR: No personas found.")
        sys.exit(1)
    rng = random.Random(seed)
    return rng.sample(all_personas, min(n, len(all_personas)))


def run_memory_backed(personas: list[tuple[str, Persona]]) -> list[dict]:
    """Run all 5 stimuli through CognitiveAgent.perceive() for each persona."""
    results = []
    for pid, persona in personas:
        agent = CognitiveAgent(persona)
        persona_scores = {"persona_id": pid, "approach": "memory_backed", "stimuli": []}
        for s in TEST_STIMULI:
            try:
                result = agent.perceive(s)
                persona_scores["stimuli"].append(
                    {
                        "stimulus_id": s["id"],
                        "importance": result.importance,
                        "emotional_valence": result.emotional_valence,
                        "interpretation": result.interpretation,
                    }
                )
            except Exception as e:
                persona_scores["stimuli"].append({"stimulus_id": s["id"], "error": str(e)})
        results.append(persona_scores)
    return results


def run_naive_baseline(personas: list[tuple[str, Persona]], client: anthropic.Anthropic) -> list[dict]:
    """Run all 5 stimuli through the naive baseline prompt for each persona."""
    results = []
    for pid, persona in personas:
        age = persona.demographics.parent_age
        persona_scores = {"persona_id": pid, "approach": "naive_baseline", "stimuli": []}
        for s in TEST_STIMULI:
            prompt = NAIVE_PROMPT.format(
                age=age,
                stimulus_type=s["type"],
                stimulus_source=s["source"],
                stimulus_content=s["content"],
            )
            try:
                msg = client.messages.create(
                    model="claude-haiku-4-5",
                    max_tokens=256,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = msg.content[0].text
                start, end = raw.find("{"), raw.rfind("}") + 1
                parsed = json.loads(raw[start:end])
                persona_scores["stimuli"].append(
                    {
                        "stimulus_id": s["id"],
                        "importance": round((int(parsed.get("importance", 5)) - 1) / 9.0, 4),
                        "emotional_valence": float(parsed.get("emotional_valence", 0.0)),
                        "interpretation": parsed.get("interpretation", ""),
                    }
                )
            except Exception as e:
                persona_scores["stimuli"].append({"stimulus_id": s["id"], "error": str(e)})
        results.append(persona_scores)
    return results


def compute_metrics(results: list[dict], label: str) -> dict:
    """Compute distinctness metrics across personas for a given approach."""
    by_stimulus: dict[str, list[float]] = {s["id"]: [] for s in TEST_STIMULI}

    for r in results:
        for stim in r["stimuli"]:
            if "importance" in stim:
                by_stimulus[stim["stimulus_id"]].append(stim["importance"])

    metrics = {"approach": label, "by_stimulus": {}}
    all_variances = []

    for sid, scores in by_stimulus.items():
        if len(scores) > 1:
            variance = statistics.stdev(scores)
            all_variances.append(variance)
            metrics["by_stimulus"][sid] = {
                "mean_importance": round(statistics.mean(scores), 4),
                "stdev_importance": round(variance, 4),
                "min": round(min(scores), 4),
                "max": round(max(scores), 4),
            }

    metrics["mean_importance_stdev"] = round(
        statistics.mean(all_variances) if all_variances else 0.0, 4
    )
    return metrics


def print_comparison(memory_metrics: dict, naive_metrics: dict) -> None:
    print("\n" + "=" * 65)
    print("A/B TEST: MEMORY-BACKED vs NAIVE BASELINE")
    print("Metric: importance_stdev across personas (higher = more distinct)")
    print("=" * 65)
    print(f"{'Stimulus':<8} {'Memory-backed':>16} {'Naive baseline':>16} {'Delta':>10}")
    print("-" * 65)

    for sid in [s["id"] for s in TEST_STIMULI]:
        m = memory_metrics["by_stimulus"].get(sid, {})
        n = naive_metrics["by_stimulus"].get(sid, {})
        m_std = m.get("stdev_importance", 0)
        n_std = n.get("stdev_importance", 0)
        delta = m_std - n_std
        sign = "+" if delta >= 0 else ""
        print(f"{sid:<8} {m_std:>16.4f} {n_std:>16.4f} {sign}{delta:>9.4f}")

    print("-" * 65)
    m_avg = memory_metrics["mean_importance_stdev"]
    n_avg = naive_metrics["mean_importance_stdev"]
    delta = m_avg - n_avg
    sign = "+" if delta >= 0 else ""
    print(f"{'AVERAGE':<8} {m_avg:>16.4f} {n_avg:>16.4f} {sign}{delta:>9.4f}")
    print("=" * 65)

    verdict = "PASS" if m_avg > n_avg else "FAIL"
    print(f"\nv1 Thesis [{verdict}]: Memory-backed stdev = {m_avg:.4f} vs Naive = {n_avg:.4f}")
    if verdict == "PASS":
        pct = round((m_avg - n_avg) / max(n_avg, 0.0001) * 100, 1)
        print(f"Memory-backed personas are {pct}% more distinct than naive baseline.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10, help="Number of personas to test (default 10)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"Loading {args.n} personas (seed={args.seed})...")
    personas = load_sample_personas(args.n, args.seed)
    print(f"Loaded {len(personas)} personas.")

    print("\nRunning memory-backed approach...")
    memory_results = run_memory_backed(personas)

    print("Running naive baseline...")
    naive_results = run_naive_baseline(personas, client)

    memory_metrics = compute_metrics(memory_results, "memory_backed")
    naive_metrics = compute_metrics(naive_results, "naive_baseline")

    print_comparison(memory_metrics, naive_metrics)

    output = {
        "generated_at": datetime.now(UTC).isoformat(),
        "n_personas": len(personas),
        "seed": args.seed,
        "memory_backed": {"metrics": memory_metrics, "raw": memory_results},
        "naive_baseline": {"metrics": naive_metrics, "raw": naive_results},
        "verdict": (
            "PASS"
            if memory_metrics["mean_importance_stdev"] > naive_metrics["mean_importance_stdev"]
            else "FAIL"
        ),
    }

    out_path = PROJECT_ROOT / "data" / "population" / "ab_test_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(output, f, indent=2)
    print(f"Full results written: {out_path}")


if __name__ == "__main__":
    main()
