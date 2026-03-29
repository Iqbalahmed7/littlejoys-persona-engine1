# Sprint 12 Brief — OpenCode (GPT 5.4 Nano)
## Persona Spider Chart Component

### Context
We are rebuilding the persona browser to show each persona's key anchor traits visually. Instead of scrolling through text fields, users will see a radar/spider chart highlighting the 5 most distinctive traits per persona. This component will be used in the persona browser on the Personas dashboard page (Sprint 13).

### Task: Spider/Radar Chart Component
**New file:** `app/components/persona_spider.py`

Build a reusable Streamlit component that renders a Plotly radar chart for a single persona, showing their top 5 most distinctive psychographic/behavioral traits.

#### Function Signature

```python
import streamlit as st
from src.taxonomy.schema import Persona

def render_persona_spider(persona: Persona, *, key: str = "") -> None:
    """Render a compact radar chart of a persona's top 5 anchor traits.

    Args:
        persona: The persona to visualize.
        key: Streamlit widget key suffix for uniqueness.
    """
```

#### Trait Selection Logic

1. Call `persona.to_flat_dict()` to get all attributes as a flat dictionary.

2. **Filter to psychographic/behavioral attributes only.** Use the categories defined in `src/utils/display.py` → `ATTRIBUTE_CATEGORIES` dict. Include ALL attributes from these categories:
   - "Health & Nutrition"
   - "Psychology & Decisions"
   - "Values & Beliefs"
   - "Cultural & Social"
   - "Media & Digital"
   - "Lifestyle & Routine"

3. **Exclude** any attribute that is not a float between 0.0 and 1.0 (some fields may be strings or booleans).

4. **Score distinctiveness** for each attribute: `abs(value - 0.5)`. A value of 0.95 or 0.05 is very distinctive (score 0.45). A value of 0.50 is completely average (score 0.0).

5. **Select the top 5** by distinctiveness score. If tied, prefer higher absolute value.

6. **Build labels** using `display_name()` from `src/utils/display.py`.

#### Chart Rendering

Use `plotly.graph_objects.Scatterpolar` for the radar chart:

```python
import plotly.graph_objects as go

fig = go.Figure(data=go.Scatterpolar(
    r=[values...],           # The 5 trait values (0-1 scale)
    theta=[labels...],       # The 5 display names
    fill="toself",
    fillcolor="rgba(99, 102, 241, 0.15)",  # Light indigo fill
    line=dict(color="#6366f1", width=2),    # Indigo outline
    marker=dict(size=6),
))

fig.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True,
            range=[0, 1],
            tickvals=[0.25, 0.50, 0.75],
            ticktext=["Low", "Mid", "High"],
            tickfont=dict(size=10),
        ),
    ),
    showlegend=False,
    margin=dict(l=40, r=40, t=20, b=20),
    height=280,
)
```

Then render with:
```python
st.plotly_chart(fig, use_container_width=True, key=f"spider_{persona.id}_{key}")
```

#### Trait Summary Caption

Below the chart, render a single-line caption listing the 5 traits with their values:

```python
trait_summary = " · ".join(f"{label}: {value:.0%}" for label, value in top_5)
st.caption(trait_summary)
```

Example output: `Health Anxiety: 92% · Brand Loyalty: 88% · Risk Tolerance: 8% · Diet Consciousness: 85% · Authority Bias: 82%`

### Reference Files
- `src/utils/display.py` — `display_name()` function (line ~22), `ATTRIBUTE_CATEGORIES` dict (line ~120)
- `src/taxonomy/schema.py` — `Persona` class (line ~430), `to_flat_dict()` method
- `app/components/persona_card.py` — existing component pattern to follow for imports and structure
- Brand colors: `DASHBOARD_BRAND_COLORS` in `src/constants.py`

### Deliverables
1. `app/components/persona_spider.py` with `render_persona_spider()` function
2. File must be importable without errors
3. Chart must render correctly in Streamlit when called with any Persona from the population

### Do NOT
- Modify existing files
- Create new Streamlit pages
- Add new dependencies (Plotly is already installed)
- Include decision outcomes or scenario data in the chart
- Show demographic attributes (age, income, city tier) in the radar — only psychographic/behavioral
