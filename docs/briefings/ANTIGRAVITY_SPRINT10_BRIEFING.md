# Antigravity — Sprint 10 Track D: Tests for Auto-Scenario Explorer

**Branch:** `sprint-10-track-d-tests`
**Base:** `main`

## Context

Sprint 10 introduces the Auto-Scenario Exploration system with three new modules:
- `src/simulation/explorer.py` (Track A) — Variant generation with 4 strategies
- `src/simulation/batch.py` (Track B) — Batch simulation runner
- `src/simulation/consolidation.py` (Track B) — Results consolidation + insights

This track writes tests for all three.

## Deliverables

### 1. Variant Generator Tests

**File:** `tests/test_variant_generator.py` (NEW)

```python
"""Tests for scenario variant generation strategies."""

import pytest
from src.decision.scenarios import get_scenario, ScenarioConfig
from src.simulation.explorer import (
    ScenarioVariant,
    VariantStrategy,
    PARAMETER_SPACE,
    CHANNEL_PRESETS,
    generate_variants,
    generate_sweep_variants,
    generate_grid_variants,
    generate_random_variants,
    generate_smart_variants,
)


@pytest.fixture
def base_scenario() -> ScenarioConfig:
    return get_scenario("nutrimix_2_6")


class TestParameterSpace:
    def test_parameter_space_non_empty(self):
        assert len(PARAMETER_SPACE) >= 10

    def test_all_paths_resolve(self, base_scenario):
        """Every parameter path in PARAMETER_SPACE must exist on the scenario."""
        for param in PARAMETER_SPACE:
            obj = base_scenario
            for part in param.path.split("."):
                if isinstance(obj, dict):
                    assert part in obj, f"Path {param.path} not found"
                    obj = obj[part]
                else:
                    assert hasattr(obj, part), f"Path {param.path} not found at {part}"
                    obj = getattr(obj, part)

    def test_channel_presets_sum_to_one(self):
        for name, mix in CHANNEL_PRESETS.items():
            total = sum(mix.values())
            assert abs(total - 1.0) < 0.01, f"Preset {name} sums to {total}"


class TestSweepStrategy:
    def test_sweep_generates_variants(self, base_scenario):
        variants = generate_sweep_variants(base_scenario)
        assert len(variants) >= 20  # At least 20 sweep variants

    def test_sweep_variants_are_valid(self, base_scenario):
        variants = generate_sweep_variants(base_scenario)
        for v in variants:
            assert isinstance(v, ScenarioVariant)
            assert v.variant_id.startswith("sweep_")
            assert v.strategy == "sweep"
            assert len(v.modifications) >= 1

    def test_sweep_variant_configs_valid(self, base_scenario):
        """All generated ScenarioConfigs must pass Pydantic validation."""
        variants = generate_sweep_variants(base_scenario)
        for v in variants:
            # If it's a ScenarioConfig, it passed validation
            assert isinstance(v.scenario_config, ScenarioConfig)


class TestGridStrategy:
    def test_grid_generates_combinations(self, base_scenario):
        variants = generate_grid_variants(base_scenario)
        assert len(variants) >= 10

    def test_grid_respects_max_combinations(self, base_scenario):
        variants = generate_grid_variants(base_scenario, max_combinations=10)
        assert len(variants) <= 10

    def test_grid_variants_have_multiple_modifications(self, base_scenario):
        variants = generate_grid_variants(base_scenario)
        for v in variants:
            assert len(v.modifications) >= 2  # Grid = multiple params


class TestRandomStrategy:
    def test_random_generates_n_variants(self, base_scenario):
        variants = generate_random_variants(base_scenario, n_variants=50, seed=42)
        assert len(variants) == 50

    def test_random_is_deterministic(self, base_scenario):
        v1 = generate_random_variants(base_scenario, n_variants=10, seed=42)
        v2 = generate_random_variants(base_scenario, n_variants=10, seed=42)
        for a, b in zip(v1, v2):
            assert a.modifications == b.modifications

    def test_random_variants_differ(self, base_scenario):
        variants = generate_random_variants(base_scenario, n_variants=20, seed=42)
        mods_set = [frozenset(v.modifications.items()) for v in variants]
        # At least 80% should be unique
        assert len(set(mods_set)) >= len(variants) * 0.8


class TestSmartStrategy:
    def test_smart_requires_base_result(self, base_scenario):
        from src.simulation.static import run_static_simulation
        from pathlib import Path
        from src.generation.population import Population

        pop_path = Path("data/population")
        if not pop_path.exists():
            pytest.skip("Population data not generated")

        pop = Population.load(pop_path)
        base_result = run_static_simulation(pop, base_scenario)
        variants = generate_smart_variants(base_scenario, base_result)
        assert len(variants) >= 5

    def test_smart_targets_rejection_stages(self, base_scenario):
        from src.simulation.static import run_static_simulation, StaticSimulationResult
        from pathlib import Path
        from src.generation.population import Population

        pop_path = Path("data/population")
        if not pop_path.exists():
            pytest.skip("Population data not generated")

        pop = Population.load(pop_path)
        base_result = run_static_simulation(pop, base_scenario)
        variants = generate_smart_variants(base_scenario, base_result)

        # Variant names should reference rejection stages
        names = [v.variant_name.lower() for v in variants]
        has_targeted = any(
            any(stage in name for stage in ["awareness", "purchase", "consideration", "fix"])
            for name in names
        )
        assert has_targeted, f"Smart variants should target rejection stages: {names}"


class TestMasterGenerator:
    def test_always_includes_baseline(self, base_scenario):
        variants = generate_variants(
            base=base_scenario,
            strategy=VariantStrategy.SWEEP,
        )
        baselines = [v for v in variants if v.is_baseline]
        assert len(baselines) == 1
        assert baselines[0].variant_id == "baseline"

    def test_channel_mix_normalized(self, base_scenario):
        """All variants must have channel_mix summing to ~1.0."""
        variants = generate_variants(
            base=base_scenario,
            strategy=VariantStrategy.SWEEP,
        )
        for v in variants:
            mix = v.scenario_config.marketing.channel_mix
            total = sum(mix.values())
            assert abs(total - 1.0) < 0.05, (
                f"Variant {v.variant_id} channel_mix sums to {total}"
            )
```

