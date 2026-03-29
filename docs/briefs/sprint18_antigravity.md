# Sprint 18 Brief — Antigravity (Gemini 3.1 Pro — Upgrade for this sprint)
## Tests for Complete Grammar + Counterfactual + Executive Summary

### Context

Sprint 18 has 4 parallel workstreams: complete event grammar (Goose), repeat fix + counterfactual engine (Codex), executive summary + UI (Cursor), retention curve (OpenCode). You test all of them.

### Dependency
Wait for ALL other engineers to deliver before writing tests. You are the last to execute.

### Task 1: Complete Event Grammar Tests (`tests/unit/test_event_grammar.py`)

The existing file has 8 tests for the 4 original events. Add tests for the 11 new event types:

```python
def test_child_positive_reaction_fires_when_active():
    """child_positive_reaction should only fire when persona is active."""

def test_child_boredom_requires_fatigue():
    """child_boredom should only fire when fatigue > threshold."""

def test_usage_consistent_boosts_habit():
    """usage_consistent impact should increase habit_strength."""

def test_usage_drop_increases_fatigue():
    """usage_drop should increase fatigue and decrease perceived_value."""

def test_budget_pressure_increases_price_salience():
    """budget_pressure_increase should raise price_salience and lower budget."""

def test_influencer_exposure_boosts_brand_and_trust():
    """influencer_exposure should increase brand_salience and trust."""

def test_doctor_recommendation_high_impact():
    """doctor_recommendation should have larger trust impact than other events."""

def test_reminder_fires_for_inactive_adopters():
    """reminder should only fire when persona is inactive and has previously adopted."""

def test_pass_offer_fires_for_qualified_buyers():
    """pass_offer requires active + 2+ purchases + no existing pass."""

def test_all_fifteen_event_types_have_impact_handlers():
    """Every event type constant in constants.py should have a handler in apply_event_impact."""
```

### Task 2: Counterfactual Engine Tests (`tests/unit/test_counterfactual.py` — NEW)

```python
def test_generate_default_counterfactuals():
    """Default generator produces 8-12 scenarios."""

def test_counterfactual_result_structure():
    """Each result has all required fields."""

def test_counterfactual_lift_computation():
    """Lift = counterfactual_active_rate - baseline_active_rate."""

def test_counterfactual_determinism():
    """Same seed produces identical results."""

def test_counterfactual_report_sorted_by_lift():
    """Results should be sorted by lift descending."""
```

### Task 3: Executive Summary Tests (`tests/unit/test_executive_summary.py` — NEW)

```python
def test_executive_summary_mock_mode():
    """Mock mode returns a valid ExecutiveSummary without LLM call."""

def test_executive_summary_structure():
    """Summary has headline, trajectory_summary, key_drivers, recommendations, risk_factors."""

def test_executive_summary_drivers_non_empty():
    """key_drivers should have at least 1 entry."""
```

### Task 4: Repeat Purchase Fix Validation (`tests/unit/test_event_engine.py`)

Add to the existing test file:

```python
def test_repeat_purchase_possible():
    """At least some personas should reorder within a 360-day simulation."""
    # Run 200-persona simulation
    # Assert total repeat purchases > 0

def test_not_100_percent_churn():
    """Final active rate should be > 0 for a 360-day simulation."""

def test_habit_builds_over_purchases():
    """After 2+ purchases, habit_strength should exceed 0.2."""
```

### Task 5: Integration Pipeline Test (`tests/integration/test_event_pipeline.py`)

Add to the existing file:

```python
def test_counterfactual_in_pipeline():
    """Verify counterfactual results appear in ConsolidatedReport."""

def test_nutrimix_7_14_runs_temporal():
    """nutrimix_7_14 should now produce event_result when run in temporal mode."""
```

### Files to Create
- `tests/unit/test_counterfactual.py`
- `tests/unit/test_executive_summary.py`

### Files to Modify
- `tests/unit/test_event_grammar.py`
- `tests/unit/test_event_engine.py`
- `tests/integration/test_event_pipeline.py`

### Constraints
- All tests must run in < 60 seconds total
- Use mock mode for any LLM-dependent tests
- Use small populations (10-20 personas) for speed
- Run `uv run ruff check .` and `uv run pytest tests/ -x -q` before delivery
