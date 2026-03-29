# OpenCode — Sprint 9 Track C: McKinsey Decision Tree Visualization

**Branch:** `sprint-9-track-c-tree-viz`
**Base:** `main`

## Context

The probing tree results page (`app/pages/6_probing_tree.py`) renders investigation results as a flat list of expanders. It should render as a McKinsey-style decision tree with visual hierarchy: root problem → hypothesis branches → probe leaf nodes.

**Design doc:** `docs/designs/PROBING-TREE-VISUALIZATION.md`

## Deliverables

### 1. Create `app/components/probing_tree_viz.py` (NEW)

This module contains all visualization components for the tree rendering.

#### 1.1 Style Constants

```python
VERDICT_STYLES: dict[str, dict[str, str]] = {
    "confirmed": {
        "icon": "✅",
        "color": "#2ECC71",
        "label": "Confirmed",
    },
    "partially_confirmed": {
        "icon": "⚠️",
        "color": "#F39C12",
        "label": "Partially Confirmed",
    },
    "rejected": {
        "icon": "❌",
        "color": "#E74C3C",
        "label": "Rejected",
    },
    "inconclusive": {
        "icon": "❔",
        "color": "#95A5A6",
        "label": "Inconclusive",
    },
}

PROBE_TYPE_CONFIG: dict[str, dict[str, str]] = {
    "interview": {"icon": "🎤", "label": "Interview", "color": "#8E44AD"},
    "simulation": {"icon": "🔬", "label": "Simulation", "color": "#2980B9"},
    "attribute": {"icon": "📊", "label": "Attribute", "color": "#27AE60"},
}
```

#### 1.2 `render_tree_root()` — Tier 0: Problem Root Card

```python
def render_tree_root(
    problem: ProblemStatement,
    synthesis: TreeSynthesis,
    hypotheses: list[Hypothesis],
) -> None:
```

Full-width bordered container showing:
- Tree icon + problem title as `### 🌳 {problem.title}`
- Problem context as caption
- 4 metric columns: Overall Confidence, Hypotheses Tested, Confirmed, Est. Cost
- Dominant finding as `st.success()` if available
- Status caption based on overall confidence:
  - ≥0.70: "Strong evidence gathered"
  - ≥0.50: "Partial evidence — more investigation recommended"
  - <0.50: "Inconclusive — consider additional hypotheses"

#### 1.3 `render_hypothesis_card()` — Tier 1: Hypothesis Branch

```python
def render_hypothesis_card(
    hyp: Hypothesis,
    verdict: HypothesisVerdict,
    probes: list[Probe],
) -> None:
```

Rendered inside a column. Each card shows:
- Visual connector: `│` centered above the card (HTML div, centered, gray)
- Status icon + title as `#### {icon} {title}`
- Status label as caption
- Confidence progress bar via `st.progress()`
- Confidence + consistency scores as caption
- Evidence summary (truncated to 120 chars)
- Divider, then probe nodes (Tier 2)
- Expandable "Full evidence detail" with probe-by-probe breakdown

#### 1.4 `_render_probe_nodes()` — Tier 2: Probe Chips

```python
def _render_probe_nodes(probes: list[Probe]) -> None:
```

Compact row of probe indicators. For each executed probe:
- Probe type icon (🎤/🔬/📊) centered, large (28px)
- Traffic light indicator + confidence: 🟢 ≥70%, 🟡 ≥50%, 🟠 ≥30%, 🔴 <30%
- Probe type label as caption

Use `st.columns()` to arrange probes side-by-side under the hypothesis.

#### 1.5 `_render_probe_detail()` — Full Probe Evidence

```python
def _render_probe_detail(probe: Probe) -> None:
```

Reuse the existing helpers from `app/components/probing_tree_helpers.py`:

```python
from app.components.probing_tree_helpers import (
    probe_icon,
    probe_label,
    render_interview_detail,
    render_simulation_detail,
    render_attribute_detail,
)
```

Show:
- Icon + label + confidence caption
- Evidence summary text
- Type-specific detail (clusters for interview, baseline/modified for simulation, splits table for attribute)
- Divider between probes

#### 1.6 `render_results_table()` — Table View

```python
def render_results_table(
    hypotheses: list[Hypothesis],
    verdicts: dict[str, HypothesisVerdict],
    probes: list[Probe],
) -> None:
```

Compact comparison table with columns:
- Status (icon)
- Hypothesis (title)
- 🎤 Interview (avg confidence of interview probes, or "—")
- 🔬 Simulation (avg confidence, or "—")
- 📊 Attribute (avg confidence, or "—")
- Overall (hypothesis confidence)
- Verdict (status label)

