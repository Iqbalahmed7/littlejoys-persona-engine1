# Sprint 24 Brief — Cursor
## S4-01: Phase 0 Population Dashboard + Expanded Persona View

> **Engineer**: Cursor (Claude Sonnet)
> **Sprint**: 24
> **Ticket**: S4-01
> **Estimated effort**: Medium-Large
> **Reference**: LittleJoys User Flow Document v2.0, Sections 3.2, 3.3, 3.4

---

### Context

Phase 0 (`app/pages/1_personas.py`) is currently a basic filter panel + 2-column card grid + single narrative expander. The v2.0 spec requires it to be a full population intelligence layer — the first place a user builds intuition before stating their business problem.

Three things are missing:
1. Population distribution charts (the "data portrait" of the 200 personas)
2. Organic insight cards (auto-computed statistical observations)
3. A rich expanded persona view (12 taxonomy sections, memory layer, children cards)

---

### Task 1: Population Distribution Dashboard

**Location**: Top of `app/pages/1_personas.py`, above the filter panel.

Add a `st.subheader("Population Overview")` section with 4 Plotly charts in a 2×2 `st.columns` grid. All charts use `st.plotly_chart(fig, use_container_width=True)`. No raw field names on axes — translate everything.

**Chart 1 — Income Distribution (histogram)**
```python
import plotly.graph_objects as go

incomes = [p.demographics.household_income_lpa for p in pop.personas]
fig = go.Figure(go.Histogram(
    x=incomes,
    nbinsx=10,
    marker_color="#4ECDC4",
    opacity=0.8,
))
fig.update_layout(
    title="Household Income Distribution",
    xaxis_title="Annual Income (₹ Lakhs)",
    yaxis_title="Number of Personas",
    plot_bgcolor="#FAFAFA",
    paper_bgcolor="#FFFFFF",
)
```

**Chart 2 — City Tier Split (pie)**
```python
from collections import Counter
tier_counts = Counter(p.demographics.city_tier for p in pop.personas)
tier_labels = {"Tier1": "Metro", "Tier2": "Tier-1 City", "Tier3": "Tier-2 City", "Tier4": "Tier-3 City"}
fig = go.Figure(go.Pie(
    labels=[tier_labels.get(k, k) for k in tier_counts.keys()],
    values=list(tier_counts.values()),
    hole=0.4,
    marker_colors=["#FF6B6B", "#4ECDC4", "#45B7D1", "#95A5A6"],
))
fig.update_layout(title="City Distribution")
```

**Chart 3 — Child Age Distribution (bar)**
Pull child ages from `p.children` (each child has an `age` field). Bin into: 0–2, 3–5, 6–8, 9–12, 13+. Count children (not personas) per bin.

**Chart 4 — Health Consciousness (bar)**
Pull `p.psychographics.health_consciousness` (float 0–1). Bin into Low (0–0.4), Medium (0.4–0.7), High (0.7–1.0). Bar chart with colors: red/amber/green.

Wrap the 4-chart section in `st.expander("Population Distribution", expanded=True)` so users can collapse it when they want more screen space for the persona browser.

---

### Task 2: Organic Insight Cards

**Location**: Between the population distribution section and the filter panel.

Compute 3 statistical observations from the population. Render each using `render_system_voice()` from `app/components/system_voice.py`. These are pure Python calculations — no LLM.

```python
from app.components.system_voice import render_system_voice

# Insight 1: Tier-2/3 prevalence
tier2_3_count = sum(1 for p in pop.personas if p.demographics.city_tier in ("Tier3", "Tier4"))
tier2_3_pct = round(tier2_3_count / len(pop.personas) * 100)
render_system_voice(
    f"<strong>{tier2_3_pct}%</strong> of your population lives in Tier-2 or Tier-3 cities — "
    f"the fastest-growing consumption segment for kids' nutrition in India."
)

# Insight 2: Multi-child price sensitivity
multi_child = [p for p in pop.personas if len(p.children) >= 2]
single_child = [p for p in pop.personas if len(p.children) == 1]
if single_child:
    mc_price = sum(p.psychographics.budget_consciousness for p in multi_child) / len(multi_child)
    sc_price = sum(p.psychographics.budget_consciousness for p in single_child) / len(single_child)
    ratio = round(mc_price / sc_price, 1) if sc_price > 0 else 1.0
    render_system_voice(
        f"Personas with 2+ children show <strong>{ratio}×</strong> higher price sensitivity "
        f"than single-child households — discount triggers matter more than brand signals."
    )

# Insight 3: Health consciousness peak
import statistics
ages = [p.demographics.parent_age for p in pop.personas]
hc_scores = [p.psychographics.health_consciousness for p in pop.personas]
# Find the age band with highest mean health consciousness
age_bands = {"25–30": [], "31–35": [], "36–40": [], "40+": []}
for p in pop.personas:
    age = p.demographics.parent_age
    score = p.psychographics.health_consciousness
    if age <= 30: age_bands["25–30"].append(score)
    elif age <= 35: age_bands["31–35"].append(score)
    elif age <= 40: age_bands["36–40"].append(score)
    else: age_bands["40+"].append(score)
peak_band = max(age_bands, key=lambda b: statistics.mean(age_bands[b]) if age_bands[b] else 0)
render_system_voice(
    f"Health consciousness peaks in the <strong>{peak_band}</strong> age band — "
    f"your highest-receptivity window for nutrition messaging."
)
```

