# Sprint 30 — Execution Sequence

## Goal
Multi-tick simulation: model a 60-day brand journey for all 200 personas.

Answers two LittleJoys business problems directly:
- **Problem 1:** Why don't Nutrimix buyers reorder? (post-purchase journey)
- **Problem 3:** How many touchpoints does it take to sell Magnesium Gummies? (new category journey)

## What Gets Built

| Component | Engineer | File |
|---|---|---|
| `TickEngine` — schedules stimuli across time, fires perceive/reflect/decide at the right ticks | Cursor | `src/simulation/tick_engine.py` |
| `JourneyResult` dataclass + `run_journey_batch.py` — runs 60-day journey across all 200 personas | Codex | `src/simulation/journey_result.py` + `scripts/run_journey_batch.py` |
| `scripts/analyse_journey_results.py` — reads output, produces insight tables | Goose | `scripts/analyse_journey_results.py` |
| Streamlit Page 3: Journey Timeline — brand trust over time, reflection moments, decision points | OpenCode | `app/streamlit_app.py` (modify) |
| `tests/test_tick_engine.py` + `tests/test_journey_result.py` | Antigravity | `tests/test_tick_engine.py`, `tests/test_journey_result.py` |

## Fire Order

```
DAY 1 MORNING — Parallel:
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │   CURSOR    │  │    CODEX    │  │    GOOSE    │
  │ TickEngine  │  │ JourneyRes. │  │  analyse_   │
  │             │  │ + batch     │  │  journey    │
  │ 5-6 hours   │  │ 4-5 hours   │  │ 3-4 hours   │
  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
         └────────────────┴─────────────────┘
                          │ all three done
         ┌────────────────┴─────────────────┐
         │                                  │
  ┌──────▼──────┐                   ┌───────▼──────┐
  │  OPENCODE   │                   │  ANTIGRAVITY │
  │  Streamlit  │                   │    Tests     │
  │  Page 3     │                   │  4-5 hours   │
  │  4-5 hours  │                   └──────────────┘
  └─────────────┘
```

## Dependency Rules

| Engineer | Depends On | Blocks |
|---|---|---|
| Cursor | nothing | Codex (uses TickEngine), Antigravity |
| Codex | Cursor (TickEngine interface) | Antigravity, OpenCode |
| Goose | nothing (reads JSON output format) | Antigravity |
| OpenCode | Codex (JourneyResult structure) | Sprint close |
| Antigravity | All three parallel wave done | Sprint close |

## File Ownership

| Engineer | Creates | Modifies |
|---|---|---|
| Cursor | `src/simulation/__init__.py`, `src/simulation/tick_engine.py` | nothing |
| Codex | `src/simulation/journey_result.py`, `scripts/run_journey_batch.py` | nothing |
| Goose | `scripts/analyse_journey_results.py` | nothing |
| OpenCode | nothing | `app/streamlit_app.py` (add Page 3 only) |
| Antigravity | `tests/test_tick_engine.py`, `tests/test_journey_result.py` | nothing |

## Verified Field Names (from schema.py — do not deviate)

```python
persona.id                              # string
persona.display_name                    # may be None → fallback to persona.id
persona.episodic_memory                 # list[MemoryEntry]
persona.brand_memories                  # dict[str, BrandMemory]
persona.brand_memories[brand].trust_level       # float 0.0-1.0
persona.brand_memories[brand].purchase_count    # int
persona.brand_memories[brand].satisfaction_history  # list[float]
persona.parent_traits                   # may be None — always null-check
persona.parent_traits.decision_style    # only after null-check
persona.budget_profile                  # may be None — always null-check
persona.budget_profile.price_sensitivity # only after null-check
```

## The Two Journey Scenarios

Both are defined in `src/simulation/tick_engine.py` as constants.

### Journey A — Nutrimix Repeat Purchase (60 days)
Simulates the full post-purchase lifecycle. Goal: find when and why reorder happens (or doesn't).

### Journey B — Magnesium Gummies Acquisition (45 days)
Simulates category creation from zero awareness. Goal: find minimum touchpoints to first purchase.

Full stimulus schedules in CURSOR.md.

## Definition of Done

- [ ] `TickEngine` runs a 60-day journey for a single persona without error
- [ ] `run_journey_batch.py --journey A --max 5` completes with 0 errors
- [ ] Output JSON contains per-tick brand trust snapshots
- [ ] Both journeys (A and B) implemented
- [ ] `analyse_journey_results.py` prints reorder rate + avg conversion tick
- [ ] Streamlit Page 3 shows brand trust timeline chart
- [ ] 15+ tests, all passing
- [ ] `pytest tests/` exits 0
