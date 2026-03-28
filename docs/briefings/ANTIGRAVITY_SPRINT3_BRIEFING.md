# Antigravity — Sprint 3 Briefing

> **Sprint**: 3 (Days 5-6)
> **Branch**: `feat/PRD-008-waterfall` from `staging`
> **PRDs**: PRD-008 (waterfall data), PRD-010 (report generation script)

---

## Your Assignments

### Task 1: Funnel Waterfall Data Pipeline (P0)

**File**: `src/analysis/waterfall.py` (new file)

Build the funnel waterfall computation for visualization.

Models:
```python
class WaterfallStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    entered: int
    passed: int
    dropped: int
    pass_rate: float
    cumulative_pass_rate: float
```

Function:
```python
def compute_funnel_waterfall(
    results: dict[str, dict[str, Any]],
) -> list[WaterfallStage]:
```

Logic:
1. Total population = len(results)
2. Walk through funnel stages in order: `need_recognition`, `awareness`, `consideration`, `purchase`
3. For each stage, count personas whose `rejection_stage` equals that stage — those are the `dropped`
4. `entered` = total - sum of all drops in previous stages
5. `passed` = entered - dropped
6. `pass_rate` = passed / entered (handle division by zero)
7. `cumulative_pass_rate` = final adopters / total population
8. Handle edge cases: empty results, all-adopt (every stage has 0 drops), all-reject

Tests in `tests/unit/test_waterfall.py`:
- `test_waterfall_stages_in_funnel_order`
- `test_waterfall_entered_decreases_monotonically`
- `test_waterfall_all_adopt_shows_zero_drops`
- `test_waterfall_all_reject_shows_full_drop_at_first_stage`
- `test_waterfall_empty_input`
- `test_waterfall_cumulative_rate_matches_adoption`

### Task 2: Report Generation Script (P1)

**File**: `scripts/generate_reports.py` (new file)

Orchestration script that generates analysis reports for all 4 business problems.

```python
async def generate_all_reports(
    population_path: str = "data/population.parquet",
    output_dir: str = "data/results/reports",
    mock_llm: bool = True,
) -> None:
```

Logic:
1. Load population from Parquet (or generate with `PopulationGenerator` if file doesn't exist)
2. For each of the 4 scenarios (`SCENARIO_IDS` from constants):
   a. Get scenario config via `get_scenario()`
   b. Run static simulation
   c. Pass results to `ReportAgent.generate_report()`
   d. Save report markdown to `{output_dir}/{scenario_id}_report.md`
3. Generate combined executive summary from all 4 reports
4. Save to `{output_dir}/executive_summary.md`
5. Log timing for each step with structlog

**Important**: Default to `mock_llm=True` so the script runs in CI without API keys. When `mock_llm=False`, use the real LLM client.

**Note**: This task depends on Codex completing the ReportAgent (Task 2 from their briefing). If the ReportAgent isn't ready yet, implement the script skeleton with a placeholder that saves raw simulation statistics as the "report" — we can swap in the real ReportAgent later.

Tests in `tests/unit/test_report_generation.py`:
- `test_generate_reports_creates_output_files`
- `test_generate_reports_handles_mock_mode`
- `test_executive_summary_covers_all_scenarios`

---

## Standards Reminder

- Pydantic `BaseModel` with `ConfigDict(extra="forbid")` for all models
- `structlog.get_logger(__name__)` — no bare `logging` or `print`
- No magic numbers — use `src/constants.py`
- New files need `from __future__ import annotations` at the top
- Run before submitting:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest tests/unit/test_waterfall.py -v
  ```

---

## Sprint 2 Feedback

Composite was **8.5/10** — highest on the team this sprint. No bugs found, no review fixes needed. Strong improvement from Sprint 1. Keep it up.

For Sprint 3: Task 1 (waterfall) is straightforward — deliver this first. Task 2 (report generation) has a dependency on Codex's ReportAgent, so build the skeleton early and wire in the real agent when it lands.
