# Sprint 31 — CODEX Brief: BatchRunner as callable module

## Context
`scripts/run_journey_batch.py` is currently CLI-only. The Streamlit UI needs to call the
batch runner as a Python function with a progress callback. This sprint extracts the core
logic into an importable module while keeping the CLI wrapper intact.

## Dependency
Requires CURSOR's `JourneyConfig` and `journey_presets.py` to be complete first.

## Working directory
`/Users/admin/Documents/Simulatte Projects/1. LittleJoys`

## Task 1 — Create `src/simulation/batch_runner.py`

```python
"""
batch_runner.py — Importable batch runner for multi-tick journey simulations.

Used by both the CLI script and the Streamlit Simulation Builder page.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from src.simulation.journey_config import JourneyConfig
from src.simulation.journey_result import JourneyAggregate, aggregate_journeys
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
        done = 0
        for future in as_completed(future_map):
            log_dict = future.result()
            logs.append(log_dict)
            done += 1
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
```

## Task 2 — Refactor `scripts/run_journey_batch.py`

Keep the file but replace the batch execution logic with a call to `run_batch()`.
The CLI args, persona loading, JSON output, and summary printing all stay in the script.
Only the core threading loop is replaced.

Key change — replace the `ThreadPoolExecutor` block with:

```python
from src.simulation.batch_runner import run_batch, BatchResult
from src.simulation.journey_presets import list_presets

def progress_cb(done: int, total: int, log_dict: dict) -> None:
    name = str(log_dict.get("display_name") or log_dict.get("persona_id") or "?")
    second = _get_second_decision(log_dict, journey_id)
    second_decision = _decision_label(second)
    reordered = log_dict.get("reordered") or second_decision in {"buy", "trial", "reorder"}
    tick_label = "tick60_decision" if journey_id == "A" else "tick45_decision"
    print(
        f"  [{done:>3}/{total}] {name:<28} journey={journey_id}  "
        f"{tick_label}={second_decision:<6} reordered={bool(reordered)}"
    )

presets = list_presets()
if journey_id not in presets:
    print(f"Unknown journey: {journey_id}")
    return 1

result = run_batch(
    journey_config=presets[journey_id],
    personas=personas,
    concurrency=args.concurrency,
    progress_callback=progress_cb,
)
```

Then write `result.to_dict()` as JSON and call `_print_summary(journey_id, result.logs, result.aggregate)`.

## Task 3 — JSON output format

`result.to_dict()` must produce a dict with these top-level keys (same as current output):
```
journey_id, total_personas, errors, elapsed_seconds, aggregate, logs
```
`aggregate` must be the full `JourneyAggregate.to_dict()` output.

## Verification
```bash
# Import check
python3 -c "
from src.simulation.batch_runner import run_batch, BatchResult
from src.simulation.journey_presets import PRESET_JOURNEY_A
print('imports OK')

# BatchResult instantiates with empty inputs
from src.simulation.journey_result import aggregate_journeys
agg = aggregate_journeys([])
br = BatchResult('A', [], agg, 0.0, 0, 0)
d = br.to_dict()
assert 'logs' in d
assert 'aggregate' in d
print('BatchResult OK')
"

# CLI still works
python3 scripts/run_journey_batch.py --journey A --max 1 --concurrency 1
```

All existing tests must pass: `python3 -m pytest tests/ -q --ignore=tests/integration`
