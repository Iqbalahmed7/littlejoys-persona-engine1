# Probing Tree Visualization — McKinsey Decision Tree Format

**Status:** Design Draft
**Sprint:** 9
**Author:** Claude (Tech Lead)
**Last updated:** 2026-03-29

---

## 1. Problem Statement

The current probing tree results page (`app/pages/6_probing_tree.py`) renders results as a flat list of expanders:

```
✅ Hypothesis 1 — Confirmed  [progress bar]
  ▸ View 4 probe results  [expander]
⚠️ Hypothesis 2 — Partial   [progress bar]
  ▸ View 3 probe results  [expander]
```

This doesn't look like a **tree**. A McKinsey-style decision tree should visually show:
- The root problem at the top/left
- Hypotheses branching from it
- Probes as leaves under each hypothesis
- Color-coded confidence/status at every node
- The visual hierarchy makes the investigation structure immediately scannable

---

## 2. Target Visual

```
                    ┌─────────────────────┐
                    │  Why is repeat      │
                    │  purchase low?      │
                    │  ── 56% confidence  │
                    └──────┬──────────────┘
              ┌────────────┼─────────────────────┐
              ▼            ▼                     ▼
    ┌──────────────┐ ┌──────────────┐   ┌──────────────┐
    │ ✅ Price     │ │ ⚠️ Taste     │   │ ❌ Trust     │
    │ barrier      │ │ fatigue      │   │ deficit      │
    │ 78%          │ │ 55%          │   │ 22%          │
    └──┬───┬───┬───┘ └──┬───┬──────┘   └──┬───┬──────┘
       │   │   │        │   │              │   │
       ▼   ▼   ▼        ▼   ▼              ▼   ▼
      🎤  🔬  📊      🎤  📊            🎤  🔬
     72% 85% 68%     52% 61%           18% 28%
```

---

## 3. Implementation Options Evaluated

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Graphviz via `st.graphviz_chart`** | Clean dendrogram, consulting-grade | Needs `graphviz` package + system `dot` binary (neither installed) | v2 — add dependency later |
| **Plotly Treemap** | Already in stack | Area-based, not a tree shape. Wrong mental model. | ❌ Rejected |
| **Plotly Sunburst** | Radial hierarchy | Looks like a pie chart, not a decision tree | ❌ Rejected |
| **Plotly scatter + annotations** | Full control, no new deps | Manual positioning, fragile layout | Backup option |
| **`st.components.v1.html` + D3.js** | Beautiful, interactive, fully custom | Complex, maintenance burden, D3 expertise needed | v3 (future polish) |
| **Streamlit native layout (columns + containers)** | Zero new deps, works today, fully styled with Streamlit widgets | Not a true graph, but structured visual hierarchy | ✅ **v1 — ship now** |
| **Mermaid via `st.markdown`** | Clean diagrams, no deps | Streamlit doesn't support mermaid natively in markdown | ❌ Not supported |

### Decision: Hybrid approach

**v1 (Sprint 9):** Streamlit native structured layout — styled cards in a tree-like visual hierarchy using columns, containers, and metrics. Ships immediately with zero new dependencies.

**v2 (Sprint 10+):** Add `graphviz` dependency and render a proper dendrogram with `st.graphviz_chart`. Toggle between "card view" and "tree view".

---

## 4. v1 Design: Structured Card Tree

### 4.1 Layout Architecture

The visualization replaces the current flat results display (lines 159-263 of `6_probing_tree.py`). It has 3 tiers:

```
┌─────────────────────────────────────────────────────────────┐
│  TIER 0: Problem Root Card                                  │
│  Full-width banner with problem title, overall confidence,  │
│  hypothesis count, dominant finding                         │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ TIER 1:     │ │ TIER 1:     │ │ TIER 1:     │
│ Hypothesis  │ │ Hypothesis  │ │ Hypothesis  │
│ Cards       │ │ Cards       │ │ Cards       │
│ (columns)   │ │ (columns)   │ │ (columns)   │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
  ┌────┼────┐     ┌────┼────┐     ┌────┼────┐
  ▼    ▼    ▼     ▼    ▼    ▼     ▼    ▼    ▼
 🎤   🔬   📊   🎤   📊   🎤   🎤   🔬   📊
TIER 2: Probe nodes (compact chips under each hypothesis)
```

