# Development Practices & Engineering Standards

> **Owner**: Technical Lead (Claude Opus)
> **Last Updated**: 2026-03-27
> **Applies To**: All engineers (Cursor, Codex, Antigravity) and QA Agent

---

## 1. GIT WORKFLOW

### Branching Strategy: GitHub Flow (Modified)

```
main                    ← Production. Always deployable. Protected.
  │
  ├── staging           ← Integration branch. Code tested here before main.
  │     │
  │     ├── feat/PRD-001-persona-schema        ← Feature branches (one per PRD task)
  │     ├── feat/PRD-004-decision-engine
  │     ├── fix/copula-edge-case
  │     └── chore/lint-config
  │
  └── (tags: v0.1, v0.2, etc.)
```

**Rules**:
1. **NEVER push directly to `main`**. All code goes through `staging` first.
2. **NEVER push directly to `staging`**. All code goes through a feature branch → PR → review → merge.
3. Feature branches are named: `feat/PRD-XXX-short-description` or `fix/short-description`
4. One PR per logical unit of work. Don't bundle unrelated changes.
5. Every PR must pass CI (lint + type-check + tests) before merge.
6. Every PR must be reviewed by QA Agent before merge to staging.
7. Staging → Main promotion happens at sprint gates only, after full QA pass.

### Commit Message Convention

```
type(scope): short description

[optional body: what and why, not how]

Co-Authored-By: [Engineer Name] <noreply@simulatte.ai>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`
Scopes: `taxonomy`, `generation`, `decision`, `simulation`, `analysis`, `dashboard`, `infra`

Examples:
```
feat(taxonomy): implement Gaussian copula generator with 50+ correlation rules
fix(decision): handle NaN when income_factor is zero for edge-case personas
test(simulation): add property-based tests for counterfactual engine monotonicity
```

---

## 2. ENVIRONMENTS

### Development (Local)
- Each engineer works on their feature branch locally
- Runs `uv run pytest` and `uv run ruff check .` before pushing
- Uses `.env.development` for config (mock LLM responses where possible to save API costs)

### Staging
- Mirrors production config
- Runs full test suite including integration tests
- Uses real LLM API calls (with caching to minimize cost)
- Accessible for QA Agent review
- Data: uses a fixed seed population for reproducibility
- **Promotion criteria**: All tests pass. QA Agent sign-off. No known bugs above severity "Low".

### Production (Demo)
- The final Streamlit app served to the client
- Pre-computed results loaded from disk (no live LLM calls during demo unless interactive mode)
- Static fallback HTML available if Streamlit crashes
- **Promotion criteria**: Full dry-run passed. Backup assets ready. Tech Lead sign-off.

### Environment Configuration

```python
# config.py
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

# .env.development
ENVIRONMENT=development
LLM_PROVIDER=anthropic
LLM_MODEL_REASONING=claude-opus-4-6          # For reports, interviews
LLM_MODEL_BULK=claude-sonnet-4-6             # For persona generation
LLM_CACHE_ENABLED=true                       # Cache all LLM responses locally
LLM_MOCK_ENABLED=true                        # Use mock responses for unit tests
POPULATION_SEED=42                           # Fixed seed for reproducibility
POPULATION_SIZE=300
DEEP_PERSONA_COUNT=30
LOG_LEVEL=DEBUG

# .env.staging
ENVIRONMENT=staging
LLM_CACHE_ENABLED=true
LLM_MOCK_ENABLED=false
LOG_LEVEL=INFO

# .env.production
ENVIRONMENT=production
LLM_CACHE_ENABLED=true
PRECOMPUTED_RESULTS=true                     # Load from disk, don't recompute
LOG_LEVEL=WARNING
```

---

## 3. CI/CD PIPELINE

Runs on every push to any branch.

