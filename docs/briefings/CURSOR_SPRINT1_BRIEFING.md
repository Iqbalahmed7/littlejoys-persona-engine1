# CURSOR — Sprint 1 Briefing

> **Role**: Senior Software Engineer
> **Sprint**: 1
> **Branch**: `feat/PRD-001-copula-generator` (create from `staging`)
> **Deadline**: End of Day 2

---

## YOUR ASSIGNMENTS

### Task 1: Gaussian Copula Generator (P0)
**File**: `src/taxonomy/correlations.py`
**PRD**: PRD-001, Deliverable D3

Implement `GaussianCopulaGenerator` that:
1. Takes a dict of `(attribute_a, attribute_b) → target_correlation` pairs
2. Builds a positive semi-definite correlation matrix (use `scipy.linalg` nearest PSD if needed)
3. Samples from a multivariate normal using the copula
4. Transforms marginals to uniform [0,1] via CDF
5. Applies demographic conditioning (shift distributions based on demographics)
6. Returns a DataFrame with all continuous psychographic attributes

**Key correlation rules to implement** (from ARCHITECTURE.md §5.2):
- `income` ↔ `budget_consciousness`: -0.55
- `health_anxiety` ↔ `supplement_belief`: +0.45
- `authority_bias` ↔ `social_proof_sensitivity`: +0.40
- `time_scarcity` ↔ `convenience_priority`: +0.50
- `online_shopping_comfort` ↔ `digital_comfort`: +0.65
- `price_sensitivity` ↔ `budget_consciousness`: +0.70
- `first_child_anxiety` ↔ `research_before_purchase`: +0.35
- ... (see ARCHITECTURE.md for complete list — implement ALL of them)

**Conditional rules** (`ConditionalRuleEngine`):
- Tier3 personas: `authority_bias += 0.10`, `digital_comfort -= 0.08`
- Working mothers (full_time): `time_scarcity += 0.15`, `work_guilt += 0.10`
- First child parents (num_children=1): `first_child_anxiety += 0.12`
- Joint family: `extended_family_influence += 0.15`, `joint_family_influence += 0.12`
- High income (>20 LPA): `brand_premium_willingness += 0.10`, `price_sensitivity -= 0.10`

Always clip to [0, 1] after shifts.

### Task 2: Population Generator Orchestrator (P0)
**File**: `src/generation/population.py`
**PRD**: PRD-003, Deliverable D1

Implement `PopulationGenerator.generate()` that chains:
1. `DistributionTables.sample_demographics(n, seed)` → demographics DataFrame
2. `GaussianCopulaGenerator.generate(n, demographics, seed)` → psychographics DataFrame
3. `ConditionalRuleEngine.apply(merged_df)` → shifted psychographics
4. `_assign_categoricals(demographics, psychographics)` → categorical attributes
5. Build Persona objects from flat dicts
6. `PersonaValidator.validate_persona()` for each → regenerate failures
7. `_select_for_tier2()` using k-medoids for diversity
8. Return `Population` object

Also implement `Population.to_dataframe()`, `.save()`, `.load()`, `.get_persona()`, `.filter()`.

### Task 3: Population Validation Report (P1)
**File**: `src/generation/population.py` (extend)
**PRD**: PRD-003, Deliverable D3

Generate validation report with chi-square tests for categoricals, KS tests for continuous, correlation matrix comparison.

---

## CONTEXT FILES TO READ

Before you start, read these files for full context:
1. `ARCHITECTURE.md` — especially §4 (Taxonomy), §5 (Schema/Correlations), §6 (Generation)
2. `src/taxonomy/schema.py` — the Pydantic models you'll be populating
3. `src/taxonomy/distributions.py` — Codex will implement this; your copula consumes its output
4. `src/taxonomy/validation.py` — Antigravity will implement this; your orchestrator calls it
5. `docs/DEVELOPMENT_PRACTICES.md` — code standards you must follow
6. `docs/prds/PRD-001-persona-schema-generation.md` — full spec
7. `docs/prds/PRD-003-population-generator.md` — full spec

## CODE STANDARDS (CRITICAL)

- All functions MUST have type hints
- All public functions MUST have Google-style docstrings
- No magic numbers — use `src/constants.py`
- Use `structlog` for logging, never `print()`
- All randomness must be seeded via `numpy.random.Generator(seed)`
- Run `uv run ruff check .` and `uv run pytest tests/unit/` before committing
- Write tests in `tests/unit/test_correlations.py` and `tests/unit/test_population.py`

## TESTS YOU MUST WRITE

```python
# tests/unit/test_correlations.py
test_correlation_matrix_is_positive_semi_definite()
test_copula_output_all_values_in_0_1()
test_target_correlations_achieved_within_tolerance()
test_deterministic_with_same_seed()
test_different_seed_produces_different_output()
test_conditional_rules_shift_tier3_authority_bias()
test_conditional_rules_shift_working_mother_time_scarcity()
test_conditional_rules_clip_to_valid_range()

# tests/unit/test_population.py
test_generate_returns_correct_count()
test_generate_deterministic_with_seed()
test_population_to_dataframe_has_all_columns()
test_population_save_and_load_roundtrip()
test_tier2_selection_maximizes_diversity()
test_filter_by_attribute_works()
```

## WHEN YOU'RE DONE

1. Ensure `uv run ruff check .` passes
2. Ensure `uv run pytest tests/unit/ -v` — all tests pass
3. Commit to your feature branch with a descriptive message
4. Notify the Tech Lead for code review
