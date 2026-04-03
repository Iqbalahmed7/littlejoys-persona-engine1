# Sprint 30 — Brief: CURSOR

**Role:** Architecture lead
**Model:** Auto
**Assignment:** `src/simulation/tick_engine.py` — the multi-tick simulation engine
**Est. duration:** 5-6 hours
**START:** Immediately

---

## Files to Create

| Action | File |
|---|---|
| CREATE | `src/simulation/__init__.py` (empty) |
| CREATE | `src/simulation/tick_engine.py` |

## Do NOT Touch
- `src/agents/agent.py`
- `src/agents/memory.py`
- `src/agents/reflection.py`
- `src/taxonomy/schema.py`
- Any test file
- Any script in `scripts/`

---

## Verified Field Names

```python
persona.id                              # string
persona.display_name                    # may be None → use persona.id as fallback
persona.episodic_memory                 # list[MemoryEntry]
persona.brand_memories                  # dict[str, BrandMemory]
persona.brand_memories[brand].trust_level       # float 0.0-1.0
persona.brand_memories[brand].purchase_count    # int
persona.brand_memories[brand].satisfaction_history  # list[float]
persona.parent_traits                   # may be None — always null-check
persona.parent_traits.decision_style    # only after null-check
```

---

## What to Build

### Concept

A `TickEngine` runs a persona through a scheduled sequence of events across simulation ticks (each tick = 1 day). At each tick it:
1. Fires any stimuli scheduled for that tick through `agent.perceive()`
2. Tracks cumulative salience — triggers `agent.reflect()` when threshold crossed
3. Fires any decisions scheduled for that tick through `agent.decide()`
4. Records a snapshot of brand trust for every brand in `persona.brand_memories`
5. Returns a complete `TickJourneyLog` of everything that happened

### `TickJourneyLog` dataclass

```python
@dataclass
class TickSnapshot:
    """State of persona at a single simulation tick."""
    tick: int
    brand_trust: dict[str, float]       # brand → trust_level at this tick
    memories_count: int                 # total episodic memory entries
    cumulative_salience: float          # running total since last reflection
    reflected: bool                     # did reflection fire this tick?
    perception_results: list[dict]      # results of perceive() calls this tick
    decision_result: dict | None        # result of decide() this tick (if any)


@dataclass
class TickJourneyLog:
    """Complete record of a persona's multi-tick journey."""
    persona_id: str
    display_name: str
    journey_id: str                     # "A" or "B"
    total_ticks: int
    snapshots: list[TickSnapshot]       # one per tick
    final_decision: dict | None         # last decide() result
    reordered: bool                     # True if purchase_count > 1 at end
    error: str | None

    def to_dict(self) -> dict:
        """Serialise to JSON-compatible dict."""
        ...
```

### `TickEngine` class

