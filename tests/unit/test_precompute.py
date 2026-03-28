"""Unit tests for precompute pipeline used by dashboard pages."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from scripts import precompute_results as precompute_module
from src.constants import DEFAULT_SEED
from src.generation.population import PopulationGenerator

if TYPE_CHECKING:
    from pathlib import Path


def test_precompute_creates_expected_artifacts(tmp_path: Path) -> None:
    population_path = tmp_path / "population"
    output_dir = tmp_path / "precomputed"

    manifest = precompute_module.precompute_results(
        population_path=population_path,
        output_dir=output_dir,
        scenario_ids=("nutrimix_2_6",),
        size=10,
        deep_persona_count=3,
        seed=DEFAULT_SEED,
        mock_llm=True,
        include_counterfactuals=True,
        include_reports=True,
    )

    assert manifest["seed"] == DEFAULT_SEED
    assert (output_dir / "precompute_manifest.json").exists()
    assert (output_dir / "nutrimix_2_6_simulation.json").exists()
    assert (output_dir / "nutrimix_2_6_decision_rows.json").exists()
    assert (output_dir / "nutrimix_2_6_counterfactuals.json").exists()
    assert (output_dir / "reports" / "nutrimix_2_6_report.md").exists()
    assert (output_dir / "reports" / "executive_summary.md").exists()

    simulation_payload = json.loads(
        (output_dir / "nutrimix_2_6_simulation.json").read_text(encoding="utf-8")
    )
    assert simulation_payload["scenario_id"] == "nutrimix_2_6"
    assert simulation_payload["mode"] == "temporal"


def test_precompute_defaults_to_default_seed(tmp_path: Path) -> None:
    population_path = tmp_path / "population"
    output_dir = tmp_path / "precomputed"

    manifest = precompute_module.precompute_results(
        population_path=population_path,
        output_dir=output_dir,
        scenario_ids=("protein_mix",),
        size=8,
        deep_persona_count=2,
        include_counterfactuals=False,
        include_reports=False,
    )

    assert manifest["seed"] == DEFAULT_SEED

    simulation_payload = json.loads(
        (output_dir / "protein_mix_simulation.json").read_text(encoding="utf-8")
    )
    assert simulation_payload["seed"] == DEFAULT_SEED


def test_precompute_reuses_existing_population(tmp_path: Path, monkeypatch) -> None:
    population_path = tmp_path / "population"
    output_dir = tmp_path / "precomputed"

    generator = PopulationGenerator()
    population = generator.generate(size=6, seed=7, deep_persona_count=2)
    population.save(population_path)

    def _raise_generate(self: Any, *args: Any, **kwargs: Any) -> Any:
        del self, args, kwargs
        raise AssertionError("PopulationGenerator.generate should not be called")

    monkeypatch.setattr(precompute_module.PopulationGenerator, "generate", _raise_generate)

    manifest = precompute_module.precompute_results(
        population_path=population_path,
        output_dir=output_dir,
        scenario_ids=("magnesium_gummies",),
        size=6,
        deep_persona_count=2,
        include_counterfactuals=False,
        include_reports=False,
    )

    assert manifest["scenario_ids"] == ["magnesium_gummies"]
    assert (output_dir / "magnesium_gummies_simulation.json").exists()
