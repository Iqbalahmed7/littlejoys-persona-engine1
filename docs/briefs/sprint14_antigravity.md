# Sprint 14 Brief — Antigravity (Gemini 3 Flash)
## Tests for Sprint 14 Components

### Context
Sprint 14 introduces the research consolidator backend and two rewritten Streamlit pages. Your job is to write tests for the consolidator and smoke tests for the new pages.

### Task 1: Research Consolidator Tests
**New file:** `tests/unit/test_research_consolidator.py`

Test `consolidate_research()` from `src/analysis/research_consolidator.py`.

#### Setup

You'll need a mock `ResearchResult`. Build one from real components:

```python
import pytest
from src.decision.scenarios import get_scenario
from src.generation.population import Population
from src.simulation.static import run_static_simulation
from src.probing.smart_sample import select_smart_sample
from src.probing.question_bank import get_question
from src.simulation.research_runner import (
    ResearchResult, ResearchMetadata, InterviewResult, AlternativeRunSummary,
)
from src.analysis.research_consolidator import consolidate_research, ConsolidatedReport


@pytest.fixture
def population():
    """Load or generate a small test population."""
    from src.constants import DASHBOARD_DEFAULT_POPULATION_PATH
    from pathlib import Path
    path = Path(DASHBOARD_DEFAULT_POPULATION_PATH)
    if (path / "population_meta.json").exists():
        return Population.load(path)
    from src.generation.population import PopulationGenerator
    return PopulationGenerator().generate(seed=42)


@pytest.fixture
def research_result(population):
    """Build a minimal but realistic ResearchResult."""
    scenario = get_scenario("nutrimix_2_6")
    primary = run_static_simulation(population, scenario, seed=42)
    sample = select_smart_sample(population.personas, primary.results_by_persona, target_size=5, seed=42)

    # Mock interview results
    interviews = [
        InterviewResult(
            persona_id=s.persona_id,
            persona_name=s.persona_id,
            selection_reason=s.selection_reason,
            responses=[
                {"question": "What do you think about the price?", "answer": "The price seems expensive for our budget. We already spend on other health products."},
                {"question": "Would you trust this product?", "answer": "I would trust it more if a pediatrician recommended it."},
            ],
        )
        for s in sample.selections[:5]
    ]

    alternatives = [
        AlternativeRunSummary(
            variant_id=f"test_{i}",
            parameter_changes={"product.price_inr": 500 - i * 50},
            business_rationale=f"Test variant {i}",
            adoption_count=primary.adoption_count + i * 5,
            adoption_rate=min(1.0, primary.adoption_rate + i * 0.05),
            delta_vs_primary=i * 0.05,
        )
        for i in range(10)
    ]

    metadata = ResearchMetadata(
        timestamp="2026-03-29T00:00:00Z",
        duration_seconds=5.0,
        scenario_id="nutrimix_2_6",
        question_id="nutrimix_2_6_q1",
        population_size=len(population.personas),
        sample_size=5,
        alternative_count=10,
        llm_calls_made=0,
        estimated_cost_usd=0.0,
        mock_mode=True,
    )

    return ResearchResult(
        primary_funnel=primary,
        smart_sample=sample,
        interview_results=interviews,
        alternative_runs=alternatives,
        metadata=metadata,
    )
```

#### Test Cases

1. **`test_consolidation_returns_valid_report`** — `consolidate_research(result, population)` returns a `ConsolidatedReport` without errors.

2. **`test_funnel_summary_matches_primary`** — `report.funnel.adoption_count == result.primary_funnel.adoption_count` and `report.funnel.adoption_rate == result.primary_funnel.adoption_rate`.

3. **`test_segments_present`** — `report.segments_by_tier` is non-empty. Each segment has `adoption_rate` between 0 and 1.

4. **`test_clusters_from_interviews`** — `report.clusters` is non-empty (interview responses have keywords that should match clustering themes). At least one cluster mentions "price" or "trust" theme.

5. **`test_alternatives_ranked`** — `report.top_alternatives` is sorted by `delta_vs_primary` descending. `report.top_alternatives[0].rank == 1`.

6. **`test_worst_alternatives_present`** — `report.worst_alternatives` has at most 3 entries.

7. **`test_metadata_propagated`** — `report.scenario_id == "nutrimix_2_6"` and `report.mock_mode is True`.

8. **`test_question_context_populated`** — `report.question_title` is non-empty and `report.question_description` is non-empty.

9. **`test_causal_drivers_present`** — `report.causal_drivers` is a non-empty list. Each entry has `variable`, `importance`, and `direction` keys.

10. **`test_interview_count_matches`** — `report.interview_count == len(result.interview_results)`.

### Task 2: Page Smoke Tests
**Update file:** `tests/unit/test_page_imports.py`

Add these test cases to the existing file:

1. **`test_results_page_syntax`** — `ast.parse` on `app/pages/3_results.py`.

2. **`test_interviews_deepdive_page_syntax`** — `ast.parse` on `app/pages/4_interviews.py`.

3. **`test_research_consolidator_importable`** — `from src.analysis.research_consolidator import consolidate_research, ConsolidatedReport` works.

### Deliverables
1. `tests/unit/test_research_consolidator.py` — 10 test cases
2. `tests/unit/test_page_imports.py` — updated with 3 additional test cases
3. All tests pass with `pytest tests/unit/test_research_consolidator.py tests/unit/test_page_imports.py -v`

### Dependencies
- **Depends on Codex Sprint 14** delivering `src/analysis/research_consolidator.py` first
- **Depends on Cursor Sprint 14** delivering `app/pages/3_results.py` rewrite
- **Depends on OpenCode Sprint 14** delivering `app/pages/4_interviews.py`

### Do NOT
- Modify source code
- Create new source modules
- Make real LLM calls
- Skip tests with `@pytest.mark.skip`
