# Cursor — Sprint 7b Briefing

**PRD**: PRD-014b Probing Tree Streamlit UI
**Branch**: `feat/PRD-014b-probing-tree-ui`
**Priority**: P0 — The probing tree backend is complete. You are building the presentation layer.

---

## Your Task: Build `app/pages/6_probing_tree.py`

A single Streamlit page that lets a user pick a business problem, see its hypothesis tree, toggle branches on/off (with real-time confidence impact), run the investigation, drill into probe results, and read the synthesis.

**Backend is ready.** You are calling into `src/probing/` — do NOT modify any file in `src/probing/`. Import and use.

---

## Key Imports You'll Need

```python
from __future__ import annotations

import streamlit as st

from src.config import Config
from src.constants import DASHBOARD_DEFAULT_POPULATION_PATH, SCENARIO_IDS
from src.generation.population import Population
from src.probing import (
    Hypothesis,
    Probe,
    ProbeResult,
    ProbeType,
    ProbingTreeEngine,
    ProblemStatement,
    TreeSynthesis,
    get_problem_tree,
    list_problem_ids,
)
from src.utils.display import display_name
from src.utils.llm import LLMClient
```

---

## Page Structure

The page has 3 states: **Select → Configure → Results**.

### State 1: Problem Selection + Tree Preview

```python
st.title("Probing Tree")
st.caption(
    "Decompose a business question into testable hypotheses. "
    "Each hypothesis is investigated with interview, simulation, and statistical probes "
    "across your persona population."
)

# 1. Problem picker
problem_ids = list_problem_ids()
# Build display labels: "repeat_purchase_low" → "Why is repeat purchase low despite high NPS?"
problem_labels = {}
for pid in problem_ids:
    prob, _, _ = get_problem_tree(pid)
    problem_labels[pid] = prob.title

selected_id = st.selectbox(
    "Business problem",
    problem_ids,
    format_func=lambda pid: problem_labels.get(pid, pid),
    help="Each problem decomposes into 3-5 testable hypotheses with structured probes.",
)
```

### State 2: Hypothesis Toggles (BEFORE running)

After selection, show the tree structure with checkboxes. This is the key interaction — users enable/disable hypotheses before running.

```python
problem, hypotheses, probes = get_problem_tree(selected_id)

# Show problem context
st.markdown(f"**Context:** {problem.context}")
st.markdown(f"**Success metric:** {display_name(problem.success_metric)}")
st.divider()

# Hypothesis toggles
st.subheader("Investigation Plan")

for hyp in sorted(hypotheses, key=lambda h: h.order):
    # Checkbox to enable/disable
    col_check, col_title = st.columns([0.05, 0.95])
    with col_check:
        enabled = st.checkbox(
            "Enable",
            value=hyp.enabled,
            key=f"hyp_toggle_{hyp.id}",
            label_visibility="collapsed",
        )
        hyp.enabled = enabled

    with col_title:
        if enabled:
            st.markdown(f"**{hyp.title}**")
        else:
            st.markdown(f"~~{hyp.title}~~ *(skipped)*")

    # Show probes under this hypothesis (indented)
    if enabled:
        hyp_probes = [p for p in probes if p.hypothesis_id == hyp.id]
        for probe in sorted(hyp_probes, key=lambda p: p.order):
            icon = _probe_icon(probe.probe_type)
            label = _probe_label(probe)
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} {label}")

    # Show rationale in expander
    with st.expander(f"Why this hypothesis?", expanded=False):
        st.write(hyp.rationale)
        st.caption(f"Indicator attributes: {', '.join(display_name(a) for a in hyp.indicator_attributes)}")
```

**Helper functions you need to write:**

