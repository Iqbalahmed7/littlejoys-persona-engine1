#!/usr/bin/env python3
"""
run_intervention_batch.py — Run intervention journeys for problems A, B, C.

Adds targeted stimuli based on confirmed probe findings.
Runs on a 50-persona sample (non-reorderers + random reorderers).

Usage:
    ANTHROPIC_API_KEY=sk-... python3 scripts/run_intervention_batch.py

Output:
    data/population/journey_A_intervention_results.json
    data/population/journey_B_intervention_results.json
    data/population/journey_C_intervention_results.json
"""

from __future__ import annotations

import json
import os
import sys
import random
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation.batch_runner import BatchResult, run_batch  # noqa: E402
from src.simulation.journey_config import JourneyConfig, StimulusConfig  # noqa: E402
from src.simulation.journey_presets import list_presets  # noqa: E402
from src.taxonomy.schema import Persona  # noqa: E402


def load_personas(max_n: int | None = None) -> list[tuple[str, Persona]]:
    path = PROJECT_ROOT / "data" / "population" / "personas_generated.json"
    with path.open() as f:
        data = json.load(f)
    personas: list[tuple[str, Persona]] = []
    for i, p_dict in enumerate(data):
        pid = str(p_dict.get("id", f"persona_{i:03d}"))
        try:
            personas.append((pid, Persona.model_validate(p_dict)))
        except Exception as exc:
            print(f"  [SKIP] {pid}: {exc}")
    if max_n:
        personas = personas[:max_n]
    print(f"Loaded {len(personas)} personas")
    return personas


def load_journey_results(journey_id: str) -> list[dict]:
    path = PROJECT_ROOT / "data" / "population" / f"journey_{journey_id}_results.json"
    with path.open() as f:
        data = json.load(f)
    return data["logs"]


def get_sample_personas(
    all_personas: list[tuple[str, Persona]],
    journey_logs: list[dict],
    sample_size: int = 50,
    seed: int = 42,
) -> list[tuple[str, Persona]]:
    """Get sample: all non-reorderers + random reorderers, capped at sample_size."""
    random.seed(seed)
    persona_map = {pid: p for pid, p in all_personas}

    non_reorderer_ids = set(
        log["persona_id"] for log in journey_logs
        if not log.get("error") and not log.get("reordered")
    )
    reorderer_ids = [
        log["persona_id"] for log in journey_logs
        if not log.get("error") and log.get("reordered")
    ]

    # All non-reorderers
    sample_ids = list(non_reorderer_ids)

    # Fill up to sample_size with random reorderers
    remaining = sample_size - len(sample_ids)
    if remaining > 0:
        sampled_reorderers = random.sample(reorderer_ids, min(remaining, len(reorderer_ids)))
        sample_ids.extend(sampled_reorderers)

    sample_ids = sample_ids[:sample_size]
    result = [(pid, persona_map[pid]) for pid in sample_ids if pid in persona_map]
    print(f"  Sample: {len(result)} personas ({len(non_reorderer_ids)} non-reorderers + {len(result)-len(non_reorderer_ids)} reorderers)")
    return result


def create_intervention_journey_a(base_journey: JourneyConfig) -> JourneyConfig:
    """Problem A: Add loyalty price nudge + WOM social proof."""
    intervention_stimuli = [
        StimulusConfig(
            id="A-INT-S55",
            tick=55,
            type="price_change",
            source="bigbasket_app",
            content=(
                "BigBasket sends a loyalty price notification — Rs 599 on your second "
                "Nutrimix pack (Rs 50 off). Valid for 48 hours."
            ),
            brand="littlejoys",
        ),
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
    ]

    # Merge: combine base stimuli + intervention stimuli
    all_stimuli = list(base_journey.stimuli) + intervention_stimuli
    # Sort by tick
    all_stimuli_sorted = sorted(all_stimuli, key=lambda s: s.tick)

    return JourneyConfig(
        journey_id="A_intervention",
        total_ticks=base_journey.total_ticks,
        primary_brand=base_journey.primary_brand,
        stimuli=all_stimuli_sorted,
        decisions=base_journey.decisions,
    )


