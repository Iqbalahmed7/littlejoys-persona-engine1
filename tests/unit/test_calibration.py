"""Unit tests for threshold calibration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from src.constants import (
    CALIBRATION_TARGET_ADOPTION_MAX,
    CALIBRATION_TARGET_ADOPTION_MIN,
)
from src.decision.calibration import (
    CalibrationResult,
    calibrate_thresholds,
    evaluate_scenario_adoption,
)
from src.decision.scenarios import get_scenario
from src.generation.population import PopulationGenerator

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="module")
def calibration_artifacts(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[CalibrationResult, Path]:
    """Run calibration once for the module and reuse the saved artifact."""

    output_path = tmp_path_factory.mktemp("calibration") / "calibration.json"
    result = calibrate_thresholds(
        output_path=output_path,
        population_size=40,
        max_iterations=12,
        seed=42,
    )
    return result, output_path


def test_calibration_converges(calibration_artifacts: tuple[CalibrationResult, Path]) -> None:
    """Calibration should land inside the business target band within the iteration budget."""

    result, _ = calibration_artifacts

    assert result.iterations <= 12
    assert (
        CALIBRATION_TARGET_ADOPTION_MIN
        <= result.achieved_adoption_rate
        <= CALIBRATION_TARGET_ADOPTION_MAX
    )
    assert set(result.thresholds) == {
        "need_recognition",
        "awareness",
        "consideration",
        "purchase",
    }


def test_calibrated_thresholds_produce_target_adoption(
    calibration_artifacts: tuple[CalibrationResult, Path],
) -> None:
    """Re-running the calibrated scenario on the same seeded population should stay in-band."""

    result, _ = calibration_artifacts
    population = PopulationGenerator().generate(size=40, seed=42, deep_persona_count=0)
    scenario = get_scenario(result.scenario_id).model_copy(
        update={"thresholds": result.thresholds},
        deep=True,
    )
    evaluation = evaluate_scenario_adoption(population=population, scenario=scenario, seed=42)

    assert (
        CALIBRATION_TARGET_ADOPTION_MIN
        <= evaluation.adoption_rate
        <= CALIBRATION_TARGET_ADOPTION_MAX
    )
    assert evaluation.adoption_rate == pytest.approx(result.achieved_adoption_rate)


def test_calibration_result_saved_to_disk(
    calibration_artifacts: tuple[CalibrationResult, Path],
) -> None:
    """Calibration writes a JSON artifact that can be loaded back."""

    result, output_path = calibration_artifacts
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path.exists()
    assert payload["scenario_id"] == result.scenario_id
    assert payload["thresholds"] == result.thresholds
    assert payload["achieved_adoption_rate"] == pytest.approx(result.achieved_adoption_rate)
