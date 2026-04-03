"""
batch_runner.py — Importable batch runner for multi-tick journey simulations.

Used by both the CLI script and the Streamlit Simulation Builder page.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.simulation.journey_result import aggregate_journeys

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.simulation.journey_config import JourneyConfig
    from src.simulation.journey_result import JourneyAggregate
    from src.taxonomy.schema import Persona


@dataclass
class BatchResult:
    journey_id: str
    logs: list[dict]
    aggregate: JourneyAggregate
    elapsed_seconds: float
    personas_run: int
    errors: int

    def to_dict(self) -> dict:
        return {
            "journey_id": self.journey_id,
            "total_personas": self.personas_run,
            "errors": self.errors,
            "elapsed_seconds": self.elapsed_seconds,
            "aggregate": self.aggregate.to_dict(),
            "logs": self.logs,
        }


def run_batch(
    journey_config: JourneyConfig,
    personas: list[tuple[str, Persona]],
    concurrency: int = 5,
    progress_callback: Callable[[int, int, dict], None] | None = None,
) -> BatchResult:
    """
    Run a journey for all personas. Returns a BatchResult.

    Args:
        journey_config: The JourneyConfig to run.
        personas: List of (persona_id, Persona) tuples.
        concurrency: ThreadPoolExecutor max_workers.
        progress_callback: Optional callable(done, total, latest_log_dict).
            Called after each persona completes.
    """
    from src.simulation.tick_engine import TickEngine

    journey_spec = journey_config.to_journey_spec()
    engine = TickEngine()
    total = len(personas)
    logs: list[dict] = []
    start = time.monotonic()

    def _run_one(pid: str, persona: Persona) -> dict:
        try:
            log = engine.run(persona, journey_spec)
            return log.to_dict()
        except Exception as exc:
            return {
                "persona_id": pid,
                "display_name": getattr(persona, "display_name", pid) or pid,
                "journey_id": journey_config.journey_id,
                "error": str(exc),
                "snapshots": [],
                "final_decision": None,
                "reordered": False,
            }

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        future_map = {
            executor.submit(_run_one, pid, persona): (pid, persona)
            for pid, persona in personas
        }
        for done, future in enumerate(as_completed(future_map), start=1):
            log_dict = future.result()
            logs.append(log_dict)
            if progress_callback is not None:
                progress_callback(done, total, log_dict)

    elapsed = round(time.monotonic() - start, 2)
    aggregate = aggregate_journeys(logs)

    return BatchResult(
        journey_id=journey_config.journey_id,
        logs=logs,
        aggregate=aggregate,
        elapsed_seconds=elapsed,
        personas_run=total,
        errors=aggregate.errors,
    )
