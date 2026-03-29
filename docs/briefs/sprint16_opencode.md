# Sprint 16 Brief — OpenCode (GPT 5.4 Nano)
## Research Design Page Cleanup + Simulation Mode Indicators

### Context
The Research Design page has decorative hypothesis toggles that do nothing and doesn't communicate whether the scenario uses temporal or static simulation. Clean this up and add mode indicators.

### Task 1: Remove Hypothesis Toggle Checkboxes (`app/pages/2_research.py`)

Replace the checkbox section with a clean read-only display:
```python
st.subheader("Research Hypotheses")
st.caption("These hypotheses will be explored in the research pipeline.")
for h in question.hypotheses:
    st.markdown(f"- **{display_name(h.id)}**: {h.description}")
```
Delete any code that creates `st.checkbox` for hypotheses.

### Task 2: Add Simulation Mode Indicator (`app/pages/2_research.py`)

After the scenario selector, show an `st.info()` badge:
- If `scenario.mode == "temporal"`:
  ```python
  st.info("📊 Temporal mode — This scenario simulates 12 months of repeat purchase, churn, and word-of-mouth dynamics.")
  ```
- If `scenario.mode == "static"`:
  ```python
  st.info("📊 Static mode — This scenario evaluates a single purchase decision funnel.")
  ```

### Task 3: Add Mock Mode Banner (`app/pages/2_research.py`)

At the top of the page, if `not has_api_key()`:
```python
st.info("🧪 Running in mock mode — Insights reflect model structure. Add an API key for LLM-powered qualitative depth.")
```
Import `has_api_key` from `src.utils.api_keys`.

### Task 4: Simplify Run Button Label (`app/pages/2_research.py`)

Change the run button label based on scenario mode:
- Temporal: "Run 12-Month Simulation"
- Static: "Run Scenario Analysis"

### Files to Modify
- `app/pages/2_research.py`

### Constraints
- UI-only changes — do not modify any backend logic
- All existing tests must pass (`uv run pytest tests/ -x -q`)
- Run `uv run ruff check .` before delivery
