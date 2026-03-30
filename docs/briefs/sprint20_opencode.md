# Sprint 20 Brief — OpenCode
## Scenario Comparison UI + UI Polish

### Context

Codex is building a `compare_scenarios()` backend in Sprint 20. Your job is the UI for it, plus general polish across the results page. Wait for Codex to deliver before starting the comparison UI.

### Task 1: Scenario Comparison UI

Add a new section to `app/pages/3_results.py` OR create `app/pages/5_comparison.py` (new page).

**Recommended: New page `app/pages/5_comparison.py`**

```python
import streamlit as st
from src.decision.scenarios import get_all_scenarios, get_scenario
from src.analysis.scenario_comparison import compare_scenarios

st.set_page_config(page_title="Scenario Comparison", layout="wide")
st.title("Scenario Comparison")
st.caption("Compare two business scenarios side by side.")

scenarios = get_all_scenarios()
scenario_names = {s.id: s.name for s in scenarios}

col1, col2 = st.columns(2)
with col1:
    a_id = st.selectbox("Scenario A", list(scenario_names.keys()),
                         format_func=lambda x: scenario_names[x])
with col2:
    b_id = st.selectbox("Scenario B", list(scenario_names.keys()),
                         format_func=lambda x: scenario_names[x], index=1)
```

When user clicks "Compare":
1. Run `compare_scenarios(population, scenario_a, scenario_b)`
2. Display delta table:

```
| Metric              | Scenario A | Scenario B | Delta    |
|---------------------|-----------|-----------|----------|
| Adoption Rate       | 18.5%     | 12.3%     | +6.2pp   |
| Active Rate (M12)   | 15.2%     | 8.1%      | +7.1pp   |
| Est. Revenue (₹)    | 1.2L      | 0.8L      | +₹40,000 |
```

3. If both have event simulation results, overlay retention curves:
   - Two lines on same chart (different colours: blue for A, orange for B)
   - Use `_CHART_MARGINS` and `_CHART_HEIGHT` from the results page

4. Barrier comparison table:
   - Columns: Stage | Barrier | Count A | Count B | Delta
   - Highlight rows where delta > 5

### Task 2: UI Polish on Results Page

Apply these changes to `app/pages/3_results.py`:

1. **Human-readable metric labels:** Replace any remaining snake_case labels visible to users:
   - `price_salience` → "Price Sensitivity"
   - `brand_salience` → "Brand Awareness"
   - `child_acceptance` → "Child Acceptance"
   - `habit_strength` → "Usage Habit"
   - `effort_friction` → "Effort / Friction"
   - `perceived_value` → "Perceived Value"
   - `reorder_urgency` → "Reorder Urgency"
   - `discretionary_budget` → "Budget Headroom"

   Create a mapping dict at the top of the file:
   ```python
   _HUMAN_LABELS = {
       "price_salience": "Price Sensitivity",
       "brand_salience": "Brand Awareness",
       "child_acceptance": "Child Acceptance",
       "habit_strength": "Usage Habit",
       "effort_friction": "Effort / Friction",
       "perceived_value": "Perceived Value",
       "reorder_urgency": "Reorder Urgency",
       "discretionary_budget": "Budget Headroom",
       "trust": "Trust",
       "fatigue": "Fatigue",
   }

   def _label(key: str) -> str:
       return _HUMAN_LABELS.get(key, key.replace("_", " ").title())
   ```

   Apply `_label()` wherever variable names are displayed to users (chart axes, metric labels, driver names, rationale keys).

2. **Chart title cleanup:** Ensure all chart titles use sentence case, not Title Case or UPPER_CASE.

3. **Tooltips on jargon metrics:** Add `help=` parameter to any `st.metric()` that uses domain terms:
   ```python
   col.metric("Final Active %", f"{rate:.1f}%",
              help="Percentage of the population still actively using the product at month 12")
   ```

### Files to Create
- `app/pages/5_comparison.py` (new)

### Files to Modify
- `app/pages/3_results.py` (polish only)

### Constraints
- UI-only changes — do NOT modify any backend `src/` files
- The comparison page needs access to `st.session_state.population` (same as results page)
- All existing tests must pass
- Run `uv run ruff check .` before delivery
