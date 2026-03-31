# Sprint 24 Brief — Codex
## S4-02: Phase 1 Dynamic Simulation Narrative + Cohort Deep-Dive Dashboard

> **Engineer**: Codex (GPT 5.3 High Reasoning → escalate to GPT 5.4 Extra High if monthly data extraction is complex)
> **Sprint**: 24
> **Ticket**: S4-02
> **Estimated effort**: Medium
> **Reference**: LittleJoys User Flow Document v2.0, Sections 4.3, 4.4, 4.5, 4.6

---

### Context

Phase 1 (`app/pages/2_problem.py`) runs a 12-month simulation but the narrative progress messages are hardcoded static strings defined before the simulation runs. The v2.0 spec requires the monthly updates to reflect **actual simulation output** — real persona counts, real churn signals, real WOM propagation numbers.

Additionally, after the simulation, the cohort dashboard only shows metric tiles. The spec requires:
- A cohort distribution bar chart
- A funnel visualization (Awareness → Trial → Repeat)
- Per-cohort summary cards with behavioral detail

There is also a remaining bug in cohort classification: `current_user` should require **2+ purchases AND still active**, not just `is_active=True`. A persona with 1 purchase who is still active should be `first_time_buyer`.

---

### Task 1: Fix `current_user` Cohort Definition

File: `src/analysis/cohort_classifier.py`

The current classifier (lines 126-139) assigns `current_user` whenever `final_snapshot.is_active is True`. This is wrong for personas who made exactly 1 purchase and are technically still active but have not repeated.

**Change the current_user block to:**
```python
for trajectory in event_result.trajectories:
    final_snapshot = trajectory.days[-1] if trajectory.days else None
    total_purchases = trajectory.total_purchases or 0
    is_active = final_snapshot and final_snapshot.is_active

    if is_active and total_purchases >= 2:
        # Genuinely active repeat buyer
        cohort_id = "current_user"
        reason = f"Active repeat buyer ({total_purchases} purchases, still active at end)"
    elif is_active and total_purchases <= 1:
        # Active but never repeated — counts as first-time buyer
        cohort_id = "first_time_buyer"
        reason = f"One-time buyer (1 purchase, technically active but never repeated)"
    else:
        # Already churned — use purchase count (not churn timing) for classification
        # Note: churn-based logic already updated in previous sprint; keep it.
        total_purchases_for_lapse = trajectory.total_purchases or 1
        cohort_id = "first_time_buyer" if total_purchases_for_lapse <= 1 else "lapsed_user"
        churn_day = trajectory.churned_day or duration_days
        churn_month = max(1, ceil(churn_day / 30))
        purchase_label = f"{total_purchases_for_lapse} purchase{'s' if total_purchases_for_lapse != 1 else ''}"
        reason = (
            f"{'One-time buyer' if cohort_id == 'first_time_buyer' else 'Repeat buyer'} "
            f"({purchase_label}), churned in month {churn_month}"
        )

    cohorts[cohort_id].append(trajectory.persona_id)
    population.get_persona(trajectory.persona_id).product_relationship = cohort_id
    classifications.append(CohortClassification(
        persona_id=trajectory.persona_id,
        cohort_id=cohort_id,
        cohort_name=_COHORT_NAMES[cohort_id],
        classification_reason=reason,
    ))
```

This replaces the entire block from `for trajectory in event_result.trajectories:` through the `classifications.append(...)` call. Do not change anything else in the file.

---

### Task 2: Dynamic Monthly Simulation Narrative

File: `app/pages/2_problem.py`

**Current problem**: `_MONTH_NARRATIVES` is a static dict with hardcoded strings. The `_run_simulation_with_narrative()` function shows these strings BEFORE the simulation runs, so they can't contain real data.

**Fix**: Run the simulation first, then replay the narrative using the actual `temporal_result.aggregate_monthly` data.

`temporal_result` from `run_temporal_simulation()` returns an `EventSimulationResult` with `aggregate_monthly: list[dict]`. Each dict has keys: `month`, `new_adopters`, `cumulative_adopters`, `repeat_purchasers`, `churned`, `active_count`.

