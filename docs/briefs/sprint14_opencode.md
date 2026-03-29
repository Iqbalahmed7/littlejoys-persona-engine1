# Sprint 14 Brief — OpenCode (GPT 5.4 Nano → recommend Pro)
## Interview Deep-Dive Page Upgrade

### Context
The current `5_interviews.py` is a single-persona conversation UI. Sprint 14 upgrades it to show a **research interview summary** when a research result exists — the smart sample overview, per-persona interview cards, and the ability to drill into individual conversations. This is the qualitative companion to the Results page.

### Task: Rewrite `app/pages/5_interviews.py` → `app/pages/4_interviews.py`
**New file** alongside the old one. Keep `5_interviews.py` untouched (Sprint 15 cleanup).

### Page Layout

#### Guard

```python
st.header("Interview Deep-Dive")
st.caption("Explore the qualitative evidence from deep persona interviews.")

if "research_result" not in st.session_state:
    st.warning("No research results available. Run a research pipeline from the Research Design page.")
    st.page_link("pages/2_research.py", label="Go to Research Design →")
    st.stop()

result = st.session_state["research_result"]
pop = st.session_state.population
```

#### Section A — Smart Sample Overview

```python
st.subheader("Smart Sample")
st.caption(f"{len(result.smart_sample.selections)} personas selected for deep interviews.")
```

Show selection breakdown by reason:
```python
from collections import Counter
reason_counts = Counter(s.selection_reason for s in result.smart_sample.selections)
reason_cols = st.columns(len(reason_counts))
for i, (reason, count) in enumerate(reason_counts.most_common()):
    label = reason.replace("_", " ").title()
    reason_cols[i].metric(label, count)
```

#### Section B — Interview Cards

For each interviewed persona, show a card with their profile and responses:

```python
st.subheader("Interview Responses")

from src.utils.display import persona_display_name

for ir in result.interview_results:
    persona = pop.get_persona(ir.persona_id)
    decision = result.primary_funnel.results_by_persona.get(ir.persona_id, {})
    outcome = decision.get("outcome", "unknown")
    outcome_label = "Would try" if outcome == "adopt" else "Wouldn't try"

    with st.expander(
        f"{persona_display_name(persona)} · {outcome_label} · Reason: {ir.selection_reason.replace('_', ' ')}",
        expanded=False,
    ):
        # Persona summary row
        p1, p2, p3 = st.columns(3)
        p1.caption(f"City: {persona.demographics.city_tier}")
        p2.caption(f"Income: ₹{persona.demographics.household_income_lpa:.1f}L")
        p3.caption(f"Child age: {persona.demographics.youngest_child_age}")

        # Interview Q&A
        for qa in ir.responses:
            st.markdown(f"**Q:** {qa['question']}")
            st.markdown(f"**A:** {qa['answer']}")
            st.divider()
```

#### Section C — Theme Summary (from clustering)

```python
st.subheader("Response Themes")
st.caption("Keyword-based clustering of all interview responses.")

from src.probing.clustering import cluster_responses_mock

# Build response pairs
responses = []
for ir in result.interview_results:
    persona = pop.get_persona(ir.persona_id)
    combined_text = " ".join(r["answer"] for r in ir.responses)
    responses.append((persona, combined_text))

clusters = cluster_responses_mock(responses)

if clusters:
    for cluster in clusters:
        theme_label = cluster.theme.replace("_", " ").title()
        st.markdown(f"**{theme_label}** — {cluster.persona_count} personas ({cluster.percentage:.0%})")
        st.caption(cluster.description)
        if cluster.representative_quotes:
            for quote in cluster.representative_quotes[:2]:
                st.markdown(f"> {quote[:250]}")
        st.divider()
else:
    st.caption("Not enough interview data for clustering.")
```

#### Section D — Spider Chart Comparison (optional, if 2+ personas selected)

At the bottom, add a comparison tool:

```python
st.subheader("Compare Personas")
st.caption("Select 2 personas to compare their psychographic profiles side-by-side.")

interviewed_ids = [ir.persona_id for ir in result.interview_results]
interviewed_labels = {pid: persona_display_name(pop.get_persona(pid)) for pid in interviewed_ids}

compare_cols = st.columns(2)
with compare_cols[0]:
    left_id = st.selectbox("Persona A", interviewed_ids, format_func=lambda x: interviewed_labels[x], index=0, key="compare_left")
with compare_cols[1]:
    right_id = st.selectbox("Persona B", interviewed_ids, format_func=lambda x: interviewed_labels[x], index=min(1, len(interviewed_ids)-1), key="compare_right")

if left_id and right_id:
    from app.components.persona_spider import render_persona_spider
    spider_cols = st.columns(2)
    with spider_cols[0]:
        render_persona_spider(pop.get_persona(left_id), key="compare_a")
    with spider_cols[1]:
        render_persona_spider(pop.get_persona(right_id), key="compare_b")
```

### Reference Files
- `app/pages/5_interviews.py` — current implementation (reference, don't copy wholesale)
- `src/simulation/research_runner.py` — `ResearchResult`, `InterviewResult`, `SmartSample`
- `src/probing/clustering.py` — `cluster_responses_mock()`
- `app/components/persona_spider.py` — `render_persona_spider(persona, key=...)`
- `src/utils/display.py` — `persona_display_name()`

### Deliverables
1. `app/pages/4_interviews.py` — Interview Deep-Dive page with 4 sections
2. Must render without errors when `research_result` is in session state
3. Smart sample breakdown, per-persona cards, theme clustering, spider comparison all working

### Do NOT
- Delete or modify `app/pages/5_interviews.py` (Sprint 15 cleanup)
- Modify source modules
- Add new dependencies
- Make real LLM calls (page is read-only — it renders existing interview results)
