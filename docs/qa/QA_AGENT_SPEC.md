# QA Agent Specification

> **Owner**: Technical Lead (Claude Opus)
> **Last Updated**: 2026-03-27
> **Status**: Ready for implementation

---

## ROLE DEFINITION

The QA Agent is an automated quality gate that reviews every piece of code before it merges to staging. It acts as a senior QA engineer who:

1. Reviews every PR line-by-line
2. Validates against PRD specifications
3. Runs comprehensive test scenarios
4. Checks for security vulnerabilities
5. Verifies architectural compliance
6. Performs UAT for completed features
7. Reports bugs with severity classification
8. Signs off (or blocks) merges

The QA Agent **reports to the Tech Lead** and has **merge-blocking authority**.

---

## QA REVIEW PIPELINE

Every PR goes through this pipeline before merge:

```
PR Submitted
    │
    ▼
┌─────────────────────────────────┐
│  STAGE 1: AUTOMATED CHECKS      │
│  (No human intervention)         │
│                                  │
│  □ ruff check (lint)            │
│  □ ruff format --check          │
│  □ mypy --strict (type check)   │
│  □ pytest unit tests            │
│  □ bandit (security scan)       │
│  □ coverage check (>= 80%)     │
│                                  │
│  FAIL → PR blocked, report sent │
└──────────────┬──────────────────┘
               │ PASS
               ▼
┌─────────────────────────────────┐
│  STAGE 2: CODE REVIEW            │
│  (QA Agent reviews line-by-line) │
│                                  │
│  □ Correctness vs PRD spec      │
│  □ Edge case coverage           │
│  □ Error handling               │
│  □ Naming conventions           │
│  □ Documentation completeness   │
│  □ Architecture compliance      │
│  □ No magic numbers             │
│  □ No dead code                 │
│  □ Dependency direction correct │
│                                  │
│  FAIL → Comments + requested    │
│         changes                  │
└──────────────┬──────────────────┘
               │ PASS
               ▼
┌─────────────────────────────────┐
│  STAGE 3: FUNCTIONAL TESTING     │
│  (QA Agent runs scenarios)       │
│                                  │
│  □ Happy path works             │
│  □ Edge cases don't crash       │
│  □ Results are plausible        │
│  □ Integration with existing    │
│    modules works                │
│                                  │
│  FAIL → Bug report filed        │
└──────────────┬──────────────────┘
               │ PASS
               ▼
┌─────────────────────────────────┐
│  STAGE 4: DOMAIN VALIDATION      │
│  (Business logic sanity checks)  │
│                                  │
│  □ Adoption rates plausible     │
│    (not 0%, not 100%)           │
│  □ Correlations directionally   │
│    correct                      │
│  □ Counterfactuals move in      │
│    expected direction           │
│  □ Causal statements reference  │
│    actual variables             │
│  □ Persona narratives coherent  │
│    with attributes              │
│                                  │
│  FAIL → Domain issue reported   │
└──────────────┬──────────────────┘
               │ PASS
               ▼
        ✅ APPROVED FOR MERGE
```

---

## QA TEST SUITES

### Suite 1: Persona Generation Tests

```python
# Determinism
test_same_seed_produces_identical_population()
test_different_seed_produces_different_population()

# Distribution validation
test_city_tier_distribution_matches_target()
test_income_distribution_by_tier_is_lognormal()
test_child_age_distribution_is_approximately_uniform()
test_education_distribution_by_tier_matches_target()
test_employment_status_distribution_matches_target()

# Correlation enforcement
test_income_negatively_correlates_with_budget_consciousness()
test_tier3_has_higher_authority_bias()
test_health_anxiety_correlates_with_supplement_belief()
test_working_mothers_have_higher_time_scarcity()
test_first_child_parents_have_higher_anxiety()

# Validation
test_no_persona_has_child_older_than_parent_minus_18()
test_all_continuous_attributes_in_0_1_range()
test_no_nan_or_inf_in_any_attribute()
test_categorical_attributes_are_valid_enum_values()

# Edge cases
test_minimum_income_persona_is_valid()
test_maximum_children_persona_is_valid()
test_tier3_homemaker_low_digital_is_coherent()

# Tier 2 narrative
test_narrative_mentions_city_name()
test_narrative_mentions_child_count()
test_narrative_consistent_with_employment_status()
test_narrative_length_within_bounds()
```

