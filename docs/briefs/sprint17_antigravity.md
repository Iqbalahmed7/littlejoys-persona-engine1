# Sprint 17 Brief — Antigravity (Gemini 3.1 Pro — Upgrade for this sprint)
## Tests for Event Engine, State Model, and Day-Level Pipeline

### Context

Sprint 17 introduces 3 new modules: `state_model.py` (Codex), `event_grammar.py` (Goose), `event_engine.py` (Codex). You need comprehensive tests for all of them, plus integration tests for the full day-level pipeline.

### Dependency
Wait for ALL other engineers to deliver before writing tests. You'll need:
- `CanonicalState`, `initialize_state()`, `derive_thresholds()` from `src/simulation/state_model.py`
- `SimulationEvent`, `fire_deterministic_events()`, `fire_stochastic_events()`, `apply_event_impact()`, `is_decision_point()` from `src/simulation/event_grammar.py`
- `run_event_simulation()`, `EventSimulationResult`, `PersonaDayTrajectory`, `DaySnapshot` from `src/simulation/event_engine.py`
- Updated `ResearchResult` with `event_result` field from `src/simulation/research_runner.py`

### Task 1: NEW FILE `tests/unit/test_state_model.py`

Tests:
- `test_initialize_state_all_in_range` — All 10 state variables are in [0, 1] after initialization
- `test_initialize_state_deterministic` — Same persona + scenario produces identical state
- `test_derive_thresholds_range` — Thresholds are reasonable (awareness_threshold > 0, trust_threshold > 0)
- `test_apply_daily_dynamics_fatigue_grows` — Fatigue increases when active
- `test_apply_daily_dynamics_habit_decays` — Habit decreases when inactive
- `test_apply_daily_dynamics_clips` — Values stay within [0, 1] after dynamics

### Task 2: NEW FILE `tests/unit/test_event_engine.py`

Tests:
- `test_event_simulation_returns_result` — `run_event_simulation()` on nutrimix_2_6 returns `EventSimulationResult`
- `test_trajectories_match_population` — One trajectory per persona
- `test_trajectory_days_match_duration` — Each trajectory has exactly `duration_days` snapshots (or reasonable subset)
- `test_determinism` — Same seed → identical results (run twice, compare final_active_count)
- `test_decisions_are_valid` — All decisions are in {"purchase", "reorder", "churn", "switch", "delay", "subscribe", None}
- `test_pack_finished_triggers_decision` — When pack_finished fires, a decision is made
- `test_monthly_rollup_has_12_months` — `aggregate_monthly` has ~12 entries for 360-day simulation
- `test_first_purchase_requires_brand_salience` — Persona with brand_salience=0 never purchases on day 1

### Task 3: NEW FILE `tests/integration/test_event_pipeline.py`

Tests:
- `test_event_research_pipeline` — `ResearchRunner.run()` on nutrimix_2_6 produces `event_result` that is not None
- `test_consolidation_includes_event_data` — Consolidated report has `event_monthly_rollup` or `event_clusters` when event data is available
- `test_backward_compat_static` — Running a static scenario (e.g., nutrimix_7_14) still works, event_result is None

### Task 4: UPDATE `tests/unit/test_page_imports.py`

- Verify updated pages still parse with `ast.parse`
- Add import check for new modules: `state_model`, `event_engine`, `event_grammar`

### Files to Create
- `tests/unit/test_state_model.py`
- `tests/unit/test_event_engine.py`
- `tests/integration/test_event_pipeline.py`

### Files to Modify
- `tests/unit/test_page_imports.py`

### Constraints
- All tests must run in mock mode (no API key needed)
- Use `seed=42` for determinism
- Use `pytest.approx()` for float comparisons
- Use `scope="module"` fixtures for expensive operations (population generation)
- Run `uv run ruff check .` and `uv run pytest tests/ -x -q` before delivery
- Report total test count and pass rate
