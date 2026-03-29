# Sprint 16 Brief — Cursor (Claude)
## Temporal Results Page + Trajectory Visualisation

### Context
The Results page (`app/pages/3_results.py`) currently shows static funnel data only. Sprint 16 backend (Codex) wires temporal simulation into the research pipeline. You need to display temporal insights when available.

### Dependency
Codex will add these new fields to `ConsolidatedReport`:
- `temporal_snapshots: list[dict] | None` — monthly data (month, new_adopters, repeat_purchasers, churned, total_active, awareness_level_mean)
- `behaviour_clusters: list[dict] | None` — cluster_name, size, pct, avg_lifetime_months, avg_satisfaction, dominant_attributes
- `month_12_active_rate: float | None`
- `peak_churn_month: int | None`
- `revenue_estimate: float | None`

Also on `AlternativeRunSummary`:
- `temporal_active_rate: float | None`

### Task 1: Add Temporal Section to Results Page

After the existing funnel waterfall section, add a new section that **only renders when `report.temporal_snapshots` exists and is not empty**:

#### a. "Repeat Purchase Trajectory"
- Plotly line chart, months (1-12) on x-axis
- 3 lines: `total_active` (primary blue, bold), `new_adopters` (green), `churned` (red)
- Caption: "Month-by-month customer dynamics for {scenario_name}"
- `height=300`, compact margins

#### b. "Key Temporal Metrics"
4 metric columns using `st.metric()`:
- Month 12 Active Rate (with delta vs Month 1 adoption rate)
- Peak Churn Month ("Month {N}")
- Estimated Annual Revenue ("₹{X}L") — divide by 100000 for lakhs
- LJ Pass Holders (from last snapshot)

#### c. "Behavioural Segments"
If `report.behaviour_clusters` exists:
- Horizontal bar chart showing cluster sizes (sorted descending)
- Color-code: green for "Loyal Repeaters", red for churn clusters, grey for "Never Reached"
- Below the chart: one `st.expander()` per cluster containing:
  - Cluster size and percentage
  - Average lifetime (months)
  - Average satisfaction score
  - Top 3 distinguishing persona attributes with values

#### d. "Intervention Comparison"
If temporal alternative data exists (any alternative has `temporal_active_rate` not None):
- Grouped bar chart comparing top 5 alternatives on TWO metrics: static adoption rate AND month-12 active rate
- This shows the PM that some strategies with high trial have poor retention
- Sort by `temporal_active_rate` descending

### Task 2: Restructure Page Layout

New section order:
1. Overview Metrics (existing)
2. Funnel Waterfall (existing)
3. **Repeat Purchase Trajectory** (NEW — temporal, guard: only if temporal_snapshots)
4. **Behavioural Segments** (NEW — temporal, guard: only if behaviour_clusters)
5. Segment Analysis by Tier/Income (existing)
6. Key Decision Variables (existing — already renamed by OpenCode)
7. **Intervention Comparison** (NEW — replaces old alternatives table when temporal data available)
8. Interview Themes (existing)
9. Export (existing)

### Task 3: Temporal Guard

If `report.temporal_snapshots` is None or empty, skip sections 3, 4, 7 entirely and show the existing static-only layout. This maintains backward compatibility with static scenarios (magnesium_gummies, protein_mix).

### Files to Modify
- `app/pages/3_results.py`

### Constraints
- Use unique Plotly chart keys (e.g., `key="temporal_trajectory"`, `key="behaviour_clusters"`, `key="intervention_comparison"`)
- Maintain the existing `_render_legacy_dashboard()` fallback
- All charts: `height=300`, margins `dict(l=20, r=20, t=40, b=20)`
- All existing tests must pass
- Run `uv run ruff check .` before delivery
