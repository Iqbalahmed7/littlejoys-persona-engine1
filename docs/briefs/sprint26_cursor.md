# Sprint 26 — Cursor (S6-01)
**Engineer:** Cursor (Claude Sonnet)
**Theme:** Custom Hypothesis Probe Generation + Re-Investigate Flow

---

## Context

Custom hypotheses added in Phase 2 have `indicator_attributes=[]` and `signals=[]`. When "Run Investigation" is clicked with a custom hypothesis present, the probing engine generates no attribute analysis probes for it and possibly errors. This sprint fixes that gap and adds a "Re-run investigation" flow so users can add hypotheses mid-session without losing Phase 1 data.

---

## Task A — Fallback Probes for Custom Hypotheses

**File:** `src/probing/predefined_trees.py` (or wherever probes are generated per hypothesis)

When building probes for a hypothesis with `is_custom=True`:

1. **Always generate 2 interview probes** using generic question templates derived from the hypothesis title:
   - `"What has been your experience with {title_summary}?"` (focus: `wouldn't-buy` persona segment)
   - `"Did {title_summary} affect your decision to purchase again?"` (focus: `lapsed_user` segment)

   Where `title_summary` is the hypothesis title lowercased, stripped to ≤ 60 chars.

2. **Skip attribute analysis probe** if `indicator_attributes` is empty (silently — no error, no empty probe rendered in UI).

3. **Skip simulation probe** if `counterfactual_modifications` is `None` or empty.

The engine must not crash on custom hypotheses — it should produce partial results (interviews only) gracefully.

**Test:** Add `tests/unit/test_custom_hypothesis_probing.py` with at least 2 tests:
- Custom hypothesis with empty attributes produces 2 interview probes only
- Custom hypothesis with provided attributes produces interview + attribute probes

---

## Task B — Re-Investigate Button

**File:** `app/pages/3_decompose.py`

After the "Investigation Results" section (if `probe_results` is already in session state), add a button:

```python
if st.button("↩ Re-run Investigation", help="Add or remove hypotheses, then re-run"):
    # Clear only probe_results and core_finding — preserve baseline_cohorts and population
    for key in ("probe_results", "core_finding", "intervention_results", "intervention_run"):
        st.session_state.pop(key, None)
    st.rerun()
```

This returns the page to "pre-investigation" state (hypothesis list + Run Investigation button) while keeping Phase 1 baseline intact.

Show this button only after a successful run (i.e. `probe_results` in session state). Position it below the "Phase 2 complete" banner, styled as a secondary button.

---

## Task C — Fix Phase 4 Sidebar Gate

**File:** `app/utils/phase_state.py`

**Bug:** `_PHASE_KEYS[4]` is `"intervention_results"` but `5_intervention.py` writes `st.session_state["intervention_run"]`. Phase 4 sidebar never turns 🟢.

**Fix:** Change the sentinel key to match what the page actually writes:

```python
_PHASE_KEYS: dict[int, str] = {
    ...
    4: "intervention_run",   # was "intervention_results" — matches 5_intervention.py
}
```

---

## Acceptance Criteria

- [ ] "Run Investigation" with a custom hypothesis completes without error (produces 2 interview probes)
- [ ] Empty `indicator_attributes` silently skips attribute probe — no empty section in UI
- [ ] "Re-run Investigation" button appears after a completed run and resets to hypothesis list
- [ ] Phase 4 sidebar turns 🟢 after running simulations
- [ ] 2+ new unit tests pass
- [ ] All existing tests pass
