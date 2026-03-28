# Antigravity — Sprint 6 Briefing

**PRD**: PRD-013 Persona Depth & UX Overhaul
**Branch**: `feat/PRD-013-persona-depth`
**Priority**: P1 — **WAVE 2** (send after Cursor completes — depends on display layer)

---

## Your Tasks: Scatter Insights + Interview Mock Cleanup

### 1. Psychographic Scatter with Insights (`app/pages/1_population.py`)

**Goal**: The scatter plot should tell a story, not just show dots.

**A. Quadrant adoption annotations:**
When simulation results exist (adopt/reject color is visible):
```python
import numpy as np

if color_col and color_col in df.columns:
    median_x = df[x_attr].median()
    median_y = df[y_attr].median()

    quadrants = {
        "High-High": df[(df[x_attr] >= median_x) & (df[y_attr] >= median_y)],
        "High-Low": df[(df[x_attr] >= median_x) & (df[y_attr] < median_y)],
        "Low-High": df[(df[x_attr] < median_x) & (df[y_attr] >= median_y)],
        "Low-Low": df[(df[x_attr] < median_x) & (df[y_attr] < median_y)],
    }

    overall_rate = (df[color_col] == "adopt").mean()

    insight_parts = []
    for quad_name, quad_df in quadrants.items():
        if len(quad_df) > 0:
            quad_rate = (quad_df[color_col] == "adopt").mean()
            ratio = quad_rate / overall_rate if overall_rate > 0 else 0
            if ratio > 1.3 or ratio < 0.7:
                insight_parts.append(
                    f"**{quad_name}** quadrant: {quad_rate:.0%} adoption ({ratio:.1f}× average)"
                )

    # Add quadrant lines to figure
    fig_s.add_hline(y=median_y, line_dash="dot", line_color="gray", opacity=0.5)
    fig_s.add_vline(x=median_x, line_dash="dot", line_color="gray", opacity=0.5)

    if insight_parts:
        st.caption(" · ".join(insight_parts))
    else:
        st.caption("No strong adoption differences across quadrants for these attributes.")
```

**B. Auto-generated insight text:**
Below the chart, show a plain-language insight:
```python
# Use display_name from Cursor's display.py
from src.utils.display import display_name

if insight_parts:
    best_quad = max(quadrants.items(), key=lambda q: (q[1][color_col] == "adopt").mean() if len(q[1]) > 0 else 0)
    st.info(
        f"Parents with high {display_name(x_attr)} and high {display_name(y_attr)} "
        f"adopt at {best_quad_rate:.0%} vs {overall_rate:.0%} overall."
    )
```

**C. Clear message when no simulation results:**
```python
if color_col is None:
    st.info("Run a simulation from the Home page to see how these attributes relate to adoption decisions.")
```

### 2. Interview Mock Response Cleanup (`src/analysis/interviews.py`)

**Goal**: Mock responses should never quote raw attribute names or decimal values.

**Find the mock response builder** (around lines 280-329) and replace all raw attribute references.

**Before** (current):
```python
f"With our income at about {persona.demographics.household_income_lpa:.1f} lakh "
f"and my budget_consciousness sitting around {persona.daily_routine.budget_consciousness:.2f}"
```

**After** (natural language):
```python
from src.utils.display import describe_attribute_value

# Map 0-1 values to natural language
income = persona.demographics.household_income_lpa
budget_desc = _natural_budget_description(persona.daily_routine.budget_consciousness)

f"With our family income, {budget_desc}"
```

**Create helper function in interviews.py:**
```python
def _natural_budget_description(budget_consciousness: float) -> str:
    if budget_consciousness >= 0.75:
        return "I'm very careful about what we spend — every rupee counts"
    if budget_consciousness >= 0.5:
        return "I keep a close eye on our budget but I'll spend when it matters"
    if budget_consciousness >= 0.25:
        return "money isn't the first thing I think about when shopping"
    return "I don't worry too much about price if the quality is right"


def _natural_health_description(health_anxiety: float) -> str:
    if health_anxiety >= 0.75:
        return "I worry a lot about whether my kids are getting proper nutrition"
    if health_anxiety >= 0.5:
        return "I try to stay on top of their health without overthinking it"
    if health_anxiety >= 0.25:
        return "I trust that a balanced diet covers most of their needs"
    return "I believe kids are naturally resilient and don't stress about it"


def _natural_trust_description(medical_authority_trust: float) -> str:
    if medical_authority_trust >= 0.75:
        return "I always check with our pediatrician before trying anything new"
    if medical_authority_trust >= 0.5:
        return "I value medical advice but also do my own research"
    if medical_authority_trust >= 0.25:
        return "I prefer to research things myself rather than just follow doctor's orders"
    return "I trust my own instincts more than medical recommendations"
```

**Apply to all 3 mock response templates** (price question, trust question, general question):
- Replace `persona.demographics.household_income_lpa:.1f` → use income bracket language ("middle-class family", "comfortable income")
- Replace `persona.daily_routine.budget_consciousness:.2f` → `_natural_budget_description()`
- Replace `persona.health.medical_authority_trust:.2f` → `_natural_trust_description()`
- Replace `persona.psychology.health_anxiety:.2f` → `_natural_health_description()`
- Replace `persona.health.health_info_sources[:2]` → "sources I trust" or "recommendations from friends"

### 3. Use persona name in interview responses

Replace generic "As a parent..." with the persona's display name:
```python
name = persona.display_name or persona.demographics.city_name + " parent"
```

Use it naturally: "For me, {name}, price was the main factor..."

---

## Critical: Write Your OWN Delivery Report
Describe the actual files you changed. Do NOT copy another engineer's report.

## Standards
- `from __future__ import annotations`
- Import `display_name` from `src.utils.display` (Cursor's delivery)
- No raw field names in any user-facing text
- No decimal attribute values in mock responses
- Keep the report concise — under 10 lines

## Run
```bash
uv run pytest tests/ -x -q
uv run ruff check app/pages/1_population.py src/analysis/interviews.py
```
