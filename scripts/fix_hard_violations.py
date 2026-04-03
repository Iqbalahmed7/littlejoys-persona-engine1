#!/usr/bin/env python3
"""
fix_hard_violations.py — Apply enforce_hard_constraints() to all hard-violation personas.

Rather than regenerating from scratch (which loses narratives and memory),
this script patches only the offending attribute values on the 35 hard-violation
personas, preserving all other data.

Usage:
    python3 scripts/fix_hard_violations.py [--dry-run]

Output:
    Overwrites data/population/personas_generated.json with fixed population
    Prints before/after summary
"""
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.generation.tier1_generator import Tier1Generator
from src.agents.constraint_checker import ConstraintChecker
from src.taxonomy.schema import Persona


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing")
    args = parser.parse_args()

    # Load violation report to get hard-violation IDs
    report_path = PROJECT_ROOT / "data" / "population" / "constraint_violations_report.json"
    if not report_path.exists():
        print("ERROR: constraint_violations_report.json not found. Run scripts/validate_personas.py first.")
        sys.exit(1)

    report = json.loads(report_path.read_text())
    hard_ids = set(report.get("personas_with_hard_violations", []))
    print(f"Hard-violation personas to fix: {len(hard_ids)}")

    # Load population
    pop_path = PROJECT_ROOT / "data" / "population" / "personas_generated.json"
    if not pop_path.exists():
        print("ERROR: personas_generated.json not found.")
        sys.exit(1)

    with open(pop_path) as f:
        population = json.load(f)

    print(f"Total population: {len(population)}")

    checker = ConstraintChecker()
    fixed_count = 0
    still_failing = []
    changes_log = []

    for i, p_dict in enumerate(population):
        pid = str(p_dict.get("id", f"persona_{i:03d}"))
        if pid not in hard_ids:
            continue

        # Snapshot key values before
        psych_before = {
            "risk_tolerance": p_dict.get("psychology", {}).get("risk_tolerance"),
            "loss_aversion": p_dict.get("psychology", {}).get("loss_aversion"),
            "analysis_paralysis_tendency": p_dict.get("psychology", {}).get("analysis_paralysis_tendency"),
            "decision_speed": p_dict.get("psychology", {}).get("decision_speed"),
        }
        daily_before = {
            "impulse_purchase_tendency": p_dict.get("daily_routine", {}).get("impulse_purchase_tendency"),
        }
        values_before = {
            "supplement_necessity_belief": p_dict.get("values", {}).get("supplement_necessity_belief"),
            "food_first_belief": p_dict.get("values", {}).get("food_first_belief"),
        }

        # Apply fix
        Tier1Generator.enforce_hard_constraints(p_dict)

        # Snapshot key values after
        psych_after = {
            "risk_tolerance": p_dict.get("psychology", {}).get("risk_tolerance"),
            "loss_aversion": p_dict.get("psychology", {}).get("loss_aversion"),
            "analysis_paralysis_tendency": p_dict.get("psychology", {}).get("analysis_paralysis_tendency"),
            "decision_speed": p_dict.get("psychology", {}).get("decision_speed"),
        }
        daily_after = {
            "impulse_purchase_tendency": p_dict.get("daily_routine", {}).get("impulse_purchase_tendency"),
        }
        values_after = {
            "supplement_necessity_belief": p_dict.get("values", {}).get("supplement_necessity_belief"),
            "food_first_belief": p_dict.get("values", {}).get("food_first_belief"),
        }

        # Log what changed
        diffs = []
        for k in psych_before:
            if psych_before[k] != psych_after[k]:
                diffs.append(f"  psychology.{k}: {psych_before[k]:.3f} → {psych_after[k]:.3f}")
        for k in daily_before:
            if daily_before[k] != daily_after[k]:
                diffs.append(f"  daily_routine.{k}: {daily_before[k]:.3f} → {daily_after[k]:.3f}")
        for k in values_before:
            if values_before[k] != values_after[k]:
                diffs.append(f"  values.{k}: {values_before[k]:.3f} → {values_after[k]:.3f}")

        # Check decision_rights for R030
        rights = p_dict.get("decision_rights", {})
        if rights.get("child_nutrition") == "mother_final" and p_dict.get("demographics", {}).get("family_structure") == "single_parent":
            diffs.append(f"  decision_rights.child_nutrition: fixed → mother_final")

        changes_log.append((pid, diffs))

        # Re-validate
        try:
            persona = Persona.model_validate(p_dict)
            violations = checker.check_hard_only(persona)
            if violations:
                still_failing.append((pid, [v.rule_id for v in violations]))
            else:
                fixed_count += 1
        except Exception as e:
            still_failing.append((pid, [f"parse_error: {e}"]))

    # Print changes
    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Changes applied:")
    for pid, diffs in changes_log:
        print(f"\n  {pid}:")
        if diffs:
            for d in diffs:
                print(d)
        else:
            print("  (R030 decision_rights fix only — check decision_rights field)")

    print(f"\n{'─' * 50}")
    print(f"Fixed successfully:  {fixed_count} / {len(hard_ids)}")
    if still_failing:
        print(f"Still failing:       {len(still_failing)}")
        for pid, rules in still_failing:
            print(f"  {pid}: {rules}")
    else:
        print("Still failing:       0")

    if args.dry_run:
        print("\nDRY RUN complete — no files written.")
        return

    if still_failing:
        print(f"\nWARNING: {len(still_failing)} personas still have hard violations after fix.")
        print("These will need manual inspection or regeneration.")

    # Write fixed population
    with open(pop_path, "w") as f:
        json.dump(population, f, indent=2)
    print(f"\nWrote fixed population to {pop_path}")
    print("Run scripts/validate_personas.py to generate updated report.")


if __name__ == "__main__":
    main()
