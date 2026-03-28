# Codex — Sprint 5 Briefing

**PRD**: PRD-012 Hardening, QA & Demo Prep
**Branch**: `feat/PRD-012-hardening`
**Priority**: P0

---

## Your Tasks

### 1. End-to-end precompute integration test
**File**: `tests/integration/test_precompute_e2e.py` (new)

Test `precompute_results()` from `scripts/precompute_results.py`:
- Call with `size=20`, `deep_persona_count=2`, `mock_llm=True`, `seed=42`
- Use a temporary directory for both `population_path` and `output_dir`
- Assert manifest contains keys: `generated_at`, `seed`, `scenarios`, `scenario_ids`
- Assert each scenario in manifest has `simulation_file`, `decision_rows_file`, `adoption_rate`
- Assert `counterfactuals_file` exists when `include_counterfactuals=True`
- Assert report files exist when `include_reports=True`
- Assert all referenced files actually exist on disk
- Test with `include_counterfactuals=False` and `include_reports=False` to verify those are skipped

### 2. Page logic unit tests
**File**: `tests/unit/test_page_logic.py` (new)

Extract and test pure-logic functions used by Streamlit pages:

```python
# From 3_results.py — _coerce_static
def test_coerce_static_from_model():
    """StaticSimulationResult passes through."""

def test_coerce_static_from_dict():
    """Dict with results_by_persona is validated into model."""

def test_coerce_static_none():
    """None/invalid inputs return None."""

# From 5_interviews.py — _coerce_turns
def test_coerce_turns_empty():
    """Empty list returns empty."""

def test_coerce_turns_mixed():
    """Valid InterviewTurn objects and dicts are coerced; invalid items skipped."""

# From 6_report.py — precomputed loading
def test_load_precomputed_decision_rows(tmp_path):
    """JSON file loads correctly."""

def test_load_precomputed_missing():
    """Missing file returns None."""
```

Import the functions directly from the page modules. If imports fail due to Streamlit, use `unittest.mock.patch` to mock `streamlit` at import time.

### 3. Cross-scenario regression test
**File**: `tests/integration/test_scenario_regression.py` (new)

```python
from src.constants import SCENARIO_IDS, DEFAULT_SEED
from src.decision.scenarios import get_scenario
from src.generation.population import PopulationGenerator
from src.simulation.static import run_static_simulation

def test_all_scenarios_produce_valid_rates():
    pop = PopulationGenerator().generate(size=30, seed=DEFAULT_SEED)
    for sid in SCENARIO_IDS:
        result = run_static_simulation(pop, get_scenario(sid), seed=DEFAULT_SEED)
        assert 0.0 <= result.adoption_rate <= 1.0
        assert result.population_size == 30
        assert result.adoption_count <= result.population_size
```

---

## Standards
- `from __future__ import annotations` on every file
- `structlog` if any logging needed (unlikely in tests)
- Constants from `src.constants` — no magic numbers
- `ConfigDict(extra="forbid")` on any new Pydantic models
- Use `tmp_path` fixture for any file I/O in tests
- Target: 10+ new tests, all passing

## Run
```bash
uv run pytest tests/ -x -q
uv run ruff check tests/
```
