# Sprint 17 Brief — Goose (Grok-4-1-fast-reasoning)
## Event Grammar: Event Definitions, Firing Rules, and State Impact Functions

---

## PROJECT CONTEXT (Read This First)

You are working on the **LittleJoys Persona Simulation Engine** — a simulation tool that models how Indian parents decide whether to buy, repeat-purchase, or churn from a children's nutrition product (NutriMix, a powder mix priced at ₹599 for ages 2-6).

### What the system does:
1. Generates 200 synthetic **personas** — Indian parents with 145+ attributes (demographics, psychology, health attitudes, shopping behaviour, media consumption)
2. Runs a **temporal simulation** — day by day, events happen (pack finishes, child rejects the taste, a competitor runs a discount, a doctor recommends the product) and the persona's internal state evolves
3. Personas make **decisions** — purchase, reorder, switch to competitor, or churn — based on their evolving state
4. The system produces **insights** — behavioural clusters, intervention comparisons, and recommendations for the product team

### Your role in this sprint:
You are building the **event grammar** — the definitions of what events can happen, when they fire, and how they affect a persona's internal state. Think of it as the "rules of the simulation world."

### Technology stack:
- Python 3.11+
- Pydantic for data models
- All code in `/Users/admin/Documents/Simulatte Projects/1. LittleJoys/`
- Constants go in `src/constants.py` (no magic numbers in logic files)
- Run tests with: `uv run pytest tests/ -x -q`
- Run linting with: `uv run ruff check .`
- **IMPORTANT**: Before running any command, ensure PATH is set: `export PATH="/Users/admin/.local/bin:$PATH"`

---

## EXISTING CODE YOU NEED TO UNDERSTAND

### Persona Attributes (from `src/taxonomy/schema.py`)

A `Persona` object has 12 attribute groups. The ones relevant to your event grammar:

```python
persona.demographics.city_tier          # "Tier1", "Tier2", "Tier3"
persona.demographics.household_income_lpa  # 1.0 - 100.0 (lakhs per annum)

persona.health.medical_authority_trust  # [0,1] — trusts doctors
persona.health.nutrition_gap_awareness  # [0,1] — knows child needs supplements

persona.psychology.social_proof_bias    # [0,1] — influenced by peers
persona.psychology.risk_tolerance       # [0,1] — openness to new products

persona.relationships.child_taste_veto  # [0,1] — child can refuse food
persona.relationships.wom_receiver_openness  # [0,1] — receptive to recommendations
persona.relationships.peer_influence_strength  # [0,1]

persona.daily_routine.budget_consciousness  # [0,1] — price sensitive
persona.daily_routine.price_reference_point  # float ~500 — mental anchor for supplement price
persona.daily_routine.subscription_comfort  # [0,1] — willingness to subscribe
persona.daily_routine.deal_seeking_intensity  # [0,1]

persona.media.ad_receptivity           # [0,1] — responsive to ads
persona.lifestyle.wellness_trend_follower  # [0,1]

persona.education_learning.science_literacy  # [0,1] — understands nutrition science
```

### Scenario Config (from `src/decision/scenarios.py`)

```python
scenario.product.price_inr             # 599 for NutriMix
scenario.product.taste_appeal          # 0.7
scenario.product.effort_to_acquire     # 0.3
scenario.marketing.awareness_budget    # 0.5 [0,1]
scenario.marketing.channel_mix         # {"instagram": 0.4, "youtube": 0.3, "whatsapp": 0.3}
scenario.marketing.pediatrician_endorsement  # True/False
scenario.marketing.influencer_campaign       # True/False
scenario.marketing.discount_available        # [0,1]
scenario.lj_pass_available             # True/False
```

### Canonical State Model (the 10 mutable variables)

Another engineer (Codex) is building `src/simulation/state_model.py` with a `CanonicalState` class. Your events will update these variables:

```python
state.trust               # [0,1] — trust in the product/brand
state.habit_strength       # [0,1] — how habitual the purchase is
state.child_acceptance     # [0,1] — child's willingness to consume
state.price_salience       # [0,1] — how much price matters right now
state.reorder_urgency      # [0,1] — pressure to reorder
state.fatigue              # [0,1] — taste boredom / product fatigue
state.perceived_value      # [0,1] — belief that product is worth the money
state.brand_salience       # [0,1] — awareness / brand presence in mind
state.effort_friction      # [0,1] — hassle of purchasing
state.discretionary_budget # [0,1] — available spending room

# Tracking fields:
state.is_active            # bool — currently a customer
state.ever_adopted         # bool — has ever purchased
state.current_pack_day     # int — days into current pack
state.pack_duration        # int — 25 days per pack
state.days_since_purchase  # int
state.total_purchases      # int
state.has_lj_pass          # bool
```

---

## YOUR DELIVERABLE

### Create: `src/simulation/event_grammar.py`

This file defines what events exist, when they fire, and how they change state.

### Part 1: Event Model

