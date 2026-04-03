# Sprint 29 — Execution Sequence

## Goal
Prove the v1 thesis: "This persona system produces more distinct, consistent,
decision-useful behaviour than naive LLM sampling."

Three pillars:
  1. Reflection Engine — personas accumulate insights across stimuli
  2. Scenario Batch + A/B Harness — measure distinctness vs naive baseline
  3. Streamlit UI — inspect any persona's full cognitive state

## Timeline

```
DAY 1 MORNING — Fire simultaneously:

  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
  │       CURSOR        │  │        CODEX         │  │        GOOSE        │
  │  CURSOR.md          │  │  CODEX.md            │  │  GOOSE.md           │
  │  ReflectionEngine   │  │  reflect() on Agent  │  │  Scenario batch     │
  │  + Tier1 constraint │  │  + A/B test harness  │  │  runner             │
  │  enforcement        │  │                      │  │                     │
  │  Est: 5-6 hours     │  │  Est: 4-5 hours      │  │  Est: 4-5 hours     │
  └──────────┬──────────┘  └──────────┬────────── ┘  └──────────┬──────────┘
             │                        │                          │
             └────────────────────────┴──────────────────────────┘
                                      │
                           All three signal DONE
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
   ┌──────────▼──────────┐  ┌─────────▼──────────┐          │
   │      OPENCODE       │  │     ANTIGRAVITY      │          │
   │  OPENCODE.md        │  │  ANTIGRAVITY.md      │          │
   │  Streamlit app      │  │  test_reflection     │          │
   │  Est: 4-5 hours     │  │  test_schema_        │          │
   └─────────────────────┘  │  coherence           │          │
                             │  Est: 3-4 hours      │          │
                             └─────────────────────┘          │
```

## Dependency Graph

| Agent | Depends On | Blocks |
|---|---|---|
| Cursor | nothing | Codex (ReflectionEngine interface), Antigravity |
| Codex | Cursor (ReflectionEngine class) | Antigravity, OpenCode |
| Goose | nothing | Antigravity |
| OpenCode | Codex (Agent.reflect() method) | Sprint 29 close |
| Antigravity | Cursor + Codex + Goose all done | Sprint 29 close |

## Files Owned Per Agent

| Agent | Creates | Modifies |
|---|---|---|
| Cursor | `src/agents/reflection.py` | `src/generation/tier1_generator.py` (constraint enforcement post-step) |
| Codex | `scripts/ab_test_baseline.py` | `src/agents/agent.py` (add `reflect()` method only) |
| Goose | `scripts/run_scenario_batch.py` | nothing |
| OpenCode | `app/streamlit_app.py`, `app/__init__.py` | `src/agents/__init__.py` (add ReflectionEngine export) |
| Antigravity | `tests/test_reflection.py`, `tests/test_schema_coherence.py` | `tests/test_agent.py` (replace 1 test) |

## Critical Field Names (verified from schema.py — do not deviate)

| Attribute | Correct path | Common wrong path |
|---|---|---|
| Persona unique ID | `persona.id` | `persona.persona_id`, `persona.demographics.parent_name` |
| Human display name | `persona.display_name` | `persona.name`, `persona.demographics.parent_name` |
| Family structure | `persona.demographics.family_structure` | `persona.demographics.household_structure` |
| Digital payment | `persona.media.digital_payment_comfort` | `persona.daily_routine.digital_payment_comfort` |
| Sim state | `persona.state` (alias: `persona.time_state`) | `persona.temporal_state` |
| Education attrs | `persona.education_learning` (alias: `persona.education`) | — |
| Lifestyle attrs | `persona.lifestyle` (alias: `persona.lifestyle_interests`) | — |
| Family structure values | `"nuclear"`, `"joint"`, `"single_parent"` | `"single-parent"` (hyphen) |
| Parent traits | `persona.parent_traits` — **may be None, always null-check** | — |

## Sprint 29 — Definition of Done

- [ ] `from src.agents import ReflectionEngine` works
- [ ] `agent.reflect()` returns a list of `ReflectionInsight` objects
- [ ] Reflection triggered correctly when cumulative salience > 5.0
- [ ] `scripts/run_scenario_batch.py` runs against 165 clean personas, writes `scenario_results.json`
- [ ] `scripts/ab_test_baseline.py` produces a comparison table (memory-backed vs naive)
- [ ] `app/streamlit_app.py` runs: `streamlit run app/streamlit_app.py`
- [ ] Tier 1 post-sample constraint enforcement blocks all 4 anti-correlation violations
- [ ] `pytest tests/` exits 0 (all tests including new ones pass)
- [ ] `tests/test_schema_coherence.py` asserts every field path used in Sprint 28-29 code