```yaml
# Conceptual pipeline (implement via pre-commit hooks + scripts)

stages:
  lint:
    - ruff check .                    # Linting
    - ruff format --check .           # Formatting check

  typecheck:
    - mypy src/ --strict              # Type checking (strict mode)

  test:
    - pytest tests/unit/ -v           # Unit tests (fast, no LLM)
    - pytest tests/integration/ -v    # Integration tests (staging only)

  security:
    - bandit -r src/                  # Security vulnerability scan
    - check for .env / API keys in diff  # Secret detection

  quality:
    - pytest --cov=src --cov-fail-under=80  # Minimum 80% code coverage
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ruff-lint
        name: Ruff Lint
        entry: uv run ruff check --fix .
        language: system
        pass_filenames: false

      - id: ruff-format
        name: Ruff Format
        entry: uv run ruff format .
        language: system
        pass_filenames: false

      - id: typecheck
        name: MyPy Type Check
        entry: uv run mypy src/
        language: system
        pass_filenames: false

      - id: secrets
        name: Secret Detection
        entry: uv run detect-secrets-hook
        language: system

      - id: unit-tests
        name: Unit Tests
        entry: uv run pytest tests/unit/ -x -q
        language: system
        pass_filenames: false
```

---

## 4. CODE QUALITY STANDARDS

### Python Standards
- **Python 3.11+** — use modern features (match/case, type unions, etc.)
- **Type hints everywhere** — all function signatures must be fully typed
- **Pydantic v2** for all data models — enforce validation at boundaries
- **No `Any` types** unless absolutely unavoidable (and then document why)
- **Docstrings** — all public functions and classes get Google-style docstrings
- **Max function length** — 50 lines. If longer, decompose.
- **Max file length** — 400 lines. If longer, split into modules.
- **No magic numbers** — all constants named and documented in a constants module
- **No print()** — use `logging` module with appropriate levels

### Naming Conventions
```python
# Modules: snake_case
persona_generator.py

# Classes: PascalCase
class GaussianCopulaGenerator:

# Functions/methods: snake_case
def compute_purchase_decision():

# Constants: UPPER_SNAKE_CASE
MAX_PERSONA_ATTRIBUTES = 250

# Private: leading underscore
def _validate_correlation_matrix():
```

### Error Handling
```python
# DO: Specific exceptions with context
class PersonaValidationError(Exception):
    """Raised when a generated persona fails consistency checks."""
    def __init__(self, persona_id: str, violations: list[str]):
        self.persona_id = persona_id
        self.violations = violations
        super().__init__(f"Persona {persona_id} failed validation: {violations}")

# DO: Fail fast at boundaries, trust internals
def generate_population(size: int, seed: int) -> Population:
    if size < 1 or size > 10_000:
        raise ValueError(f"Population size must be 1-10000, got {size}")
    # ... no defensive checks inside the hot loop

# DON'T: Bare except, swallowed errors
try:
    result = compute_utility(persona, scenario)
except:  # NEVER
    result = 0.0  # NEVER
```

### Testing Standards
```python
# Unit tests: fast, no I/O, no LLM
# File: tests/unit/test_decision.py
def test_purchase_decision_high_price_sensitivity_rejects():
    """Persona with high price_sensitivity should reject expensive products."""
    persona = make_persona(budget_consciousness=0.9, household_income_lpa=4)
    scenario = make_scenario(price=999)
    _, decision = compute_purchase(persona, scenario.product, scenario, consideration=0.8)
    assert decision != "adopt"

# Property-based tests for invariants
from hypothesis import given, strategies as st

@given(price_multiplier=st.floats(min_value=0.5, max_value=2.0))
def test_counterfactual_monotonicity_price(price_multiplier):
    """Lower price should never decrease adoption (all else equal)."""
    base_adoption = run_sim(price=599)
    modified_adoption = run_sim(price=599 * price_multiplier)
    if price_multiplier < 1.0:
        assert modified_adoption >= base_adoption

# Integration tests: hit real APIs, use fixtures
# File: tests/integration/test_tier2_generation.py
@pytest.mark.integration
def test_tier2_persona_narrative_coherence():
    """Generated narrative should reference the persona's actual attributes."""
    persona = generate_tier2_persona(seed=42)
    assert persona.demographics.city_name in persona.narrative
    assert str(persona.demographics.num_children) in persona.narrative
```

---

## 5. CODE REVIEW CHECKLIST

Every PR reviewed by QA Agent must check:

### Correctness
- [ ] Does the code do what the PRD specifies?
- [ ] Are edge cases handled (empty inputs, zero values, None)?
- [ ] Are all mathematical formulas correct and matching ARCHITECTURE.md?
- [ ] Do utility calculations clip to valid ranges (0-1 where applicable)?

