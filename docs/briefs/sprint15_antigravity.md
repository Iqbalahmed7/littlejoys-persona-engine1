# Sprint 15 Brief — Antigravity (Gemini 3 Flash)
## Test Cleanup + Integration Smoke Test

### Context
Sprint 15 deletes 8 deprecated pages (Cursor's job). Tests that reference those pages will break. Your job is to clean up test references and add an integration smoke test for the full research pipeline.

### Task 1: Clean Up Test References to Deleted Pages

After Cursor deletes the old pages, these tests need updating:

**`tests/unit/test_page_logic.py`:**
- Lines referencing `app.pages.5_interviews` and `app.pages.6_report` — these pages no longer exist
- Either remove those test functions entirely, OR update them to test the replacement pages (`app.pages.4_interviews`, `app.pages.3_results`)
- The `_FakeStreamlit` mock approach may not work for the new pages since they import from `src.analysis.research_consolidator` etc. — if so, use the `ast.parse` approach from `test_page_imports.py` instead

**`tests/unit/test_page_imports.py`:**
- Verify all `ast.parse` paths point to files that still exist after cleanup
- Current entries: `2_research.py`, `1_personas.py`, `3_results.py`, `4_interviews.py` — all should survive cleanup

**`tests/unit/test_precompute.py`:**
- Line 37 references precomputed report markdown — verify this still works (the `6_report.py` page is gone but precompute scripts may be independent)

### Task 2: Integration Smoke Test

**New file:** `tests/integration/test_research_pipeline.py`

This test runs the full research pipeline end-to-end without a Streamlit server. It verifies the core flow works:

```python
"""Integration smoke test for the full research pipeline."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.config import Config
from src.constants import DASHBOARD_DEFAULT_POPULATION_PATH, DEFAULT_SEED
from src.decision.scenarios import get_scenario
from src.generation.population import Population, PopulationGenerator
from src.probing.question_bank import get_questions_for_scenario
from src.simulation.research_runner import ResearchRunner, ResearchResult
from src.analysis.research_consolidator import consolidate_research, ConsolidatedReport
from src.utils.llm import LLMClient


@pytest.fixture(scope="module")
def population():
    """Load or generate population once for all tests in this module."""
    path = Path(DASHBOARD_DEFAULT_POPULATION_PATH)
    if (path / "population_meta.json").exists():
        return Population.load(path)
    return PopulationGenerator().generate(seed=DEFAULT_SEED)


@pytest.fixture(scope="module")
def research_result(population):
    """Run the full research pipeline in mock mode."""
    scenario = get_scenario("nutrimix_2_6")
    questions = get_questions_for_scenario("nutrimix_2_6")
    question = questions[0]

    llm = LLMClient(Config(
        llm_mock_enabled=True,
        llm_cache_enabled=False,
        anthropic_api_key="",
    ))

    runner = ResearchRunner(
        population=population,
        scenario=scenario,
        question=question,
        llm_client=llm,
        mock_mode=True,
        alternative_count=10,  # Fewer for speed
        sample_size=5,         # Fewer for speed
        seed=42,
    )

    return runner.run()


def test_pipeline_produces_result(research_result):
    """Pipeline returns a valid ResearchResult."""
    assert isinstance(research_result, ResearchResult)
    assert research_result.primary_funnel.population_size > 0
    assert len(research_result.smart_sample.selections) > 0
    assert len(research_result.interview_results) > 0
    assert len(research_result.alternative_runs) > 0


def test_consolidation_succeeds(research_result, population):
    """Consolidation transforms raw result into a report."""
    report = consolidate_research(research_result, population)
    assert isinstance(report, ConsolidatedReport)
    assert report.funnel.population_size > 0
    assert len(report.segments_by_tier) > 0
    assert report.interview_count > 0


def test_report_has_alternatives(research_result, population):
    """Consolidated report includes ranked alternatives."""
    report = consolidate_research(research_result, population)
    assert len(report.top_alternatives) > 0
    # Top alternatives should be ranked by delta descending
    deltas = [a.delta_vs_primary for a in report.top_alternatives]
    assert deltas == sorted(deltas, reverse=True)


def test_all_scenarios_run(population):
    """Quick check that pipeline can run for all 4 scenarios."""
    from src.constants import SCENARIO_IDS

    llm = LLMClient(Config(
        llm_mock_enabled=True,
        llm_cache_enabled=False,
        anthropic_api_key="",
    ))

    for sid in SCENARIO_IDS:
        scenario = get_scenario(sid)
        questions = get_questions_for_scenario(sid)
        runner = ResearchRunner(
            population=population,
            scenario=scenario,
            question=questions[0],
            llm_client=llm,
            mock_mode=True,
            alternative_count=5,
            sample_size=3,
            seed=42,
        )
        result = runner.run()
        assert result.primary_funnel.population_size > 0
        assert result.metadata.scenario_id == sid
```

### Task 3: Update Test Count Expectations

After cleanup, run the full suite and report the final test count:
```bash
uv run pytest tests/ -v
```

### Deliverables
1. `tests/unit/test_page_logic.py` — updated to remove/fix references to deleted pages
2. `tests/unit/test_page_imports.py` — verified all paths are correct
3. `tests/integration/test_research_pipeline.py` — 4 integration tests
4. All tests pass after Cursor's page deletions

### Dependencies
- **Depends on Cursor Sprint 15** completing page deletions first

### Do NOT
- Modify source modules in `src/`
- Modify page files in `app/pages/`
- Skip tests with `@pytest.mark.skip`
- Make real LLM calls (all tests use mock mode)
