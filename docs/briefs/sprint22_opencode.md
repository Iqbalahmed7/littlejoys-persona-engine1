# Sprint 22 Brief — OpenCode
## S1-Cleanup: Navigation Cleanup & Page Archiving

> **Engineer**: OpenCode (GPT 5.4 Nano → escalate to GPT 5.4 if any import resolution issues arise)
> **Sprint**: 22
> **Ticket**: S1-Cleanup
> **Estimated effort**: Low (deterministic wiring task, no logic changes)

---

### Context

The new 5-phase UX is now live across three pages:
- `app/pages/2_problem.py` — Phase 1 (Problem & Simulation)
- `app/pages/3_decompose.py` — Phase 2 (Decomposition & Probing)

But two **old pages** still exist in the sidebar and home page links:
- `app/pages/2_research.py` — old research design page (replaced by `2_problem.py`)
- `app/pages/2_diagnose.py` — old diagnose page (replaced by `3_decompose.py`)

These must be archived (prefixed with `_`) so Streamlit stops auto-detecting them as pages, and all navigation wiring updated to point to the new pages.

---

### Task 1: Archive old pages

Rename the following files (prefix with underscore = Streamlit ignores them):

```
app/pages/2_research.py   →   app/pages/_archive_2_research.py
app/pages/2_diagnose.py   →   app/pages/_archive_2_diagnose.py
```

Use `git mv` so the rename is tracked:
```bash
git mv "app/pages/2_research.py" "app/pages/_archive_2_research.py"
git mv "app/pages/2_diagnose.py" "app/pages/_archive_2_diagnose.py"
```

---

### Task 2: Update `app/streamlit_app.py` sidebar captions

The home page currently shows old captions. Replace the entire sidebar caption block:

**Current (lines 35–41):**
```python
st.sidebar.caption("1️⃣ Personas — Explore synthetic households")
st.sidebar.caption("2️⃣ Research — Run scenario research")
st.sidebar.caption("3️⃣ Results — View research results")
st.sidebar.caption("4️⃣ Diagnose — Phase A problem decomposition")
st.sidebar.caption("5️⃣ Simulate — Phase C intervention testing")
st.sidebar.caption("6️⃣ Interviews — Deep dive conversations")
st.sidebar.caption("7️⃣ Comparison — Compare two scenarios")
```

**Replace with:**
```python
st.sidebar.caption("1️⃣ Personas — Explore synthetic households")
st.sidebar.caption("2️⃣ Problem — Select a business problem & run simulation")
st.sidebar.caption("3️⃣ Decompose — Review hypotheses & run investigation")
st.sidebar.caption("4️⃣ Finding — Core insight synthesis")
st.sidebar.caption("5️⃣ Interventions — Test and compare solutions")
st.sidebar.caption("6️⃣ Interviews — Deep dive persona conversations")
st.sidebar.caption("7️⃣ Comparison — Compare two scenarios")
```

---

### Task 3: Update home page quick-link buttons

In `app/streamlit_app.py`, the bottom quick-link section (around lines 100–107) currently links to `pages/2_research.py` and `pages/2_diagnose.py`. Update to:

```python
col1, col2, col3 = st.columns(3)
with col1:
    st.page_link("pages/1_personas.py", label="Browse Personas →", icon="👥")
with col2:
    st.page_link("pages/2_problem.py", label="Define Problem →", icon="🎯")
with col3:
    st.page_link("pages/3_decompose.py", label="Investigate →", icon="🔬")
```

---

### Task 4: Verify Getting Started text is consistent

In `app/streamlit_app.py` around lines 91–98, update the markdown to match the new flow:

```python
st.markdown(
    "1. **Browse personas** — Explore your synthetic population\n"
    "2. **Define your problem** — Pick a business question; the engine runs a 12-month simulation\n"
    "3. **Investigate** — Review hypotheses, run the probing tree, see evidence accumulate\n"
    "4. **Core Finding** — One synthesised insight with evidence chain\n"
    "5. **Interventions** — Compare solutions on effort, cost, and projected lift\n"
    "6. **Deep-dive interviews** — Read smart-sampled persona conversations"
)
```

---

### Acceptance Criteria

- [ ] `app/pages/2_research.py` and `app/pages/2_diagnose.py` no longer appear in Streamlit sidebar (renamed with `_` prefix)
- [ ] Sidebar captions in `streamlit_app.py` match the 5-phase flow
- [ ] Home page quick-link buttons point to `2_problem.py` and `3_decompose.py`
- [ ] Getting Started text is consistent with Phase naming
- [ ] Import check: `python -c "import app.streamlit_app"` passes without errors
- [ ] No logic or backend code changed — purely navigation wiring

---

### Files to Modify

| File | Change |
|------|--------|
| `app/pages/2_research.py` | Rename to `_archive_2_research.py` |
| `app/pages/2_diagnose.py` | Rename to `_archive_2_diagnose.py` |
| `app/streamlit_app.py` | Update sidebar captions + quick-links + Getting Started text |

### Files NOT to modify

Any `src/` files, any `app/pages/1_personas.py`, `2_problem.py`, `3_decompose.py` — leave these untouched.
