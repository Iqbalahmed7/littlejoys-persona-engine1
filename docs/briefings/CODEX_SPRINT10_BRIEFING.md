# Codex — Sprint 10 Track B: Batch Runner + Consolidator

**Branch:** `sprint-10-track-b-batch-consolidator`
**Base:** `main`

## Context

Once scenario variants are generated (Track A), they need to be run against the population and the results consolidated into actionable insights. This track builds the batch execution engine and the analysis/consolidation layer.

**Design doc:** `docs/designs/AUTO-SCENARIO-EXPLORATION.md`

## Deliverables

### 1. Create `src/simulation/batch.py` (NEW)

#### 1.1 BatchSimulationRunner

```python
"""Batch simulation runner for auto-scenario exploration."""

from __future__ import annotations

import time
from typing import Any, Callable

import structlog

from src.constants import DEFAULT_SEED
from src.simulation.static import StaticSimulationResult, run_static_simulation

logger = structlog.get_logger(__name__)


class BatchSimulationRunner:
    """Run multiple scenario variants against a population."""

    def __init__(
        self,
        population: Any,  # Population type
        seed: int = DEFAULT_SEED,
    ) -> None:
        self.population = population
        self.seed = seed

    def run_batch(
        self,
        variants: list,  # list[ScenarioVariant]
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[VariantResult]:
        """
        Run all variants sequentially and return ranked results.

        Each variant's ScenarioConfig is run through run_static_simulation().
        Results are sorted by adoption_rate descending and ranked 1..N.
        """
        start_time = time.monotonic()
        results: list[VariantResult] = []

        for i, variant in enumerate(variants):
            sim_result = run_static_simulation(
                self.population,
                variant.scenario_config,
                seed=self.seed,
            )

            results.append(VariantResult(
                variant_id=variant.variant_id,
                variant_name=variant.variant_name,
                adoption_rate=sim_result.adoption_rate,
                adoption_count=sim_result.adoption_count,
                population_size=sim_result.population_size,
                rejection_distribution=dict(sim_result.rejection_distribution),
                modifications=dict(variant.modifications),
                is_baseline=variant.is_baseline,
            ))

            if progress_callback:
                progress_callback(i + 1, len(variants))

        # Rank by adoption rate descending
        results.sort(key=lambda r: r.adoption_rate, reverse=True)
        for rank, result in enumerate(results, 1):
            result.rank = rank

        elapsed = time.monotonic() - start_time
        logger.info(
            "batch_simulation_complete",
            total_variants=len(results),
            elapsed_seconds=round(elapsed, 2),
            best_rate=results[0].adoption_rate if results else 0,
        )

        return results

    @property
    def estimated_time_per_variant(self) -> float:
        """Rough estimate: ~0.1s per variant for 300 personas."""
        return 0.1
```

### 2. Create `src/simulation/consolidation.py` (NEW)

#### 2.1 Data Models

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Any


class VariantResult(BaseModel):
    """Result of running one scenario variant."""

    model_config = ConfigDict(extra="forbid")

    variant_id: str
    variant_name: str
    adoption_rate: float
    adoption_count: int
    population_size: int
    rejection_distribution: dict[str, int]
    modifications: dict[str, Any]
    is_baseline: bool = False
    rank: int = 0


class ParameterSensitivity(BaseModel):
    """How much one parameter affects adoption rate."""

    model_config = ConfigDict(extra="forbid")

    parameter_path: str
    parameter_display_name: str
    min_value: Any                # The value that produced lowest adoption
    max_value: Any                # The value that produced highest adoption
    adoption_rate_at_min: float
    adoption_rate_at_max: float
    sensitivity_score: float      # |max_rate - min_rate|


class MissedInsight(BaseModel):
    """An auto-discovered configuration that outperforms the user's scenario."""

    model_config = ConfigDict(extra="forbid")

    variant_id: str
    variant_name: str
    adoption_rate: float
    lift_over_baseline: float     # Absolute percentage points
    key_differences: list[str]    # Human-readable
    explanation: str


class ExplorationReport(BaseModel):
    """Consolidated results from running all variants."""

    model_config = ConfigDict(extra="forbid")

    base_scenario_id: str
    strategy: str
    total_variants: int
    execution_time_seconds: float

    baseline_result: VariantResult
    best_result: VariantResult
    worst_result: VariantResult
    median_adoption_rate: float
    all_results: list[VariantResult]

    parameter_sensitivities: list[ParameterSensitivity]
    missed_insights: list[MissedInsight]
    recommended_modifications: dict[str, Any]
```

#### 2.2 ExplorationConsolidator

```python
class ExplorationConsolidator:
    """Analyze batch results and produce actionable insights."""

    def consolidate(
        self,
        base_scenario_id: str,
        base_scenario: ScenarioConfig,
        all_results: list[VariantResult],
        execution_time: float,
        strategy: str,
    ) -> ExplorationReport:
```

This method must:

1. **Find baseline, best, worst:**
   ```python
   baseline = next(r for r in all_results if r.is_baseline)
   best = all_results[0]  # Already sorted by adoption_rate desc
   worst = all_results[-1]
   median_rate = statistics.median(r.adoption_rate for r in all_results)
   ```

2. **Compute parameter sensitivities** via `_compute_sensitivities()`:
   - Group results by which parameter was modified (look at `modifications` keys)
   - For each parameter path, find the result with min and max adoption rates
   - Sensitivity score = max_rate - min_rate
   - Sort by sensitivity descending
   - Filter out params with sensitivity < `EXPLORER_SENSITIVITY_MIN_SCORE` (0.02)
   - Use `display_name()` from `src.utils.display` for human labels

3. **Generate missed insights** via `_generate_missed_insights()`:
   - Find all variants that beat baseline by > `EXPLORER_MISSED_INSIGHT_LIFT_THRESHOLD` (0.05 = 5pp)
   - For each, build human-readable difference descriptions:
     - Price: `"Price: ₹599 → ₹399"`
     - Float params: `"Awareness Budget: 45% → 70%"`
     - Bool params: `"School Partnership: enabled"`
   - Build explanation string: `"This variant achieves 67% adoption (+25% over your scenario) by reducing Price from ₹599 to ₹399 and enabling School Partnership."`
   - Limit to top 10 by lift, sorted descending
   - To get the old value for comparison, read from `base_scenario` using the dot-path

4. **Recommend configuration:**
   - Start with the best variant's modifications
   - Return as `recommended_modifications: dict[str, Any]`

#### 2.3 Helper: Get Nested Value from ScenarioConfig

```python
def _get_nested_value(config: ScenarioConfig, dot_path: str) -> Any:
    """
    Read a value from a ScenarioConfig using dot-notation.

    Example: _get_nested_value(config, "product.price_inr") → 599.0
    """
    obj = config
    for part in dot_path.split("."):
        if isinstance(obj, dict):
            obj = obj[part]
        else:
            obj = getattr(obj, part)
    return obj
```

#### 2.4 Helper: Format Modification for Display

```python
def _format_modification(
    path: str,
    old_value: Any,
    new_value: Any,
) -> str:
    """Human-readable description of a parameter change."""
    field_name = display_name(path.split(".")[-1])

    if "price" in path.lower():
        return f"{field_name}: ₹{old_value:.0f} → ₹{new_value:.0f}"
    if isinstance(new_value, bool):
        return f"{field_name}: {'enabled' if new_value else 'disabled'}"
    if isinstance(new_value, float) and isinstance(old_value, float):
        return f"{field_name}: {old_value:.0%} → {new_value:.0%}"
    return f"{field_name}: {old_value} → {new_value}"
```

### 3. Add Constants to `src/constants.py`

```python
# Auto-Scenario Exploration (Sprint 10)
EXPLORER_DEFAULT_VARIANT_COUNT = 100
EXPLORER_MAX_VARIANT_COUNT = 2000
EXPLORER_SWEEP_STEPS = 6
EXPLORER_GRID_MAX_COMBINATIONS = 500
EXPLORER_MISSED_INSIGHT_LIFT_THRESHOLD = 0.05
EXPLORER_MISSED_INSIGHT_MAX_DISPLAY = 10
EXPLORER_SENSITIVITY_MIN_SCORE = 0.02
EXPLORER_PRICE_MIN = 199
EXPLORER_PRICE_MAX = 999
EXPLORER_PRICE_STEP = 100
```

## Files to Read Before Starting

1. `src/simulation/static.py` — **full file** (88 lines) — `run_static_simulation()`, `StaticSimulationResult`
2. `src/simulation/counterfactual.py` — nested modification helpers, `CounterfactualResult`
3. `src/decision/scenarios.py` — `ScenarioConfig` model structure
4. `src/utils/display.py` — `display_name()` for parameter labels
5. `src/constants.py` — existing constants pattern
6. `docs/designs/AUTO-SCENARIO-EXPLORATION.md` — Sections 4-6

## Constraints

- Python 3.11+, Pydantic v2 with `ConfigDict(extra="forbid")`
- `VariantResult` must be importable by Track A (shared model) — if Track A defines `ScenarioVariant`, this track defines `VariantResult` and the report models
- Sequential execution is fine for v1 (ProcessPoolExecutor is future optimization)
- structlog for logging batch completion
- All models must pass `model_rebuild()` if they have forward references
- No new pip dependencies
- Use `statistics.median()` from stdlib

## Acceptance Criteria

- [ ] `VariantResult`, `ParameterSensitivity`, `MissedInsight`, `ExplorationReport` models defined
- [ ] `BatchSimulationRunner.run_batch()` executes all variants and returns ranked results
- [ ] Progress callback invoked after each variant
- [ ] `ExplorationConsolidator.consolidate()` produces complete report
- [ ] Parameter sensitivities computed and sorted by impact
- [ ] Missed insights generated with human-readable explanations
- [ ] Insights limited to top 10 by lift
- [ ] Constants added to `src/constants.py`
- [ ] All existing tests still pass