### 2. Batch Runner Tests

**File:** `tests/test_batch_runner.py` (NEW)

```python
"""Tests for batch simulation runner."""

import pytest
from pathlib import Path
from src.decision.scenarios import get_scenario


@pytest.fixture
def population():
    pop_path = Path("data/population")
    if not pop_path.exists():
        pytest.skip("Population data not generated")
    from src.generation.population import Population
    return Population.load(pop_path)


class TestBatchRunner:
    def test_runs_all_variants(self, population):
        from src.simulation.explorer import generate_sweep_variants, ScenarioVariant
        from src.simulation.batch import BatchSimulationRunner

        base = get_scenario("nutrimix_2_6")
        # Use just a few sweep variants for speed
        variants = generate_sweep_variants(base)[:5]
        baseline = ScenarioVariant(
            variant_id="baseline",
            variant_name="Baseline",
            strategy="sweep",
            modifications={},
            scenario_config=base,
            is_baseline=True,
        )

        runner = BatchSimulationRunner(population)
        results = runner.run_batch([baseline] + variants)

        assert len(results) == len(variants) + 1  # +1 for baseline

    def test_results_sorted_by_adoption(self, population):
        from src.simulation.explorer import generate_sweep_variants, ScenarioVariant
        from src.simulation.batch import BatchSimulationRunner

        base = get_scenario("nutrimix_2_6")
        variants = generate_sweep_variants(base)[:5]
        baseline = ScenarioVariant(
            variant_id="baseline",
            variant_name="Baseline",
            strategy="sweep",
            modifications={},
            scenario_config=base,
            is_baseline=True,
        )

        runner = BatchSimulationRunner(population)
        results = runner.run_batch([baseline] + variants)

        rates = [r.adoption_rate for r in results]
        assert rates == sorted(rates, reverse=True)

    def test_progress_callback_invoked(self, population):
        from src.simulation.explorer import ScenarioVariant
        from src.simulation.batch import BatchSimulationRunner

        base = get_scenario("nutrimix_2_6")
        baseline = ScenarioVariant(
            variant_id="baseline",
            variant_name="Baseline",
            strategy="sweep",
            modifications={},
            scenario_config=base,
            is_baseline=True,
        )

        calls = []
        def callback(done, total):
            calls.append((done, total))

        runner = BatchSimulationRunner(population)
        runner.run_batch([baseline], progress_callback=callback)

        assert len(calls) == 1
        assert calls[0] == (1, 1)

    def test_results_have_ranks(self, population):
        from src.simulation.explorer import generate_sweep_variants, ScenarioVariant
        from src.simulation.batch import BatchSimulationRunner

        base = get_scenario("nutrimix_2_6")
        variants = generate_sweep_variants(base)[:3]
        baseline = ScenarioVariant(
            variant_id="baseline",
            variant_name="Baseline",
            strategy="sweep",
            modifications={},
            scenario_config=base,
            is_baseline=True,
        )

        runner = BatchSimulationRunner(population)
        results = runner.run_batch([baseline] + variants)

        ranks = [r.rank for r in results]
        assert ranks == list(range(1, len(results) + 1))
```

