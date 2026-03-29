# Sprint 13 Brief — OpenCode (GPT 5.4 Nano → recommend Pro)
## Home + Personas Compact Dashboard

### Context
The current population page is a long scroll with scattered insights, scatter plots, and a persona browser mixed together. Sprint 13 transforms it into a compact, dashboard-style Personas page. Psychographic scatter plots move to the Results page (Sprint 14). This page becomes purely about **"who are these people?"** — no simulation data, no decision outcomes.

**Note to operator:** Recommend upgrading OpenCode to GPT 5.4 Pro for this sprint — it's a complex layout refactor.

### Task: Rewrite `app/pages/1_population.py` → `app/pages/1_personas.py`
**New file.** Keep the old `1_population.py` untouched for now (Sprint 15 cleanup).

### Page Layout

#### Top Panel — Metrics (3 columns)

```python
import streamlit as st
from src.constants import SCENARIO_IDS, DASHBOARD_DEFAULT_POPULATION_PATH
from src.generation.population import Population

st.header("Personas")
st.caption("Browse your synthetic population. Use filters to explore segments.")

if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()

pop = st.session_state.population

m1, m2, m3 = st.columns(3)
m1.metric("Personas", len(pop.personas))
m2.metric("With Narratives", sum(1 for p in pop.personas if p.narrative))
m3.metric("Scenarios Available", len(SCENARIO_IDS))
```

#### Static Section — Demographics Overview (no filters)

A 2×2 grid of small bar charts showing the full population breakdown. Use `plotly.express` bar charts.

```python
import plotly.express as px
from src.utils.display import display_name

st.subheader("Population Overview")
```

Build a DataFrame from the population:
```python
df = pop.to_dataframe()
```

**Chart 1 — City Tier** (top-left):
```python
c1, c2 = st.columns(2)
with c1:
    tier_counts = df["city_tier"].value_counts().reset_index()
    tier_counts.columns = ["City Tier", "Count"]
    fig = px.bar(tier_counts, x="City Tier", y="Count", title="City Tier Distribution")
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)
```

**Chart 2 — Income Brackets** (top-right):
```python
with c2:
    # Bin household_income_lpa into brackets
    import pandas as pd
    bins = [0, 5, 10, 20, 50, 100]
    labels = ["<5L", "5-10L", "10-20L", "20-50L", "50L+"]
    df["income_bracket"] = pd.cut(df["household_income_lpa"], bins=bins, labels=labels, right=False)
    income_counts = df["income_bracket"].value_counts().sort_index().reset_index()
    income_counts.columns = ["Income Bracket", "Count"]
    fig = px.bar(income_counts, x="Income Bracket", y="Count", title="Income Distribution")
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)
```

**Chart 3 — Family Structure** (bottom-left):
```python
c3, c4 = st.columns(2)
with c3:
    fam_counts = df["family_structure"].map(display_name).value_counts().reset_index()
    fam_counts.columns = ["Family Structure", "Count"]
    fig = px.bar(fam_counts, x="Family Structure", y="Count", title="Family Structure")
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)
```

**Chart 4 — Child Age Groups** (bottom-right):
```python
with c4:
    def age_group(age):
        if pd.isna(age): return "Unknown"
        age = float(age)
        if age <= 5: return "Toddler (2-5)"
        if age <= 10: return "School-age (6-10)"
        return "Pre-teen (11-14)"

    df["age_group"] = df["youngest_child_age"].apply(age_group)
    age_counts = df["age_group"].value_counts().reset_index()
    age_counts.columns = ["Age Group", "Count"]
    fig = px.bar(age_counts, x="Age Group", y="Count", title="Youngest Child Age")
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)
```

#### Dynamic Section — Filtered Charts

```python
st.subheader("Explore Segments")
st.caption("Select filters to drill down. Empty = show all.")
```

**Common filter bar** (4 multiselects in a row):
```python
f1, f2, f3, f4 = st.columns(4)
with f1:
    sel_tier = st.multiselect("City Tier", sorted(df["city_tier"].dropna().unique()), default=[], placeholder="All tiers")
with f2:
    sel_sec = st.multiselect("SEC", sorted(df["socioeconomic_class"].dropna().unique()), default=[], placeholder="All SEC")
with f3:
    sel_diet = st.multiselect("Diet", sorted(df["dietary_preference"].dropna().unique()), default=[], placeholder="All diets")
with f4:
    sel_religion = st.multiselect("Religion", sorted(df["religion"].dropna().unique()), default=[], placeholder="All")

# Apply filters
filtered = df.copy()
if sel_tier: filtered = filtered[filtered["city_tier"].isin(sel_tier)]
if sel_sec: filtered = filtered[filtered["socioeconomic_class"].isin(sel_sec)]
if sel_diet: filtered = filtered[filtered["dietary_preference"].isin(sel_diet)]
if sel_religion: filtered = filtered[filtered["religion"].isin(sel_religion)]

st.caption(f"Showing {len(filtered)} of {len(df)} personas")
```

**Filtered charts** (2 columns): repeat the same 4 chart types but using `filtered` DataFrame. Only show this section if filters are active (at least one filter has a selection). If no filters active, show a caption: "Apply filters above to see segmented views."

#### Persona Browser (bottom section)

```python
st.subheader("Persona Browser")
```

**Persona selector** (searchable dropdown):
```python
from src.utils.display import persona_display_name

persona_ids = [p.id for p in pop.personas]
persona_labels = {p.id: f"{persona_display_name(p)} · {p.id}" for p in pop.personas}

# Filter persona list if filters are active
if sel_tier or sel_sec or sel_diet or sel_religion:
    filtered_ids = set(filtered["id"].tolist())
    persona_ids = [pid for pid in persona_ids if pid in filtered_ids]

selected_id = st.selectbox(
    "Select persona",
    options=persona_ids,
    format_func=lambda pid: persona_labels.get(pid, pid),
    placeholder="Choose a persona...",
    index=None,
)
```

**Persona detail** (when selected):
```python
if selected_id:
    persona = pop.get_persona(selected_id)
    from app.components.persona_card import render_persona_card
    from app.components.persona_spider import render_persona_spider

    col_card, col_spider = st.columns([3, 2])
    with col_card:
        render_persona_card(persona)  # No decision_result — just persona details
    with col_spider:
        render_persona_spider(persona, key="browser")

    if persona.narrative:
        with st.expander("Full Narrative", expanded=False):
            st.markdown(persona.narrative)
```

### Reference Files
- `app/pages/1_population.py` — current implementation (reference for what exists, not for copying wholesale)
- `app/components/persona_card.py` — `render_persona_card(persona)` (no decision_result param)
- `app/components/persona_spider.py` — `render_persona_spider(persona, key=...)` (Sprint 12)
- `src/utils/display.py` — `display_name()`, `persona_display_name()`
- `src/generation/population.py` — `Population.personas`, `Population.to_dataframe()`, `Population.get_persona()`

### Deliverables
1. `app/pages/1_personas.py` — complete Personas dashboard page
2. Must render without errors when navigated to in Streamlit
3. Static charts show full population, dynamic charts respond to filters, persona browser shows card + spider chart

### Do NOT
- Delete or modify `app/pages/1_population.py` (Sprint 15 cleanup)
- Include any simulation/decision data (no outcomes, no scatter plots, no quadrant analysis)
- Include scenario selectors on this page — that's the Research Design page's job
- Modify existing source modules
- Add new dependencies
