"""Precompute simulation, counterfactual, and report artifacts for demo speed."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

import structlog

from src.analysis.report_agent import ReportAgent
from src.config import Config
from src.constants import (
    DEFAULT_DEEP_PERSONA_COUNT,
    DEFAULT_POPULATION_SIZE,
    DEFAULT_SEED,
    SCENARIO_IDS,
    SCENARIO_MODE_TEMPORAL,
)
from src.decision.scenarios import get_scenario
from src.generation.population import Population, PopulationGenerator
from src.simulation.counterfactual import (
    get_predefined_counterfactuals,
    run_predefined_counterfactual,
)
from src.simulation.static import run_static_simulation
from src.simulation.temporal import run_temporal_simulation
from src.utils.llm import LLMClient

log = structlog.get_logger(__name__)

PRECOMPUTE_DEFAULT_POPULATION_PATH = "data/population"
PRECOMPUTE_DEFAULT_OUTPUT_DIR = "data/results/precomputed"

_T = TypeVar("_T")


def _run_async(coro: Any) -> _T:
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_or_generate_population(
    population_path: str | Path,
    *,
    size: int,
    deep_persona_count: int,
    seed: int,
) -> Population:
    """Load a saved population; generate one if not present."""

    path = Path(population_path)
    meta_path = path / "population_meta.json"

    if meta_path.exists():
        log.info("precompute_population_loaded", path=str(path))
        return Population.load(path)

    log.info("precompute_population_generate", path=str(path), size=size, seed=seed)
    population = PopulationGenerator().generate(
        size=size,
        seed=seed,
        deep_persona_count=deep_persona_count,
    )
    population.save(path)
    return population


def _build_simulation_payload(
    population: Population,
    scenario_id: str,
    *,
    seed: int,
) -> dict[str, Any]:
    scenario = get_scenario(scenario_id)
    if scenario.mode == SCENARIO_MODE_TEMPORAL:
        temporal = run_temporal_simulation(
            population=population,
            scenario=scenario,
            months=scenario.months,
            seed=seed,
        )
        return {
            "scenario_id": scenario.id,
            "scenario_name": scenario.name,
            "mode": SCENARIO_MODE_TEMPORAL,
            "seed": seed,
            "result": temporal.model_dump(mode="json"),
        }

    static = run_static_simulation(population=population, scenario=scenario, seed=seed)
    return {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "mode": "static",
        "seed": seed,
        "result": static.model_dump(mode="json"),
    }


def _build_decision_rows_payload(
    population: Population,
    scenario_id: str,
    *,
    seed: int,
) -> dict[str, Any]:
    scenario = get_scenario(scenario_id)
    static = run_static_simulation(population=population, scenario=scenario, seed=seed)
    return {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "seed": seed,
        "population_size": static.population_size,
        "adoption_count": static.adoption_count,
        "adoption_rate": static.adoption_rate,
        "results_by_persona": static.results_by_persona,
    }


def _build_counterfactual_payload(
    population: Population,
    scenario_id: str,
    *,
    seed: int,
) -> dict[str, Any]:
    catalog = get_predefined_counterfactuals(scenario_id)
    names = sorted(catalog.keys())

    results: list[dict[str, Any]] = []
    for name in names:
        result = run_predefined_counterfactual(
            population=population,
            scenario_id=scenario_id,
            counterfactual_name=name,
            seed=seed,
        )
        results.append(result.model_dump(mode="json"))

    return {
        "scenario_id": scenario_id,
        "seed": seed,
        "counterfactuals": results,
    }


async def _generate_reports(
    *,
    scenario_ids: tuple[str, ...],
    population: Population,
    decision_rows_by_scenario: dict[str, dict[str, Any]],
    reports_dir: Path,
    mock_llm: bool,
) -> dict[str, str]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    client = LLMClient(
        Config(
            llm_mock_enabled=mock_llm,
            llm_cache_enabled=False,
            anthropic_api_key="",
        )
    )
    agent = ReportAgent(client)

    report_paths: dict[str, str] = {}
    summary_blocks: list[str] = ["# Executive Summary", f"*Generated with mock_llm={mock_llm}*"]

    for scenario_id in scenario_ids:
        report = await agent.generate_report(
            scenario_id=scenario_id,
            results=decision_rows_by_scenario[scenario_id],
            population=population,
        )
        report_path = reports_dir / f"{scenario_id}_report.md"
        report_path.write_text(report.raw_markdown, encoding="utf-8")
        report_paths[scenario_id] = str(report_path)

        executive = next(
            (
                section.content
                for section in report.sections
                if section.title == "Executive Summary"
            ),
            "No executive summary generated.",
        )
        summary_blocks.append(f"## {scenario_id}\n{executive}")

    summary_path = reports_dir / "executive_summary.md"
    summary_path.write_text("\n\n".join(summary_blocks), encoding="utf-8")
    report_paths["executive_summary"] = str(summary_path)
    return report_paths


def precompute_results(
    *,
    population_path: str | Path = PRECOMPUTE_DEFAULT_POPULATION_PATH,
    output_dir: str | Path = PRECOMPUTE_DEFAULT_OUTPUT_DIR,
    scenario_ids: tuple[str, ...] = SCENARIO_IDS,
    size: int = DEFAULT_POPULATION_SIZE,
    deep_persona_count: int = DEFAULT_DEEP_PERSONA_COUNT,
    seed: int = DEFAULT_SEED,
    mock_llm: bool = True,
    include_counterfactuals: bool = True,
    include_reports: bool = True,
) -> dict[str, Any]:
    """
    Precompute artifacts used by Streamlit pages for instant demo interactions.

    Returns:
        Manifest payload written to ``precompute_manifest.json``.
    """

    scenario_list = scenario_ids
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    population = load_or_generate_population(
        population_path,
        size=size,
        deep_persona_count=deep_persona_count,
        seed=seed,
    )

    manifest_scenarios: dict[str, dict[str, Any]] = {}
    decision_rows_by_scenario: dict[str, dict[str, Any]] = {}

    for scenario_id in scenario_list:
        log.info("precompute_scenario_started", scenario_id=scenario_id)

        simulation_payload = _build_simulation_payload(population, scenario_id, seed=seed)
        simulation_path = out_path / f"{scenario_id}_simulation.json"
        _write_json(simulation_path, simulation_payload)

        decision_rows_payload = _build_decision_rows_payload(population, scenario_id, seed=seed)
        decision_rows_path = out_path / f"{scenario_id}_decision_rows.json"
        _write_json(decision_rows_path, decision_rows_payload)
        decision_rows_by_scenario[scenario_id] = decision_rows_payload["results_by_persona"]

        scenario_manifest: dict[str, Any] = {
            "mode": simulation_payload["mode"],
            "simulation_file": str(simulation_path),
            "decision_rows_file": str(decision_rows_path),
            "adoption_rate": decision_rows_payload["adoption_rate"],
            "population_size": decision_rows_payload["population_size"],
        }

        if include_counterfactuals:
            counterfactual_payload = _build_counterfactual_payload(
                population, scenario_id, seed=seed
            )
            counterfactual_path = out_path / f"{scenario_id}_counterfactuals.json"
            _write_json(counterfactual_path, counterfactual_payload)
            scenario_manifest["counterfactuals_file"] = str(counterfactual_path)

        manifest_scenarios[scenario_id] = scenario_manifest
        log.info("precompute_scenario_complete", scenario_id=scenario_id)

    report_paths: dict[str, str] = {}
    if include_reports:
        reports_dir = out_path / "reports"
        report_paths = _run_async(
            _generate_reports(
                scenario_ids=scenario_list,
                population=population,
                decision_rows_by_scenario=decision_rows_by_scenario,
                reports_dir=reports_dir,
                mock_llm=mock_llm,
            )
        )
        for scenario_id in scenario_list:
            manifest_scenarios[scenario_id]["report_file"] = report_paths[scenario_id]
        manifest_scenarios["executive_summary"] = {"report_file": report_paths["executive_summary"]}

    manifest = {
        "generated_at": _iso_now(),
        "seed": seed,
        "mock_llm": mock_llm,
        "population_path": str(Path(population_path)),
        "output_dir": str(out_path),
        "scenario_ids": list(scenario_list),
        "include_counterfactuals": include_counterfactuals,
        "include_reports": include_reports,
        "scenarios": manifest_scenarios,
    }
    _write_json(out_path / "precompute_manifest.json", manifest)
    return manifest


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Precompute scenario artifacts for Streamlit demo."
    )
    parser.add_argument("--population-path", default=PRECOMPUTE_DEFAULT_POPULATION_PATH)
    parser.add_argument("--output-dir", default=PRECOMPUTE_DEFAULT_OUTPUT_DIR)
    parser.add_argument("--size", type=int, default=DEFAULT_POPULATION_SIZE)
    parser.add_argument("--deep-persona-count", type=int, default=DEFAULT_DEEP_PERSONA_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--scenario-ids",
        default=",".join(SCENARIO_IDS),
        help="Comma-separated scenario IDs to precompute.",
    )
    parser.add_argument(
        "--mock-llm",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether to run report generation in mock mode.",
    )
    parser.add_argument(
        "--include-counterfactuals",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--include-reports",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    scenario_ids = tuple(
        scenario_id.strip() for scenario_id in args.scenario_ids.split(",") if scenario_id.strip()
    )

    manifest = precompute_results(
        population_path=args.population_path,
        output_dir=args.output_dir,
        scenario_ids=scenario_ids,
        size=args.size,
        deep_persona_count=args.deep_persona_count,
        seed=args.seed,
        mock_llm=args.mock_llm,
        include_counterfactuals=args.include_counterfactuals,
        include_reports=args.include_reports,
    )
    log.info("precompute_complete", output_dir=manifest["output_dir"])


if __name__ == "__main__":
    main()
