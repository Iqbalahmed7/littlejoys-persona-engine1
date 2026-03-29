# OpenCode — Sprint 10 Track C: Scenario Explorer UI

**Branch:** `sprint-10-track-c-explorer-ui`
**Base:** `main`

## Context

This track builds the Streamlit UI page for the Auto-Scenario Explorer. Users select a base scenario, choose a strategy, run the exploration, and see consolidated results with "you missed this" insights.

**Design doc:** `docs/designs/AUTO-SCENARIO-EXPLORATION.md` — Section 7

## Deliverables

### 1. Create `app/pages/7_explorer.py` (NEW)

#### 1.1 Page Header

```python
# ruff: noqa: N999
"""Scenario Explorer — auto-generate and compare hundreds of scenario variations."""

from __future__ import annotations

import streamlit as st

st.title("Scenario Explorer")
st.caption(
    "Run hundreds of scenario variations to find the optimal configuration "
    "for your population. Zero LLM cost — pure simulation."
)
```

#### 1.2 Controls Section

```python
from src.constants import SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.utils.display import display_name

# Scenario selection
scenario_id = st.selectbox(
    "Base Scenario",
    SCENARIO_IDS,
    format_func=lambda sid: get_scenario(sid).name,
    key="explorer_scenario",
)

# Strategy selection
strategy_options = {
    "smart": "🧠 Smart — Target rejection reasons",
    "sweep": "📊 Sweep — One parameter at a time",
    "grid": "🔢 Grid — Parameter combinations",
    "random": "🎲 Random — Monte Carlo sampling",
}
strategy = st.radio(
    "Exploration Strategy",
    options=list(strategy_options.keys()),
    format_func=lambda s: strategy_options[s],
    horizontal=True,
    key="explorer_strategy",
)

# Variant count (only for random strategy)
n_variants = 100
if strategy == "random":
    n_variants = st.slider(
        "Number of variants",
        min_value=50,
        max_value=1000,
        value=100,
        step=50,
        key="explorer_n_variants",
        help="More variants = better coverage but longer runtime. "
             "100 variants takes ~30 seconds.",
    )

# Run button
run_clicked = st.button(
    "🚀 Explore Variations",
    type="primary",
    use_container_width=True,
    key="explorer_run",
)
```

#### 1.3 Execution Logic

When "Explore Variations" is clicked:

```python
if run_clicked:
    # Check population exists
    if "population" not in st.session_state:
        st.error("No population found. Generate one from the Home page first.")
        st.stop()

    pop = st.session_state.population
    base_scenario = get_scenario(scenario_id)

    # Import exploration modules
    from src.simulation.explorer import VariantStrategy, generate_variants
    from src.simulation.batch import BatchSimulationRunner
    from src.simulation.consolidation import ExplorationConsolidator
    from src.simulation.static import run_static_simulation

    # For smart strategy, need baseline result first
    base_result = None
    if strategy == "smart":
        with st.spinner("Running baseline scenario..."):
            base_result = run_static_simulation(pop, base_scenario)

    # Generate variants
    with st.spinner("Generating scenario variants..."):
        variants = generate_variants(
            base=base_scenario,
            strategy=VariantStrategy(strategy),
            n_variants=n_variants,
            base_result=base_result,
        )
    st.caption(f"Generated {len(variants)} variants (including baseline)")

    # Run batch
    progress_bar = st.progress(0.0)
    status_text = st.empty()

    def on_progress(done: int, total: int) -> None:
        progress_bar.progress(done / total)
        status_text.caption(f"Running variant {done}/{total}...")

    runner = BatchSimulationRunner(pop)
    results = runner.run_batch(variants, progress_callback=on_progress)

    progress_bar.progress(1.0)
    status_text.caption("✅ All variants complete")

    # Consolidate
    consolidator = ExplorationConsolidator()
    import time
    report = consolidator.consolidate(
        base_scenario_id=scenario_id,
        base_scenario=base_scenario,
        all_results=results,
        execution_time=0.0,  # batch runner logs this
        strategy=strategy,
    )

    # Store in session state
    st.session_state["explorer_report"] = report
    st.session_state["explorer_scenario_id"] = scenario_id
    st.rerun()
```

#### 1.4 Results Display

When results are available in session state:

```python
if "explorer_report" in st.session_state:
    report = st.session_state["explorer_report"]

    st.divider()
    st.subheader("Exploration Results")
```

**1.4.1 Top Metrics Row:**

```python
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Your Scenario",
        f"{report.baseline_result.adoption_rate:.0%}",
    )
    m2.metric(
        "Best Variant",
        f"{report.best_result.adoption_rate:.0%}",
        delta=f"{report.best_result.adoption_rate - report.baseline_result.adoption_rate:+.0%}",
    )
    m3.metric(
        "Worst Variant",
        f"{report.worst_result.adoption_rate:.0%}",
        delta=f"{report.worst_result.adoption_rate - report.baseline_result.adoption_rate:+.0%}",
    )
    m4.metric(
        "Median Adoption",
        f"{report.median_adoption_rate:.0%}",
    )
```

**1.4.2 Missed Insights Section:**

```python
    if report.missed_insights:
        st.subheader("⚡ You Missed This")
        for insight in report.missed_insights[:5]:
            with st.container(border=True):
                cols = st.columns([0.7, 0.3])
                with cols[0]:
                    st.markdown(f"**{insight.variant_name}**")
                    st.write(insight.explanation)
                    for diff in insight.key_differences:
                        st.markdown(f"- {diff}")
                with cols[1]:
                    st.metric(
                        "Adoption Rate",
                        f"{insight.adoption_rate:.0%}",
                        delta=f"+{insight.lift_over_baseline:.0%} vs yours",
                    )
```

