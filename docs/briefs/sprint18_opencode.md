# Sprint 18 Brief — OpenCode (GPT-5.4 Nano)
## Retention Curve Chart + Calibration Dashboard Tab

### Context

Sprint 18 fixes the simulation (Codex), completes events (Goose), and adds the intelligence layer (Cursor). Your job is two focused UI additions.

### Task 1: Retention Curve on Results Page (`app/pages/3_results.py`)

Add a "Retention Curve" section after the existing trajectory chart. This shows what % of adopters are still active at each month — the classic SaaS/subscription retention view.

```python
if report.event_monthly_rollup:
    st.subheader("Retention Curve")
    st.caption("Of all personas who ever adopted, what fraction are still active each month?")

    monthly = report.event_monthly_rollup
    # Compute cumulative adopters and active rate at each month
    retention_data = []
    for m in monthly:
        cumulative = int(m.get("cumulative_adopters", 0))
        active = int(m.get("total_active", 0))
        retention = (active / cumulative * 100) if cumulative > 0 else 0
        retention_data.append({
            "month": int(m["month"]),
            "retention_pct": round(retention, 1),
            "active": active,
            "cumulative_adopters": cumulative,
        })

    # Line chart: retention % over months
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[r["month"] for r in retention_data],
        y=[r["retention_pct"] for r in retention_data],
        mode="lines+markers",
        name="Retention %",
        line={"color": "#2ca02c", "width": 3},
        fill="tozeroy",
        fillcolor="rgba(44, 160, 44, 0.1)",
    ))
    fig.update_layout(
        height=300,
        margin={"l": 40, "r": 20, "t": 20, "b": 40},
        xaxis_title="Month",
        yaxis_title="Retention %",
        yaxis={"range": [0, 100]},
    )
    st.plotly_chart(fig, use_container_width=True, key="retention_curve")
```

### Task 2: Simulation Health Banner (`app/pages/3_results.py`)

At the top of the results page, after the executive summary (if present) or after the header metrics, add a compact health indicator:

```python
if report.event_monthly_rollup:
    monthly = report.event_monthly_rollup
    # Extract key health metrics
    month_1 = monthly[0] if monthly else {}
    month_final = monthly[-1] if monthly else {}

    trial_rate = int(month_1.get("cumulative_adopters", 0)) / report.population_size if report.population_size else 0
    final_active = int(month_final.get("total_active", 0))
    final_active_rate = final_active / report.population_size if report.population_size else 0
    repeat_count = sum(int(m.get("repeat_purchasers", 0)) for m in monthly)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Month-1 Trial", f"{trial_rate:.0%}")
    col2.metric("Final Active", f"{final_active_rate:.0%}")
    col3.metric("Repeat Purchases", f"{repeat_count:,}")
    col4.metric("Peak Churn Month", f"Month {report.peak_churn_month or '—'}")
```

### Files to Modify
- `app/pages/3_results.py`

### Constraints
- UI-only changes — do NOT modify any backend files
- Chart key: `key="retention_curve"`
- Use existing `_CHART_HEIGHT` and `_CHART_MARGINS` constants if they're set to 300 and compact margins
- All existing tests must pass: `uv run pytest tests/ -x -q`
- Run `uv run ruff check .` before delivery