---

### Task 3: Expanded Persona View

**Location**: `render_persona_card()` function or the expander section in the persona browser loop.

The current expanded view shows the narrative + basic demographics. Add the following collapsible sections using `st.expander`:

**Children Detail Cards**
```python
if p.children:
    st.markdown("**Children**")
    child_cols = st.columns(min(len(p.children), 3))
    for ci, child in enumerate(p.children):
        with child_cols[ci % 3]:
            with st.container(border=True):
                st.markdown(f"**{child.name}**, {child.age} yrs")
                st.caption(f"Health conditions: {', '.join(child.health_conditions) or 'None'}")
                st.caption(f"Food preferences: {', '.join(child.food_preferences) or 'Not specified'}")
```

**Memory Layer** (if persona has narrative memory data)
```python
with st.expander("Memory & Anchors", expanded=False):
    if hasattr(p, 'memories') and p.memories:
        if p.memories.episodic:
            st.markdown("**Episodic Memories**")
            for mem in p.memories.episodic[:3]:
                st.caption(f"• {mem}")
        if p.memories.semantic_anchors:
            st.markdown("**Beliefs & Values**")
            for anchor in p.memories.semantic_anchors[:3]:
                st.caption(f"• {anchor}")
        if p.memories.brand_memories:
            st.markdown("**Brand Associations**")
            for brand, memory in list(p.memories.brand_memories.items())[:3]:
                st.caption(f"• {brand}: {memory}")
    else:
        st.caption("No memory layer available for this persona.")
```

**Attribute Deep-Dive** (collapsible, below narrative)
Render the 12 taxonomy categories as collapsible sections. Use `p.to_flat_dict()` to get all attributes, then group them. Import the display name translator from `src/utils/display.py` — use `display_name(field)` for every field label. Never show raw field names.

```python
with st.expander("Full Attribute Profile", expanded=False):
    flat = p.to_flat_dict()
    # Group into sections
    sections = {
        "Demographics": ["household_income_lpa", "city_tier", "education_level", "employment_status"],
        "Health & Nutrition": ["health_consciousness", "immunity_concern", "doctor_trust"],
        "Psychographics": ["budget_consciousness", "health_anxiety", "social_proof_bias"],
        # ... add remaining groups
    }
    for section_name, fields in sections.items():
        st.markdown(f"**{section_name}**")
        for field in fields:
            if field in flat:
                val = flat[field]
                label = display_name(field)  # from src/utils/display.py
                if isinstance(val, float):
                    st.caption(f"{label}: {qualitative_level(val)} ({val:.2f})")
                else:
                    st.caption(f"{label}: {val}")
```

---

### Task 4: Free-Text Narrative Search

**Location**: Filter panel in `1_personas.py`.

Add one more filter input at the bottom of the existing filter panel:

```python
narrative_search = st.text_input(
    "Search in persona stories",
    placeholder="e.g. 'working mother', 'organic food', 'Tier-2 city'",
    key="narrative_search",
)
```

Apply the filter:
```python
if narrative_search:
    search_lower = narrative_search.lower()
    filtered = [
        p for p in filtered
        if narrative_search and search_lower in (p.narrative or "").lower()
    ]
```

---

### Acceptance Criteria

- [ ] 4 distribution charts render without error for any population size
- [ ] 3 organic insight cards appear, all using `render_system_voice()` callout format
- [ ] No raw field names visible anywhere (income_lpa → "Annual Income (₹ Lakhs)")
- [ ] Children detail cards render correctly (handles personas with 0 children gracefully)
- [ ] Memory layer expander shows when data exists, shows "No memory layer" when not
- [ ] Free-text search filters persona grid in real-time
- [ ] Distribution charts section can be collapsed without breaking anything
- [ ] Import check: `python -c "from app.pages import one_personas"` passes (adjust for your import path)

---

### Files to Modify

| File | Change |
|------|--------|
| `app/pages/1_personas.py` | Add distribution charts, insight cards, expanded view sections, narrative search |

### Files NOT to Modify

Any `src/` files. Do not change persona data models or generation logic.

---

### Escalation Rule

If `p.memories` or `p.children` attributes have different names in the actual Persona model, grep `src/generation/population.py` and `src/taxonomy/schema.py` for the correct field names before coding. Do not assume field names — check first.