**Replace `_run_simulation_with_narrative()` with:**

```python
def _run_simulation_with_narrative(pop: Population, scenario_id: str) -> tuple[Any, Any]:
    scenario = get_scenario(scenario_id)
    n = len(pop.personas)

    with st.status("Running 12-month baseline simulation...", expanded=True) as status:
        st.write(f"⚙️ Introducing product to {n} personas via their most likely discovery channels...")
        temporal_result = run_temporal_simulation(pop, scenario, months=12, seed=DEFAULT_SEED)

        st.write("⚙️ Classifying behavioral cohorts...")
        cohorts = classify_population(pop, scenario, seed=DEFAULT_SEED)

        # Replay narrative from actual monthly data
        monthly = temporal_result.aggregate_monthly or []
        checkpoints = {3, 6, 9, 12}
        for month_data in monthly:
            m = month_data.get("month", 0)
            if m in checkpoints:
                cumulative = month_data.get("cumulative_adopters", 0)
                churned = month_data.get("churned", 0)
                active = month_data.get("active_count", 0)
                repeat = month_data.get("repeat_purchasers", 0)
                if m == 3:
                    st.write(f"Month 3: {cumulative} personas have now tried the product. First churn signals emerging ({churned} drop-offs so far).")
                elif m == 6:
                    st.write(f"Month 6: Trial rate reaching {round(cumulative/n*100)}%. {repeat} personas repeated this month. {active} still active.")
                elif m == 9:
                    st.write(f"Month 9: Habit patterns solidifying. {active} active buyers. {churned} cumulative lapsed.")
                elif m == 12:
                    st.write(f"Month 12: Simulation complete. {cumulative} total adopters across {n} personas.")

        status.update(
            label=f"✅ Simulation complete — {n} personas × 365 days",
            state="complete",
            expanded=False,
        )

    return temporal_result, cohorts
```

If `aggregate_monthly` is empty or None, fall back gracefully with a single message: `"Simulation complete — cohorts formed from behavioral trajectories."`. Do not crash.

---

### Task 3: Cohort Distribution Bar Chart

File: `app/pages/2_problem.py`

**Location**: After the 5 cohort metric tiles and before the 4-column KPI row.

Add a horizontal bar chart showing cohort counts:

```python
import plotly.graph_objects as go

_cohort_order = ["current_user", "lapsed_user", "first_time_buyer", "aware_not_tried", "never_aware"]
_cohort_display = {
    "current_user": "Current User ⭐",
    "lapsed_user": "Lapsed User 💤",
    "first_time_buyer": "First-Time Buyer 🛒",
    "aware_not_tried": "Aware, Not Tried 👁️",
    "never_aware": "Never Aware 🔇",
}
_cohort_colors = {
    "current_user": "#2ECC71",
    "lapsed_user": "#E67E22",
    "first_time_buyer": "#3498DB",
    "aware_not_tried": "#9B59B6",
    "never_aware": "#95A5A6",
}

bar_y = [_cohort_display[c] for c in _cohort_order]
bar_x = [cohorts.summary.get(c, 0) for c in _cohort_order]
bar_colors = [_cohort_colors[c] for c in _cohort_order]

fig_cohorts = go.Figure(go.Bar(
    x=bar_x,
    y=bar_y,
    orientation="h",
    marker_color=bar_colors,
    text=[f"{v} personas ({round(v/max(sum(bar_x),1)*100)}%)" for v in bar_x],
    textposition="outside",
))
fig_cohorts.update_layout(
    title="How 200 households moved through the product journey",
    xaxis_title="Number of Personas",
    plot_bgcolor="#FAFAFA",
    paper_bgcolor="#FFFFFF",
    margin=dict(l=10, r=80, t=40, b=10),
    height=280,
)
st.plotly_chart(fig_cohorts, use_container_width=True)
```

---

### Task 4: Funnel Visualization

File: `app/pages/2_problem.py`

**Location**: After the bar chart.

Add a funnel showing the product journey stages:

