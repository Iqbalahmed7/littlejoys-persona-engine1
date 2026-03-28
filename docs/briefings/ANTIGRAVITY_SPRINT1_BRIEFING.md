# ANTIGRAVITY — Sprint 1 Briefing

> **Role**: Software Engineer
> **Sprint**: 1
> **Branch**: `feat/PRD-001-validation` (create from `staging`)
> **Deadline**: End of Day 2

---

## YOUR ASSIGNMENTS

### Task 1: Persona Validation Framework (P0)
**File**: `src/taxonomy/validation.py`
**PRD**: PRD-001, Deliverable D5

Implement `PersonaValidator` with two levels of validation:

**Hard failures** (persona is REJECTED and must be regenerated):
- Any continuous attribute outside [0, 1]
- Any NaN or Inf value
- `youngest_child_age > oldest_child_age`
- `parent_age - oldest_child_age < 18`
- `num_children` doesn't match child age fields
- Categorical attribute value not in valid enum
- Missing required field

**Soft warnings** (flagged but persona is kept):
- Tier3 + `digital_comfort > 0.85` (unusual but possible)
- `household_income_lpa < 3` + `brand_premium_willingness > 0.7` (unlikely)
- `homemaker` + `time_scarcity > 0.8` (unusual)
- `health_anxiety < 0.2` + `supplement_belief > 0.8` (inconsistent)

**Population-level validation** (`validate_population`):
- Chi-square goodness-of-fit test for each categorical distribution vs target
- KS test for each continuous distribution vs expected (normal/uniform)
- Pairwise correlation check: actual vs target, flag if |delta| > 0.15
- Overall pass: all chi-square p > 0.05, at least 80% of correlation checks pass

Return structured `PopulationValidationReport` with all results.

### Task 2: Web Scraping Pipeline (P1)
**File**: `src/scraping/amazon_reviews.py`, `src/scraping/parenting_forums.py`, `src/scraping/google_trends.py`
**PRD**: PRD-002

Implement scrapers for real-world data enrichment. This is P1 — if blocked by anti-scraping measures, document the issue and we'll use fallback distributions.

**Amazon/Flipkart reviews**: Use `httpx` + `beautifulsoup4`. Target 200 reviews per product for: Nutrimix, Pediasure, Horlicks, Bournvita, Protinex Junior.

**Parenting forums**: Scrape BabyChakra threads about child nutrition, supplements. Extract concerns, brands mentioned, trust sources.

**Google Trends**: Use `pytrends` for search interest data on kids nutrition terms.

Save all scraped data as JSON in `data/scraped/`.

### Task 3: Distribution Fitting (P1)
**File**: `src/scraping/distribution_fitter.py` (new file)
**PRD**: PRD-002, Deliverable D4

Analyze scraped data to refine distribution parameters. Compare against defaults in `DistributionTables`. Save refined params to `data/distributions/`.

---

## CONTEXT FILES TO READ

1. `ARCHITECTURE.md` — especially §4.3 (Taxonomy), §6.3 (Validation)
2. `src/taxonomy/schema.py` — the Pydantic models you'll validate
3. `src/taxonomy/validation.py` — the stub you'll implement
4. `docs/DEVELOPMENT_PRACTICES.md` — code standards
5. `docs/prds/PRD-001-persona-schema-generation.md` — validation spec
6. `docs/prds/PRD-002-data-enrichment.md` — scraping spec

## TESTS YOU MUST WRITE

```python
# tests/unit/test_validation.py
test_valid_persona_passes()
test_out_of_range_attribute_fails_hard()
test_nan_value_fails_hard()
test_child_older_than_parent_fails_hard()
test_unusual_tier3_digital_warns_soft()
test_population_distribution_check_passes_good_data()
test_population_distribution_check_fails_bad_data()
test_correlation_check_within_tolerance_passes()
test_correlation_check_outside_tolerance_fails()
test_validation_report_overall_pass()
```

## WHEN YOU'RE DONE

1. Ensure `uv run ruff check .` passes
2. Ensure `uv run pytest tests/unit/ -v` — all tests pass
3. Commit to your feature branch
4. Notify the Tech Lead for code review
