# Sprint 16 Brief — Antigravity (Gemini 3 Flash)
## Tests for Temporal Pipeline + Trajectory Clustering

### Context
Sprint 16 adds temporal simulation to the research pipeline, trajectory clustering, and updated UI. Write comprehensive tests for all new functionality.

### Dependency
Wait for Codex's backend delivery before writing tests. You'll need:
- `PersonaTrajectory` and `MonthState` from `src/simulation/temporal.py`
- `extract_persona_trajectories()` from `src/simulation/temporal.py`
- `TrajectoryClusterResult` and `BehaviourCluster` from `src/analysis/trajectory_clustering.py`
- Updated `ResearchResult` with `temporal_result` field from `src/simulation/research_runner.py`
- Updated `ConsolidatedReport` with temporal fields from `src/analysis/research_consolidator.py`

### Task 1: NEW FILE `tests/unit/test_trajectory_clustering.py`

Tests:
- `test_clustering_produces_clusters` — clustering returns 4-6 clusters from a temporal simulation on nutrimix_2_6
- `test_all_personas_assigned` — every persona_id appears in exactly one cluster
- `test_cluster_sizes_sum` — cluster sizes sum to population size
- `test_loyal_vs_fatigued_lifetime` — "Loyal Repeaters" cluster has higher `avg_lifetime_months` than any churn cluster
- `test_zero_adopters_edge_case` — if no personas adopt (extreme thresholds), only "Never Reached" cluster exists
- `test_cluster_dominant_attributes` — each cluster has at least 1 entry in `dominant_attributes`

Use fixtures similar to `tests/unit/test_research_consolidator.py`. Generate population from seed=42.

### Task 2: NEW FILE `tests/unit/test_temporal_trajectories.py`

Tests:
- `test_trajectory_count_matches_population` — `extract_persona_trajectories()` returns one trajectory per persona
- `test_trajectory_months_match` — each trajectory has exactly `months` monthly states
- `test_adopted_persona_active` — personas that adopted have `is_active=True` at some point in their trajectory
- `test_churned_flag_set` — churned personas have `churned_this_month=True` exactly once
- `test_determinism` — same seed produces identical trajectories (run twice, compare)
- `test_non_adopter_always_inactive` — personas that never adopted have `is_active=False` for all months

### Task 3: NEW FILE `tests/integration/test_temporal_pipeline.py`

Tests:
- `test_temporal_research_pipeline` — `ResearchRunner.run()` on `nutrimix_2_6` (temporal mode) produces a `ResearchResult` with `temporal_result is not None`
- `test_temporal_snapshots_count` — `temporal_result.monthly_snapshots` has 12 entries
- `test_consolidation_includes_temporal` — consolidation produces `temporal_snapshots` and `behaviour_clusters` that are not None
- `test_alternatives_have_temporal_rate` — at least some alternatives have `temporal_active_rate` not None
- `test_peak_churn_month_valid` — `peak_churn_month` is between 1 and 12

Use `scope="module"` fixtures for efficiency (same as `tests/integration/test_research_pipeline.py`).

### Task 4: UPDATE `tests/unit/test_page_imports.py`

- Verify all modified pages (`2_research.py`, `3_results.py`) still parse with `ast.parse`
- Add import check for new module: `from src.analysis.trajectory_clustering import TrajectoryClusterResult`

### Task 5: Run Full Suite

Run `uv run pytest tests/ -x -q` and report results. All tests (existing + new) must pass.

### Files to Create
- `tests/unit/test_trajectory_clustering.py`
- `tests/unit/test_temporal_trajectories.py`
- `tests/integration/test_temporal_pipeline.py`

### Files to Modify
- `tests/unit/test_page_imports.py`

### Constraints
- All tests must run in mock mode (no API key needed)
- Use `seed=42` for determinism
- Use `pytest.approx()` for float comparisons
- Run `uv run ruff check .` before delivery