def create_intervention_journey_b(base_journey: JourneyConfig) -> JourneyConfig:
    """Problem B: Add sleep tracking + community outcome data."""
    intervention_stimuli = [
        StimulusConfig(
            id="B-INT-S05",
            tick=5,
            type="product",
            source="lj_app",
            content=(
                "LittleJoys app prompts: 'Track your child's sleep this week — "
                "3 quick questions each morning. We'll show you what changed at Day 10.'"
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="B-INT-S30",
            tick=30,
            type="social_event",
            source="lj_app",
            content=(
                "Push notification: '1,200 parents completed their first Magnesium "
                "Gummies pack. Average bedtime moved 22 minutes earlier. Here's the data.'"
            ),
            brand="littlejoys",
        ),
    ]

    all_stimuli = list(base_journey.stimuli) + intervention_stimuli
    all_stimuli_sorted = sorted(all_stimuli, key=lambda s: s.tick)

    return JourneyConfig(
        journey_id="B_intervention",
        total_ticks=base_journey.total_ticks,
        primary_brand=base_journey.primary_brand,
        stimuli=all_stimuli_sorted,
        decisions=base_journey.decisions,
    )


def create_intervention_journey_c(base_journey: JourneyConfig) -> JourneyConfig:
    """Problem C: Add nutritional comparison + family pack deal."""
    intervention_stimuli = [
        StimulusConfig(
            id="C-INT-S55",
            tick=55,
            type="ad",
            source="lj_app",
            content=(
                "LittleJoys push: 'Nutrimix has 3x the iron of Bournvita and zero "
                "added sugar. That's your Rs 250 explained.' With a comparison "
                "infographic showing micronutrient levels side-by-side."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="C-INT-S22",
            tick=22,
            type="price_change",
            source="bigbasket",
            content=(
                "Family pack offer: 2 x 500g Nutrimix for Rs 1,099 (Rs 549 each). "
                "Valid this week."
            ),
            brand="littlejoys",
        ),
    ]

    all_stimuli = list(base_journey.stimuli) + intervention_stimuli
    all_stimuli_sorted = sorted(all_stimuli, key=lambda s: s.tick)

    return JourneyConfig(
        journey_id="C_intervention",
        total_ticks=base_journey.total_ticks,
        primary_brand=base_journey.primary_brand,
        stimuli=all_stimuli_sorted,
        decisions=base_journey.decisions,
    )


def run_intervention(
    journey_id: str,
    journey_config: JourneyConfig,
    sample_personas: list[tuple[str, Persona]],
    concurrency: int = 3,
) -> None:
    """Run an intervention journey and save results."""
    total = len(sample_personas)
    print(f"\nRunning journey {journey_id} intervention for {total} personas...")

    def progress_cb(done: int, total: int, log_dict: dict) -> None:
        name = str(log_dict.get("display_name") or log_dict.get("persona_id") or "?")
        reordered = log_dict.get("reordered", False)
        print(f"  [{done:>3}/{total}] {name:<28} reordered={reordered}")

    result: BatchResult = run_batch(
        journey_config=journey_config,
        personas=sample_personas,
        concurrency=concurrency,
        progress_callback=progress_cb,
    )

    # Compute summary stats
    logs = result.logs
    total_valid = len([l for l in logs if not l.get("error")])
    reordered_count = len([l for l in logs if not l.get("error") and l.get("reordered")])
    reorder_pct = round(100 * reordered_count / total_valid, 1) if total_valid else 0

    print(f"\n  Results: {reordered_count}/{total_valid} reordered = {reorder_pct:.1f}%")

    output = result.to_dict()
    out_name = f"journey_{journey_id}_intervention_results.json"
    out_path = PROJECT_ROOT / "data" / "population" / out_name
    with out_path.open("w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {out_path}")


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set")
        return 1

    presets = list_presets()
    all_personas = load_personas()
    out_dir = PROJECT_ROOT / "data" / "population"

    # Problem A interventions
    print("\n" + "=" * 60)
    print("INTERVENTION A: Nutrimix Repeat Purchase")
    print("=" * 60)
    try:
        logs_a = load_journey_results("A")
        sample_a = get_sample_personas(all_personas, logs_a, sample_size=50)
        journey_a_int = create_intervention_journey_a(presets["A"])
        run_intervention("A", journey_a_int, sample_a, concurrency=3)
    except Exception as exc:
        print(f"ERROR in Intervention A: {exc}")
        import traceback; traceback.print_exc()

    # Problem B interventions
    print("\n" + "=" * 60)
    print("INTERVENTION B: Magnesium Gummies Growth")
    print("=" * 60)
    try:
        logs_b = load_journey_results("B")
        sample_b = get_sample_personas(all_personas, logs_b, sample_size=50)
        journey_b_int = create_intervention_journey_b(presets["B"])
        run_intervention("B", journey_b_int, sample_b, concurrency=3)
    except Exception as exc:
        print(f"ERROR in Intervention B: {exc}")
        import traceback; traceback.print_exc()

    # Problem C interventions
    print("\n" + "=" * 60)
    print("INTERVENTION C: Nutrimix 7-14 Expansion")
    print("=" * 60)
    try:
        logs_c = load_journey_results("C")
        sample_c = get_sample_personas(all_personas, logs_c, sample_size=50)
        journey_c_int = create_intervention_journey_c(presets["C"])
        run_intervention("C", journey_c_int, sample_c, concurrency=3)
    except Exception as exc:
        print(f"ERROR in Intervention C: {exc}")
        import traceback; traceback.print_exc()

    print("\n\nAll interventions complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
