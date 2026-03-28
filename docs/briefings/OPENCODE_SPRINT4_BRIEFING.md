# OpenCode — Sprint 4 Briefing

> **Sprint**: 4 (Days 7-8)
> **Branch**: `feat/PRD-011-dashboard-constants` from `staging`
> **PRD**: PRD-011 (Streamlit Dashboard)

---

## Your Assignments

### Task 1: Dashboard Constants (P0)

**File**: `src/constants.py` — add dashboard constants

```python
# Dashboard
DASHBOARD_PAGE_TITLE = "LittleJoys Persona Engine"
DASHBOARD_BRAND_COLORS = {
    "primary": "#FF6B6B",
    "secondary": "#4ECDC4",
    "accent": "#45B7D1",
    "adopt": "#2ECC71",
    "reject": "#E74C3C",
    "neutral": "#95A5A6",
}
DASHBOARD_DEFAULT_POPULATION_PATH = "data/population"
DASHBOARD_DEFAULT_RESULTS_PATH = "data/results"
DASHBOARD_CHART_HEIGHT = 500
DASHBOARD_HEATMAP_COLORSCALE = "RdYlGn"
DASHBOARD_SCATTER_MARKER_SIZE = 6
DASHBOARD_MAX_TIER2_DISPLAY = 30
```

### Task 2: Component Init Files (P0)

Create `app/components/__init__.py` and `app/pages/__init__.py` (empty init files to make them proper Python packages).

### Task 3: Data Directory Setup Script (P1)

**File**: `scripts/setup_data_dirs.py`

Simple script that creates the required data directories:
```python
from pathlib import Path

DIRS = [
    "data/population",
    "data/results",
    "data/results/reports",
    "data/scraped",
    "data/distributions",
]

def setup() -> None:
    for d in DIRS:
        Path(d).mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    setup()
```

### Task 4: Extend Viz Tests (P1)

**File**: `tests/unit/test_viz.py`

After Cursor delivers the viz helpers, add edge case tests:
```python
test_funnel_chart_single_stage()
test_segment_heatmap_single_segment()
test_barrier_chart_single_barrier()
test_importance_bar_single_variable()
```

If viz.py isn't ready yet, write the tests with expected imports and mark as `@pytest.mark.skip(reason="awaiting viz implementation")`.

---

## Standards

- Run before submitting:
  ```
  uv run ruff check src/constants.py scripts/
  uv run pytest tests/unit/ -q
  ```

---

## Sprint 3 Feedback

Your assigned tests overlapped with Cursor's proactive delivery, so no new code was contributed. Sprint 4 gives you concrete deliverables that won't overlap — constants and setup scripts are yours alone. Deliver these cleanly and you'll get a page assignment in Sprint 5.
