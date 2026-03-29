# Sprint 13 Brief — Antigravity (Gemini 3 Flash)
## Tests for Sprint 13 Components

### Context
Sprint 13 introduces a business-meaningful variant generator and two new Streamlit pages. Your job is to write tests for the auto-variant generator and basic smoke tests for the page modules.

### Task 1: Auto-Variant Generator Tests
**New file:** `tests/unit/test_auto_variants.py`

Test `generate_business_variants()` from `src/simulation/auto_variants.py`.

#### Test Cases

1. **`test_variant_count`** — Default call produces between 40 and 55 variants (including baseline).

2. **`test_baseline_included`** — First variant has `is_baseline=True` and empty `parameter_changes`.

3. **`test_all_categories_present`** — Variants span all 5 categories: `pricing`, `trust`, `awareness`, `product`, `combined`.

4. **`test_no_duplicate_variant_ids`** — All variant IDs are unique.

5. **`test_channel_mix_valid`** — For every variant, `sum(scenario_config.marketing.channel_mix.values())` is between 0.99 and 1.01.

6. **`test_business_rationale_non_empty`** — Every variant has a non-empty `business_rationale` string.

7. **`test_business_rationale_mentions_product`** — For pricing variants, the `business_rationale` mentions the product name from the base scenario (e.g. "Nutrimix" or "ProteinMix").

8. **`test_deterministic`** — Same base scenario + seed produces identical variant IDs. Run twice, compare.

9. **`test_max_variants_respected`** — `generate_business_variants(base, max_variants=20)` returns at most 20 variants.

10. **`test_all_scenarios`** — Run generator for each of the 4 scenarios. All produce valid VariantBatch objects without errors.

#### Setup

```python
import pytest
from src.decision.scenarios import get_scenario
from src.simulation.auto_variants import generate_business_variants

@pytest.fixture(params=["nutrimix_2_6", "nutrimix_7_14", "magnesium_gummies", "protein_mix"])
def scenario(request):
    return get_scenario(request.param)
```

### Task 2: Page Smoke Tests
**New file:** `tests/unit/test_page_imports.py`

Basic import tests to verify the new pages are syntactically valid and their key functions/modules are importable. These are NOT full Streamlit rendering tests (those need a running server).

#### Test Cases

1. **`test_research_page_importable`** — `import app.pages.2_research` does not raise ImportError. This may need to be wrapped with Streamlit mocking since pages execute on import. Use the same `_FakeStreamlit` pattern from `tests/unit/test_page_logic.py` if needed, or simply verify the file parses:
   ```python
   import ast
   def test_research_page_syntax():
       with open("app/pages/2_research.py") as f:
           ast.parse(f.read())
   ```

2. **`test_personas_page_importable`** — Same for `app/pages/1_personas.py`.

3. **`test_auto_variants_importable`** — `from src.simulation.auto_variants import generate_business_variants, BusinessVariant, VariantBatch` works.

4. **`test_question_bank_tree_resolution_all`** — For every question in `list_all_questions()`, `get_tree_for_question(q.id)` returns a valid tree with at least 1 hypothesis and 1 probe.

### Deliverables
1. `tests/unit/test_auto_variants.py` — 10 test cases
2. `tests/unit/test_page_imports.py` — 4 test cases
3. All tests pass with `pytest tests/unit/test_auto_variants.py tests/unit/test_page_imports.py -v`

### Do NOT
- Modify source code
- Create new source modules
- Make real LLM calls
- Skip tests with `@pytest.mark.skip`
