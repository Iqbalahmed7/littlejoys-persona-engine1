# Sprint 31 — Execution Sequence

## Goal
Client self-service simulation: LittleJoys team tweaks product/marketing, presses Run, gets results.

## Wave 1 — Foundation (fire first, must complete before Wave 2)
- **CURSOR** → `journey_config.py` + `journey_presets.py` + refactor `tick_engine.py`

## Wave 2 — Parallel (fire after CURSOR signals done)
- **CODEX** → `batch_runner.py` + refactor `run_journey_batch.py`
- **GOOSE** → `journey_comparison.py`

## Wave 3 — Final (fire after CODEX signals done)
- **OPENCODE** → Streamlit Simulation Builder page
- **ANTIGRAVITY** → tests for JourneyConfig + BatchRunner

## Deliverable check (Claude's job after each agent)
| Agent | File | Check |
|---|---|---|
| CURSOR | `src/simulation/journey_config.py` | Verification block passes |
| CURSOR | `src/simulation/journey_presets.py` | PRESET_JOURNEY_A.to_journey_spec().total_ticks == 61 |
| CODEX | `src/simulation/batch_runner.py` | Import check + BatchResult.to_dict() has required keys |
| CODEX | `scripts/run_journey_batch.py` | CLI: `--max 1` run completes without error |
| GOOSE | `scripts/journey_comparison.py` | `--self-verify` passes all checks |
| OPENCODE | `app/streamlit_app.py` | Syntax OK + 4 nav pages visible |
| ANTIGRAVITY | `tests/test_journey_config.py` | 12/12 pass |
| ANTIGRAVITY | `tests/test_batch_runner.py` | 10/10 pass |
