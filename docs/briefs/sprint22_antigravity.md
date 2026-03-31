# Sprint 22 Brief — Antigravity
## S2-03: Reactive Probing Tree Visualisation

> **Engineer**: Antigravity (Gemini 3 Flash → escalate to Gemini Pro if reactive state proves complex)
> **Sprint**: 22
> **Ticket**: S2-03
> **Estimated effort**: Medium (reactive state + partial render logic)

---

### Context

The current probing tree viz (`app/components/probing_tree_viz.py`) renders **statically** — it only draws after `ProbingTreeEngine.execute_tree()` returns the complete `TreeSynthesis`. This means the user stares at a spinner for the entire duration of probe execution with no feedback.

The goal is to make the tree **grow visibly** as each probe completes — hypothesis cards appear one at a time, each with its verdict badge and probe detail rows rendered progressively.

---

### Architecture Pattern

Use a **callback + session state** approach:

1. `ProbingTreeEngine` gains an optional `on_probe_complete` callback parameter.
2. As each probe finishes, the engine calls `on_probe_complete(hypothesis_id, probe_result)`.
3. The page (`app/pages/3_decompose.py`) passes a callback that appends to `st.session_state["partial_probe_results"]` and calls `st.rerun()`.
4. The viz component reads `partial_probe_results` and renders whatever has accumulated so far.

**Do NOT use `st.fragment` for this** — fragment auto-reruns on a timer and is hard to synchronize. Manual `st.rerun()` inside the callback is the correct pattern.

---

### Task 1: Add callback to ProbingTreeEngine

File: `src/probing/engine.py`

Add an optional `on_probe_complete` parameter to `ProbingTreeEngine.__init__()` and call it after each probe result is appended:

```python
def __init__(
    self,
    population: Population,
    scenario_id: str,
    llm_client: LLMClient,
    on_probe_complete: Callable[[str, ProbeResult], None] | None = None,
):
    ...
    self._on_probe_complete = on_probe_complete
```

After each probe executes, call:
```python
if self._on_probe_complete:
    self._on_probe_complete(hypothesis_id, probe_result)
```

**Critical**: This must be backward-compatible. `on_probe_complete=None` (default) must leave existing behaviour unchanged.

---

### Task 2: Update `render_probing_tree_progress()` in the viz component

File: `app/components/probing_tree_viz.py`

Add a new function (do NOT modify existing `render_tree_root`, `render_hypothesis_card` etc.):

```python
def render_probing_tree_progress(
    problem: ProblemStatement,
    hypotheses: list[Hypothesis],
    partial_results: dict[str, list[ProbeResult]],
) -> None:
    """
    Render a live-growing tree from partial probe results accumulated so far.
    Shows completed hypothesis cards; pending hypotheses show a pulsing spinner row.
    """
```

- For hypotheses with results in `partial_results`: render a hypothesis card (reuse `render_hypothesis_card` where possible, adapt as needed to work from raw `ProbeResult` list rather than `HypothesisVerdict`).
- For hypotheses with **no results yet**: render a placeholder row with `st.spinner("Investigating…")`.
- Each completed hypothesis card should show: hypothesis title, probe count, top evidence snippet (first 120 chars of evidence_summary from the last probe result).

---

### Task 3: Wire in `3_decompose.py`

In `app/pages/3_decompose.py`, update the `run_clicked` block:

1. Initialise `st.session_state["partial_probe_results"] = {}` before engine call.
2. Define a callback:
```python
def _on_probe(hypothesis_id: str, result: ProbeResult) -> None:
    bucket = st.session_state["partial_probe_results"]
    bucket.setdefault(hypothesis_id, []).append(result)
    st.session_state["partial_probe_results"] = bucket
    st.rerun()
```
3. Pass `on_probe_complete=_on_probe` to `ProbingTreeEngine(...)`.
4. Replace the static spinner with a call to `render_probing_tree_progress(...)` during execution.

---

### Acceptance Criteria

- [ ] Engine callback is optional and backward-compatible (all existing tests still pass)
- [ ] Hypothesis cards appear incrementally — not all at once when engine finishes
- [ ] Pending hypotheses show a "Investigating…" placeholder row
- [ ] After engine completes, the full synthesis render (existing `render_tree_root` + `render_hypothesis_card`) still fires as today
- [ ] No new third-party dependencies introduced
- [ ] Import check passes: `python -c "from app.components.probing_tree_viz import render_probing_tree_progress"`

---

### Files to Modify

| File | Change |
|------|--------|
| `src/probing/engine.py` | Add `on_probe_complete` callback (optional) |
| `app/components/probing_tree_viz.py` | Add `render_probing_tree_progress()` function |
| `app/pages/3_decompose.py` | Wire callback + partial render in run block |

### Files NOT to modify

`src/probing/models.py`, `src/probing/predefined_trees.py`, `app/utils/probe_orchestrator.py` — leave these untouched.

---

### Escalation Rule

If the Streamlit rerun loop causes infinite-rerun edge cases, escalate to **Gemini Pro** and implement using `st.empty()` placeholder containers with in-place updates instead of `st.rerun()`.
