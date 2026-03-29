# Sprint 17 Brief — Codex (GPT-5.4 — Upgrade for this sprint)
## Canonical State Model + EventEngine Day Loop

### Context

Sprint 16 wired the existing month-level temporal simulation into the research pipeline. Sprint 17 replaces the month-level loop with a **day-level event-driven engine** powered by a 10-variable Canonical State Model. This is the simulation-native leap.

**Reference documents** (read these before starting):
- `docs/designs/CANONICAL-STATE-MODEL-V1.md` — Full state model spec
- `docs/ARCHITECTURE.md` — Section 5.3 (Event-Driven Simulation) and 5.4 (Canonical State Model)

### Task 1: Canonical State Model — NEW FILE `src/simulation/state_model.py`

Create the core state model with 10 mutable variables:

```python
class CanonicalState(BaseModel):
    """Mutable state for one persona across the simulation. All values [0, 1]."""

    model_config = ConfigDict(validate_assignment=True)

    trust: float = 0.0
    habit_strength: float = 0.0
    child_acceptance: float = 0.0
    price_salience: float = 0.0
    reorder_urgency: float = 0.0
    fatigue: float = 0.0
    perceived_value: float = 0.0
    brand_salience: float = 0.0
    effort_friction: float = 0.0
    discretionary_budget: float = 0.0

    # Tracking fields (not decision inputs)
    days_since_purchase: int = 0
    total_purchases: int = 0
    consecutive_purchase_months: int = 0
    has_lj_pass: bool = False
    is_active: bool = False       # Currently a customer
    ever_adopted: bool = False
    churned: bool = False
    current_pack_day: int = 0     # Days into current pack (0 = no pack)
    pack_duration: int = 25       # Days per pack (default)
```

**Initialization function:**
```python
def initialize_state(persona: Persona, scenario: ScenarioConfig) -> CanonicalState:
    """Initialize state from immutable persona identity + scenario config."""
```

Use the exact initialization formulas from `CANONICAL-STATE-MODEL-V1.md` Section "State Variables":
- `trust` = `medical_authority_trust * 0.3 + social_proof_bias * 0.2`
- `child_acceptance` = `taste_appeal * (1 - 0.3 * child_taste_veto)`
- `price_salience` = `budget_consciousness * 0.5`
- `perceived_value` = `taste_appeal * 0.5 + science_literacy * 0.3 + nutrition_gap_awareness * 0.2`
- `effort_friction` = `effort_to_acquire * (1 - online_shopping_comfort)`
- `discretionary_budget` = `1.0 - budget_consciousness`
- `habit_strength`, `reorder_urgency`, `fatigue`, `brand_salience` = 0.0

Note: `child_taste_veto` is at `persona.relationships.child_taste_veto` in the schema. Check the actual attribute path — it may be `child_taste_veto` or `child_taste_veto_power`. Use whichever exists.

**Threshold derivation function:**
```python
def derive_thresholds(persona: Persona) -> dict[str, float]:
    """Derive persona-specific decision thresholds from identity attributes."""
    return {
        "awareness_threshold": 0.25 - 0.1 * persona.media.ad_receptivity,
        "trust_threshold": 0.4 + 0.2 * (1 - persona.psychology.risk_tolerance),
        "price_reference_point": persona.daily_routine.price_reference_point,
    }
```

**Daily decay/growth function:**
```python
def apply_daily_dynamics(state: CanonicalState) -> None:
    """Apply natural decay/growth per day. Mutates state in-place."""
    # brand_salience decays 0.02/day without touchpoint (applied externally only when no event)
    # fatigue grows 0.03/7 ≈ 0.0043/day when active
    # habit decays 0.05/30 ≈ 0.0017/day when inactive
    # reorder_urgency ramps when pack is depleting
```

All values must be clipped to [0, 1] after every update.

### Task 2: Event Engine — NEW FILE `src/simulation/event_engine.py`

The core simulation loop, processing days and events:

```python
class DaySnapshot(BaseModel):
    """State capture for one persona on one day."""
    day: int
    state: dict[str, float]  # Snapshot of all 10 state variables
    events_fired: list[str]  # Event type IDs that fired this day
    decision: str | None = None  # "purchase", "reorder", "churn", "switch", "delay", None
    decision_rationale: dict[str, float] | None = None  # Top 3 variables that drove decision

class PersonaDayTrajectory(BaseModel):
    """Full day-by-day trajectory for one persona."""
    persona_id: str
    days: list[DaySnapshot]
    total_purchases: int
    churned_day: int | None = None
    first_purchase_day: int | None = None

class EventSimulationResult(BaseModel):
    """Output of the day-level event simulation."""
    scenario_id: str
    duration_days: int
    population_size: int
    trajectories: list[PersonaDayTrajectory]
    aggregate_monthly: list[dict]  # Monthly rollups for backward compat
    final_active_count: int
    final_active_rate: float
    total_revenue_estimate: float
    random_seed: int = 42
```

**Core engine function:**
```python
def run_event_simulation(
    population: Population,
    scenario: ScenarioConfig,
    duration_days: int = 360,  # ~12 months
    seed: int = 42,
    progress_callback: Callable[[float], None] | None = None,
) -> EventSimulationResult:
```

