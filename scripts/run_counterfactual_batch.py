#!/usr/bin/env python3
"""
run_counterfactual_batch.py — Run counterfactual journeys for problems A, B, C.

Counterfactuals test "what could have been different" scenarios.

Usage:
    ANTHROPIC_API_KEY=sk-... python3 scripts/run_counterfactual_batch.py

Output:
    data/population/journey_A_counterfactual_results.json
    data/population/journey_B_counterfactual_results.json
    data/population/journey_C_counterfactual_results.json
"""

from __future__ import annotations

import json
import os
import sys
import random
from pathlib import Path
from copy import deepcopy

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation.batch_runner import BatchResult, run_batch  # noqa: E402
from src.simulation.journey_config import JourneyConfig, StimulusConfig, DecisionScenarioConfig  # noqa: E402
from src.simulation.journey_presets import list_presets  # noqa: E402
from src.taxonomy.schema import Persona  # noqa: E402


def load_personas() -> list[tuple[str, Persona]]:
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
    seed: int = 99,
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

    sample_ids = list(non_reorderer_ids)
    remaining = sample_size - len(sample_ids)
    if remaining > 0:
        sampled_reorderers = random.sample(reorderer_ids, min(remaining, len(reorderer_ids)))
        sample_ids.extend(sampled_reorderers)

    sample_ids = sample_ids[:sample_size]
    result = [(pid, persona_map[pid]) for pid in sample_ids if pid in persona_map]
    print(f"  Sample: {len(result)} personas ({len(non_reorderer_ids)} non-reorderers + {len(result)-len(non_reorderer_ids)} reorderers)")
    return result


def create_counterfactual_journey_a(base_journey: JourneyConfig) -> JourneyConfig:
    """
    Counterfactual A: Remove the tick 55 nudge entirely + no discount.
    'What if full-price reorder AND no nudge at all?'
    This tests the worst case — no loyalty discount, no social proof nudge.
    """
    # Remove the existing tick 55 pharmacist stimulus (already complan nudge)
    # and ensure NO positive nudges at all near reorder
    # Keep all original stimuli except remove any near tick 55
    # Also set reorder price back to full 649 (already at 649)
    stimuli_without_nudge = [
        s for s in base_journey.stimuli
        if s.tick < 48  # Remove pharmacist at 55, keep early stimuli
    ]

    # Replace tick 60 decision description to emphasize no discount/no community info
    new_decisions = [
        DecisionScenarioConfig(
            tick=60,
            product="LittleJoys Nutrimix 500g",
            price_inr=699,  # Price went up
            channel="bigbasket",
            description=(
                "Your LittleJoys Nutrimix pack is nearly finished. Your child has been "
                "having it for 5 weeks. You're on BigBasket — it's Rs 699, price went up "
                "this month, no discount available. No loyalty program. "
                "Complan is Rs 420. Do you reorder Nutrimix?"
            ),
        ) if d.tick == 60 else d
        for d in base_journey.decisions
    ]

    return JourneyConfig(
        journey_id="A_counterfactual",
        total_ticks=base_journey.total_ticks,
        primary_brand=base_journey.primary_brand,
        stimuli=stimuli_without_nudge,
        decisions=new_decisions,
    )


def create_counterfactual_journey_b(base_journey: JourneyConfig) -> JourneyConfig:
    """
    Counterfactual B: Extend trial window to 21 days instead of 10.
    'What if trial window was 21 days?'
    """
    # Modify the tick 45 reorder decision description to mention 21 days
    new_decisions = [
        DecisionScenarioConfig(
            tick=45,
            product="LittleJoys Magnesium Gummies 30-day pack",
            price_inr=499,
            channel="firstcry_online",
            description=(
                "You've been giving your child LittleJoys Magnesium Gummies for 21 days "
                "instead of 10 — an extended trial period. You have stronger evidence of "
                "whether it's working. Sleep improvement is now clearer and more consistent. "
                "The pack will run out in 5 days. Rs 499 to reorder. Do you continue?"
            ),
        ) if d.tick == 45 else d
        for d in base_journey.decisions
    ]

    return JourneyConfig(
        journey_id="B_counterfactual",
        total_ticks=base_journey.total_ticks,
        primary_brand=base_journey.primary_brand,
        stimuli=base_journey.stimuli,
        decisions=new_decisions,
    )