```python
from pydantic import BaseModel

class SimulationEvent(BaseModel):
    """A single event that occurs during simulation."""
    event_type: str          # One of the EVENT_TYPES below
    day: int                 # Day number (1-360)
    intensity: float = 1.0   # Impact strength [0, 1]
    attributes: dict = {}    # Optional extra data (e.g., which competitor, which channel)
```

### Part 2: Event Type Registry

Define all event types as string constants. Group into 4 categories:

**CONSUMPTION events** (related to product usage):
- `pack_finished` — the pack runs out (deterministic: every `pack_duration` days after purchase)
- `usage_consistent` — child consuming regularly (deterministic: fires daily when active)
- `usage_drop` — child skipping servings (stochastic: probability increases with fatigue)

**CHILD events** (child's reaction to the product):
- `child_positive_reaction` — child enjoys the product
- `child_rejection` — child actively refuses
- `child_boredom` — child loses interest gradually

**ECONOMIC events** (money and competition):
- `budget_pressure_increase` — household financial stress
- `payday_relief` — monthly salary credit
- `competitor_discount` — a competitor brand offers a deal

**BRAND events** (marketing and social):
- `ad_exposure` — persona sees a LittleJoys ad
- `influencer_exposure` — persona sees influencer content about the product
- `doctor_recommendation` — pediatrician recommends the product
- `peer_wom` — friend/family mentions the product positively
- `reminder` — re-engagement notification (e.g., email, WhatsApp)
- `pass_offer` — LJ Pass subscription offer

### Part 3: Deterministic Event Firing

```python
def fire_deterministic_events(
    state: CanonicalState,
    day: int,
    scenario: ScenarioConfig,
) -> list[SimulationEvent]:
    """Fire events that happen on known schedules. Called every day."""
```

Rules:
- `pack_finished`: Fires when `state.current_pack_day >= state.pack_duration` and `state.is_active`. Intensity 1.0.
- `payday_relief`: Fires on day 1 and every 30 days thereafter. Intensity 0.5.
- `usage_consistent`: Fires daily when `state.is_active` and `state.current_pack_day > 0`. Intensity scales with `1.0 - state.fatigue`.

### Part 4: Stochastic Event Firing

```python
def fire_stochastic_events(
    state: CanonicalState,
    persona: Persona,
    day: int,
    scenario: ScenarioConfig,
    rng: random.Random,
) -> list[SimulationEvent]:
    """Fire events probabilistically based on persona attributes and state."""
```

**Firing probabilities** (per day):

| Event | Daily Probability Formula | Notes |
|-------|--------------------------|-------|
| `ad_exposure` | `0.03 * scenario.marketing.awareness_budget * persona.media.ad_receptivity` | ~1x per 10 days at full budget/receptivity |
| `influencer_exposure` | `0.02 * persona.lifestyle.wellness_trend_follower` if `scenario.marketing.influencer_campaign` else 0 | Only if campaign active |
| `doctor_recommendation` | `0.005 * persona.health.medical_authority_trust` if `scenario.marketing.pediatrician_endorsement` else 0 | Rare but high impact |
| `peer_wom` | `0.01 * persona.relationships.wom_receiver_openness * persona.psychology.social_proof_bias` | Word of mouth |
| `child_positive_reaction` | `0.05 * scenario.product.taste_appeal * (1 - state.fatigue)` when `state.is_active` | More likely early on |
| `child_rejection` | `0.02 * persona.relationships.child_taste_veto * state.fatigue` when `state.is_active` | More likely when fatigued |
| `child_boredom` | `0.01 * state.fatigue` when `state.is_active` and `state.fatigue > 0.3` | Slow onset |
| `budget_pressure_increase` | `0.01 * persona.daily_routine.budget_consciousness` | Economic stress |
| `competitor_discount` | `0.008 * persona.daily_routine.deal_seeking_intensity` | Competitive pressure |
| `reminder` | `0.02` when `state.days_since_purchase > 20` and `not state.is_active` or `state.current_pack_day > state.pack_duration - 5` | Re-engagement |
| `pass_offer` | `0.005` when `state.total_purchases >= 2` and `not state.has_lj_pass` and `scenario.lj_pass_available` | After 2+ purchases |

For each event: roll `rng.random()` against the probability. If `< probability`, fire the event with `intensity = rng.uniform(0.5, 1.0)`.

### Part 5: State Impact Rules

```python
def apply_event_impact(
    state: CanonicalState,
    event: SimulationEvent,
    persona: Persona,
) -> None:
    """Apply an event's impact to the persona's mutable state. Mutates state in-place."""
```

Impact rules (all values clipped to [0, 1] after update):

| Event | State Updates |
|-------|-------------|
| `pack_finished` | `reorder_urgency = 0.8`, `current_pack_day = 0` |
| `usage_consistent` | `current_pack_day += 1`, `habit_strength += 0.001` (daily micro-habit) |
| `usage_drop` | `fatigue += 0.02`, `perceived_value -= 0.01` |
| `child_positive_reaction` | `child_acceptance += 0.05 * intensity`, `perceived_value += 0.02` |
| `child_rejection` | `child_acceptance -= 0.10 * intensity`, `fatigue += 0.03` |
| `child_boredom` | `child_acceptance -= 0.03 * intensity`, `fatigue += 0.02` |
| `budget_pressure_increase` | `price_salience += 0.08 * intensity`, `discretionary_budget -= 0.05 * intensity` |
| `payday_relief` | `price_salience -= 0.03`, `discretionary_budget += 0.04` |
| `competitor_discount` | `price_salience += 0.06 * intensity` (store as `state._competitor_discount_active = True` for decision eval, reset after decision) |
| `ad_exposure` | `brand_salience += 0.05 * intensity * persona.media.ad_receptivity` |
| `influencer_exposure` | `brand_salience += 0.07 * intensity`, `trust += 0.02 * intensity` |
| `doctor_recommendation` | `trust += 0.10 * intensity`, `perceived_value += 0.05 * intensity` |
| `peer_wom` | `brand_salience += 0.04 * intensity`, `trust += 0.03 * intensity * persona.psychology.social_proof_bias` |
| `reminder` | `reorder_urgency += 0.15 * intensity`, `brand_salience += 0.03` |
| `pass_offer` | (no direct state change — the decision engine evaluates subscription at this point) |

**Clip function**: After every state update, clip all float fields to [0.0, 1.0]:
```python
def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))
```

### Part 6: Helper — Is This a Decision Point?

```python
def is_decision_point(state: CanonicalState, events: list[SimulationEvent]) -> bool:
    """Should the decision engine evaluate this day?"""
    # Decision points:
    # 1. pack_finished event fired (reorder decision)
    # 2. brand_salience crossed awareness threshold for first time (first purchase)
    # 3. pass_offer event fired (subscription decision)
    # 4. reminder fired and persona is inactive (re-engagement)
    event_types = {e.event_type for e in events}
    if "pack_finished" in event_types:
        return True
    if not state.ever_adopted and state.brand_salience > 0.3:  # Rough awareness check
        return True
    if "pass_offer" in event_types:
        return True
    if "reminder" in event_types and not state.is_active:
        return True
    return False
```

---

## TESTING YOUR CODE

Create a small test file `tests/unit/test_event_grammar.py`:

```python
"""Unit tests for event grammar."""
from src.simulation.event_grammar import (
    SimulationEvent,
    fire_deterministic_events,
    fire_stochastic_events,
    apply_event_impact,
    is_decision_point,
)

# Test 1: SimulationEvent model creates correctly
# Test 2: fire_deterministic_events returns pack_finished when pack expires
# Test 3: fire_deterministic_events returns payday_relief on day 1
# Test 4: fire_stochastic_events is deterministic with same seed
# Test 5: apply_event_impact clips values to [0, 1]
# Test 6: is_decision_point returns True on pack_finished
# Test 7: doctor_recommendation increases trust
# Test 8: child_rejection decreases child_acceptance
```

You'll need to create a mock `CanonicalState` and `Persona` for testing. For CanonicalState, since Codex may not have delivered yet, you can create a minimal version:

```python
# In your test file, create a minimal state for testing:
from pydantic import BaseModel

class MockState:
    """Minimal state for testing event grammar independently."""
    def __init__(self):
        self.trust = 0.5
        self.habit_strength = 0.3
        self.child_acceptance = 0.6
        self.price_salience = 0.4
        self.reorder_urgency = 0.0
        self.fatigue = 0.1
        self.perceived_value = 0.5
        self.brand_salience = 0.3
        self.effort_friction = 0.3
        self.discretionary_budget = 0.6
        self.is_active = True
        self.ever_adopted = True
        self.current_pack_day = 25
        self.pack_duration = 25
        self.days_since_purchase = 25
        self.total_purchases = 1
        self.has_lj_pass = False
```

If the real `CanonicalState` exists when you run, import and use it instead.

---

## FILES TO CREATE
- `src/simulation/event_grammar.py` — Main deliverable
- `tests/unit/test_event_grammar.py` — Tests

## CONSTRAINTS
- All probability values must be defined as constants in `src/constants.py` (not hardcoded in logic). Name them with prefix `EVENT_PROB_` (e.g., `EVENT_PROB_AD_EXPOSURE_BASE = 0.03`).
- All impact magnitudes must also be constants with prefix `EVENT_IMPACT_` (e.g., `EVENT_IMPACT_DOCTOR_TRUST = 0.10`).
- Use `random.Random` instance (not global `random`) for determinism.
- Type hints on all functions.
- Run `uv run ruff check .` before delivery.
- Run `uv run pytest tests/unit/test_event_grammar.py -x -q` to verify your tests pass.

## HOW TO RUN
```bash
export PATH="/Users/admin/.local/bin:$PATH"
cd "/Users/admin/Documents/Simulatte Projects/1. LittleJoys"
uv run ruff check src/simulation/event_grammar.py
uv run pytest tests/unit/test_event_grammar.py -x -q
```
