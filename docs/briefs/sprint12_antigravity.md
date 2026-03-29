# Sprint 12 Brief — Antigravity (Gemini 3 Flash)
## Tests for Sprint 12 Components

### Context
Sprint 12 introduces three new modules: smart sampling, business question bank, and research runner. Your job is to write comprehensive unit tests for all three. Tests must work with the existing test infrastructure (pytest, no external dependencies beyond what's in pyproject.toml).

### Important: Test Pattern
All tests must use **mock mode** — no real LLM calls. The codebase uses `Config(llm_mock_enabled=True)` to enable mock mode. Some tests may need to monkeypatch environment variables. Follow patterns in existing tests at `tests/unit/`.

### Task 1: Smart Sampling Tests
**New file:** `tests/unit/test_smart_sample.py`

Test the `select_smart_sample()` function from `src/probing/smart_sample.py`.

You will need to create test fixtures — a small population with known funnel results. Use the existing population generator in mock mode or build minimal Persona objects.

**Fixture approach:** Load the real population and run the funnel to get decisions:
```python
from src.generation.population import Population
from src.simulation.static import run_static_simulation
from src.decision.scenarios import get_scenario

@pytest.fixture
def population_with_decisions():
    pop = Population.load("data/population")
    scenario = get_scenario("nutrimix_2_6")
    result = run_static_simulation(pop, scenario)
    return pop, result.results_by_persona
```

#### Test Cases

1. **`test_determinism`** — Same inputs + seed produce identical SmartSample output. Run twice, assert `sample1.persona_ids == sample2.persona_ids`.

2. **`test_sample_size`** — Output has exactly `target_size` personas (default 18), or fewer if population is smaller.

3. **`test_all_buckets_represented`** — The sample contains at least 1 persona from each of the 5 selection reasons: `fragile_yes`, `persuadable_no`, `underrepresented`, `high_need_rejecter`, `control`.

4. **`test_no_duplicates`** — No persona_id appears twice in the sample.

5. **`test_small_population`** — Population of 10 personas (smaller than target_size). Should return all 10 without error.

6. **`test_all_adopt`** — Edge case: mock a decisions dict where every persona adopted. Should still produce a valid sample (no persuadable_no or high_need_rejecters, redistributed to control).

7. **`test_all_reject`** — Edge case: every persona rejected. Should still produce a valid sample (no fragile_yes, redistributed to control).

8. **`test_reason_detail_populated`** — Every SampledPersona in the output has a non-empty `reason_detail` string.

### Task 2: Business Question Bank Tests
**New file:** `tests/unit/test_question_bank.py`

Test the question bank from `src/probing/question_bank.py`.

#### Test Cases

1. **`test_every_scenario_has_questions`** — Each of the 4 scenario IDs (`nutrimix_2_6`, `nutrimix_7_14`, `magnesium_gummies`, `protein_mix`) has at least 3 questions.

2. **`test_no_duplicate_question_ids`** — All question IDs across all scenarios are unique.

3. **`test_question_fields_populated`** — Every BusinessQuestion has non-empty `title`, `description`, `success_metric`.

4. **`test_probing_tree_mapping`** — For questions with a `probing_tree_id`, verify the tree exists by calling `get_problem_tree(tree_id)` from `src/probing/predefined_trees.py`. It should not raise KeyError.

5. **`test_get_question_by_id`** — `get_question("some_valid_id")` returns the correct BusinessQuestion. `get_question("nonexistent")` raises KeyError.

6. **`test_get_questions_for_scenario`** — Returns only questions matching the given scenario_id.

7. **`test_scenario_id_valid`** — Every question's `scenario_id` is one of the 4 valid scenario IDs from `src.constants.SCENARIO_IDS`.

### Task 3: Research Runner Tests
**New file:** `tests/unit/test_research_runner.py`

Test the ResearchRunner from `src/simulation/research_runner.py`. All tests must use **mock mode**.

#### Test Cases

1. **`test_full_mock_run`** — Create a ResearchRunner with mock_mode=True, run it, assert it returns a valid ResearchResult with:
   - `primary_funnel` is a StaticSimulationResult with adoption_count > 0
   - `smart_sample` has selections
   - `interview_results` is a non-empty list
   - `alternative_runs` is a non-empty list
   - `metadata.mock_mode` is True

2. **`test_progress_callback_invoked`** — Pass a mock callback, assert it's called multiple times with increasing progress values (0.0 < p1 < p2 < ... <= 1.0).

3. **`test_alternative_count`** — Request 10 alternatives, assert `len(result.alternative_runs) == 10` (or close — some variants may be deduplicated).

4. **`test_interview_results_match_sample`** — Every persona_id in interview_results is also in smart_sample.persona_ids.

5. **`test_metadata_populated`** — All metadata fields are populated with reasonable values (duration > 0, population_size == 200, etc).

6. **`test_alternatives_sorted_by_delta`** — `alternative_runs` are sorted by `delta_vs_primary` descending (best first).

#### Setup for Research Runner Tests

```python
from src.generation.population import Population
from src.decision.scenarios import get_scenario
from src.probing.question_bank import get_questions_for_scenario
from src.simulation.research_runner import ResearchRunner
from src.utils.llm import LLMClient
from src.config import Config

@pytest.fixture
def mock_runner():
    pop = Population.load("data/population")
    scenario = get_scenario("nutrimix_2_6")
    questions = get_questions_for_scenario("nutrimix_2_6")
    llm = LLMClient(Config(llm_mock_enabled=True, llm_cache_enabled=False, anthropic_api_key=""))
    return ResearchRunner(
        population=pop,
        scenario=scenario,
        question=questions[0],
        llm_client=llm,
        mock_mode=True,
        alternative_count=10,
        sample_size=18,
    )
```

### Deliverables
1. `tests/unit/test_smart_sample.py` — 8 test cases
2. `tests/unit/test_question_bank.py` — 7 test cases
3. `tests/unit/test_research_runner.py` — 6 test cases
4. All tests must pass with `pytest tests/unit/test_smart_sample.py tests/unit/test_question_bank.py tests/unit/test_research_runner.py -v`

### Do NOT
- Make real LLM API calls
- Modify source code (tests only)
- Create new source modules
- Skip tests with `@pytest.mark.skip` — all tests must run