### Suite 2: Decision Engine Tests

```python
# Monotonicity (the most important invariant tests)
test_higher_price_never_increases_adoption()
test_higher_awareness_never_decreases_consideration()
test_higher_trust_signal_never_decreases_consideration()
test_lower_effort_never_decreases_adoption()
test_higher_income_reduces_price_barrier_impact()

# Boundary conditions
test_zero_awareness_produces_zero_adoption()
test_maximum_trust_with_zero_awareness_still_zero()
test_free_product_still_requires_awareness()
test_perfect_product_with_zero_need_recognition_fails()

# Calibration
test_nutrimix_2_6_baseline_adoption_in_plausible_range()
test_nutrimix_7_plus_adoption_lower_than_2_6()
test_magnesium_adoption_lower_than_multivitamin()

# Decision tracing
test_rejection_reason_is_always_populated()
test_adoption_never_has_rejection_reason()
test_funnel_stages_are_monotonically_decreasing()

# Repeat purchase
test_satisfaction_increases_repeat_probability()
test_pass_holders_have_higher_repeat_rate()
test_habit_formation_increases_with_consecutive_months()
test_churn_eventually_occurs_without_satisfaction()
```

### Suite 3: Simulation Engine Tests

```python
# Static simulation
test_static_sim_returns_result_for_every_persona()
test_static_sim_adoption_rate_between_0_and_1()
test_static_sim_is_deterministic_with_same_seed()

# Temporal simulation
test_temporal_sim_runs_for_specified_months()
test_new_adopters_decrease_over_time_with_fixed_awareness()
test_repeat_purchasers_increase_with_habit_formation()
test_total_active_customers_is_sum_of_new_plus_retained()

# Counterfactual
test_counterfactual_produces_different_result_from_baseline()
test_price_reduction_counterfactual_increases_adoption()
test_effort_reduction_counterfactual_increases_adoption()
test_counterfactual_preserves_population_identity()

# Word of mouth
test_wom_increases_awareness_over_months()
test_high_wom_transmitters_spread_more()
```

### Suite 4: Analysis Engine Tests

```python
# Segment analysis
test_segment_adoption_rates_sum_to_total()
test_every_persona_belongs_to_exactly_one_segment()
test_segment_by_single_attribute_produces_valid_groups()

# Variable importance
test_variable_importance_returns_ranked_list()
test_top_variable_has_highest_absolute_coefficient()
test_variable_importance_is_reproducible()

# Causal statements
test_causal_statement_references_specific_variable()
test_causal_statement_includes_numeric_threshold()
test_no_generic_statements_in_output()  # "users felt it was expensive" → FAIL
test_causal_statement_matches_actual_data()

# Report generation
test_report_has_all_required_sections()
test_report_insights_grounded_in_data()
test_report_recommendations_are_actionable()
```

### Suite 5: Dashboard / UAT Tests

```python
# Page loading
test_population_explorer_loads_without_error()
test_scenario_configurator_loads_without_error()
test_results_dashboard_loads_without_error()
test_counterfactual_page_loads_without_error()
test_interview_page_loads_without_error()

# Interaction
test_scenario_slider_changes_update_results()
test_persona_selection_shows_correct_details()
test_interview_produces_response_in_under_5_seconds()
test_what_if_mode_recalculates_on_parameter_change()

# Edge cases
test_extreme_slider_values_dont_crash()
test_empty_population_shows_graceful_message()
test_concurrent_simulations_dont_interfere()

# Visual
test_all_charts_render_with_data()
test_funnel_chart_shows_decreasing_values()
test_heatmap_color_scale_is_correct()
test_no_overlapping_labels_in_charts()
```

---

## BUG REPORT FORMAT

