# Sprint 17 Brief — OpenCode (GPT-5.4 Nano)
## Research Design Page: Event Simulation Controls

### Context

Sprint 17 adds a day-level event-driven simulation. The Research Design page needs minor updates to communicate this to the PM.

### Task 1: Update Simulation Mode Indicator (`app/pages/2_research.py`)

Change the temporal mode indicator text to reflect the new engine:

**Before** (Sprint 16):
```python
st.info("📊 Temporal mode — This scenario simulates 12 months of repeat purchase, churn, and word-of-mouth dynamics.")
```

**After**:
```python
st.info("📊 Event simulation — This scenario models day-by-day behaviour over 12 months: product events, child reactions, competitive pressures, and purchase decisions.")
```

### Task 2: Update Run Button Progress Labels

In the progress callback section, if the scenario is temporal, update the progress step labels to reflect the event engine:

- 0-10%: "Running decision funnel..."
- 10-20%: "Selecting interview sample..."
- 20-50%: "Running day-by-day event simulation..." (was "Running temporal simulation...")
- 50-70%: "Conducting persona interviews..."
- 70-90%: "Testing alternative strategies..."
- 90-100%: "Consolidating results..."

Find where the progress labels are set and update the text for the temporal simulation step.

### Task 3: Add Duration Display

After the simulation mode indicator, show the simulation duration:

```python
if scenario.mode == "temporal":
    duration_days = scenario.months * 30
    st.caption(f"Simulation duration: {duration_days} days ({scenario.months} months) · 200 personas · Day-level events")
```

### Files to Modify
- `app/pages/2_research.py`

### Constraints
- UI text changes only — do NOT modify any backend logic
- All existing tests must pass: `uv run pytest tests/ -x -q`
- Run `uv run ruff check .` before delivery