### 4.2 Tier 0: Problem Root Card

```python
def render_tree_root(
    problem: ProblemStatement,
    synthesis: TreeSynthesis,
    hypotheses: list[Hypothesis],
) -> None:
    """Top-level banner: the business question being investigated."""

    # Status color based on overall confidence
    if synthesis.overall_confidence >= 0.70:
        border_color = "#2ECC71"  # green — strong findings
        status_text = "Strong evidence gathered"
    elif synthesis.overall_confidence >= 0.50:
        border_color = "#F39C12"  # amber — partial findings
        status_text = "Partial evidence — more investigation recommended"
    else:
        border_color = "#E74C3C"  # red — inconclusive
        status_text = "Inconclusive — consider additional hypotheses"

    with st.container(border=True):
        st.markdown(
            f"### 🌳 {problem.title}",
        )
        st.caption(problem.context)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Overall Confidence", f"{synthesis.overall_confidence:.0%}")
        m2.metric("Hypotheses Tested", synthesis.hypotheses_tested)
        m3.metric("Confirmed", synthesis.hypotheses_confirmed)
        m4.metric("Est. Cost", f"${synthesis.total_cost_estimate:.2f}")

        if synthesis.dominant_hypothesis:
            dominant_title = next(
                (h.title for h in hypotheses if h.id == synthesis.dominant_hypothesis),
                synthesis.dominant_hypothesis,
            )
            st.success(f"**Dominant finding:** {dominant_title}")

        st.caption(status_text)
```

### 4.3 Tier 1: Hypothesis Cards (Branching Columns)

Hypotheses render as **equal-width columns** branching from the root. Each card shows:
- Status icon (✅ ⚠️ ❌ ❔)
- Title
- Confidence bar (color-coded)
- Consistency score
- Key evidence summary (1-line)

```python
# Status-to-style mapping
VERDICT_STYLES: dict[str, dict[str, str]] = {
    "confirmed": {
        "icon": "✅",
        "color": "#2ECC71",
        "label": "Confirmed",
        "bg": "#E8F8F0",
    },
    "partially_confirmed": {
        "icon": "⚠️",
        "color": "#F39C12",
        "label": "Partially Confirmed",
        "bg": "#FEF5E7",
    },
    "rejected": {
        "icon": "❌",
        "color": "#E74C3C",
        "label": "Rejected",
        "bg": "#FDEDEC",
    },
    "inconclusive": {
        "icon": "❔",
        "color": "#95A5A6",
        "label": "Inconclusive",
        "bg": "#F2F3F4",
    },
}


def render_hypothesis_card(
    hyp: Hypothesis,
    verdict: HypothesisVerdict,
    probes: list[Probe],
) -> None:
    """One hypothesis branch card with its probe nodes beneath."""

    style = VERDICT_STYLES.get(verdict.status, VERDICT_STYLES["inconclusive"])

    with st.container(border=True):
        # Visual connector line (CSS trick)
        st.markdown(
            f"<div style='text-align:center; color:#ccc; font-size:24px;'>│</div>",
            unsafe_allow_html=True,
        )

        # Header
        st.markdown(f"#### {style['icon']} {hyp.title}")
        st.caption(style["label"])

        # Confidence bar
        st.progress(min(verdict.confidence, 1.0))
        st.caption(
            f"Confidence: {verdict.confidence:.0%} · "
            f"Consistency: {verdict.consistency_score:.0%}"
        )

        # Evidence one-liner
        # Truncate to first sentence
        summary = verdict.evidence_summary
        if len(summary) > 120:
            summary = summary[:117] + "..."
        st.markdown(f"*{summary}*")

        # Probe nodes (Tier 2)
        st.markdown("---")
        _render_probe_nodes(probes)

        # Expandable detail
        with st.expander("Full evidence detail"):
            st.write(verdict.evidence_summary)
            for probe in sorted(probes, key=lambda p: p.order):
                _render_probe_detail(probe)
```

### 4.4 Tier 2: Probe Nodes (Compact Chips)

Each probe renders as a compact chip showing type icon, confidence, and a one-word status.

