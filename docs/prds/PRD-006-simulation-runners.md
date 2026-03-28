# PRD-006: Simulation Runners (Static + Temporal)

> **Sprint**: 2
> **Priority**: P0 (Critical Path)
> **Assignee**: Cursor
> **Depends On**: PRD-004 (decision engine), PRD-005 (scenarios)
> **Status**: Ready for Development

---

## Objective

Build the two simulation modes: static (single-pass funnel) and temporal (month-by-month with repeat purchase, WOM, and churn).

---

## Deliverables

### D1: Static Simulation (Mode A)

**File**: `src/simulation/static.py`

```python
def run_static_simulation(population, scenario, thresholds, seed) -> StaticSimulationResult:
```

1. Load calibrated thresholds (or use provided)
2. For each Tier 1 persona: `run_funnel(persona, scenario)` → `DecisionResult`
3. Aggregate: adoption count, adoption rate, rejection distribution by stage
4. Return `StaticSimulationResult` with per-persona results and aggregates

### D2: Temporal Simulation (Mode B)

**File**: `src/simulation/temporal.py`

```python
def run_temporal_simulation(population, scenario, thresholds, months, seed) -> TemporalSimulationResult:
```

Month-by-month loop:
1. **Awareness growth**: base awareness increases monthly (marketing budget effect)
2. **New adopters**: personas who now pass the funnel (weren't aware before, now are)
3. **WOM propagation**: adopters spread awareness to non-adopters (call `propagate_wom`)
4. **Repeat purchase**: existing adopters decide to repurchase or churn
5. **LJ Pass**: pass holders have higher repeat rate and lower churn
6. **Snapshot**: record MonthlySnapshot (new_adopters, repeat, churned, total_active)

Return `TemporalSimulationResult` with monthly snapshots and final metrics.

### D3: Word-of-Mouth Propagation

**File**: `src/simulation/wom.py`
**Assignee**: Antigravity

```python
def propagate_wom(population, adopter_ids, month, transmission_rate, decay) -> dict[str, float]:
```

1. For each adopter: `wom_transmitter_score` determines probability of spreading
2. Each adopter "reaches" ~3-5 random non-adopters (social network size proxy)
3. Awareness boost = `transmitter_score × transmission_rate × decay^month`
4. Receiving persona's `social_proof_bias` amplifies the boost
5. Return dict of persona_id → awareness_delta

---

## Tests

```python
# tests/unit/test_static_sim.py
test_static_returns_result_for_every_persona()
test_static_adoption_rate_between_0_and_1()
test_static_deterministic_with_seed()
test_static_rejection_distribution_sums_to_rejections()

# tests/unit/test_temporal_sim.py
test_temporal_runs_for_specified_months()
test_awareness_increases_over_time()
test_cumulative_adopters_never_decrease()
test_temporal_deterministic_with_seed()
test_lj_pass_holders_have_lower_churn()

# tests/unit/test_wom.py
test_wom_returns_awareness_boost_for_non_adopters()
test_wom_boost_decays_over_months()
test_high_transmitter_spreads_more()
test_wom_does_not_affect_existing_adopters()
```

---

## Acceptance Criteria

- [ ] Static sim runs all 300 personas in < 5 seconds
- [ ] Temporal sim runs 12 months in < 30 seconds
- [ ] No NaN/Inf in any output
- [ ] Monthly snapshots show plausible dynamics (awareness grows, adoption follows)
- [ ] All tests pass
