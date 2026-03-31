# Sprint 25 — Cursor (S5-01)
**Engineer:** Cursor (Claude Sonnet)
**Theme:** Custom Hypothesis Escape Hatch + Sidebar Nav Fix

---

## Context

Phase 2 (Decomposition & Probing) auto-generates 4 hypotheses from the simulation data. Users currently have no way to inject their own hypothesis if the system misses something they believe is important. This sprint adds an "Add Custom Hypothesis" escape hatch and fixes a sidebar nav issue where the archived comparison page is leaking into the nav.

---

## Task A — Custom Hypothesis Escape Hatch

**File:** `app/pages/3_decompose.py`

After the hypothesis list (before the "Run Investigation" button), add a collapsible section:

```
▶ Add your own hypothesis (optional)
```

When expanded, show:
- `st.text_input("Hypothesis title", placeholder="e.g. Packaging looks cheap at shelf")`
- `st.text_area("Why you believe this", placeholder="Describe the signal you're seeing...")`
- `st.button("Add hypothesis")` — on click, appends a custom `Hypothesis` object to the hypotheses list in `probe_results`

**Custom Hypothesis object structure** (must match `src/analysis/hypothesis.py`):
- `id`: generate as `f"custom_{slug(title)}"` where slug lowercases and replaces spaces with `_`
- `title`: from text input
- `rationale`: from text area
- `signals`: `[]` (empty — no auto-signals for custom hypotheses)
- `is_custom = True` (add this field to the model if not present)

After adding, show a `st.success("Hypothesis added — it will be included in the next investigation run.")` and re-render the list.

Custom hypotheses should be **visually distinguished** in the list with a 🧑 icon prefix and a light purple left border (instead of the default styling).

**Gate:** Only show the escape hatch if `baseline_cohorts` is in session state (i.e. Phase 1 is complete).

---

## Task B — Fix Archive Page Leaking into Sidebar Nav

**File:** `app/pages/_archive_8_comparison.py`

Streamlit 1.55.0 is showing `_archive_8_comparison` in the sidebar navigation despite the underscore prefix. Fix by moving the file out of the `pages/` directory entirely:

```bash
mkdir -p app/pages/_archive
mv app/pages/_archive_8_comparison.py app/pages/_archive/_archive_8_comparison.py
```

Verify the sidebar no longer shows the archive entry after the move.

---

## Acceptance Criteria

- [ ] "Add your own hypothesis" section appears in Phase 2 after the auto-generated list
- [ ] Custom hypothesis can be added and appears with 🧑 prefix + purple border
- [ ] Custom hypothesis is included when "Run Investigation" is clicked
- [ ] `_archive_8_comparison.py` no longer appears in sidebar nav
- [ ] All existing tests pass (`pytest tests/`)
