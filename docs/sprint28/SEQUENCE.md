# Sprint 28 — Execution Sequence

## Timeline

```
DAY 1 MORNING — Fire simultaneously (4 agents):

  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
  │    CURSOR    │  │    CODEX     │  │    GOOSE     │  │       OPENCODE       │
  │  CURSOR.md   │  │  CODEX.md   │  │  GOOSE.md    │  │     OPENCODE.md      │
  │  4-6 hours   │  │  4-5 hours  │  │  5-7 hours   │  │  Part 1 immediately  │
  │              │  │             │  │              │  │  Parts 2-3 gated     │
  └──────┬───────┘  └──────┬──────┘  └──────┬───────┘  └──────────┬───────────┘
         │                 │                 │                     │
         │                 │                 │  ──── Part 1 ────►  │ (writes __init__.py)
         │                 │                 │                     │
         │                 │                 │  Goose done ──────► │ Part 2: validate_personas.py
         │                 │                 │                     │
         └─────────────────┴─────────────────┘
                           │
                Cursor + Codex done ──────────► OpenCode Part 3: run_perception_sample.py
                           │
                  All three (Cursor/Codex/Goose) signal DONE
                           │
                 ┌─────────▼──────────┐
                 │     ANTIGRAVITY    │
                 │   ANTIGRAVITY.md   │
                 │    3-4 hours       │
                 └────────────────────┘
```

## Dependency Graph

| Agent | Depends On | Blocks |
|---|---|---|
| Cursor | nothing | Codex (memory interface), Antigravity, OpenCode Part 3 |
| Codex | nothing (stubs against Cursor's interface) | Antigravity, OpenCode Part 3 |
| Goose | nothing | Antigravity, OpenCode Part 2 |
| OpenCode | Part 1: nothing / Part 2: Goose / Part 3: Cursor + Codex | Antigravity (exports) |
| Antigravity | Cursor + Codex + Goose + OpenCode Part 1 all done | Sprint 28 close |

## Files Owned Per Agent

| Agent | Creates | Modifies |
|---|---|---|
| Cursor | `src/agents/embedding_cache.py` | `src/agents/memory.py` |
| Codex | `src/agents/perception_result.py` | `src/agents/agent.py` (perceive + update_memory only) |
| Goose | `src/agents/constraint_checker.py`, `src/agents/decision_result.py` | `src/agents/agent.py` (decide only) |
| OpenCode | `scripts/validate_personas.py`, `scripts/run_perception_sample.py` | `src/agents/__init__.py` |
| Antigravity | `tests/test_memory.py`, `tests/test_agent.py`, `tests/test_constraint_checker.py`, `tests/conftest.py` | nothing |

## Sprint 28 — Definition of Done

All must be true before sprint closes:

- [ ] `grep -r "NotImplementedError" src/agents/` returns zero results
- [ ] `python -c "from src.agents.memory import MemoryManager"` exits 0
- [ ] `python -c "from src.agents.agent import CognitiveAgent"` exits 0
- [ ] `python -c "from src.agents.constraint_checker import ConstraintChecker"` exits 0
- [ ] `pytest tests/` exits 0 (all tests pass, no real API calls)
- [ ] `ConstraintChecker` has exactly 30 rules
- [ ] All 4 known violations (R001-R004 from population_meta.json) fire correctly

## Coordination Note for Codex

Tell Codex: `MemoryManager` is being written in parallel by Cursor.
Your `perceive()` calls `self.memory.add_episodic()` and `self.memory.update_brand_memory()`.
Do NOT implement these methods yourself — just call them.
In `__init__` write: `self.memory = MemoryManager(persona)` and it will resolve when Cursor lands.

## Coordination Note for Goose

Tell Goose: Read `agent.py` as Codex left it. Your only job in `agent.py` is replacing the
single `decide()` stub. Do NOT touch `perceive()`, `update_memory()`, `__init__`, or `_llm_call`.
Put `DecisionResult` in its own file: `src/agents/decision_result.py`.
