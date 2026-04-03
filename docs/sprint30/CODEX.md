# Sprint 30 — Brief: CODEX

**Role:** Backend algorithms
**Model:** GPT-5.3
**Assignment:** `src/simulation/journey_result.py` + `scripts/run_journey_batch.py`
**Est. duration:** 4-5 hours
**START:** After Cursor signals done (`TickEngine` and `JOURNEY_A`/`JOURNEY_B` must exist)

---

## Files to Create

| Action | File |
|---|---|
| CREATE | `src/simulation/journey_result.py` |
| CREATE | `scripts/run_journey_batch.py` |

## Do NOT Touch
- `src/simulation/tick_engine.py` — Cursor owns it
- `src/agents/` — any file
- `src/taxonomy/schema.py`
- Any test file
- `src/agents/__init__.py`

---

## Verified Field Names

```python
persona.id                              # string
persona.display_name                    # may be None → use persona.id as fallback
persona.demographics.parent_age
persona.demographics.city_tier
persona.parent_traits                   # may be None — always null-check
persona.parent_traits.decision_style    # only after null-check
persona.budget_profile                  # may be None — always null-check
persona.budget_profile.price_sensitivity  # only after null-check
persona.brand_memories[brand].trust_level  # float 0-1
persona.brand_memories[brand].purchase_count  # int
```

---

## Part 1: `src/simulation/journey_result.py`

Aggregation functions that summarise a list of `TickJourneyLog` objects into insight tables. Imported by `run_journey_batch.py` and by Goose's analysis script.

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.simulation.tick_engine import TickJourneyLog


@dataclass
class JourneyAggregate:
    """Summary statistics across all persona journeys for one journey type."""
    journey_id: str
    total_personas: int
    errors: int

    # First decision (tick 20 for Journey A, tick 35 for Journey B)
    first_decision_distribution: dict[str, dict]    # decision → {count, pct}
    first_decision_drivers: dict[str, int]          # driver → count (top 10)
    first_decision_objections: dict[str, int]

    # Second decision (tick 60 for A, tick 45 for B)
    second_decision_distribution: dict[str, dict]
    second_decision_drivers: dict[str, int]
    second_decision_objections: dict[str, int]

    # Reorder / continuation rate
    reorder_rate_pct: float                         # % who reordered among first-time buyers
    avg_trust_at_first_decision: float              # mean brand trust at decision tick
    avg_trust_at_second_decision: float

    # Trust trajectory
    trust_by_tick: dict[int, float]                 # tick → mean trust across personas

    def to_dict(self) -> dict: ...


def aggregate_journeys(logs: list["TickJourneyLog"]) -> JourneyAggregate:
    """
    Compute summary statistics from a list of TickJourneyLog objects.

    Handles errors gracefully — skips logs with errors in the aggregate.
    """
    ...


def find_conversion_tick(logs: list["TickJourneyLog"]) -> dict:
    """
    For Journey B (Gummies): find which tick was the most common
    first-awareness-to-decision conversion point.

    Returns: {tick: count_of_first_purchase_decisions}
    """
    ...


def segment_by_reorder(logs: list["TickJourneyLog"]) -> dict:
    """
    Split personas into reorderers vs lapsers.
    Return two lists of persona_ids for downstream analysis.

    Returns: {"reorderers": [...], "lapsers": [...]}
    """
    ...
```

Implement all three functions. Handle empty lists, all-error lists, and missing decision results gracefully.

---

## Part 2: `scripts/run_journey_batch.py`

```python
#!/usr/bin/env python3
"""
run_journey_batch.py — Run multi-tick journeys across all 200 personas.

Usage:
    ANTHROPIC_API_KEY=sk-... python3 scripts/run_journey_batch.py --journey A
    ANTHROPIC_API_KEY=sk-... python3 scripts/run_journey_batch.py --journey B
    python3 scripts/run_journey_batch.py --journey A --max 10 --concurrency 3

Arguments:
    --journey   A (Nutrimix repeat purchase, 60 ticks) or B (Gummies, 45 ticks)
    --max       Cap number of personas (default: all 200)
    --concurrency  Thread pool size (default: 3)

Output:
    data/population/journey_A_results.json  (or journey_B_results.json)
    Prints progress + final summary table
"""
```

### Key implementation requirements

**Loading personas:**
Load ALL 200 personas (not just clean ones — the 35 previously hard-violation personas have now been fixed). Do not filter by violations report.

```python
def load_all_personas(max_n: int | None = None) -> list[tuple[str, Persona]]:
    candidates = [
        PROJECT_ROOT / "data" / "population" / "personas_generated.json",
        PROJECT_ROOT / "data" / "population" / "personas.json",
    ]
    # load, parse, return list[tuple[str, Persona]]
    # print how many loaded
