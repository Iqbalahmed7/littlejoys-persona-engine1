# Sprint 20 Brief — Codex
## Scenario Comparison Backend

### Context

The dashboard currently runs one scenario at a time. For the pitch, we need "Compare Scenario A vs Scenario B" — run both, compute deltas, return a structured comparison. This is the backend; OpenCode builds the UI.

### Task: `src/analysis/scenario_comparison.py` (new)

```python
"""Side-by-side scenario comparison engine."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from src.decision.scenarios import ScenarioConfig

class BarrierDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: str
    barrier: str
    count_a: int
    count_b: int
    delta: int

class DriverDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variable: str
    importance_a: float
    importance_b: float
    delta: float

class ScenarioComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_a_id: str
    scenario_b_id: str
    scenario_a_name: str
    scenario_b_name: str

    # Static funnel
    adoption_rate_a: float
    adoption_rate_b: float
    adoption_delta: float

    # Event simulation (optional — only for temporal scenarios)
    active_rate_a: float | None = None
    active_rate_b: float | None = None
    active_delta: float | None = None
    revenue_a: float | None = None
    revenue_b: float | None = None
    revenue_delta: float | None = None

    # Structural comparison
    barrier_comparison: list[BarrierDelta] = Field(default_factory=list)
    driver_comparison: list[DriverDelta] = Field(default_factory=list)


def compare_scenarios(
    population: Population,
    scenario_a: ScenarioConfig,
    scenario_b: ScenarioConfig,
    seed: int = 42,
) -> ScenarioComparisonResult:
    """Run both scenarios and produce a structured comparison."""
```

### Implementation

1. Run `evaluate_scenario_adoption()` for both scenarios (static funnel)
2. If both scenarios have `mode == "temporal"`, also run `run_event_simulation()` for each
3. Compute barrier differences: for each (stage, barrier) pair, count in A vs B, delta
4. Compute driver differences: run `compute_variable_importance()` on each, match by variable name, delta

Use the existing `evaluate_scenario_adoption` from `src/decision/calibration.py` and `run_event_simulation` from `src/simulation/event_engine.py`.

### Edge Cases
- If one scenario is static and the other is temporal, `active_rate` and `revenue` fields are None for the static one
- If barrier sets don't overlap, pad the missing side with 0

### Files to Create
- `src/analysis/scenario_comparison.py`

### Constraints
- Do NOT modify existing files
- Use small populations for testing (pass in the population, don't generate inside)
- All existing tests must pass
- Run `uv run ruff check .` before delivery
