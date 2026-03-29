# Sprint 16 Brief — Codex (GPT 5.3 Medium)
## Wire Temporal Simulation into Research Pipeline

### Context
`ResearchRunner.run()` currently only calls `run_static_simulation()`. The temporal simulation in `temporal.py` already models month-by-month repeat purchase, churn, WOM, and LJ Pass — but it's disconnected from the research pipeline. Your job is to connect them and add trajectory-level analysis.

### Task 1: Extend `ResearchRunner.run()` (`src/simulation/research_runner.py`)

- After running the primary static funnel, check `scenario.mode`. If `"temporal"`, also run `run_temporal_simulation()` from `src/simulation/temporal.py`.
- Store the `TemporalSimulationResult` in `ResearchResult` as a new field `temporal_result: TemporalSimulationResult | None = None`.
- Update `ResearchResult` model in the same file to include this field.

### Task 2: Add Trajectory Export (`src/simulation/temporal.py`)

Create a new function:
```python
def extract_persona_trajectories(
    population: Population,
    scenario: ScenarioConfig,
    months: int = 12,
    seed: int = 42,
) -> list[PersonaTrajectory]:
```

Returns per-persona month-by-month state:
- `persona_id, month, is_active, satisfaction, consecutive_months, has_lj_pass, churned_this_month, adopted_this_month`

Create `PersonaTrajectory` as a Pydantic model:
```python
class MonthState(BaseModel):
    month: int
    is_active: bool
    satisfaction: float
    consecutive_months: int
    has_lj_pass: bool
    churned_this_month: bool
    adopted_this_month: bool

class PersonaTrajectory(BaseModel):
    persona_id: str
    monthly_states: list[MonthState]
```

This function should reuse the internal `_PersonaTemporalState` tracking from `run_temporal_simulation()` but expose per-persona data (currently only aggregate snapshots are returned).

### Task 3: Wire Temporal into Alternative Runs

In `ResearchRunner`, when generating alternative scenario variants:
- If `scenario.mode == "temporal"`, run `run_temporal_simulation()` for the **top 10 alternatives only** (ranked by static adoption rate). Not all 50 — too slow.
- Add `temporal_adoption_rate: float | None = None` and `temporal_active_rate: float | None = None` to `AlternativeRunSummary`.
- Rank alternatives by `temporal_active_rate` (month-12 active customers) rather than static adoption rate when temporal data is available.

### Task 4: Add Behavioural Clustering — NEW FILE `src/analysis/trajectory_clustering.py`

Input: list of `PersonaTrajectory` + population.

Cluster personas into 4-6 behavioural segments based on trajectory shape:
- **"Loyal Repeaters"** — adopted early (month 1-2), never churned, high satisfaction throughout
- **"Late Adopters"** — adopted month 3+ via WOM, moderate retention
- **"Taste-Fatigued Droppers"** — adopted, satisfaction declined, churned month 2-4
- **"Price-Triggered Switchers"** — adopted, churned when satisfaction dipped + high budget_consciousness
- **"Forgot-to-Reorder"** — adopted, low consecutive_months, sporadic repurchase
- **"Never Reached"** — never adopted (further split by rejection stage from static funnel)

Output model:
```python
class BehaviourCluster(BaseModel):
    cluster_name: str
    persona_ids: list[str]
    size: int
    pct: float  # fraction of total population
    avg_lifetime_months: float
    avg_satisfaction: float
    dominant_attributes: dict[str, float]  # top 5 persona attributes that distinguish this cluster

class TrajectoryClusterResult(BaseModel):
    clusters: list[BehaviourCluster]
    population_size: int
```

Use simple heuristic rules (not ML) based on trajectory patterns: `churned_month`, `max_consecutive`, satisfaction trend slope, adoption month.

### Task 5: Extend `consolidate_research()` (`src/analysis/research_consolidator.py`)

If `research_result.temporal_result` is not None, add to `ConsolidatedReport`:
- `temporal_snapshots: list[dict] | None = None` — month, new_adopters, repeat, churned, active, awareness
- `behaviour_clusters: list[dict] | None = None` — cluster_name, size, pct, avg_lifetime, key_traits
- `month_12_active_rate: float | None = None`
- `peak_churn_month: int | None = None` — which month has highest churn
- `revenue_estimate: float | None = None`

Call `extract_persona_trajectories()` and `cluster_trajectories()` inside `consolidate_research()` when temporal data is available.

### Files to Modify
- `src/simulation/research_runner.py`
- `src/simulation/temporal.py`
- `src/analysis/research_consolidator.py`

### Files to Create
- `src/analysis/trajectory_clustering.py`

### Constraints
- All existing tests must pass (`uv run pytest tests/ -x -q`)
- Add type hints to all new code
- Use Pydantic `BaseModel` for all new data structures
- Import from existing modules — do not duplicate logic
- Run `uv run ruff check .` before delivery