### 3. Consolidation Tests

**File:** `tests/test_consolidation.py` (NEW)

```python
"""Tests for exploration consolidation and insight generation."""

import pytest
from src.simulation.consolidation import (
    VariantResult,
    ParameterSensitivity,
    MissedInsight,
    ExplorationReport,
    ExplorationConsolidator,
)
from src.decision.scenarios import get_scenario


def _make_result(variant_id, name, rate, mods=None, is_baseline=False):
    return VariantResult(
        variant_id=variant_id,
        variant_name=name,
        adoption_rate=rate,
        adoption_count=int(rate * 200),
        population_size=200,
        rejection_distribution={"awareness": 50, "purchase": 30},
        modifications=mods or {},
        is_baseline=is_baseline,
        rank=0,
    )


@pytest.fixture
def sample_results():
    return [
        _make_result("baseline", "Baseline", 0.40, is_baseline=True),
        _make_result("v001", "Price ₹399", 0.65, {"product.price_inr": 399}),
        _make_result("v002", "Price ₹799", 0.20, {"product.price_inr": 799}),
        _make_result("v003", "High Awareness", 0.55, {"marketing.awareness_budget": 0.8}),
        _make_result("v004", "Low Awareness", 0.25, {"marketing.awareness_budget": 0.2}),
        _make_result("v005", "School ON", 0.48, {"marketing.school_partnership": True}),
    ]


class TestConsolidator:
    def test_report_has_all_fields(self, sample_results):
        base = get_scenario("nutrimix_2_6")
        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=sample_results,
            execution_time=5.0,
            strategy="sweep",
        )
        assert isinstance(report, ExplorationReport)
        assert report.total_variants == len(sample_results)
        assert report.baseline_result.is_baseline
        assert report.best_result.adoption_rate >= report.worst_result.adoption_rate

    def test_sensitivities_sorted_by_impact(self, sample_results):
        base = get_scenario("nutrimix_2_6")
        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=sample_results,
            execution_time=5.0,
            strategy="sweep",
        )
        if len(report.parameter_sensitivities) >= 2:
            scores = [s.sensitivity_score for s in report.parameter_sensitivities]
            assert scores == sorted(scores, reverse=True)

    def test_missed_insights_have_positive_lift(self, sample_results):
        base = get_scenario("nutrimix_2_6")
        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=sample_results,
            execution_time=5.0,
            strategy="sweep",
        )
        for insight in report.missed_insights:
            assert insight.lift_over_baseline > 0
            assert insight.adoption_rate > report.baseline_result.adoption_rate

    def test_missed_insights_limited(self, sample_results):
        base = get_scenario("nutrimix_2_6")
        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=sample_results,
            execution_time=5.0,
            strategy="sweep",
        )
        assert len(report.missed_insights) <= 10

    def test_missed_insights_have_explanations(self, sample_results):
        base = get_scenario("nutrimix_2_6")
        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=sample_results,
            execution_time=5.0,
            strategy="sweep",
        )
        for insight in report.missed_insights:
            assert len(insight.explanation) > 20
            assert len(insight.key_differences) >= 1


class TestVariantResultModel:
    def test_variant_result_creation(self):
        result = _make_result("test", "Test", 0.5)
        assert result.variant_id == "test"
        assert result.adoption_rate == 0.5

    def test_variant_result_extra_forbidden(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            VariantResult(
                variant_id="x", variant_name="x",
                adoption_rate=0.5, adoption_count=100,
                population_size=200, rejection_distribution={},
                modifications={}, extra_field="bad",
            )


class TestParameterSensitivityModel:
    def test_creation(self):
        ps = ParameterSensitivity(
            parameter_path="product.price_inr",
            parameter_display_name="Price",
            min_value=399,
            max_value=799,
            adoption_rate_at_min=0.65,
            adoption_rate_at_max=0.20,
            sensitivity_score=0.45,
        )
        assert ps.sensitivity_score == 0.45
```