```python
PROBE_TYPE_CONFIG: dict[str, dict[str, str]] = {
    "interview": {"icon": "🎤", "label": "Interview", "color": "#8E44AD"},
    "simulation": {"icon": "🔬", "label": "Simulation", "color": "#2980B9"},
    "attribute": {"icon": "📊", "label": "Attribute", "color": "#27AE60"},
}


def _render_probe_nodes(probes: list[Probe]) -> None:
    """Compact probe chips arranged in a row under the hypothesis."""

    if not probes:
        st.caption("No probes executed.")
        return

    executed = [p for p in probes if p.result is not None]
    cols = st.columns(max(len(executed), 1))

    for col, probe in zip(cols, sorted(executed, key=lambda p: p.order)):
        result = probe.result
        config = PROBE_TYPE_CONFIG.get(
            probe.probe_type.value,
            PROBE_TYPE_CONFIG["attribute"],
        )

        with col:
            # Confidence determines chip color intensity
            conf = result.confidence if result else 0.0
            if conf >= 0.70:
                indicator = "🟢"
            elif conf >= 0.50:
                indicator = "🟡"
            elif conf >= 0.30:
                indicator = "🟠"
            else:
                indicator = "🔴"

            st.markdown(
                f"<div style='text-align:center; font-size:28px;'>"
                f"{config['icon']}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='text-align:center; font-size:14px;'>"
                f"{indicator} {conf:.0%}</div>",
                unsafe_allow_html=True,
            )
            st.caption(config["label"])
```

### 4.5 Full Tree Assembly

```python
def render_probing_tree_visualization(
    problem: ProblemStatement,
    synthesis: TreeSynthesis,
    hypotheses: list[Hypothesis],
    probes: list[Probe],
    verdicts: dict[str, HypothesisVerdict],
) -> None:
    """
    McKinsey decision-tree visualization of probing results.

    Renders as a 3-tier visual hierarchy:
    Tier 0 (root) → Tier 1 (hypotheses in columns) → Tier 2 (probe chips)
    """

    # Tier 0: Problem root
    render_tree_root(problem, synthesis, hypotheses)

    # Visual connector
    st.markdown(
        "<div style='text-align:center; color:#ccc; font-size:20px;'>"
        "┃<br>┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫"
        "</div>",
        unsafe_allow_html=True,
    )

    # Tier 1: Hypothesis branches
    tested = [h for h in hypotheses if h.id in verdicts]

    # Dynamic column count based on hypothesis count
    # Max 4 columns, min 1
    n_cols = min(len(tested), 4)
    if n_cols == 0:
        st.info("No hypotheses were tested.")
        return

    # If more than 4 hypotheses, render in rows of 4
    for row_start in range(0, len(tested), n_cols):
        row_hyps = tested[row_start:row_start + n_cols]
        cols = st.columns(len(row_hyps))

        for col, hyp in zip(cols, row_hyps):
            with col:
                verdict = verdicts[hyp.id]
                hyp_probes = [
                    p for p in probes
                    if p.hypothesis_id == hyp.id and p.result is not None
                ]
                render_hypothesis_card(hyp, verdict, hyp_probes)

    # Synthesis & Actions (below the tree)
    st.divider()
    st.subheader("Synthesis")
    st.write(synthesis.synthesis_narrative)

    if synthesis.recommended_actions:
        st.subheader("Recommended Actions")
        for i, action in enumerate(synthesis.recommended_actions, 1):
            st.markdown(f"{i}. {action}")

    # Disabled hypotheses
    disabled = [h for h in hypotheses if not h.enabled]
    if disabled:
        with st.expander(f"{len(disabled)} hypothesis(es) skipped"):
            for hyp in disabled:
                st.markdown(f"~~{hyp.title}~~")
            if synthesis.confidence_impact_of_disabled > 0:
                st.warning(
                    f"Skipping these may reduce confidence "
                    f"by up to {synthesis.confidence_impact_of_disabled:.0%}."
                )

    # Legend
    st.caption(
        "🎤 = Interview (sampled, 30 personas) · "
        "🔬 = Simulation (full population, no LLM) · "
        "📊 = Attribute analysis (full population, no LLM) · "
        "🟢 ≥70% · 🟡 ≥50% · 🟠 ≥30% · 🔴 <30%"
    )
```

---

## 5. File Structure

### 5.1 New File

**`app/components/probing_tree_viz.py`** (NEW)

