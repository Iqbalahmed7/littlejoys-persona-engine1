# CODEX — Sprint 1 Briefing

> **Role**: Senior Software Engineer
> **Sprint**: 1
> **Branch**: `feat/PRD-001-schema-distributions` (create from `staging`)
> **Deadline**: End of Day 2

---

## YOUR ASSIGNMENTS

### Task 1: Complete Pydantic Schema — All 145 Attributes (P0)
**File**: `src/taxonomy/schema.py`
**PRD**: PRD-001, Deliverable D1

The schema stub already exists with ~80 attributes across 12 categories. Your job:
1. Review ARCHITECTURE.md §4.3 taxonomy tree
2. Add ALL missing attributes to reach the full 145
3. Add cross-field validators (e.g., `oldest_child_age >= youngest_child_age`)
4. Implement `Persona.from_flat_dict()` classmethod
5. Ensure `model_config = ConfigDict(frozen=True)` on all identity-layer models

**Key additions needed**:
- Complete the attribute list per ARCHITECTURE.md (some categories may need more fields)
- Add validators using `@model_validator(mode="after")` for cross-field checks
- Ensure `to_flat_dict()` / `from_flat_dict()` are inverse operations

### Task 2: Demographic Distribution Tables (P0)
**File**: `src/taxonomy/distributions.py`
**PRD**: PRD-001, Deliverable D2

Implement `DistributionTables` with real Indian demographic data:

```python
class DistributionTables:
    # City tier distribution
    CITY_TIER = {"Tier1": 0.45, "Tier2": 0.35, "Tier3": 0.20}

    # Household income (LPA) — tier-conditional lognormal
    INCOME_PARAMS = {
        "Tier1": {"mean": 18, "std": 8, "min": 5, "max": 80},
        "Tier2": {"mean": 12, "std": 6, "min": 3, "max": 50},
        "Tier3": {"mean": 7, "std": 4, "min": 2, "max": 30},
    }

    # Parent age — truncated normal
    PARENT_AGE = {"mean": 32, "std": 4, "min": 22, "max": 45}

    # Child age — uniform 2-14
    CHILD_AGE = {"min": 2, "max": 14}

    # Number of children
    NUM_CHILDREN = {1: 0.35, 2: 0.45, 3: 0.15, 4: 0.04, 5: 0.01}

    # Education — tier-conditional
    EDUCATION = {
        "Tier1": {"high_school": 0.05, "bachelors": 0.35, "masters": 0.40, "doctorate": 0.10, "professional": 0.10},
        "Tier2": {"high_school": 0.15, "bachelors": 0.40, "masters": 0.30, "doctorate": 0.08, "professional": 0.07},
        "Tier3": {"high_school": 0.30, "bachelors": 0.40, "masters": 0.20, "doctorate": 0.05, "professional": 0.05},
    }

    # Employment status
    EMPLOYMENT = {"homemaker": 0.30, "full_time": 0.35, "part_time": 0.15, "self_employed": 0.12, "freelance": 0.08}

    # Family structure — tier-conditional
    FAMILY_STRUCTURE = {
        "Tier1": {"nuclear": 0.65, "joint": 0.25, "single_parent": 0.10},
        "Tier2": {"nuclear": 0.50, "joint": 0.40, "single_parent": 0.10},
        "Tier3": {"nuclear": 0.35, "joint": 0.55, "single_parent": 0.10},
    }

    # Dietary culture — region proxy via tier
    DIETARY = {
        "Tier1": {"vegetarian": 0.30, "eggetarian": 0.15, "non_vegetarian": 0.50, "vegan": 0.05},
        "Tier2": {"vegetarian": 0.35, "eggetarian": 0.15, "non_vegetarian": 0.45, "vegan": 0.05},
        "Tier3": {"vegetarian": 0.40, "eggetarian": 0.15, "non_vegetarian": 0.40, "vegan": 0.05},
    }
```

Implement `sample_demographics(n, seed)` that:
1. Samples city_tier from multinomial
2. Conditionally samples income, education, family_structure, dietary from tier-specific distributions
3. Samples parent_age from truncated normal
4. Samples child ages consistent with parent age
5. Assigns city names randomly within tier
6. Returns a fully populated DataFrame