```python
_total = sum(cohorts.summary.values()) or 1
_aware = _total - cohorts.summary.get("never_aware", 0)
_tried = cohorts.summary.get("first_time_buyer", 0) + cohorts.summary.get("current_user", 0) + cohorts.summary.get("lapsed_user", 0)
_repeated = cohorts.summary.get("current_user", 0) + cohorts.summary.get("lapsed_user", 0)
_active = cohorts.summary.get("current_user", 0)

fig_funnel = go.Figure(go.Funnel(
    y=["Became Aware", "Tried Product", "Repeated Purchase", "Still Active"],
    x=[_aware, _tried, _repeated, _active],
    textinfo="value+percent initial",
    marker_color=["#3498DB", "#2ECC71", "#27AE60", "#1A8A50"],
))
fig_funnel.update_layout(
    title="Purchase Journey Funnel",
    margin=dict(l=10, r=10, t=40, b=10),
    height=300,
)
st.plotly_chart(fig_funnel, use_container_width=True)
```

---

### Task 5: Per-Cohort Summary Cards

File: `app/pages/2_problem.py`

**Location**: Below the funnel, before the `st.success()` phase-complete banner.

For each of the 5 cohorts, add a collapsible `st.expander` showing behavioral summary:

```python
st.subheader("Cohort Profiles")
st.caption("Click any cohort to see the behavioral patterns behind the numbers.")

for cid, (label, icon, desc) in cohort_display.items():
    count = cohorts.summary.get(cid, 0)
    if count == 0:
        continue
    with st.expander(f"{icon} {label} — {count} personas", expanded=False):
        st.caption(desc)

        # List 2 representative persona names from this cohort
        persona_ids = cohorts.cohorts.get(cid, [])[:2]
        if persona_ids:
            st.markdown("**Representative personas:**")
            for pid in persona_ids:
                try:
                    p = pop.get_persona(pid)
                    st.caption(f"• {p.name}, {p.demographics.city_tier} — {p.narrative[:80] if p.narrative else 'No narrative'}…")
                except Exception:
                    st.caption(f"• Persona {pid[:8]}…")

        # Cohort-specific behavioral hint
        hints = {
            "never_aware": "These personas never encountered the product through any channel. Brand salience and distribution reach are the levers to address here.",
            "aware_not_tried": "These personas know the product exists but didn't convert. Price, trust, and perceived need are the likely barriers.",
            "first_time_buyer": "These personas tried once but didn't come back. Something broke between the first experience and the reorder decision.",
            "current_user": "These are your most valuable personas — they've formed a habit. Understanding what made them stick tells you how to scale.",
            "lapsed_user": "These personas were active buyers who stopped. Identifying their exit signal is the key to retention strategy.",
        }
        st.info(hints.get(cid, ""), icon="💡")
```

---

### Acceptance Criteria

- [ ] `current_user` cohort correctly requires 2+ purchases AND active (not just is_active=True)
- [ ] Monthly narrative messages reflect actual simulation data (not hardcoded strings)
- [ ] Narrative doesn't crash if `aggregate_monthly` is empty — graceful fallback
- [ ] Cohort bar chart renders with correct counts matching the metric tiles
- [ ] Funnel shows correct stage values (Aware ≥ Tried ≥ Repeated ≥ Active)
- [ ] Per-cohort expanders show representative personas without crashing on missing data
- [ ] All changes backward-compatible — existing tests still pass

---

### Files to Modify

| File | Change |
|------|--------|
| `src/analysis/cohort_classifier.py` | Fix current_user to require 2+ purchases |
| `app/pages/2_problem.py` | Dynamic narrative, bar chart, funnel, per-cohort expanders |

### Files NOT to Modify

`src/simulation/event_engine.py`, `src/simulation/temporal.py`, `src/decision/scenarios.py` — leave engine untouched.

---

### Escalation Rule

If `temporal_result.aggregate_monthly` doesn't exist or has different key names than expected, first run `print(vars(temporal_result))` in a debug expander to inspect the actual structure. Do not guess field names.
