from __future__ import annotations

import asyncio
from pathlib import Path

import structlog

from src.constants import SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.generation.population import Population, PopulationGenerator
from src.simulation.static import run_static_simulation

log = structlog.get_logger(__name__)


async def generate_all_reports(
    population_path: str = "data/population",
    output_dir: str = "data/results/reports",
    mock_llm: bool = True,
) -> None:
    path = Path(population_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("starting_report_generation", output_dir=str(out_dir), mock_llm=mock_llm)

    if not path.exists():
        log.info("generating_population", path=str(path))
        gen = PopulationGenerator()
        population = gen.generate()
        population.save(path)
    else:
        log.info("loading_population", path=str(path))
        population = Population.load(path)

    reports = []
    for scenario_id in SCENARIO_IDS:
        log.info("processing_scenario", scenario_id=scenario_id)
        scenario = get_scenario(scenario_id)
        results = run_static_simulation(population, scenario)

        # Temporary placeholder since ReportAgent is missing
        # We will dump some simulation statistics into markdown
        total = results.population_size
        adopters = results.adoption_count
        rate = results.adoption_rate
        report_content = (
            f"# Report for {scenario_id}\n\n"
            f"- Evaluated Personas: {total}\n"
            f"- Adopters: {adopters}\n"
            f"- Conversion Rate: {rate:.2%}\n"
            f"\n*Generated with mock_llm={mock_llm}*"
        )

        report_path = out_dir / f"{scenario_id}_report.md"
        report_path.write_text(report_content, encoding="utf-8")
        reports.append(report_content)

    summary_content = "# Executive Summary\n\n" + "\n\n".join(reports)
    summary_path = out_dir / "executive_summary.md"
    summary_path.write_text(summary_content, encoding="utf-8")

    log.info("reports_generated_successfully")


if __name__ == "__main__":
    asyncio.run(generate_all_reports())
