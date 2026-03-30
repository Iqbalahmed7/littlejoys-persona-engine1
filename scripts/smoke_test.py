"""Standalone smoke test for verify all 4 scenarios across the full pipeline."""

from __future__ import annotations

import time
from pathlib import Path

import structlog

from src.analysis.pdf_export import generate_pdf_report
from src.analysis.research_consolidator import ConsolidatedReport, consolidate_research
from src.constants import SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.generation.population import PopulationGenerator
from src.simulation.research_runner import ResearchRunner

log = structlog.get_logger(__name__)


def run_smoke_test(size: int = 50, seed: int = 42) -> None:
    """Run all 4 scenarios through the full pipeline."""
    start_total = time.time()

    from src.config import Config
    from src.probing.question_bank import get_question
    from src.utils.llm import LLMClient

    log.info("generating_population", size=size, seed=seed)
    pop = PopulationGenerator().generate(size=size, seed=seed)

    config = Config(llm_mock_enabled=True)
    llm_client = LLMClient(config)
    question = get_question("q_nm26_repeat_purchase")

    output_dir = Path("data/results/smoke_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    for scenario_id in SCENARIO_IDS:
        log.info("processing_scenario", scenario_id=scenario_id)
        scenario = get_scenario(scenario_id)

        # 1. Run full simulation pipeline
        runner = ResearchRunner(
            population=pop,
            scenario=scenario,
            question=question,
            llm_client=llm_client,
            seed=seed,
            mock_mode=True
        )
        result = runner.run()

        # 2. Consolidate results
        report_dict = consolidate_research(result, pop)
        report = ConsolidatedReport.model_validate(report_dict)

        # 3. Basic assertions
        trial_rate = report.funnel.adoption_rate
        log.info("scenario_complete", scenario_id=scenario_id, trial_rate=f"{trial_rate:.1%}")

        if trial_rate <= 0:
            log.warning("zero_trial_rate", scenario_id=scenario_id)

        # 4. Generate PDF
        try:
            pdf_bytes = generate_pdf_report(report, scenario)
            pdf_path = output_dir / f"{scenario_id}_smoke.pdf"
            pdf_path.write_bytes(pdf_bytes)
            log.info("pdf_generated", path=str(pdf_path), size_kb=len(pdf_bytes) // 1024)
        except Exception as e:
            log.error("pdf_failed", scenario_id=scenario_id, error=str(e))
            raise

    duration = time.time() - start_total
    log.info("smoke_test_finished", duration_seconds=f"{duration:.1f}s")


if __name__ == "__main__":
    run_smoke_test()
