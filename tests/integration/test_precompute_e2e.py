"""Integration tests for the precompute pipeline."""

from __future__ import annotations

from pathlib import Path

from scripts.precompute_results import precompute_results
from src.constants import DEFAULT_SEED, SCENARIO_IDS


def _assert_manifest_files_exist(manifest: dict[str, object]) -> None:
    scenarios = manifest["scenarios"]
    assert isinstance(scenarios, dict)

    for scenario_id in manifest["scenario_ids"]:
        assert isinstance(scenario_id, str)
        scenario_entry = scenarios[scenario_id]
        assert isinstance(scenario_entry, dict)
        for key, value in scenario_entry.items():
            if key.endswith("_file"):
                assert isinstance(value, str)
                assert Path(value).exists(), f"Missing artifact for {scenario_id}: {key}"

    executive_summary = scenarios.get("executive_summary")
    if isinstance(executive_summary, dict):
        report_file = executive_summary.get("report_file")
        assert isinstance(report_file, str)
        assert Path(report_file).exists()


def test_precompute_e2e_with_counterfactuals_and_reports(tmp_path: Path) -> None:
    population_path = tmp_path / "population"
    output_dir = tmp_path / "precomputed"

    manifest = precompute_results(
        population_path=population_path,
        output_dir=output_dir,
        size=20,
        deep_persona_count=2,
        mock_llm=True,
        seed=DEFAULT_SEED,
        include_counterfactuals=True,
        include_reports=True,
    )

    assert "generated_at" in manifest
    assert "seed" in manifest
    assert "scenarios" in manifest
    assert "scenario_ids" in manifest
    assert manifest["seed"] == DEFAULT_SEED
    assert set(manifest["scenario_ids"]) == set(SCENARIO_IDS)

    scenarios = manifest["scenarios"]
    assert isinstance(scenarios, dict)
    for scenario_id in SCENARIO_IDS:
        scenario_entry = scenarios[scenario_id]
        assert isinstance(scenario_entry, dict)
        assert "simulation_file" in scenario_entry
        assert "decision_rows_file" in scenario_entry
        assert "adoption_rate" in scenario_entry
        assert "counterfactuals_file" in scenario_entry
        assert "report_file" in scenario_entry

    _assert_manifest_files_exist(manifest)


def test_precompute_e2e_skip_counterfactuals_and_reports(tmp_path: Path) -> None:
    population_path = tmp_path / "population"
    output_dir = tmp_path / "precomputed"

    manifest = precompute_results(
        population_path=population_path,
        output_dir=output_dir,
        scenario_ids=("nutrimix_2_6",),
        size=20,
        deep_persona_count=2,
        mock_llm=True,
        seed=DEFAULT_SEED,
        include_counterfactuals=False,
        include_reports=False,
    )

    scenarios = manifest["scenarios"]
    assert isinstance(scenarios, dict)
    scenario_entry = scenarios["nutrimix_2_6"]
    assert isinstance(scenario_entry, dict)
    assert "simulation_file" in scenario_entry
    assert "decision_rows_file" in scenario_entry
    assert "adoption_rate" in scenario_entry
    assert "counterfactuals_file" not in scenario_entry
    assert "report_file" not in scenario_entry
    assert "executive_summary" not in scenarios

    _assert_manifest_files_exist(manifest)
