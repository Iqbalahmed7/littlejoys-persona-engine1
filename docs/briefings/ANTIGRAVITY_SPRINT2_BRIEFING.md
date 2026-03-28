# ANTIGRAVITY — Sprint 2 Briefing

> **Role**: Software Engineer (Standard Trust — 3.15)
> **Sprint**: 2
> **Branch**: `feat/PRD-006-wom` (create from `staging`)
> **Deadline**: End of Day 4

---

## YOUR ASSIGNMENTS

### Task 1: Word-of-Mouth Propagation (P1)
**File**: `src/simulation/wom.py`
**PRD**: PRD-006, D3

Implement `propagate_wom()`:

```python
def propagate_wom(
    population: Population,
    adopter_ids: list[str],
    month: int,
    transmission_rate: float = 0.15,
    decay: float = 0.85,
) -> dict[str, float]:
```

Logic:
1. For each adopter in `adopter_ids`:
   - Get their `wom_transmitter_score` from persona attributes
   - If `wom_transmitter_score > 0.3`: this persona is an active transmitter
   - Each transmitter reaches 3-5 random non-adopters (sample from population)
   - Use seeded RNG: `np.random.default_rng(seed=hash(persona_id) + month)`
2. For each reached non-adopter:
   - awareness_boost = transmitter_score × transmission_rate × (decay ** month)
   - Receiver's `social_proof_bias` amplifies: boost × (1 + social_proof_bias)
3. Aggregate: if a non-adopter is reached by multiple transmitters, sum the boosts (cap at 0.3 per month)
4. Return dict of persona_id → total awareness_boost

**Important**: WOM does NOT affect existing adopters. Only non-adopters receive awareness boosts.

### Task 2: Variable Importance Analysis (P1)
**File**: `src/analysis/causal.py`
**PRD**: PRD-008 (Sprint 3 early start)

Implement `compute_variable_importance()`:
1. Take simulation results (persona flat dicts + outcome 0/1)
2. Fit logistic regression: outcome ~ all continuous attributes
3. Extract coefficients → rank by absolute value
4. Compute SHAP values using `shap.LinearExplainer`
5. Return sorted list of `VariableImportance` objects

This is a Sprint 3 task being started early because you have capacity and it's self-contained.

### Task 3: Funnel Waterfall Data (P1)
**File**: `src/analysis/barriers.py`

Implement `analyze_barriers()`:
1. Take static simulation results
2. Count rejections at each funnel stage
3. Count specific rejection reasons within each stage
4. Return list of `BarrierDistribution` objects

---

## CONTEXT FILES TO READ

1. `src/simulation/wom.py` — existing stub
2. `src/taxonomy/schema.py` — persona attributes (wom_transmitter_score, social_proof_bias)
3. `src/generation/population.py` — Population object
4. `src/analysis/causal.py` — existing stub for variable importance
5. `src/analysis/barriers.py` — existing stub for barrier analysis
6. `docs/prds/PRD-006-simulation-runners.md` — WOM spec

## CODE STANDARDS REMINDER

Based on Sprint 1 review:
- Use `structlog`, not `logging` (you fixed this last sprint — keep it consistent)
- No duplicate logic — check for existing checks before adding new ones
- Test edge cases: empty adopter list, all personas already adopted, month=0

## TESTS TO WRITE

```python
# tests/unit/test_wom.py
test_wom_returns_awareness_boost_for_non_adopters()
test_wom_boost_decays_over_months()
test_high_transmitter_spreads_more()
test_wom_does_not_affect_existing_adopters()
test_wom_boost_capped_per_month()
test_wom_empty_adopter_list_returns_empty()
test_wom_deterministic_per_persona()

# tests/unit/test_barriers.py
test_barrier_distribution_sums_to_rejections()
test_every_rejection_has_a_reason()
test_barrier_analysis_empty_results()

# tests/unit/test_variable_importance.py
test_variable_importance_returns_ranked_list()
test_top_variable_has_highest_coefficient()
test_variable_importance_reproducible()
```

## WHEN DONE

1. `uv run ruff check .` passes
2. `uv run pytest tests/unit/ -v` — all tests pass
3. Commit: `feat(simulation): WOM propagation, variable importance, barrier analysis`
4. Notify Tech Lead