Use `st.dataframe()` with `hide_index=True`, `use_container_width=True`.

#### 1.7 `render_probing_tree_visualization()` — Master Orchestrator

```python
def render_probing_tree_visualization(
    problem: ProblemStatement,
    synthesis: TreeSynthesis,
    hypotheses: list[Hypothesis],
    probes: list[Probe],
    verdicts: dict[str, HypothesisVerdict],
) -> None:
```

Assembly logic:

1. **View toggle** at the top:
   ```python
   view_mode = st.radio(
       "View",
       ["🌳 Tree", "📋 Table", "📝 Detail"],
       horizontal=True,
       key="probing_tree_view_mode",
   )
   ```

2. **Tree view (default):**
   - Call `render_tree_root()`
   - Render visual connector between root and branches
   - Arrange hypothesis cards in columns (max 4 per row, wrap if more)
   - Show synthesis narrative and recommended actions below
   - Show skipped hypotheses in a collapsed expander
   - Show legend

3. **Table view:**
   - Call `render_tree_root()` (same metrics banner)
   - Call `render_results_table()`
   - Show synthesis below

4. **Detail view:**
   - Render the current flat expander-based layout (preserve backward compat)
   - This is essentially the existing rendering from lines 166-263 of `6_probing_tree.py`, moved here

### 2. Modify `app/pages/6_probing_tree.py`

Replace lines 159-263 (the results rendering section) with:

```python
from app.components.probing_tree_viz import render_probing_tree_visualization

if "probing_synthesis" in st.session_state:
    synthesis: TreeSynthesis = st.session_state["probing_synthesis"]
    verdicts: dict = st.session_state["probing_verdicts"]
    hypotheses_r: list[Hypothesis] = st.session_state["probing_hypotheses"]
    probes_r: list[Probe] = st.session_state["probing_probes"]
    problem_r: ProblemStatement = st.session_state["probing_problem"]

    st.divider()
    render_probing_tree_visualization(
        problem=problem_r,
        synthesis=synthesis,
        hypotheses=hypotheses_r,
        probes=probes_r,
        verdicts=verdicts,
    )
```

The investigation plan section (lines 1-157, problem selection + hypothesis toggles + run button) stays UNCHANGED.

## Files to Read Before Starting

1. `app/pages/6_probing_tree.py` — **full file** (263 lines) — current implementation
2. `app/components/probing_tree_helpers.py` — **full file** (138 lines) — existing helpers to reuse
3. `src/probing/models.py` — **full file** (186 lines) — all data models
4. `docs/designs/PROBING-TREE-VISUALIZATION.md` — full design doc

## Constraints

- Python 3.11+
- Do NOT add `st.set_page_config()` — it's only in `app/streamlit_app.py`
- Do NOT modify `app/components/probing_tree_helpers.py` — import from it
- Do NOT modify `src/probing/` models or engine — visualization only
- Use `unsafe_allow_html=True` only for visual connectors (│ lines between tiers), not for core content
- Use `use_container_width=True` for all dataframes and charts
- All widgets need unique `key=` parameters
- No new pip dependencies
- The detail view must preserve the exact current behavior for backward compatibility

## Data Flow

The visualization receives these objects from session state:
- `ProblemStatement` — root problem (title, context, success_metric)
- `TreeSynthesis` — overall results (confidence, dominant_hypothesis, ranking, actions)
- `list[Hypothesis]` — all hypotheses (title, enabled, order)
- `list[Probe]` — all probes with `.result: ProbeResult | None`
- `dict[str, HypothesisVerdict]` — verdict per hypothesis (confidence, status, evidence)

Key relationships:
- `probe.hypothesis_id` links probes to hypotheses
- `probe.result` is `None` for unexecuted probes
- `verdict.status` is one of: "confirmed", "partially_confirmed", "rejected", "inconclusive"

## Acceptance Criteria

- [ ] `probing_tree_viz.py` created with all rendering functions
- [ ] Tree view shows 3-tier hierarchy (root → hypotheses in columns → probe chips)
- [ ] Table view shows compact comparison matrix
- [ ] Detail view preserves current expander-based rendering
- [ ] View toggle switches between all 3 views
- [ ] Hypothesis cards are color-coded by status
- [ ] Probe chips show traffic-light confidence indicators
- [ ] Root card shows overall metrics + dominant finding
- [ ] Legend explains icons and color codes
- [ ] Handles edge cases: 0 tested hypotheses, probes with no results
- [ ] No `st.set_page_config()` in page files
- [ ] All existing tests still pass
