#!/usr/bin/env python3
"""patch_work_hours.py — Fix CAT2-R009: set work_hours_per_week for full_time personas.

For all full_time personas where work_hours_per_week == 0,
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def derive_work_hours(career_ambition: float, income_lpa: float) -> int:
    """Derive plausible weekly hours from ambition + income.

    Range: 35-55 hours. Higher ambition/income → more hours.
    """

    base = 38
    ambition_bump = int(career_ambition * 12)  # 0-12 extra hours
    income_bump = min(int(income_lpa / 10), 5)  # 0-5 extra hours, capped
    return min(base + ambition_bump + income_bump, 55)


def patch_personas(data_path: Path) -> tuple[int, int]:
    """Return (total_loaded, total_patched)."""

    with open(data_path) as f:
        data = json.load(f)

    is_list = isinstance(data, list)
    items = data if is_list else list(data.values())
    patched = 0

    for p_dict in items:
        career = p_dict.get("career", {})
        status = career.get("employment_status", "")
        hours = career.get("work_hours_per_week", 0)

        if status == "full_time" and hours == 0:
            income = p_dict.get("demographics", {}).get("household_income_lpa", 8.0)
            ambition = career.get("career_ambition", 0.5)
            new_hours = derive_work_hours(ambition, income)
            p_dict["career"]["work_hours_per_week"] = new_hours
            patched += 1

    with open(data_path, "w") as f:
        json.dump(data, f, indent=2)

    return len(items), patched


def main() -> None:
    candidates = [
        PROJECT_ROOT / "data" / "population" / "personas_generated.json",
        PROJECT_ROOT / "data" / "population" / "personas.json",
    ]

    for path in candidates:
        if path.exists():
            print(f"Patching: {path}")
            total, patched = patch_personas(path)
            print(f"Loaded:   {total} personas")
            print(f"Patched:  {patched} personas (CAT2-R009 fix)")
            print(
                f"Skipped:  {total - patched} (not full_time or already have hours)",
            )
            return

    print("ERROR: No persona file found.")
    sys.exit(1)


if __name__ == "__main__":
    main()
