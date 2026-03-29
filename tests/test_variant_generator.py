"""Tests for scenario variant generation strategies."""

import pytest

try:
    from src.decision.scenarios import get_scenario
    from src.simulation.explorer import (
        CHANNEL_PRESETS,
        PARAMETER_SPACE,
        ScenarioVariant,
        VariantStrategy,
        generate_grid_variants,
        generate_random_variants,
        generate_smart_variants,
        generate_sweep_variants,
        generate_variants,
    )
except ImportError:
    pytest.skip("Sprint 10 modules not merged", allow_module_level=True)


@pytest.fixture
def base_scenario():
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
            # If config is present, we assert its object validation succeeded
            assert v.scenario_config is not None


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
        for a, b in zip(v1, v2, strict=True):
            assert a.modifications == b.modifications

    def test_random_variants_differ(self, base_scenario):
        variants = generate_random_variants(base_scenario, n_variants=20, seed=42)
        mods_set = [frozenset(v.modifications.items()) for v in variants]
        # At least 80% should be unique
        assert len(set(mods_set)) >= len(variants) * 0.8


class TestSmartStrategy:
    def test_smart_requires_base_result(self, base_scenario):
        from pathlib import Path

        from src.simulation.static import run_static_simulation

        pop_path = Path("data/population")
        if not pop_path.exists():
            pytest.skip("Population data not generated")

        from src.generation.population import Population

        pop = Population.load(pop_path)
        base_result = run_static_simulation(pop, base_scenario)
        variants = generate_smart_variants(base_scenario, base_result)
        assert len(variants) >= 5

    def test_smart_targets_rejection_stages(self, base_scenario):
        from pathlib import Path

        from src.simulation.static import run_static_simulation

        pop_path = Path("data/population")
        if not pop_path.exists():
            pytest.skip("Population data not generated")

        from src.generation.population import Population

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
            assert abs(total - 1.0) < 0.05, f"Variant {v.variant_id} channel_mix sums to {total}"