### Architecture
- [ ] Does the code follow the project structure in ARCHITECTURE.md?
- [ ] Are the three persona layers (Identity/Memory/State) respected?
- [ ] No circular dependencies between modules?
- [ ] Is the dependency direction correct? (decision depends on taxonomy, not vice versa)

### Quality
- [ ] All functions have type hints?
- [ ] All public functions have docstrings?
- [ ] No magic numbers (all constants named)?
- [ ] No dead code, no commented-out code?
- [ ] No TODO/FIXME/HACK left unresolved (create an issue instead)?

### Testing
- [ ] New code has corresponding unit tests?
- [ ] Edge cases tested?
- [ ] Tests are deterministic (seeded randomness)?
- [ ] Tests are fast (< 1s for unit, < 30s for integration)?

### Security
- [ ] No hardcoded API keys, tokens, or secrets?
- [ ] No user input passed directly to LLM prompts without sanitization?
- [ ] No pickle/eval/exec on untrusted data?
- [ ] File paths validated (no path traversal)?

### Performance
- [ ] No O(n^2) or worse where O(n) is possible?
- [ ] LLM calls cached appropriately?
- [ ] Large data uses generators/iterators, not lists in memory?

---

## 6. SECURITY PRACTICES

### Secrets Management
- **NEVER** commit `.env` files, API keys, or credentials
- Use `.env.example` with placeholder values checked into git
- Real secrets in `.env.local` (gitignored)
- CI/CD secrets in environment variables, never in config files

### Input Validation
- All external inputs (user parameters in Streamlit, scraped data) validated via Pydantic
- LLM outputs parsed and validated before use (don't trust LLM JSON blindly)
- Scenario parameters bounded to valid ranges

### Dependency Security
- Pin all dependencies in `pyproject.toml` with exact versions
- Run `pip-audit` weekly during development
- No dependencies from unknown/unverified sources

### Data Privacy
- Scraped data is aggregate/public (no PII)
- Generated personas are synthetic (no real person data)
- LLM prompts don't contain client-confidential data (use scenario parameters, not raw business data)

---

## 7. LOGGING & OBSERVABILITY

```python
import logging
import structlog

# Structured logging throughout
logger = structlog.get_logger()

# Key events to log:
logger.info("population_generated", size=300, seed=42, validation_passed=True)
logger.info("simulation_started", scenario="nutrimix_7plus", mode="static", population_size=300)
logger.info("simulation_completed", scenario="nutrimix_7plus", adoption_rate=0.12, duration_ms=450)
logger.warning("persona_validation_soft_fail", persona_id="abc-123", rule="tier3_high_digital", value=0.92)
logger.error("llm_api_error", model="claude-sonnet-4-6", error="rate_limit", retry_in_seconds=30)
```

---

## 8. DOCUMENTATION REQUIREMENTS

### Code Documentation
- Every module has a module-level docstring explaining its purpose and relationship to ARCHITECTURE.md
- Every class has a class docstring with usage example
- Every public function has a Google-style docstring with Args, Returns, Raises
- Complex algorithms get inline comments explaining the WHY, not the WHAT

### Architecture Documentation
- ARCHITECTURE.md is the single source of truth
- If code deviates from ARCHITECTURE.md, update the doc OR fix the code — never leave them out of sync
- Tech Lead reviews ARCHITECTURE.md at each sprint gate

### Decision Log
- Non-obvious decisions get a brief entry in `docs/DECISION_LOG.md`
- Format: Date | Decision | Context | Alternatives Considered | Rationale

---

## 9. DEFINITION OF DONE

A task is "Done" when ALL of the following are true:

1. Code implements the PRD specification completely
2. All new code has type hints and docstrings
3. Unit tests written and passing
4. Integration tests written (where applicable) and passing
5. `ruff check .` passes with zero warnings
6. `mypy src/ --strict` passes
7. Code coverage >= 80% for new code
8. PR created with clear description referencing the PRD
9. QA Agent has reviewed and approved
10. Merged to staging branch
11. Verified working in staging environment
12. Tech Lead notified of completion