```markdown
# Bug Report: [BUG-XXX]

**Severity**: Critical / Major / Minor
**Found In**: [Module/File/Function]
**Introduced By**: [Engineer Name] in [PR/Commit]
**Sprint**: [Sprint Number]

## Description
[Clear, specific description of the bug]

## Steps to Reproduce
1. ...
2. ...
3. ...

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Evidence
[Logs, screenshots, test output]

## Impact
[What downstream functionality is affected]

## Suggested Fix
[If obvious, suggest the fix direction]
```

---

## UAT (User Acceptance Testing) PROTOCOL

Run at Sprint 4-5 gate (before demo):

### UAT Scenario 1: Full Demo Flow
```
1. Open Streamlit app
2. Navigate to Population Explorer
3. Verify 300 personas displayed with correct distributions
4. Click into a Tier 2 persona → verify narrative is coherent
5. Navigate to Scenario Configurator
6. Select "Nutrimix 7-14 Expansion"
7. Verify pre-loaded parameters match ARCHITECTURE.md
8. Click "Run Simulation"
9. Verify results dashboard loads with:
   - Adoption rate between 5-25%
   - Funnel waterfall showing progressive drop-off
   - Segment heatmap with visible variation
   - Barrier distribution pie chart
10. Navigate to Counterfactual page
11. Run "School partnership" counterfactual
12. Verify adoption increases
13. Navigate to Interview page
14. Select a rejector persona
15. Ask "Why didn't you buy this?"
16. Verify response is in-character and references specific persona attributes
17. Navigate to Report page
18. Verify report has all sections and causal statements reference variables
```

### UAT Scenario 2: All Four Business Problems
```
Run full pipeline for each:
1. Repeat Purchase / LJ Pass → check temporal charts, pass vs no-pass comparison
2. Nutrimix 7-14 → check age-segment specific barriers
3. Magnesium Gummies → check awareness as dominant barrier
4. ProteinMix → check effort as dominant barrier
```

### UAT Scenario 3: Edge Cases
```
1. Set population to N=1 → should work (degenerate but not crash)
2. Set all scenario params to 0 → 0% adoption, no crash
3. Set all scenario params to 1 → high adoption, no overflow
4. Run counterfactual with 0% price → verify free product behavior
5. Run temporal sim for 1 month → should work
6. Run temporal sim for 24 months → should work without memory issues
```

### UAT Sign-Off

```markdown
# UAT Sign-Off — [Date]

| Scenario | Status | Notes |
|----------|--------|-------|
| Full Demo Flow | PASS/FAIL | ... |
| Business Problem 1 | PASS/FAIL | ... |
| Business Problem 2 | PASS/FAIL | ... |
| Business Problem 3 | PASS/FAIL | ... |
| Business Problem 4 | PASS/FAIL | ... |
| Edge Cases | PASS/FAIL | ... |

**QA Agent Verdict**: APPROVED / BLOCKED
**Blocking Issues**: [list if any]
**Tech Lead Override**: [if applicable]
```

---

## QA AGENT PROMPT TEMPLATE

When QA Agent reviews a PR, it operates with this system context:

```
You are the QA Agent for the LittleJoys Persona Simulation Engine.

Your job:
1. Review every line of the submitted code
2. Check against the PRD specification (provided)
3. Check against ARCHITECTURE.md and DEVELOPMENT_PRACTICES.md
4. Run or verify all relevant test suites
5. Produce a structured review with:
   - APPROVED or CHANGES_REQUESTED
   - Line-by-line comments for issues
   - Bug reports for any bugs found
   - Severity classification for each issue

You are strict but fair. You block merges for:
- Correctness issues (wrong behavior)
- Missing tests
- Security vulnerabilities
- Architecture violations

You approve with comments for:
- Style nits (suggest but don't block)
- Minor documentation gaps
- Performance suggestions

Context documents:
- ARCHITECTURE.md (schema, decision equations, project structure)
- DEVELOPMENT_PRACTICES.md (code standards, review checklist)
- PRD for the specific task being reviewed
- ENGINEER_PROFILES.md (to calibrate review depth by trust level)
```