```python
class TickEngine:
    """
    Runs a persona through a multi-tick simulation journey.

    A journey is a schedule of stimuli and decision scenarios mapped to
    specific simulation ticks. The engine advances tick by tick, fires
    the appropriate perceive/decide calls, tracks memory accumulation,
    triggers reflection when cumulative salience crosses threshold, and
    records brand trust snapshots at every tick.

    Usage:
        engine = TickEngine()
        log = engine.run(persona, JOURNEY_A)
    """

    REFLECTION_THRESHOLD = 5.0

    def __init__(self) -> None:
        pass

    def run(
        self,
        persona: "Persona",
        journey: "JourneySpec",
    ) -> TickJourneyLog:
        """
        Run a complete journey for one persona.

        Args:
            persona:  The Persona object to simulate.
            journey:  A JourneySpec defining the stimulus/decision schedule.

        Returns:
            TickJourneyLog with full tick-by-tick history.
        """
        from src.agents.agent import CognitiveAgent

        agent = CognitiveAgent(persona)
        cumulative_salience = 0.0
        snapshots: list[TickSnapshot] = []
        final_decision: dict | None = None
        error: str | None = None

        try:
            for tick in range(journey.total_ticks):
                tick_perceptions: list[dict] = []
                tick_decision: dict | None = None
                reflected = False

                # Fire any stimuli scheduled for this tick
                for stimulus in journey.stimuli_at(tick):
                    try:
                        pr = agent.perceive(stimulus)
                        cumulative_salience += pr.importance
                        tick_perceptions.append({
                            "stimulus_id": stimulus.get("id", f"S-{tick}"),
                            "importance": pr.importance,
                            "emotional_valence": pr.emotional_valence,
                            "reflection_trigger": pr.reflection_trigger_candidate,
                        })
                    except Exception as e:
                        tick_perceptions.append({
                            "stimulus_id": stimulus.get("id", f"S-{tick}"),
                            "error": str(e),
                        })

                # Trigger reflection if threshold crossed
                if cumulative_salience >= self.REFLECTION_THRESHOLD:
                    try:
                        agent.reflect(n_insights=2)
                        reflected = True
                        cumulative_salience = 0.0   # reset after reflection
                    except Exception:
                        pass

                # Fire any decision scheduled for this tick
                if journey.decision_at(tick):
                    try:
                        dr = agent.decide(journey.decision_at(tick))
                        tick_decision = dr.to_dict()
                        final_decision = tick_decision

                        # Record purchase in brand memory if decided to buy/trial
                        if dr.decision in ("buy", "trial"):
                            brand = journey.primary_brand
                            if brand in persona.brand_memories:
                                persona.brand_memories[brand].purchase_count += 1
                    except Exception as e:
                        tick_decision = {"error": str(e)}

                # Snapshot brand trust at this tick
                brand_trust = {
                    brand: round(bm.trust_level, 4)
                    for brand, bm in persona.brand_memories.items()
                }

                snapshots.append(TickSnapshot(
                    tick=tick,
                    brand_trust=brand_trust,
                    memories_count=len(persona.episodic_memory),
                    cumulative_salience=round(cumulative_salience, 4),
                    reflected=reflected,
                    perception_results=tick_perceptions,
                    decision_result=tick_decision,
                ))

        except Exception as e:
            error = str(e)

        reordered = False
        brand = journey.primary_brand
        if brand in persona.brand_memories:
            reordered = persona.brand_memories[brand].purchase_count > 1

        return TickJourneyLog(
            persona_id=persona.id,
            display_name=persona.display_name or persona.id,
            journey_id=journey.journey_id,
            total_ticks=journey.total_ticks,
            snapshots=snapshots,
            final_decision=final_decision,
            reordered=reordered,
            error=error,
        )
```

### `JourneySpec` dataclass

```python
@dataclass
class JourneySpec:
    """Defines a simulation journey: which stimuli fire at which ticks."""
    journey_id: str
    total_ticks: int
    primary_brand: str
    _stimuli_schedule: dict[int, list[dict]]   # tick → list of stimuli
    _decision_schedule: dict[int, dict]        # tick → decision scenario

    def stimuli_at(self, tick: int) -> list[dict]:
        return self._stimuli_schedule.get(tick, [])

    def decision_at(self, tick: int) -> dict | None:
        return self._decision_schedule.get(tick)
```

---

## The Two Journey Specs

Define these as module-level constants in `tick_engine.py`.

### JOURNEY_A — Nutrimix Repeat Purchase (60 ticks)

**Purpose:** Model the full post-purchase lifecycle. Understand why first-time buyers don't reorder.

**Pre-purchase phase (ticks 0-20):**
```python
tick 1:  Instagram ad — LittleJoys Nutrimix launch awareness
tick 5:  WhatsApp WOM — friend recommends it
tick 8:  Price drop — Rs 799 → Rs 649 on BigBasket
tick 12: Pediatrician mention — recommends for low iron
tick 15: School WhatsApp group — Horlicks vs cleaner options debate
tick 20: DECISION — First purchase (BigBasket, Rs 649)
```

**Post-purchase phase (ticks 21-60):**
```python
tick 23: Product experience — child accepts the taste, mixes well
tick 28: Outcome observation — parent notices child energy levels
tick 32: Competitor retargeting — Horlicks ad on Instagram
tick 38: Replenishment awareness — pack running low (internal stimulus)
tick 42: Social reinforcement — school mom asks how it's going
tick 48: Price check — current price Rs 649, no discount active
tick 55: Competitor suggestion — pharmacist mentions Complan
tick 60: DECISION — Reorder decision (BigBasket, Rs 649)
```

