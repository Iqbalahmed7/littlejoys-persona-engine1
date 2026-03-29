# Sprint 15 Brief — Cursor (Claude)
## Page Cleanup + Home Page Update

### Context
The app currently has 12 page files in `app/pages/`, mixing deprecated Sprint ≤11 pages with the new Sprint 12-14 pages. Users see duplicate entries in the Streamlit sidebar. Sprint 15 cleans this up: delete deprecated pages, renumber the active ones, and update the home page to guide users into the new research flow.

### Task 1: Delete Deprecated Pages

Delete these files — they are fully replaced:

| Deprecated File | Replaced By |
|---|---|
| `app/pages/1_population.py` | `app/pages/1_personas.py` |
| `app/pages/2_scenario.py` | `app/pages/2_research.py` |
| `app/pages/3_results_legacy.py` | `app/pages/3_results.py` (already rewritten) |
| `app/pages/4_counterfactual.py` | Subsumed by alternatives in `3_results.py` |
| `app/pages/5_interviews.py` | `app/pages/4_interviews.py` |
| `app/pages/6_probing_tree.py` | Section B of `2_research.py` |
| `app/pages/6_report.py` | Subsumed by `3_results.py` consolidated report |
| `app/pages/7_explorer.py` | Subsumed by auto-variants in research pipeline |

After deletion, remaining pages should be:
```
app/pages/1_personas.py
app/pages/2_research.py
app/pages/3_results.py
app/pages/4_interviews.py
```

### Task 2: Update Home Page (`app/streamlit_app.py`)

Update the home page to guide users into the new flow:

1. **Title/caption** — Keep as-is ("LittleJoys Persona Simulation Engine")

2. **After population loads**, replace the current 3-metric row + scenario pre-computation with:

```python
if "population" in st.session_state:
    pop = st.session_state.population

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Personas", len(pop.personas))
    c2.metric("With Narratives", sum(1 for p in pop.personas if p.narrative))
    c3.metric("Scenarios Available", len(SCENARIO_IDS))

    st.markdown("---")
    st.subheader("Getting Started")
    st.markdown(
        "1. **Browse personas** — Explore your synthetic population\n"
        "2. **Design research** — Pick a scenario, choose a business question, run the hybrid pipeline\n"
        "3. **View results** — Quantitative findings, qualitative themes, strategic alternatives\n"
        "4. **Deep-dive interviews** — Read the smart-sampled persona conversations"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.page_link("pages/1_personas.py", label="Browse Personas →", icon="👥")
    with col2:
        st.page_link("pages/2_research.py", label="Design Research →", icon="🔬")
```

3. **Keep scenario pre-computation** — The `scenario_results` pre-computation block is still useful for backward compat (legacy dashboard fallback in `3_results.py`). Keep it but make it silent (remove the spinner/toast):

```python
if "scenario_results" not in st.session_state:
    st.session_state.scenario_results = {}
    if "population" in st.session_state:
        for sid in SCENARIO_IDS:
            st.session_state.scenario_results[sid] = run_static_simulation(
                st.session_state.population, get_scenario(sid)
            )
```

### Task 3: Fix Cross-Page Links

Verify that `st.page_link` calls in the active pages use correct paths after cleanup:
- `app/pages/2_research.py` line 423: `st.page_link("pages/3_results.py", ...)` — correct
- `app/pages/2_research.py` line 432: `st.page_link("pages/3_results.py", ...)` — correct
- `app/pages/4_interviews.py` line 26: `st.page_link("pages/2_research.py", ...)` — correct

No changes needed if paths already resolve correctly. Just verify.

### Deliverables
1. 8 deprecated page files deleted
2. `app/streamlit_app.py` updated with getting-started section + page links
3. 4 clean pages remain in `app/pages/`
4. App loads without import errors when run with `streamlit run app/streamlit_app.py`

### Do NOT
- Modify source modules in `src/`
- Modify test files (Antigravity handles that)
- Add new dependencies
