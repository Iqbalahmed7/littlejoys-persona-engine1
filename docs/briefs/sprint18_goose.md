# Sprint 18 Brief — Goose (Grok-4-1-fast-reasoning)
## Complete Event Grammar: All 15 Event Types

### Context

Sprint 17 delivered an event grammar with 4 stochastic events. The simulation is BROKEN because positive events (child_positive_reaction, usage_consistent, doctor_recommendation) are missing — personas can only decline, never improve. This sprint completes all 15 event types.

**You MUST modify the EXISTING file at `src/simulation/event_grammar.py`.** Do NOT create a new file. Do NOT rename or remove existing functions. Add to them.

### Current State of `src/simulation/event_grammar.py`

The file already has these functions that you must EXTEND (not replace):
- `fire_deterministic_events(state, day, scenario)` → returns `list[SimulationEvent]`
- `fire_stochastic_events(state, persona, day, scenario, rng)` → returns `list[SimulationEvent]`
- `apply_event_impact(state, event, persona)` → modifies state in-place
- `is_decision_point(state, events)` → returns bool

Current events implemented:
- Deterministic: `ad_exposure` (weekly), `pack_finished`, `payday_relief`, `subscription_reminder`
- Stochastic: `ad_exposure`, `child_rejection`, `competitor_discount`, `peer_mention`

### Events to ADD

You need to add 11 event types. Here are the EXACT specifications:

#### Stochastic Events to Add in `fire_stochastic_events`:

**1. `child_positive_reaction`** (CRITICAL — currently only negative events exist)
```python
# Only fires when persona is active (using the product)
if state.is_active and rng.random() < EVENT_PROB_CHILD_POSITIVE_REACTION_BASE:
    events.append(SimulationEvent(event_type="child_positive_reaction", day=day, intensity=0.3))
```

**2. `child_boredom`** (gradual taste fatigue, different from rejection)
```python
# Only fires when active AND fatigue is building
if state.is_active and state.fatigue > EVENT_FATIGUE_THRESHOLD_BOREDOM and rng.random() < EVENT_PROB_CHILD_BOREDOM_BASE:
    events.append(SimulationEvent(event_type="child_boredom", day=day, intensity=0.2))
```

**3. `usage_consistent`** (daily habit reinforcement when using product)
```python
# Fires daily when active — very small habit boost
if state.is_active and rng.random() < 0.8:  # 80% chance when actively using
    events.append(SimulationEvent(event_type="usage_consistent", day=day, intensity=0.1))
```

**4. `usage_drop`** (reduced usage, precursor to churn)
```python
if state.is_active and state.fatigue > 0.4 and rng.random() < EVENT_PROB_USAGE_DROP_BASE:
    events.append(SimulationEvent(event_type="usage_drop", day=day, intensity=0.3))
```

**5. `budget_pressure_increase`** (random financial pressure)
```python
if rng.random() < EVENT_PROB_BUDGET_PRESSURE_INCREASE_BASE:
    events.append(SimulationEvent(event_type="budget_pressure_increase", day=day, intensity=0.5))
```

**6. `influencer_exposure`** (social media influencer content)
```python
if rng.random() < EVENT_PROB_INFLUENCER_EXPOSURE_BASE * (0.5 + persona.media.ad_receptivity):
    events.append(SimulationEvent(event_type="influencer_exposure", day=day, intensity=0.3))
```

**7. `doctor_recommendation`** (pediatrician recommends the product — rare but high impact)
```python
if rng.random() < EVENT_PROB_DOCTOR_RECOMMENDATION_BASE:
    events.append(SimulationEvent(event_type="doctor_recommendation", day=day, intensity=0.8))
```

**8. `reminder`** (brand sends a re-engagement reminder)
```python
# Only for inactive personas who have purchased before
if not state.is_active and state.ever_adopted and state.days_since_purchase > EVENT_REMINDER_DAYS_SINCE_PURCHASE_THRESHOLD:
    if rng.random() < EVENT_PROB_REMINDER_BASE:
        events.append(SimulationEvent(event_type="reminder", day=day, intensity=0.4))
```

**9. `pass_offer`** (LJ Pass subscription offer — only for qualified buyers)
```python
if (scenario.lj_pass_available and state.is_active
        and state.total_purchases >= EVENT_PASS_OFFER_MIN_PURCHASES
        and not state.has_lj_pass
        and rng.random() < EVENT_PROB_PASS_OFFER_BASE):
    events.append(SimulationEvent(event_type="pass_offer", day=day, intensity=0.5))
```

#### Impact Rules to Add in `apply_event_impact`:

Add these `elif` branches to the EXISTING function:

