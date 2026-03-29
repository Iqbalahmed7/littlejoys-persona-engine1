# Sprint 14 Brief — Cursor (Claude)
## Research Results Page

### Context
Sprint 14 replaces the existing `3_results.py` (static dashboard) with a new `3_results.py` that renders the consolidated research report from the hybrid pipeline. The old file gets renamed to `3_results_legacy.py` (Sprint 15 cleanup). This page reads the `ConsolidatedReport` from session state and renders a polished, multi-section results experience.

### Task: Rewrite `app/pages/3_results.py` → new Research Results page
**Overwrite the existing file.** Back up the old one as `app/pages/3_results_legacy.py` first.

### Page Structure

#### Guard + Fallback

```python
st.header("Research Results")
st.caption("Quantitative findings, qualitative themes, and strategic alternatives from your research run.")

if "research_result" not in st.session_state:
    # Fallback: check if old-style scenario_results exist for backward compat
    if st.session_state.get("scenario_results"):
        st.info("These results are from a quick simulation run. Run a full research pipeline from the Research Design page for the complete report.")
        # Render the legacy dashboard inline (import the old functions)
        _render_legacy_dashboard()
        st.stop()
    st.warning("No research results available. Run a research pipeline from the Research Design page.")
    st.stop()
```

For the legacy fallback, extract the core dashboard logic from the current `3_results.py` into a helper function `_render_legacy_dashboard()` at the top of the file. This ensures backward compat with the home page's quick-run flow.

#### Consolidation

```python
from src.analysis.research_consolidator import consolidate_research, ConsolidatedReport

result = st.session_state["research_result"]
pop = st.session_state.population

# Cache consolidation so it doesn't recompute on every rerun
@st.cache_data(show_spinner="Consolidating results...")
def _consolidate(_result_json: str, _pop_path: str) -> dict:
    from src.simulation.research_runner import ResearchResult
    from src.generation.population import Population
    r = ResearchResult.model_validate_json(_result_json)
    p = st.session_state.population  # Already loaded
    report = consolidate_research(r, p)
    return report.model_dump(mode="json")

report = ConsolidatedReport.model_validate(_consolidate(result.model_dump_json(), "cached"))
```

#### Section 1 — Overview Metrics (top row)

```python
st.subheader(f"{report.scenario_name}: {report.question_title}")
st.caption(report.question_description)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Population", f"{report.funnel.population_size:,}")
m2.metric("Would Try", f"{report.funnel.adoption_count:,}", f"{report.funnel.adoption_rate:.1%}")
m3.metric("Interviews", f"{report.interview_count}")
m4.metric("Alternatives Tested", f"{len(report.top_alternatives) + len(report.worst_alternatives)}")
m5.metric("Duration", f"{report.duration_seconds:.1f}s")
```

#### Section 2 — Decision Pathway Waterfall

```python
st.subheader("Decision Pathway")
```

Use `report.funnel.waterfall_data` to render the funnel chart:
```python
from src.utils.viz import create_funnel_chart
st.plotly_chart(create_funnel_chart(report.funnel.waterfall_data), use_container_width=True)
```

Show top barriers below:
```python
if report.funnel.top_barriers:
    st.caption("Top barriers to trial:")
    for b in report.funnel.top_barriers[:5]:
        st.markdown(f"- **{b['stage']}** → {b['reason']} ({b['count']} personas)")
```

#### Section 3 — Segment Deep-Dives (tabs)

```python
st.subheader("Segment Analysis")

tab_tier, tab_income = st.tabs(["By City Tier", "By Income Bracket"])

with tab_tier:
    if report.segments_by_tier:
        for seg in report.segments_by_tier:
            delta_str = f"+{seg.delta_vs_population:.1%}" if seg.delta_vs_population > 0 else f"{seg.delta_vs_population:.1%}"
            st.metric(
                f"{seg.segment_value}",
                f"{seg.adoption_rate:.1%}",
                delta_str,
                help=f"{seg.persona_count} personas"
            )

with tab_income:
    # Same pattern for income segments
```

#### Section 4 — Causal Drivers

```python
st.subheader("Key Drivers")
st.caption("Variables most strongly associated with trial openness, ranked by importance.")

if report.causal_drivers:
    from src.utils.display import display_name
    for driver in report.causal_drivers[:8]:
        direction = "↑" if driver["direction"] == "positive" else "↓"
        name = display_name(str(driver["variable"]))
        st.markdown(f"- {direction} **{name}** — importance: {driver['importance']:.3f}")
```

#### Section 5 — Qualitative Themes (from interviews)

```python
st.subheader("Interview Themes")
st.caption(f"Themes identified from {report.interview_count} deep interviews.")

if report.clusters:
    for cluster in report.clusters:
        with st.expander(f"{cluster.theme.replace('_', ' ').title()} — {cluster.persona_count} personas ({cluster.percentage:.0%})"):
            st.markdown(cluster.description)
            if cluster.representative_quotes:
                st.markdown("**Sample responses:**")
                for quote in cluster.representative_quotes[:2]:
                    st.markdown(f"> {quote[:300]}")
            if cluster.dominant_attributes:
                st.caption("Dominant persona traits: " + ", ".join(
                    f"{display_name(k)}: {v:.2f}" for k, v in list(cluster.dominant_attributes.items())[:5]
                ))
else:
    st.caption("No interview themes available (mock mode or insufficient responses).")
```

#### Section 6 — Alternative Scenarios

```python
st.subheader("Strategic Alternatives")
st.caption("Top-performing and worst-performing scenario variants ranked by impact on trial rate.")

col_top, col_worst = st.columns([2, 1])

with col_top:
    st.markdown("**Best alternatives:**")
    for alt in report.top_alternatives[:10]:
        delta_str = f"+{alt.delta_vs_primary:.1%}" if alt.delta_vs_primary > 0 else f"{alt.delta_vs_primary:.1%}"
        with st.expander(f"#{alt.rank} {alt.variant_id} ({delta_str})"):
            st.markdown(alt.business_rationale)
            st.caption(f"Adoption rate: {alt.adoption_rate:.1%}")

with col_worst:
    st.markdown("**Worst alternatives:**")
    for alt in report.worst_alternatives:
        delta_str = f"{alt.delta_vs_primary:.1%}"
        st.markdown(f"- {alt.variant_id}: {delta_str}")
```

#### Section 7 — Export

```python
st.divider()
export_cols = st.columns(2)
with export_cols[0]:
    st.download_button(
        "Download Report (JSON)",
        data=report.model_dump_json(indent=2),
        file_name=f"{report.scenario_id}_research_report.json",
        mime="application/json",
    )
```

### Reference Files
- `app/pages/3_results.py` — current dashboard (copy to `3_results_legacy.py`, then overwrite)
- `src/analysis/research_consolidator.py` — `ConsolidatedReport`, `consolidate_research()` (Sprint 14, Codex)
- `src/utils/viz.py` — `create_funnel_chart()`, chart builders
- `src/utils/display.py` — `display_name()`
- `src/simulation/research_runner.py` — `ResearchResult` model

### Dependencies
- **Depends on Codex Sprint 14** delivering `src/analysis/research_consolidator.py` first

### Deliverables
1. `app/pages/3_results_legacy.py` — copy of old `3_results.py`
2. `app/pages/3_results.py` — new Research Results page with all 7 sections
3. Must render without errors when `research_result` is in session state
4. Must also render a useful fallback when only `scenario_results` exists (backward compat)

### Do NOT
- Delete old pages (Sprint 15 cleanup)
- Modify source modules
- Add new dependencies