**Decision scenario at tick 20 (first purchase):**
```python
{
    "description": "You see LittleJoys Nutrimix available on BigBasket. Rs 649 for 500g. You have seen ads, heard from a friend, and your pediatrician mentioned it. Do you buy?",
    "product": "LittleJoys Nutrimix 500g",
    "price_inr": 649,
    "channel": "bigbasket",
    "simulation_tick": 20,
}
```

**Decision scenario at tick 60 (reorder):**
```python
{
    "description": "Your LittleJoys Nutrimix pack is nearly finished. Your child has been having it for 5 weeks. You're on BigBasket — it's Rs 649, no discount this time. Do you reorder?",
    "product": "LittleJoys Nutrimix 500g",
    "price_inr": 649,
    "channel": "bigbasket",
    "simulation_tick": 60,
}
```

---

### JOURNEY_B — Magnesium Gummies Acquisition (45 ticks)

**Purpose:** Model category creation from zero awareness. Measure how many touchpoints convert a persona who has never thought about magnesium.

**Awareness phase (ticks 0-15):**
```python
tick 2:  Instagram reel — child sleep and magnesium connection
tick 7:  Pediatrician mention — mentions poor sleep may relate to magnesium
tick 10: WhatsApp forward — article on magnesium for growing kids
```

**Consideration phase (ticks 16-35):**
```python
tick 18: Google search stimulus — parent searches "magnesium for kids India"
tick 22: Instagram ad — LittleJoys Magnesium Gummies, 30-day pack Rs 499
tick 27: Mom influencer reel — shows her child taking gummies, sleep improved
tick 32: Pediatrician follow-up — confirms supplementation is safe and useful
tick 35: DECISION — First purchase decision (Rs 499 for 30-day pack)
```

**Post-purchase phase (ticks 36-45):**
```python
tick 38: First use — child likes the taste (gummy format)
tick 42: Outcome check — parent notices sleep improvement or not
tick 45: DECISION — Continue or stop?
```

**Decision scenario at tick 35:**
```python
{
    "description": "You've been reading about magnesium for kids. Your pediatrician mentioned it. You see LittleJoys Magnesium Gummies — Rs 499 for a 30-day supply, gummy format your child will actually eat. Do you try it?",
    "product": "LittleJoys Magnesium Gummies 30-day pack",
    "price_inr": 499,
    "channel": "firstcry_online",
    "simulation_tick": 35,
}
```

**Decision scenario at tick 45:**
```python
{
    "description": "You've been giving your child LittleJoys Magnesium Gummies for 10 days. You've noticed some improvement in sleep. The pack will run out in 5 days. Rs 499 to reorder. Do you continue?",
    "product": "LittleJoys Magnesium Gummies 30-day pack",
    "price_inr": 499,
    "channel": "firstcry_online",
    "simulation_tick": 45,
}
```

---

## Required Imports

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona
```

---

## Acceptance Criteria

- [ ] `TickEngine().run(persona, JOURNEY_A)` returns a `TickJourneyLog` without error
- [ ] `log.snapshots` has exactly `journey.total_ticks` entries
- [ ] Each snapshot contains `brand_trust` dict with trust levels for all brands encountered
- [ ] `reflected=True` appears in at least one snapshot when cumulative salience crosses 5.0
- [ ] `reordered=True` when a persona buys at both tick 20 and tick 60
- [ ] `reordered=False` when a persona buys at tick 20 but rejects at tick 60
- [ ] `TickJourneyLog.to_dict()` returns a JSON-serialisable dict
- [ ] `JOURNEY_A` and `JOURNEY_B` defined as module-level constants
- [ ] `JourneySpec.stimuli_at(tick)` returns `[]` for ticks with no stimuli
- [ ] `JourneySpec.decision_at(tick)` returns `None` for ticks with no decision
- [ ] No LLM calls at construction time — only during `engine.run()`
- [ ] `src/simulation/__init__.py` exports `TickEngine`, `TickJourneyLog`, `JourneySpec`, `JOURNEY_A`, `JOURNEY_B`