**Day loop algorithm (per persona):**
```python
for day in range(1, duration_days + 1):
    # 1. Fire deterministic events
    events = fire_deterministic_events(state, day, scenario)

    # 2. Fire stochastic events
    events += fire_stochastic_events(state, persona, day, scenario, rng)

    # 3. Apply event impacts to state
    for event in events:
        apply_event_impact(state, event, persona)

    # 4. Apply daily dynamics (decay/growth)
    apply_daily_dynamics(state)

    # 5. Evaluate decisions at decision points
    decision = None
    if is_decision_point(state, events):
        decision = evaluate_decision(state, thresholds, scenario, events)
        apply_decision(state, decision, scenario)

    # 6. Snapshot (every day, or sample for efficiency)
    snapshots.append(DaySnapshot(day, state.dict(), [...], decision, rationale))
```

**Important**: The event firing functions (`fire_deterministic_events`, `fire_stochastic_events`) and the event impact function (`apply_event_impact`) will be provided by Goose in `src/simulation/event_grammar.py`. Your engine should import and call them. Here is the interface contract:

```python
# From src/simulation/event_grammar.py (Goose's module):
class SimulationEvent(BaseModel):
    event_type: str          # e.g., "pack_finished", "child_rejection"
    day: int
    intensity: float         # [0, 1]
    attributes: dict = {}

def fire_deterministic_events(state: CanonicalState, day: int, scenario: ScenarioConfig) -> list[SimulationEvent]
def fire_stochastic_events(state: CanonicalState, persona: Persona, day: int, scenario: ScenarioConfig, rng: Random) -> list[SimulationEvent]
def apply_event_impact(state: CanonicalState, event: SimulationEvent, persona: Persona) -> None
```

**If Goose's module is not yet available**, create a temporary stub `src/simulation/event_grammar.py` with these functions returning minimal default events (pack_finished every 25 days, one ad_exposure per week). This allows your engine to be tested independently.

### Task 3: Decision Evaluation — In `src/simulation/event_engine.py`

Implement the decision rules from `CANONICAL-STATE-MODEL-V1.md`:

```python
def evaluate_decision(
    state: CanonicalState,
    thresholds: dict[str, float],
    scenario: ScenarioConfig,
    active_events: list[SimulationEvent],
) -> str:
    """Evaluate what decision the persona makes at this decision point.

    Returns: "purchase", "reorder", "switch", "churn", "delay", "subscribe"
    """
```

**First purchase** (when `not state.ever_adopted`):
- Check brand_salience > awareness_threshold AND trust > trust_threshold AND perceived_value > price_salience AND discretionary_budget > price_ratio * 0.3 AND effort_friction < 0.7

**Repeat purchase** (at pack_finished event, when `state.is_active`):
- REORDER if: reorder_urgency > 0.4, habit_strength > 0.2, child_acceptance > 0.3, perceived_value > price_salience, fatigue < 0.6, discretionary_budget > price_ratio * 0.25
- SWITCH if: not reorder AND price_salience > 0.6 AND competitor_discount in active_events AND trust < 0.5
- CHURN if: not reorder/switch AND (child_acceptance < 0.2 OR fatigue > 0.7 OR trust < 0.3)
- DELAY otherwise

**Decision rationale**: Return the top 3 state variables that most influenced the decision (largest gap between value and threshold).

### Task 4: Monthly Rollup for Backward Compatibility

The existing Results page and trajectory clustering expect monthly data. Add a function:

```python
def rollup_to_monthly(trajectories: list[PersonaDayTrajectory], duration_days: int) -> list[dict]:
    """Aggregate day-level trajectories into monthly snapshots matching MonthlySnapshot format."""
```

Each monthly dict should have: `month, new_adopters, repeat_purchasers, churned, total_active, cumulative_adopters, awareness_level_mean, lj_pass_holders`.

### Task 5: Constants

Add all new constants to `src/constants.py`:
```python
# --- Event Engine ---
DEFAULT_PACK_DURATION_DAYS = 25
EVENT_BRAND_SALIENCE_DECAY_PER_DAY = 0.02
EVENT_FATIGUE_GROWTH_PER_DAY = 0.0043  # 0.03/week
EVENT_HABIT_DECAY_PER_DAY = 0.0017     # 0.05/month when inactive
EVENT_REORDER_URGENCY_RAMP_DAYS = 5    # Ramp starts 5 days before pack empty
EVENT_DEFAULT_DURATION_DAYS = 360
```

### Files to Create
- `src/simulation/state_model.py`
- `src/simulation/event_engine.py`
- `src/simulation/event_grammar.py` (stub — will be replaced by Goose's implementation)

### Files to Modify
- `src/constants.py` (add event engine constants)

### Constraints
- All state values clipped to [0, 1] after every mutation
- Deterministic given seed: `random.Random(seed)` passed through, no global state
- All new code fully type-hinted
- Pydantic BaseModel for all data structures
- Run `uv run ruff check .` and `uv run pytest tests/ -x -q` before delivery
