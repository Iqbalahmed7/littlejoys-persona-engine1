#!/usr/bin/env python3
"""validate_personas.py — Run ConstraintChecker against all 200 generated personas.

Usage:
    python3 scripts/validate_personas.py
    python3 scripts/validate_personas.py --input data/population/personas.json
    python3 scripts/validate_personas.py --hard-only
    python3 scripts/validate_personas.py --fix-report

Output:
    data/population/constraint_violations_report.json   (always)
    data/population/personas_to_regenerate.json         (with --fix-report)
    Summary table printed to stdout
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.constraint_checker import ConstraintChecker
from src.taxonomy.schema import Persona


def _parse_persona_data(data: list | dict) -> list[tuple[str, Persona]]:
    results: list[tuple[str, Persona]] = []
    items = enumerate(data) if isinstance(data, list) else data.items()
    for idx, p_dict in items:
        if isinstance(data, list):
            pid = p_dict.get("id", p_dict.get("persona_id", f"persona_{idx:03d}"))
        else:
            pid = idx
        try:
            results.append((str(pid), Persona.model_validate(p_dict)))
        except Exception as e:
            print(f"  [SKIP] {pid}: {e}")
    return results


def load_personas(input_path: Path | None) -> list[tuple[str, Persona]]:
    """Load all personas from disk.

    Returns list of (persona_id, Persona) tuples.

    Tries in order:
      1. --input path if provided
      2. data/population/personas.json
      3. data/population/personas_generated.json
      4. data/population/personas/ directory (individual .json files)
    """

    candidates = [
        input_path,
        PROJECT_ROOT / "data" / "population" / "personas.json",
        PROJECT_ROOT / "data" / "population" / "personas_generated.json",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists() and Path(candidate).is_file():
            print(f"Loading from: {candidate}")
            with open(candidate) as f:
                data = json.load(f)
            return _parse_persona_data(data)

    persona_dir = PROJECT_ROOT / "data" / "population" / "personas"
    if persona_dir.exists() and persona_dir.is_dir():
        print(f"Loading from directory: {persona_dir}")
        results: list[tuple[str, Persona]] = []
        for json_file in sorted(persona_dir.glob("*.json")):
            with open(json_file) as f:
                p_dict = json.load(f)
            pid = json_file.stem
            try:
                results.append((pid, Persona.model_validate(p_dict)))
            except Exception as e:
                print(f"  [SKIP] {pid}: {e}")
        return results

    print("ERROR: No persona files found. Tried:")
    for c in candidates:
        print(f"  {c}")
    print(f"  {PROJECT_ROOT / 'data' / 'population'}/personas/")
    sys.exit(1)


def run_validation(
    personas: list[tuple[str, Persona]],
    hard_only: bool = False,
) -> dict:
    checker = ConstraintChecker()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_personas": len(personas),
        "hard_only_mode": hard_only,
        "summary": {},
        "rule_hit_counts": defaultdict(int),
        "personas_with_hard_violations": [],
        "personas_with_soft_violations": [],
        "personas_clean": [],
        "violations_by_persona": {},
    }

    hard_count = 0
    soft_count = 0

    for pid, persona in personas:
        violations = checker.check_hard_only(persona) if hard_only else checker.check(persona)

        if not violations:
            report["personas_clean"].append(pid)
            continue

        hard_viols = [v for v in violations if v.severity == "hard"]
        soft_viols = [v for v in violations if v.severity == "soft"]

        if hard_viols:
            hard_count += 1
            report["personas_with_hard_violations"].append(pid)

        if soft_viols and not hard_only:
            soft_count += 1
            if pid not in report["personas_with_hard_violations"]:
                report["personas_with_soft_violations"].append(pid)

        report["violations_by_persona"][pid] = [
            {
                "rule_id": v.rule_id,
                "severity": v.severity,
                "message": v.message,
                "attribute_a": v.attribute_a,
                "attribute_b": v.attribute_b,
                "values": v.values,
            }
            for v in violations
        ]

        for v in violations:
            report["rule_hit_counts"][v.rule_id] += 1

    report["rule_hit_counts"] = dict(
        sorted(report["rule_hit_counts"].items(), key=lambda x: x[1], reverse=True)
    )
    report["summary"] = {
        "clean": len(report["personas_clean"]),
        "hard_violations": hard_count,
        "soft_violations": soft_count,
        "pct_clean": round(len(report["personas_clean"]) / len(personas) * 100, 1),
        "pct_hard": round(hard_count / len(personas) * 100, 1),
        "top_violated_rule": next(iter(report["rule_hit_counts"]), "none"),
    }
    return report


def print_summary(report: dict) -> None:
    s = report["summary"]
    total = report["total_personas"]

    print("\n" + "=" * 60)
    print("CONSTRAINT VALIDATION REPORT")
    print("=" * 60)
    print(f"Personas checked:      {total}")
    print(f"Clean (no violations): {s['clean']} ({s['pct_clean']}%)")
    print(f"Hard violations:       {s['hard_violations']} ({s['pct_hard']}%)")
    print(f"Soft violations only:  {s['soft_violations']}")
    print()

    if report["rule_hit_counts"]:
        print("Top 10 rules violated:")
        for i, (rule_id, count) in enumerate(list(report["rule_hit_counts"].items())[:10], 1):
            pct = round(count / total * 100, 1)
            print(f"  {i:2}. {rule_id:<15} {count:>4} personas ({pct}%)")

    if report["personas_with_hard_violations"]:
        print(f"\nPersonas needing regeneration ({len(report['personas_with_hard_violations'])}):")
        for pid in report["personas_with_hard_violations"][:20]:
            viols = report["violations_by_persona"][pid]
            hard = [v for v in viols if v["severity"] == "hard"]
            print(f"  {pid}: {', '.join(v['rule_id'] for v in hard)}")
        if len(report["personas_with_hard_violations"]) > 20:
            print(f"  ... and {len(report['personas_with_hard_violations']) - 20} more")

    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--hard-only", action="store_true")
    parser.add_argument("--fix-report", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    print("Loading personas...")
    personas = load_personas(args.input)
    print(f"Loaded {len(personas)} personas.")

    print("Running constraint checks...")
    report = run_validation(personas, hard_only=args.hard_only)
    print_summary(report)

    output_dir = PROJECT_ROOT / "data" / "population"
    output_path = args.output or output_dir / "constraint_violations_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report written: {output_path}")

    if args.fix_report:
        fix_path = output_dir / "personas_to_regenerate.json"
        fix_data = {
            "generated_at": report["generated_at"],
            "reason": "hard constraint violations",
            "persona_ids": report["personas_with_hard_violations"],
            "violations": {
                pid: [v["rule_id"] for v in viols if v["severity"] == "hard"]
                for pid, viols in report["violations_by_persona"].items()
                if any(v["severity"] == "hard" for v in viols)
            },
        }
        with open(fix_path, "w") as f:
            json.dump(fix_data, f, indent=2)
        print(f"Fix list written: {fix_path}")

    sys.exit(1 if report["personas_with_hard_violations"] else 0)


if __name__ == "__main__":
    main()