Contains:
- `VERDICT_STYLES` — status-to-visual-style mapping
- `PROBE_TYPE_CONFIG` — probe type display config
- `render_tree_root()` — Tier 0 root card
- `render_hypothesis_card()` — Tier 1 hypothesis card with embedded probe nodes
- `_render_probe_nodes()` — Tier 2 probe chips
- `_render_probe_detail()` — full detail for a single probe (relocated from current expander logic)
- `render_probing_tree_visualization()` — orchestrator

### 5.2 Modified File

**`app/pages/6_probing_tree.py`** (MODIFY)

Replace lines 159-263 (the current flat results rendering) with:

```python
from app.components.probing_tree_viz import render_probing_tree_visualization

if "probing_synthesis" in st.session_state:
    synthesis = st.session_state["probing_synthesis"]
    verdicts = st.session_state["probing_verdicts"]
    hypotheses_r = st.session_state["probing_hypotheses"]
    probes_r = st.session_state["probing_probes"]
    problem_r = st.session_state["probing_problem"]

    st.divider()
    render_probing_tree_visualization(
        problem=problem_r,
        synthesis=synthesis,
        hypotheses=hypotheses_r,
        probes=probes_r,
        verdicts=verdicts,
    )
```

### 5.3 Retained File

**`app/components/probing_tree_helpers.py`** — Keep existing helpers (`render_interview_detail`, `render_simulation_detail`, `render_attribute_detail`). The new viz module imports from it.

---

## 6. v2 Design: Graphviz Dendrogram (Sprint 10+)

When we add `graphviz` as a dependency:

```python
def render_graphviz_tree(
    problem: ProblemStatement,
    synthesis: TreeSynthesis,
    hypotheses: list[Hypothesis],
    probes: list[Probe],
    verdicts: dict[str, HypothesisVerdict],
) -> str:
    """Generate DOT source for a McKinsey-style decision tree."""

    dot_lines = [
        "digraph ProbingTree {",
        '  rankdir=TB;',
        '  node [shape=box, style="filled,rounded", fontname="Helvetica"];',
        '  edge [color="#CCCCCC", penwidth=2];',
        "",
    ]

    # Root node
    root_color = _confidence_to_color(synthesis.overall_confidence)
    dot_lines.append(
        f'  root [label="{problem.title}\\n'
        f'{synthesis.overall_confidence:.0%} confidence", '
        f'fillcolor="{root_color}", fontcolor="white", fontsize=14];'
    )

    # Hypothesis nodes
    for hyp in hypotheses:
        if hyp.id not in verdicts:
            continue
        verdict = verdicts[hyp.id]
        style = VERDICT_STYLES[verdict.status]
        dot_lines.append(
            f'  {hyp.id} [label="{style["icon"]} {hyp.title}\\n'
            f'{verdict.confidence:.0%}", '
            f'fillcolor="{style["bg"]}", fontsize=11];'
        )
        dot_lines.append(f'  root -> {hyp.id};')

        # Probe leaf nodes
        hyp_probes = [p for p in probes if p.hypothesis_id == hyp.id and p.result]
        for probe in hyp_probes:
            config = PROBE_TYPE_CONFIG[probe.probe_type.value]
            conf = probe.result.confidence
            dot_lines.append(
                f'  {probe.id} [label="{config["icon"]}\\n{conf:.0%}", '
                f'shape=circle, width=0.8, fillcolor="{_confidence_to_color(conf)}", '
                f'fontcolor="white", fontsize=10];'
            )
            dot_lines.append(f'  {hyp.id} -> {probe.id};')

    dot_lines.append("}")
    return "\n".join(dot_lines)


def _confidence_to_color(confidence: float) -> str:
    if confidence >= 0.70:
        return "#2ECC71"
    if confidence >= 0.50:
        return "#F39C12"
    if confidence >= 0.30:
        return "#E67E22"
    return "#E74C3C"
```

Usage:
```python
dot_source = render_graphviz_tree(problem, synthesis, hypotheses, probes, verdicts)
st.graphviz_chart(dot_source)
```

### v2 Dependency Addition

```bash
uv add graphviz
brew install graphviz  # system binary needed for rendering
```

---

## 7. Interactive Features (v1)

### 7.1 Hypothesis Click-to-Focus

When a user clicks on a hypothesis card, expand it to full width showing all probe details. Use `st.session_state` to track which hypothesis is "focused":