```python
def _probe_icon(probe_type: ProbeType) -> str:
    """Return emoji icon for probe type."""
    return {
        ProbeType.INTERVIEW: "🎤",
        ProbeType.SIMULATION: "🔬",
        ProbeType.ATTRIBUTE: "📊",
    }.get(probe_type, "❓")


def _probe_label(probe: Probe) -> str:
    """One-line description of what this probe does."""
    if probe.probe_type == ProbeType.INTERVIEW:
        target = f" (only {probe.target_outcome}s)" if probe.target_outcome else ""
        return f'"{probe.question_template}"{target}'
    if probe.probe_type == ProbeType.SIMULATION:
        changes = ", ".join(
            f"{display_name(k.split('.')[-1])} → {v}"
            for k, v in (probe.scenario_modifications or {}).items()
        )
        return f"Simulate: {changes}"
    if probe.probe_type == ProbeType.ATTRIBUTE:
        attrs = ", ".join(display_name(a) for a in probe.analysis_attributes[:3])
        return f"Analyse: {attrs} by outcome"
    return probe.id
```

### State 3: Run + Results

```python
# Count enabled
enabled_hyps = [h for h in hypotheses if h.enabled]
enabled_probes = [p for p in probes if any(h.id == p.hypothesis_id for h in enabled_hyps)]
interview_count = sum(1 for p in enabled_probes if p.probe_type == ProbeType.INTERVIEW)

st.divider()
col_run, col_info = st.columns([0.3, 0.7])
with col_info:
    st.caption(
        f"{len(enabled_hyps)} hypotheses enabled · "
        f"{len(enabled_probes)} probes · "
        f"{interview_count} interviews (30 personas each)"
    )

with col_run:
    run_clicked = st.button(
        "Run Investigation",
        type="primary",
        disabled=len(enabled_hyps) == 0,
        use_container_width=True,
        help="Runs all enabled probes against your persona population. Mock mode: instant. Real LLM: ~30 seconds.",
    )
```

**When the user clicks Run:**

```python
if run_clicked:
    # Load population
    pop = _load_population()
    if pop is None:
        st.error("No population found. Generate one from the Home page first.")
        st.stop()

    # Create engine
    config = Config()
    llm_client = LLMClient(config)
    engine = ProbingTreeEngine(
        population=pop,
        scenario_id=problem.scenario_id,
        llm_client=llm_client,
    )

    # Run with progress bar
    with st.spinner("Running probing tree..."):
        progress = st.progress(0.0)
        total_probes = len(enabled_probes)

        # Execute tree
        synthesis = engine.execute_tree(problem, hypotheses, probes)
        progress.progress(1.0)

    # Store results in session state
    st.session_state["probing_synthesis"] = synthesis
    st.session_state["probing_hypotheses"] = hypotheses
    st.session_state["probing_probes"] = probes
    st.session_state["probing_verdicts"] = engine.verdicts
    st.session_state["probing_problem"] = problem
```

### State 4: Display Results (after run)

This is the most important section. Show the tree with confidence bars, expandable probes, and synthesis.