**City name mapping** (sample from these per tier):
- Tier1: Mumbai, Delhi, Bangalore, Hyderabad, Chennai, Pune, Kolkata, Ahmedabad
- Tier2: Jaipur, Lucknow, Chandigarh, Kochi, Indore, Bhopal, Nagpur, Coimbatore, Visakhapatnam, Surat
- Tier3: Mangalore, Mysore, Dehradun, Udaipur, Raipur, Ranchi, Bhubaneswar, Guwahati

### Task 3: LLM Wrapper Implementation (P0 — carry from Sprint 0)
**File**: `src/utils/llm.py`
**PRD**: PRD-000, Deliverable D4

Implement the full `LLMClient`:
1. Use `anthropic` SDK for API calls
2. Implement disk cache in `data/.llm_cache/` — key = SHA256(model+system+prompt+temp), value = JSON file
3. Mock mode: when `config.llm_mock_enabled`, return deterministic fixtures
4. Retry with exponential backoff (3 retries, 1s base delay)
5. Batch generation with `asyncio.Semaphore(max_concurrency)`
6. Token usage tracking via `TokenUsageTracker`
7. Structured JSON output: parse response, validate with Pydantic if schema provided

### Task 4: Tier 2 Narrative Generator (P0)
**File**: `src/generation/tier2_generator.py`
**PRD**: PRD-003, Deliverable D2

Implement progressive LLM attribute sampling:
1. **Anchor**: Extract core demographics + top 5 psychographic values
2. **Values inference**: LLM generates 3-5 core values from anchors
3. **Life story**: LLM generates 2-3 specific life story snippets
4. **Full narrative**: LLM synthesizes 300-500 word third-person biography

Use `model="bulk"` (Sonnet) for cost efficiency. Cache all outputs.

Prompts must:
- Reference at least 10 specific persona attributes in output
- Be unique per persona (no template phrases)
- Include Hindi-English code-mixing where culturally appropriate
- Be coherent with ALL numeric attributes

---

## CONTEXT FILES TO READ

Before you start, read these files for full context:
1. `ARCHITECTURE.md` — especially §4.3 (Taxonomy), §5 (Schema), §6 (Generation)
2. `src/taxonomy/schema.py` — the existing schema stub you'll complete
3. `src/utils/llm.py` — the existing LLM client stub you'll implement
4. `src/generation/tier2_generator.py` — the Tier 2 stub you'll implement
5. `docs/DEVELOPMENT_PRACTICES.md` — code standards
6. `docs/prds/PRD-001-persona-schema-generation.md` — full spec
7. `docs/prds/PRD-003-population-generator.md` — Tier 2 spec

## CODE STANDARDS (CRITICAL)

- All functions MUST have type hints
- All public functions MUST have Google-style docstrings
- No magic numbers — use `src/constants.py`
- Use `structlog` for logging, never `print()`
- All randomness must be seeded
- Run `uv run ruff check .` and `uv run pytest tests/unit/` before committing

## TESTS YOU MUST WRITE

```python
# tests/unit/test_schema.py
test_persona_creation_with_all_fields()
test_persona_from_flat_dict_roundtrip()
test_demographics_frozen_after_creation()
test_cross_field_validator_child_age()
test_continuous_attributes_bounded_0_1()
test_categorical_attributes_valid_enum()

# tests/unit/test_distributions.py
test_sample_demographics_returns_correct_count()
test_sample_demographics_deterministic_with_seed()
test_city_tier_distribution_approximately_correct()
test_income_conditional_on_tier()
test_child_age_within_valid_range()
test_parent_age_within_valid_range()

# tests/unit/test_llm.py
test_mock_mode_returns_deterministic_response()
test_cache_key_deterministic()
test_cache_hit_returns_cached_response()
test_token_usage_tracking()
```

## WHEN YOU'RE DONE

1. Ensure `uv run ruff check .` passes
2. Ensure `uv run pytest tests/unit/ -v` — all tests pass
3. Commit to your feature branch with a descriptive message
4. Notify the Tech Lead for code review