```python
elif event.event_type == "child_positive_reaction":
    state.child_acceptance += EVENT_IMPACT_CHILD_ACCEPTANCE_POSITIVE * intensity
    state.perceived_value += EVENT_IMPACT_PERCEIVED_VALUE_CHILD_POSITIVE * intensity

elif event.event_type == "child_boredom":
    state.child_acceptance -= EVENT_IMPACT_CHILD_ACCEPTANCE_BOREDOM * intensity
    state.fatigue += EVENT_IMPACT_FATIGUE_CHILD_BOREDOM * intensity

elif event.event_type == "usage_consistent":
    state.habit_strength += EVENT_IMPACT_HABIT_STRENGTH_USAGE_DAILY * intensity

elif event.event_type == "usage_drop":
    state.fatigue += EVENT_IMPACT_FATIGUE_USAGE_DROP * intensity
    state.perceived_value -= EVENT_IMPACT_PERCEIVED_VALUE_USAGE_DROP_NEG * intensity

elif event.event_type == "budget_pressure_increase":
    state.price_salience += EVENT_IMPACT_PRICE_SALIENCE_BUDGET_PRESSURE * intensity
    state.discretionary_budget -= EVENT_IMPACT_DISCRETIONARY_BUDGET_BUDGET_PRESSURE_NEG * intensity

elif event.event_type == "influencer_exposure":
    state.brand_salience += EVENT_IMPACT_BRAND_SALIENCE_INFLUENCER * intensity
    state.trust += EVENT_IMPACT_TRUST_INFLUENCER * intensity

elif event.event_type == "reminder":
    state.reorder_urgency += EVENT_IMPACT_REORDER_URGENCY_REMINDER * intensity
    state.brand_salience += EVENT_IMPACT_BRAND_SALIENCE_REMINDER * intensity

elif event.event_type == "pass_offer":
    state.reorder_urgency += 0.1 * intensity
```

### Constants

All `EVENT_PROB_*`, `EVENT_IMPACT_*`, and `EVENT_*_THRESHOLD` constants are already defined in `src/constants.py`. Import them at the top of the file:

```python
from src.constants import (
    EVENT_PROB_CHILD_POSITIVE_REACTION_BASE,
    EVENT_PROB_CHILD_BOREDOM_BASE,
    EVENT_PROB_USAGE_DROP_BASE,
    EVENT_PROB_BUDGET_PRESSURE_INCREASE_BASE,
    EVENT_PROB_INFLUENCER_EXPOSURE_BASE,
    EVENT_PROB_DOCTOR_RECOMMENDATION_BASE,
    EVENT_PROB_REMINDER_BASE,
    EVENT_PROB_PASS_OFFER_BASE,
    EVENT_FATIGUE_THRESHOLD_BOREDOM,
    EVENT_REMINDER_DAYS_SINCE_PURCHASE_THRESHOLD,
    EVENT_PASS_OFFER_MIN_PURCHASES,
    EVENT_IMPACT_CHILD_ACCEPTANCE_POSITIVE,
    EVENT_IMPACT_PERCEIVED_VALUE_CHILD_POSITIVE,
    EVENT_IMPACT_CHILD_ACCEPTANCE_BOREDOM,
    EVENT_IMPACT_FATIGUE_CHILD_BOREDOM,
    EVENT_IMPACT_HABIT_STRENGTH_USAGE_DAILY,
    EVENT_IMPACT_FATIGUE_USAGE_DROP,
    EVENT_IMPACT_PERCEIVED_VALUE_USAGE_DROP_NEG,
    EVENT_IMPACT_PRICE_SALIENCE_BUDGET_PRESSURE,
    EVENT_IMPACT_DISCRETIONARY_BUDGET_BUDGET_PRESSURE_NEG,
    EVENT_IMPACT_BRAND_SALIENCE_INFLUENCER,
    EVENT_IMPACT_TRUST_INFLUENCER,
    EVENT_IMPACT_REORDER_URGENCY_REMINDER,
    EVENT_IMPACT_BRAND_SALIENCE_REMINDER,
)
```

Note: `EVENT_FATIGUE_THRESHOLD_BOREDOM` is currently named `EVENT_FATIGUE_THRESHOLD_BORedom` with a typo. It has been fixed to `EVENT_FATIGUE_THRESHOLD_BOREDOM`. Use the corrected name.

### Files to Modify
- `src/simulation/event_grammar.py` — ADD to existing functions

### DO NOT
- Do NOT create new files
- Do NOT rename or remove existing functions
- Do NOT change the function signatures
- Do NOT modify `state_model.py`, `event_engine.py`, or `constants.py`

### Verification
```bash
uv run ruff check .
uv run pytest tests/ -x -q
```
All existing tests must still pass. The new events should integrate seamlessly with the existing engine.
