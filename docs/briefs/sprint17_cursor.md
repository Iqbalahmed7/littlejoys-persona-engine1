# Sprint 17 Brief — Cursor (Auto)
## Wire Event Engine into Research Pipeline + Update Results Page

### Context

Sprint 17 introduces a day-level event-driven simulation (Codex: `event_engine.py`, Goose: `event_grammar.py`). Your job is to integrate the new engine into the research pipeline and update the Results page to show day-level insights.

### Dependency
Wait for Codex and Goose to deliver:
- `src/simulation/event_engine.py` — `run_event_simulation()` returning `EventSimulationResult`
- `src/simulation/event_grammar.py` — Event types and firing rules
- `src/simulation/state_model.py` — `CanonicalState`, `initialize_state()`

### Task 1: Wire into ResearchRunner (`src/simulation/research_runner.py`)

Add a new execution path alongside the existing temporal simulation:

```python
# In ResearchRunner.run():
if scenario.mode == "temporal":
    # Run new event engine (day-level) as PRIMARY
    event_result = run_event_simulation(
        population, scenario,
        duration_days=scenario.months * 30,
        seed=self.seed,
        progress_callback=...
    )
    # Store in ResearchResult
    result.event_result = event_result

    # Also keep the existing monthly temporal for backward compat
    temporal_primary = run_temporal_simulation(population, scenario, seed=self.seed)
    result.temporal_result = temporal_primary
```

Add `event_result: EventSimulationResult | None = None` to `ResearchResult`.

For alternative scenario runs: run the event simulation on the top 5 alternatives (day-level is slower — fewer alts). Add `event_active_rate: float | None = None` to `AlternativeRunSummary`.

### Task 2: Extend ConsolidatedReport (`src/analysis/research_consolidator.py`)

When `event_result` is available, add:
- `event_monthly_rollup: list[dict] | None` — monthly aggregates from day-level data
- `event_clusters: list[dict] | None` — behavioural clusters from day-level trajectories (use existing `cluster_trajectories` adapted to day data, or create monthly rollups and pass to existing clustering)
- `peak_churn_day: int | None` — which day has highest churn count
- `decision_rationale_summary: list[dict] | None` — aggregate of top decision drivers across all personas (from `DaySnapshot.decision_rationale`)

### Task 3: Update Results Page (`app/pages/3_results.py`)

When event-level data is available, enhance the temporal sections:

**a. Replace trajectory chart with day-level version** (when event data exists):
- X-axis: Days (1-360) grouped by month
- Y-axis: Same 3 lines (active, new, churned) but at day resolution
- Add a toggle: "Show daily / Show monthly" using `st.radio`

**b. Add "Event Timeline" section** (new, after behavioural segments):
- For a selected persona from the browser, show a mini event timeline
- Plotly scatter/strip chart: days on x-axis, event types on y-axis, intensity as marker size
- Include decision points as diamond markers
- Let user select persona via `st.selectbox` from the smart sample

**c. Add "Decision Drivers" section** (new):
- Horizontal bar chart: top 10 state variables by frequency as dominant driver across all decisions
- Shows: "child_acceptance was the dominant factor in 35% of churn decisions"
- Only render when `decision_rationale_summary` is available

### Files to Modify
- `src/simulation/research_runner.py`
- `src/analysis/research_consolidator.py`
- `app/pages/3_results.py`

### Constraints
- Maintain full backward compat: if `event_result` is None, all existing behaviour unchanged
- Use unique chart keys: `key="event_trajectory"`, `key="event_timeline"`, `key="decision_drivers"`
- All charts: `height=300`, compact margins
- Run `uv run ruff check .` and `uv run pytest tests/ -x -q` before delivery
