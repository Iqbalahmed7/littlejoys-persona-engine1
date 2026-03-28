# CURSOR — Sprint 2 Briefing

> **Role**: Senior Software Engineer (High Trust — 3.90)
> **Sprint**: 2
> **Branch**: `feat/PRD-004-decision-engine` (create from `staging`)
> **Deadline**: End of Day 4

---

## YOUR ASSIGNMENTS

### Task 1: Purchase Funnel — Layers 0-3 (P0)
**File**: `src/decision/funnel.py`
**PRD**: PRD-004

Implement the 4-layer purchase funnel. Each layer is a pure function:

**Layer 0 — Need Recognition**:
```python
def compute_need_recognition(persona: Persona, scenario: ScenarioConfig) -> float:
```
Weighted sum of health_anxiety (0.20), nutrition_gap_awareness (0.25), child_health_proactivity (0.20), immunity_concern (0.15), growth_concern (0.15). Multiply by age_relevance_factor (1.0 if child in target range, 0.3 if outside).

**Layer 1 — Awareness**:
```python
def compute_awareness(persona: Persona, scenario: ScenarioConfig) -> float:
```
Base = marketing budget × channel-persona match. Boosts: pediatrician (+0.15 if trust > 0.6), school (+0.20 if engagement > 0.5), influencer (+0.10 if trust > 0.5).

**Layer 2 — Consideration**:
```python
def compute_consideration(persona: Persona, scenario: ScenarioConfig, awareness: float) -> float:
```
Awareness × trust_factor × research_factor × cultural_fit × brand_factor × risk_factor.

**Layer 3 — Purchase**:
```python
def compute_purchase(persona: Persona, scenario: ScenarioConfig, consideration: float) -> tuple[float, str | None]:
```
Consideration × (value + emotional - price_barrier - effort_barrier). Returns (score, rejection_reason).

**Full funnel runner**:
```python
def run_funnel(persona: Persona, scenario: ScenarioConfig, thresholds: dict[str, float] | None = None) -> DecisionResult:
```

Read PRD-004 for full formulas. Key invariants:
- Every rejection MUST have a specific reason (not generic)
- Scores must be clipped to [0, 1]
- If rejected at layer N, layers N+1.. score 0

### Task 2: Repeat Purchase Model (P0)
**File**: `src/decision/repeat.py`
**PRD**: PRD-004, D5

Implement satisfaction, repeat probability, and churn. See PRD-004 for formulas.

### Task 3: Static Simulation Runner (P0)
**File**: `src/simulation/static.py`
**PRD**: PRD-006, D1

Chain: load population → run_funnel for each persona → aggregate results → return StaticSimulationResult.

### Task 4: Temporal Simulation Runner (P0)
**File**: `src/simulation/temporal.py`
**PRD**: PRD-006, D2

Month-by-month loop with awareness growth, new adopters, WOM, repeat purchase, churn.

---

## CONTEXT FILES TO READ

1. `ARCHITECTURE.md` §8 (Decision Model), §9 (Simulation)
2. `src/taxonomy/schema.py` — persona attributes you'll reference in formulas
3. `src/decision/scenarios.py` — scenario configs (Codex will implement, but read the PRD-005 for structure)
4. `src/generation/population.py` — Population object you'll consume
5. `docs/prds/PRD-004-decision-engine.md` — full decision spec
6. `docs/prds/PRD-006-simulation-runners.md` — full simulation spec

## DEPENDENCY NOTE

Your decision functions need `ScenarioConfig` from `src/decision/scenarios.py`. Codex is implementing the full configs, but the Pydantic models already exist as stubs. Code against the existing `ScenarioConfig`, `ProductConfig`, `MarketingConfig` models — they won't change shape.

## TESTS TO WRITE

See PRD-004 and PRD-006 for full test lists. Minimum:
- `tests/unit/test_funnel.py` — 10 tests
- `tests/unit/test_repeat.py` — 5 tests
- `tests/unit/test_static_sim.py` — 4 tests
- `tests/unit/test_temporal_sim.py` — 5 tests

## WHEN DONE

1. `uv run ruff check .` passes
2. `uv run pytest tests/unit/ -v` — all tests pass
3. Commit: `feat(decision): purchase funnel layers 0-4 with static and temporal simulation`
4. Notify Tech Lead
