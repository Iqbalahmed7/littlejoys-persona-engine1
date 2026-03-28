# OpenCode — Sprint 5 Briefing

**PRD**: PRD-012 Hardening, QA & Demo Prep
**Branch**: `feat/PRD-012-hardening`
**Priority**: P1

---

## Your Tasks

### 1. Fix bare `assert` in calibration.py (P1 — Security)

**File**: `src/decision/calibration.py`, line 425

Current:
```python
assert best_result is not None
```

Replace with:
```python
if best_result is None:
    raise RuntimeError("Calibration failed to converge after exhausting search space")
```

This is a bandit S101 finding. Python's `-O` flag strips `assert` statements, which would turn this into a silent `None` return.

### 2. Sidebar consistency audit (P1)

Check all 6 pages in `app/pages/` for consistent sidebar patterns:

**Expected pattern for pages that need scenario selection:**
```python
with st.sidebar:
    st.subheader("[Page] Controls")
    scenario_id = st.selectbox("Scenario", options=SCENARIO_IDS, index=0)
```

**Audit checklist:**
- [ ] `1_population.py` — no scenario selector needed (OK as-is)
- [ ] `2_scenario.py` — has scenario selector
- [ ] `3_results.py` — has scenario selector
- [ ] `4_counterfactual.py` — has scenario selector
- [ ] `5_interviews.py` — has scenario selector + mock LLM toggle
- [ ] `6_report.py` — has scenario selector + mock LLM toggle

Verify that `SCENARIO_IDS` is used consistently (not hardcoded lists). Report any inconsistencies but only fix if the page is genuinely broken.

### 3. Edge case test for empty population

**File**: `tests/unit/test_edge_cases.py` (new)

```python
from src.generation.population import Population

def test_empty_population_tier1():
    """Population with no tier1 personas has zero-length list."""
    # Create minimal valid population with empty persona lists
    # Verify .tier1_personas == [] and .tier2_personas == []

def test_static_simulation_empty_population():
    """Static sim on empty population returns 0 adoption."""
    # run_static_simulation with 0 personas should return
    # adoption_rate=0.0, adoption_count=0, population_size=0

def test_funnel_waterfall_empty():
    """Waterfall on empty results dict returns empty list."""
    from src.analysis.waterfall import compute_funnel_waterfall
    assert compute_funnel_waterfall({}) == []

def test_analyze_barriers_empty():
    """Barriers on empty results returns empty list."""
    from src.analysis.barriers import analyze_barriers
    assert analyze_barriers({}) == []
```

---

## Standards
- `from __future__ import annotations`
- No magic numbers — use constants
- `structlog` for any logging
- Target: 4+ new tests

## Run
```bash
uv run pytest tests/ -x -q
uv run ruff check src/decision/calibration.py
uv run bandit src/decision/calibration.py -ll
```
