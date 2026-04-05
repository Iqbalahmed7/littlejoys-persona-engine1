"""
Regenerate persona cohort with a given seed and size, saving to
data/population/personas_generated.json (list of Persona dicts).

Usage:
    python scripts/regenerate_cohort.py --seed 42 --size 200
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import structlog

from src.generation.population import PopulationGenerator

log = structlog.get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate persona cohort.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "data" / "population" / "personas_generated.json"),
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    log.info(
        "regenerate_cohort_started",
        seed=args.seed,
        size=args.size,
        output=str(output_path),
    )
    t0 = time.perf_counter()

    population = PopulationGenerator().generate(size=args.size, seed=args.seed)

    personas_json = [p.model_dump(mode="json") for p in population.tier1_personas]
    output_path.write_text(json.dumps(personas_json, indent=2, ensure_ascii=False), encoding="utf-8")

    duration = time.perf_counter() - t0
    log.info(
        "regenerate_cohort_complete",
        personas_written=len(personas_json),
        output=str(output_path),
        duration_seconds=round(duration, 2),
    )
    print(
        f"\nDone. {len(personas_json)} personas written to {output_path} "
        f"in {duration:.1f}s"
    )


if __name__ == "__main__":
    main()