```python
if "probing_synthesis" in st.session_state:
    synthesis = st.session_state["probing_synthesis"]
    verdicts = st.session_state["probing_verdicts"]
    hypotheses = st.session_state["probing_hypotheses"]
    probes = st.session_state["probing_probes"]
    problem = st.session_state["probing_problem"]

    # ── Header metrics ──
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Confidence", f"{synthesis.overall_confidence:.0%}")
    c2.metric("Hypotheses Tested", synthesis.hypotheses_tested)
    c3.metric("Confirmed", synthesis.hypotheses_confirmed)
    c4.metric("Estimated Cost", f"${synthesis.total_cost_estimate:.2f}")

    if synthesis.dominant_hypothesis:
        dominant_title = next(
            (h.title for h in hypotheses if h.id == synthesis.dominant_hypothesis),
            synthesis.dominant_hypothesis,
        )
        st.info(f"**Dominant finding:** {dominant_title} ({synthesis.overall_confidence:.0%} confidence)")

    # ── Hypothesis results ──
    st.subheader("Hypothesis Results")

    for hyp_id, confidence in synthesis.confidence_ranking:
        verdict = verdicts.get(hyp_id)
        hyp = next((h for h in hypotheses if h.id == hyp_id), None)
        if not verdict or not hyp:
            continue

        # Confidence bar colour
        bar_color = "green" if verdict.status == "confirmed" else (
            "orange" if verdict.status == "partially_confirmed" else "red"
        )

        # Header row: title + confidence bar
        col_title, col_bar = st.columns([0.55, 0.45])
        with col_title:
            status_icon = {"confirmed": "✅", "partially_confirmed": "⚠️", "rejected": "❌", "inconclusive": "❔"}.get(verdict.status, "")
            st.markdown(f"**{status_icon} {hyp.title}** — {verdict.status.replace('_', ' ').title()}")
        with col_bar:
            st.progress(min(verdict.confidence, 1.0))
            st.caption(f"Confidence: {verdict.confidence:.0%} · Consistency: {verdict.consistency_score:.0%}")

        # Expandable: probe-level results
        hyp_probes = [p for p in probes if p.hypothesis_id == hyp_id and p.result]
        with st.expander(f"View {len(hyp_probes)} probe results", expanded=False):
            for probe in sorted(hyp_probes, key=lambda p: p.order):
                result = probe.result
                icon = _probe_icon(probe.probe_type)

                # Probe header
                sample_info = ""
                if result.population_size and result.population_size > result.sample_size:
                    sample_info = f" · {result.sample_size}/{result.population_size} sampled"
                if result.clustering_method:
                    sample_info += f" · {result.clustering_method} clustering"

                st.markdown(f"{icon} **{_probe_label(probe)}**")
                st.caption(f"Confidence: {result.confidence:.0%}{sample_info}")
                st.write(result.evidence_summary)

                # Type-specific details
                if probe.probe_type == ProbeType.INTERVIEW and result.response_clusters:
                    _render_interview_detail(result)
                elif probe.probe_type == ProbeType.SIMULATION and result.lift is not None:
                    _render_simulation_detail(result)
                elif probe.probe_type == ProbeType.ATTRIBUTE and result.attribute_splits:
                    _render_attribute_detail(result)

                st.markdown("---")

        # Evidence summary
        st.caption(verdict.evidence_summary)

    # ── Disabled hypotheses ──
    disabled = [h for h in hypotheses if not h.enabled]
    if disabled:
        st.subheader("Skipped Hypotheses")
        for hyp in disabled:
            st.markdown(f"~~{hyp.title}~~")
        if synthesis.confidence_impact_of_disabled > 0:
            st.warning(
                f"Skipping {len(disabled)} hypothesis(es) may reduce confidence "
                f"by up to {synthesis.confidence_impact_of_disabled:.0%}."
            )

    # ── Synthesis ──
    st.subheader("Synthesis")
    st.write(synthesis.synthesis_narrative)

    if synthesis.recommended_actions:
        st.subheader("Recommended Actions")
        for i, action in enumerate(synthesis.recommended_actions, 1):
            st.markdown(f"{i}. {action}")
```

---

## Probe Detail Renderers

These three functions render expanded details for each probe type:

### Interview Detail

```python
def _render_interview_detail(result: ProbeResult) -> None:
    """Show response clusters with representative quotes."""
    for cluster in result.response_clusters:
        pct = f"{cluster.percentage:.0%}"
        st.markdown(f"**{cluster.theme.replace('_', ' ').title()}** — {pct} of responses")
        st.caption(cluster.description)
        if cluster.representative_quotes:
            for quote in cluster.representative_quotes[:3]:
                st.markdown(f"> _{quote[:300]}_")
        if cluster.dominant_attributes:
            attrs = ", ".join(
                f"{display_name(k)}: {v:.2f}" for k, v in list(cluster.dominant_attributes.items())[:5]
            )
            st.caption(f"Dominant attributes: {attrs}")
```

### Simulation Detail

```python
def _render_simulation_detail(result: ProbeResult) -> None:
    """Show baseline vs modified metric with lift."""
    col_base, col_mod, col_lift = st.columns(3)
    col_base.metric("Baseline", f"{result.baseline_metric:.0%}" if result.baseline_metric is not None else "—")
    col_mod.metric("Modified", f"{result.modified_metric:.0%}" if result.modified_metric is not None else "—")
    col_lift.metric(
        "Lift",
        f"{result.lift:+.1%}" if result.lift is not None else "—",
        delta=f"{result.lift:+.1%}" if result.lift is not None else None,
    )
```

### Attribute Detail