**1.4.3 Parameter Sensitivity Chart:**

```python
    if report.parameter_sensitivities:
        st.subheader("Parameter Sensitivity")
        st.caption("Which parameters move the needle most?")

        import pandas as pd
        import plotly.express as px
        from src.constants import DASHBOARD_BRAND_COLORS

        sens_df = pd.DataFrame([
            {
                "Parameter": s.parameter_display_name,
                "Impact": s.sensitivity_score,
                "Best Value": s.max_value,
                "Worst Value": s.min_value,
            }
            for s in report.parameter_sensitivities[:10]
        ])

        fig = px.bar(
            sens_df,
            x="Impact",
            y="Parameter",
            orientation="h",
            title="Adoption rate swing by parameter",
            color="Impact",
            color_continuous_scale="RdYlGn",
        )
        fig.update_layout(
            height=400,
            showlegend=False,
            yaxis={"autorange": "reversed"},
        )
        fig.update_xaxes(title="Adoption Rate Range (max - min)", tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)
```

**1.4.4 Adoption Distribution Histogram:**

```python
    st.subheader("Adoption Distribution")

    rates = [r.adoption_rate for r in report.all_results]
    rates_df = pd.DataFrame({"adoption_rate": rates})

    fig_hist = px.histogram(
        rates_df,
        x="adoption_rate",
        nbins=30,
        title=f"Adoption rate distribution across {report.total_variants} variants",
        color_discrete_sequence=[DASHBOARD_BRAND_COLORS["primary"]],
    )
    fig_hist.add_vline(
        x=report.baseline_result.adoption_rate,
        line_dash="dash",
        line_color=DASHBOARD_BRAND_COLORS["accent"],
        annotation_text="Your scenario",
    )
    fig_hist.update_xaxes(title="Adoption Rate", tickformat=".0%")
    fig_hist.update_yaxes(title="Number of Variants")
    fig_hist.update_layout(height=400)
    st.plotly_chart(fig_hist, use_container_width=True)
```

**1.4.5 All Variants Table:**

```python
    st.subheader("All Variants")

    table_data = []
    for r in report.all_results:
        mods_summary = ", ".join(
            f"{k.split('.')[-1]}: {v}" for k, v in list(r.modifications.items())[:3]
        ) if r.modifications else "—"
        table_data.append({
            "Rank": r.rank,
            "Variant": r.variant_name,
            "Adoption": f"{r.adoption_rate:.1%}",
            "Count": r.adoption_count,
            "Key Changes": mods_summary,
        })

    st.dataframe(
        pd.DataFrame(table_data),
        use_container_width=True,
        hide_index=True,
    )
```

**1.4.6 Recommended Configuration:**

```python
    if report.recommended_modifications:
        st.subheader("Recommended Configuration")
        st.caption("Based on the best-performing variant")

        rec_cols = st.columns(2)
        for i, (path, value) in enumerate(report.recommended_modifications.items()):
            col = rec_cols[i % 2]
            field = display_name(path.split(".")[-1])
            if isinstance(value, float) and "price" not in path:
                col.metric(field, f"{value:.0%}")
            elif isinstance(value, bool):
                col.metric(field, "Enabled" if value else "Disabled")
            else:
                col.metric(field, str(value))
```

#### 1.5 Clear Results on Scenario Change

```python
# At the top, after scenario selection
if st.session_state.get("explorer_scenario_id") != scenario_id:
    st.session_state.pop("explorer_report", None)
    st.session_state.pop("explorer_scenario_id", None)
```

## Files to Read Before Starting

1. `app/pages/6_probing_tree.py` — pattern for run button + progress + session state
2. `app/pages/2_scenario.py` — pattern for scenario selection
3. `src/constants.py` — SCENARIO_IDS, DASHBOARD_BRAND_COLORS
4. `src/utils/display.py` — `display_name()`
5. `docs/designs/AUTO-SCENARIO-EXPLORATION.md` — Section 7 UI wireframe

## Constraints

- Python 3.11+
- Do NOT add `st.set_page_config()` — it's only in `app/streamlit_app.py`
- Use `use_container_width=True` for all charts and dataframes
- All widgets need unique `key=` parameters
- Use lazy imports for simulation modules (inside the `if run_clicked` block) to keep page load fast
- Handle missing population gracefully
- Clear results when scenario changes
- No new pip dependencies

## Import Fallback

If Track A/B modules aren't merged yet, the page will error on import. That's expected — it will work once all tracks merge. Add a try/except with helpful message:

```python
try:
    from src.simulation.explorer import VariantStrategy, generate_variants
    from src.simulation.batch import BatchSimulationRunner
    from src.simulation.consolidation import ExplorationConsolidator
except ImportError:
    st.error("Exploration modules not yet available. Waiting for Sprint 10 Tracks A & B.")
    st.stop()
```

## Acceptance Criteria

- [ ] Page renders with scenario selector, strategy radio, variant slider
- [ ] Run button triggers variant generation + batch execution with progress bar
- [ ] Top metrics show baseline vs best/worst/median
- [ ] Missed insights displayed as bordered cards with lift metrics
- [ ] Parameter sensitivity horizontal bar chart renders
- [ ] Adoption distribution histogram with baseline vertical line
- [ ] All variants table with rank, name, adoption, key changes
- [ ] Recommended configuration displayed as metric tiles
- [ ] Results cleared when scenario changes
- [ ] No `st.set_page_config()` in page file
- [ ] Handles missing population gracefully
