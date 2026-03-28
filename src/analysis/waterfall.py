from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict

log = structlog.get_logger(__name__)


class WaterfallStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    entered: int
    passed: int
    dropped: int
    pass_rate: float
    cumulative_pass_rate: float


def compute_funnel_waterfall(
    results: dict[str, dict[str, Any]],
) -> list[WaterfallStage]:
    """
    Computes passing rates and retention across four primary adoption stages.
    Stages: need_recognition, awareness, consideration, purchase.
    """
    total_population = len(results)
    if total_population == 0:
        return []

    stages = ["need_recognition", "awareness", "consideration", "purchase"]

    log.debug("computing_funnel_waterfall", total_population=total_population, stages=stages)

    # Pre-aggregate dropped numbers for each stage
    drops_per_stage = {stage: 0 for stage in stages}
    for person_data in results.values():
        rej_stage = person_data.get("rejection_stage")
        if rej_stage in drops_per_stage:
            drops_per_stage[rej_stage] += 1

    # Final adopters are those who didn't drop
    total_dropped = sum(drops_per_stage.values())
    adopted = total_population - total_dropped
    cumulative_rate = adopted / total_population

    waterfall = []
    current_entered = total_population

    for stage in stages:
        dropped = drops_per_stage[stage]
        passed = current_entered - dropped

        pass_rate = 0.0
        if current_entered > 0:
            pass_rate = passed / current_entered

        waterfall.append(
            WaterfallStage(
                stage=stage,
                entered=current_entered,
                passed=passed,
                dropped=dropped,
                pass_rate=pass_rate,
                cumulative_pass_rate=cumulative_rate,
            )
        )
        current_entered = passed

    log.info("funnel_waterfall_computed", adopted=adopted, total_dropped=total_dropped)
    return waterfall