```

**Running a single persona:**
```python
def run_persona_journey(pid: str, persona: Persona, journey_id: str) -> dict:
    """Run the full journey for one persona. Returns TickJourneyLog.to_dict(). Never raises."""
    from src.simulation.tick_engine import TickEngine, JOURNEY_A, JOURNEY_B
    journey = JOURNEY_A if journey_id == "A" else JOURNEY_B
    engine = TickEngine()
    log = engine.run(persona, journey)
    return log.to_dict()
```

**Concurrency:** Use `ThreadPoolExecutor` with `as_completed` — same pattern as `run_scenario_batch.py`.

**Progress output:**
```
  [  1/200] Priya-Delhi-Mom-32        journey=A  tick60_decision=buy    reordered=True
  [  2/200] Rahul-Mumbai-Dad-29       journey=A  tick60_decision=defer  reordered=False
```

**Summary table:**

After all personas complete, print:
```
===========================================================
JOURNEY A — NUTRIMIX REPEAT PURCHASE — SUMMARY
===========================================================
Personas run:    200
Errors:          0

FIRST PURCHASE (tick 20):
  buy          XXX (XX.X%)  ######
  trial         XX (XX.X%)  ###
  ...

REORDER RATE (among first-time buyers):
  Reordered:    XX%
  Lapsed:       XX%

BRAND TRUST TRAJECTORY (mean across personas):
  Tick 0:  0.00
  Tick 10: X.XX
  Tick 20: X.XX  ← first decision
  Tick 40: X.XX
  Tick 60: X.XX  ← reorder decision

TOP REORDER DRIVERS:
  1. driver_name: count
  ...

TOP LAPSE REASONS (objections from non-reorderers):
  1. objection_name: count
  ...
===========================================================
```

**Output file structure:**
```python
output = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "journey_id": journey_id,
    "total_personas": len(personas),
    "elapsed_seconds": elapsed,
    "aggregate": aggregate.to_dict(),   # from journey_result.aggregate_journeys()
    "logs": [log_dict, ...],            # all TickJourneyLog.to_dict() results
}
```

Write to:
- Journey A → `data/population/journey_A_results.json`
- Journey B → `data/population/journey_B_results.json`

---

## Self-Verify Before Signalling Done

```bash
python3 -c "import ast; ast.parse(open('scripts/run_journey_batch.py').read()); print('syntax OK')"
python3 -c "import ast; ast.parse(open('src/simulation/journey_result.py').read()); print('syntax OK')"
python3 -c "from src.simulation.journey_result import aggregate_journeys, segment_by_reorder; print('imports OK')"
```

Also verify with a function call — not just import:
```bash
python3 -c "
from src.simulation.journey_result import segment_by_reorder
result = segment_by_reorder([])
assert 'reorderers' in result and 'lapsers' in result
print('segment_by_reorder: OK')
"
```

---

## Acceptance Criteria

- [ ] `from src.simulation.journey_result import aggregate_journeys, segment_by_reorder, find_conversion_tick` works
- [ ] `aggregate_journeys([])` returns a `JourneyAggregate` without error
- [ ] `segment_by_reorder([])` returns `{"reorderers": [], "lapsers": []}`
- [ ] `run_journey_batch.py --journey A --max 5` runs end-to-end (needs API key)
- [ ] `run_journey_batch.py --journey B --max 5` runs end-to-end
- [ ] Output JSON written to correct path per journey
- [ ] Progress line printed per persona
- [ ] Summary table printed with reorder rate
- [ ] `--max` and `--concurrency` flags work
- [ ] `ANTHROPIC_API_KEY` check at startup
- [ ] Exit code 0 on success
- [ ] No syntax errors — verify with `ast.parse` AND a function call