### 4. Integration Test

**File:** `tests/test_explorer_integration.py` (NEW)

```python
"""Integration test: full exploration pipeline."""

import pytest
from pathlib import Path


@pytest.fixture
def population():
    pop_path = Path("data/population")
    if not pop_path.exists():
        pytest.skip("Population data not generated")
    from src.generation.population import Population
    return Population.load(pop_path)


class TestFullPipeline:
    def test_sweep_end_to_end(self, population):
        from src.decision.scenarios import get_scenario
        from src.simulation.explorer import VariantStrategy, generate_variants
        from src.simulation.batch import BatchSimulationRunner
        from src.simulation.consolidation import ExplorationConsolidator

        base = get_scenario("nutrimix_2_6")

        # Generate
        variants = generate_variants(base, VariantStrategy.SWEEP)
        assert len(variants) >= 10

        # Run (just first 10 for speed)
        runner = BatchSimulationRunner(population)
        results = runner.run_batch(variants[:10])
        assert len(results) == 10

        # Consolidate
        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=results,
            execution_time=1.0,
            strategy="sweep",
        )

        assert report.total_variants == 10
        assert report.best_result.adoption_rate >= report.worst_result.adoption_rate
        assert report.baseline_result.is_baseline

    def test_smart_end_to_end(self, population):
        from src.decision.scenarios import get_scenario
        from src.simulation.explorer import VariantStrategy, generate_variants
        from src.simulation.batch import BatchSimulationRunner
        from src.simulation.consolidation import ExplorationConsolidator
        from src.simulation.static import run_static_simulation

        base = get_scenario("nutrimix_2_6")
        base_result = run_static_simulation(population, base)

        variants = generate_variants(
            base, VariantStrategy.SMART, base_result=base_result,
        )
        assert len(variants) >= 5

        runner = BatchSimulationRunner(population)
        results = runner.run_batch(variants)

        consolidator = ExplorationConsolidator()
        report = consolidator.consolidate(
            base_scenario_id="nutrimix_2_6",
            base_scenario=base,
            all_results=results,
            execution_time=1.0,
            strategy="smart",
        )

        assert report.total_variants >= 5
```

## Files to Read Before Starting

1. `src/decision/scenarios.py` — ScenarioConfig model
2. `src/simulation/static.py` — StaticSimulationResult, run_static_simulation
3. `docs/designs/AUTO-SCENARIO-EXPLORATION.md` — full design doc
4. `tests/test_probing_tree_viz.py` — existing test patterns

## Constraints

- Python 3.11+, pytest
- Tests requiring population: use `pytest.skip` if `data/population/` not available
- Unit tests (model validation, channel normalization): use synthetic data
- Integration tests: use real population but limit variants for speed
- No Streamlit rendering in tests
- Aim for ~32 tests total

## Acceptance Criteria

- [ ] 4 test files created
- [ ] ~32 tests total
- [ ] Variant generator tests cover all 4 strategies
- [ ] Channel mix normalization validated
- [ ] Batch runner tests verify ranking and progress callback
- [ ] Consolidation tests verify sensitivities, insights, and report structure
- [ ] Integration tests run full pipeline (generate → run → consolidate)
- [ ] All tests pass or skip gracefully