```python
def _render_attribute_detail(result: ProbeResult) -> None:
    """Show attribute splits as a comparison table."""
    import pandas as pd

    rows = []
    for split in result.attribute_splits:
        rows.append({
            "Attribute": display_name(split.attribute),
            "Would-buy mean": f"{split.adopter_mean:.2f}",
            "Wouldn't-buy mean": f"{split.rejector_mean:.2f}",
            "Effect size": f"{split.effect_size:+.2f}",
            "Significant": "Yes" if split.significant else "No",
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
```

---

## Population Loading Helper

Reuse the pattern from other pages:

```python
from pathlib import Path

def _load_population() -> Population | None:
    """Load population from session state or disk."""
    if "population" in st.session_state:
        return st.session_state["population"]
    pop_path = Path(DASHBOARD_DEFAULT_POPULATION_PATH)
    if pop_path.exists():
        pop = Population.load(pop_path)
        st.session_state["population"] = pop
        return pop
    return None
```

---

## Legend Footer

At the bottom of the page, after results:

```python
st.divider()
st.caption(
    "🎤 = Interview probe (sampled, 30 personas) · "
    "🔬 = Simulation probe (full population, no LLM) · "
    "📊 = Attribute analysis (full population, no LLM)"
)
```

---

## What NOT to Do

1. **Do NOT modify any file in `src/probing/`** — the backend is finished.
2. **Do NOT create new Pydantic models** — use the existing ones from `src.probing.models`.
3. **Do NOT use raw field names** — all persona attributes go through `display_name()`.
4. **Do NOT use "Adopted"/"Rejected"** — use "Would buy"/"Wouldn't buy" in any outcome references.
5. **Do NOT run the tree on page load** — only run when user clicks "Run Investigation".

---

## Tests

**File**: `tests/unit/test_page_probing_tree.py` (new)

Add structural tests that import and validate the page's helpers:

```python
def test_probe_icon_all_types():
    """Every ProbeType has an icon."""
    from src.probing.models import ProbeType
    # Import _probe_icon from the page or move to a shared util
    for pt in ProbeType:
        icon = _probe_icon(pt)
        assert len(icon) > 0

def test_probe_label_interview():
    """Interview probe label shows the question."""
    from src.probing.models import Probe, ProbeType
    p = Probe(
        id="test",
        hypothesis_id="h1",
        probe_type=ProbeType.INTERVIEW,
        question_template="What made you hesitate?",
    )
    label = _probe_label(p)
    assert "hesitate" in label

def test_probe_label_simulation():
    """Simulation probe label shows parameter changes."""
    from src.probing.models import Probe, ProbeType
    p = Probe(
        id="test",
        hypothesis_id="h1",
        probe_type=ProbeType.SIMULATION,
        scenario_modifications={"product.price_inr": 479},
    )
    label = _probe_label(p)
    assert "479" in label

def test_probe_label_attribute():
    """Attribute probe label shows attribute names."""
    from src.probing.models import Probe, ProbeType
    p = Probe(
        id="test",
        hypothesis_id="h1",
        probe_type=ProbeType.ATTRIBUTE,
        analysis_attributes=["budget_consciousness"],
    )
    label = _probe_label(p)
    # Should use display_name, so "Price Sensitivity" not "budget_consciousness"
    assert "Price Sensitivity" in label or "budget" in label.lower()

def test_load_population_returns_none_when_missing(tmp_path):
    """Returns None when no population exists."""
    # Temporarily clear session state and use nonexistent path
    # This test verifies graceful handling
    pass  # Implement based on your import structure
```

If the helper functions are inside the Streamlit page and hard to import, move `_probe_icon`, `_probe_label`, `_render_interview_detail`, `_render_simulation_detail`, `_render_attribute_detail` into a new file `app/components/probing_tree_helpers.py` and import them in both the page and tests.

---

## Standards

- `from __future__ import annotations`
- No raw field names — all through `display_name()`
- All user-facing text written for a marketing executive
- Status labels: "Confirmed" / "Partially Confirmed" / "Inconclusive" / "Rejected" (title case, no underscores)
- Help text on Run button and problem selector
- Page must work even if no population is loaded (show error, don't crash)

## Run

```bash
uv run pytest tests/ -x -q
uv run ruff check app/pages/6_probing_tree.py
```