def create_counterfactual_journey_c(base_journey: JourneyConfig) -> JourneyConfig:
    """
    Counterfactual C: Bournvita counter-ad hits before Day 28 trial decision.
    Move Bournvita counter-ad to tick 12 (instead of tick 48).
    """
    # Filter out original Bournvita ad at tick 48
    stimuli_without_late_bournvita = [
        s for s in base_journey.stimuli
        if not (s.tick == 48 and "Bournvita" in s.content)
    ]

    # Add Bournvita counter-ad at tick 12 — before first purchase decision at tick 28
    early_bournvita_stimulus = StimulusConfig(
        id="C-CF-S12",
        tick=12,
        type="ad",
        source="youtube_preroll",
        content=(
            "YouTube: Bournvita 'Junior Champion' campaign — 'Trusted by Indian families "
            "for 70 years. Scientifically proven for growth.' Featuring sports trophies, "
            "school toppers, strong brand. Price: Rs 399 vs Rs 649 for newer brands."
        ),
        brand="bournvita",
    )

    all_stimuli = stimuli_without_late_bournvita + [early_bournvita_stimulus]
    all_stimuli_sorted = sorted(all_stimuli, key=lambda s: s.tick)

    return JourneyConfig(
        journey_id="C_counterfactual",
        total_ticks=base_journey.total_ticks,
        primary_brand=base_journey.primary_brand,
        stimuli=all_stimuli_sorted,
        decisions=base_journey.decisions,
    )


def run_counterfactual(
    journey_id: str,
    journey_config: JourneyConfig,
    sample_personas: list[tuple[str, Persona]],
    concurrency: int = 3,
) -> None:
    """Run a counterfactual journey and save results."""
    total = len(sample_personas)
    print(f"\nRunning counterfactual {journey_id} for {total} personas...")

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

    logs = result.logs
    total_valid = len([l for l in logs if not l.get("error")])
    reordered_count = len([l for l in logs if not l.get("error") and l.get("reordered")])
    reorder_pct = round(100 * reordered_count / total_valid, 1) if total_valid else 0

    print(f"\n  Results: {reordered_count}/{total_valid} reordered = {reorder_pct:.1f}%")

    output = result.to_dict()
    out_name = f"journey_{journey_id}_counterfactual_results.json"
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

    # Counterfactual A
    print("\n" + "=" * 60)
    print("COUNTERFACTUAL A: No discount, price went up")
    print("=" * 60)
    try:
        logs_a = load_journey_results("A")
        sample_a = get_sample_personas(all_personas, logs_a, sample_size=50)
        journey_a_cf = create_counterfactual_journey_a(presets["A"])
        run_counterfactual("A", journey_a_cf, sample_a, concurrency=3)
    except Exception as exc:
        print(f"ERROR in Counterfactual A: {exc}")
        import traceback; traceback.print_exc()

    # Counterfactual B
    print("\n" + "=" * 60)
    print("COUNTERFACTUAL B: 21-day trial window")
    print("=" * 60)
    try:
        logs_b = load_journey_results("B")
        sample_b = get_sample_personas(all_personas, logs_b, sample_size=50)
        journey_b_cf = create_counterfactual_journey_b(presets["B"])
        run_counterfactual("B", journey_b_cf, sample_b, concurrency=3)
    except Exception as exc:
        print(f"ERROR in Counterfactual B: {exc}")
        import traceback; traceback.print_exc()

    # Counterfactual C
    print("\n" + "=" * 60)
    print("COUNTERFACTUAL C: Bournvita counter-ad at tick 12")
    print("=" * 60)
    try:
        logs_c = load_journey_results("C")
        sample_c = get_sample_personas(all_personas, logs_c, sample_size=50)
        journey_c_cf = create_counterfactual_journey_c(presets["C"])
        run_counterfactual("C", journey_c_cf, sample_c, concurrency=3)
    except Exception as exc:
        print(f"ERROR in Counterfactual C: {exc}")
        import traceback; traceback.print_exc()

    print("\n\nAll counterfactuals complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