```python
focus_key = f"tree_focus_{problem.id}"
focused_hyp_id = st.session_state.get(focus_key)

if focused_hyp_id:
    # Render focused hypothesis full-width with all details
    st.button("← Back to tree view", key=f"unfocus_{problem.id}")
    hyp = next(h for h in hypotheses if h.id == focused_hyp_id)
    verdict = verdicts[focused_hyp_id]
    _render_full_hypothesis_detail(hyp, verdict, probes)
else:
    # Render the tree layout
    render_probing_tree_visualization(...)
```

### 7.2 Confidence Threshold Filter

Add a slider that dims/hides low-confidence hypotheses:

```python
min_confidence = st.slider(
    "Minimum confidence to display",
    0.0, 1.0, 0.0, 0.05,
    key="tree_conf_filter",
    help="Hide hypotheses below this confidence threshold",
)
filtered_hyps = [h for h in tested if verdicts[h.id].confidence >= min_confidence]
```

### 7.3 View Toggle

```python
view_mode = st.radio(
    "View",
    ["Tree", "Table", "Detail"],
    horizontal=True,
    key="tree_view_mode",
)

if view_mode == "Tree":
    render_probing_tree_visualization(...)
elif view_mode == "Table":
    _render_results_table(...)  # Compact comparison table
elif view_mode == "Detail":
    _render_detailed_results(...)  # Current expander-based view
```

---

## 8. Comparison Table View

For the "Table" view mode — a compact McKinsey-style comparison matrix:

```python
def _render_results_table(
    hypotheses: list[Hypothesis],
    verdicts: dict[str, HypothesisVerdict],
    probes: list[Probe],
) -> None:
    """Compact table: hypotheses as rows, probe types as columns."""

    rows = []
    for hyp in hypotheses:
        if hyp.id not in verdicts:
            continue
        verdict = verdicts[hyp.id]
        hyp_probes = [p for p in probes if p.hypothesis_id == hyp.id]

        interview_conf = _avg_probe_conf(hyp_probes, ProbeType.INTERVIEW)
        sim_conf = _avg_probe_conf(hyp_probes, ProbeType.SIMULATION)
        attr_conf = _avg_probe_conf(hyp_probes, ProbeType.ATTRIBUTE)

        style = VERDICT_STYLES[verdict.status]
        rows.append({
            "Status": f"{style['icon']}",
            "Hypothesis": hyp.title,
            "🎤 Interview": f"{interview_conf:.0%}" if interview_conf else "—",
            "🔬 Simulation": f"{sim_conf:.0%}" if sim_conf else "—",
            "📊 Attribute": f"{attr_conf:.0%}" if attr_conf else "—",
            "Overall": f"{verdict.confidence:.0%}",
            "Verdict": style["label"],
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )
```

---

## 9. Test Plan

| Test File | What | Count |
|-----------|------|-------|
| `test_probing_tree_viz.py` | `VERDICT_STYLES` covers all statuses | 4 |
| `test_probing_tree_viz.py` | `PROBE_TYPE_CONFIG` covers all probe types | 3 |
| `test_probing_tree_viz.py` | `_confidence_to_color` returns correct colors | 4 |
| `test_probing_tree_viz.py` | Tree assembly doesn't crash with empty verdicts | 1 |
| `test_probing_tree_viz.py` | Tree assembly handles >4 hypotheses (row wrapping) | 1 |
| `test_probing_tree_viz.py` | Results table produces correct column structure | 2 |
| `test_probing_tree_viz.py` | Graphviz DOT output (v2) is valid syntax | 2 |
| **Total** | | **~17** |

---

## 10. Implementation Estimate

| Component | Effort | Engineer |
|-----------|--------|----------|
| `app/components/probing_tree_viz.py` (v1 Streamlit layout) | 3-4 hours | Cursor |
| Modify `app/pages/6_probing_tree.py` integration | 1 hour | Cursor |
| View toggle (Tree/Table/Detail) | 1 hour | Cursor |
| Tests | 2 hours | Antigravity |
| v2 Graphviz (Sprint 10) | 2 hours + dependency setup | Codex |

---

## 11. Dependencies

**v1 (Sprint 9):** Zero new dependencies. Uses only Streamlit, Plotly (for any charts inside detail views), and HTML/CSS via `unsafe_allow_html`.

**v2 (Sprint 10):** `graphviz` Python package + system `dot` binary.
