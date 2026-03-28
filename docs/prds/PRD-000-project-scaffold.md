# PRD-000: Project Scaffold & Infrastructure

> **Sprint**: 0
> **Priority**: P0 (Blocking)
> **Assignees**: Cursor (scaffold, CI, staging), Codex (LLM wrapper, base models)
> **Status**: Ready for Development
> **Estimated Effort**: 4-6 hours total

---

## Objective

Set up the complete development environment so all engineers can start Sprint 1 immediately. This includes the Python project, CI pipeline, staging environment, shared LLM client, and base data models.

---

## Deliverables

### D1: Python Project Scaffold (Cursor)

Create the project at the repo root with the following structure:

```
littlejoys-persona-engine/
├── pyproject.toml              # Project config (uv-compatible)
├── .python-version             # 3.11+
├── .gitignore                  # Python, .env, data/, __pycache__, .mypy_cache
├── .env.example                # Template with all env vars (no real values)
├── .pre-commit-config.yaml     # Hooks per DEVELOPMENT_PRACTICES.md
├── .ruff.toml                  # Linter config
├── README.md                   # Quick start instructions
│
├── src/
│   ├── __init__.py
│   ├── config.py               # Environment config loader (Pydantic Settings)
│   ├── constants.py            # All project-wide constants
│   │
│   ├── taxonomy/
│   │   ├── __init__.py
│   │   ├── schema.py           # Stub: persona Pydantic models
│   │   ├── distributions.py    # Stub: distribution tables
│   │   ├── correlations.py     # Stub: correlation rules
│   │   └── validation.py       # Stub: validation framework
│   │
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── tier1_generator.py  # Stub
│   │   ├── tier2_generator.py  # Stub
│   │   └── population.py       # Stub
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── agent.py            # Stub
│   │   ├── memory.py           # Stub
│   │   ├── perception.py       # Stub
│   │   └── serialization.py    # Stub
│   │
│   ├── decision/
│   │   ├── __init__.py
│   │   ├── funnel.py           # Stub
│   │   ├── repeat.py           # Stub
│   │   ├── calibration.py      # Stub
│   │   └── scenarios.py        # Stub
│   │
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── static.py           # Stub
│   │   ├── temporal.py         # Stub
│   │   ├── counterfactual.py   # Stub
│   │   └── wom.py              # Stub
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── segments.py         # Stub
│   │   ├── barriers.py         # Stub
│   │   ├── causal.py           # Stub
│   │   ├── report_agent.py     # Stub
│   │   └── interviews.py       # Stub
│   │
│   ├── scraping/
│   │   ├── __init__.py
│   │   ├── amazon_reviews.py   # Stub
│   │   ├── parenting_forums.py # Stub
│   │   ├── google_trends.py    # Stub
│   │   └── littlejoys_site.py  # Stub
│   │
│   └── utils/
│       ├── __init__.py
│       ├── llm.py              # Stub (Codex will implement)
│       └── viz.py              # Stub
│
├── app/
│   ├── streamlit_app.py        # Stub: main entry
│   ├── pages/                  # Empty stubs
│   └── components/             # Empty stubs
│
├── data/
│   ├── scraped/.gitkeep
│   ├── distributions/.gitkeep
│   ├── populations/.gitkeep
│   └── results/.gitkeep
│
├── notebooks/
│   └── .gitkeep
│
└── tests/
    ├── __init__.py
    ├── conftest.py             # Shared fixtures
    ├── unit/
    │   ├── __init__.py
    │   └── test_smoke.py       # Basic import smoke test
    └── integration/
        ├── __init__.py
        └── .gitkeep
```

**Stubs**: Each stub file should contain:
- Module docstring referencing the relevant section of ARCHITECTURE.md
- Placeholder class/function signatures with `NotImplementedError`
- Type hints on all signatures

**pyproject.toml dependencies**:
```toml
[project]
name = "littlejoys-persona-engine"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "numpy>=1.26",
    "scipy>=1.12",
    "pandas>=2.2",
    "scikit-learn>=1.4",
    "shap>=0.44",
    "anthropic>=0.40",
    "plotly>=5.18",
    "streamlit>=1.30",
    "structlog>=24.1",
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
    "pytrends>=4.9",
    "pyarrow>=15.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.1",
    "hypothesis>=6.98",
    "mypy>=1.8",
    "ruff>=0.5",
    "bandit>=1.7",
    "pre-commit>=3.6",
    "detect-secrets>=1.4",
    "pip-audit>=2.7",
]
```

### D2: CI Pipeline (Cursor)

Create `scripts/ci.sh`:
```bash
#!/bin/bash
set -e
echo "=== Lint ==="
uv run ruff check .
uv run ruff format --check .
echo "=== Type Check ==="
uv run mypy src/ --strict --ignore-missing-imports
echo "=== Security ==="
uv run bandit -r src/ -q
echo "=== Tests ==="
uv run pytest tests/unit/ -v --cov=src --cov-fail-under=80
echo "=== All Checks Passed ==="
```

### D3: Staging Environment (Cursor)

Create `scripts/run_staging.sh`:
```bash
#!/bin/bash
export ENVIRONMENT=staging
uv run streamlit run app/streamlit_app.py --server.port 8501
```

Create `scripts/run_dev.sh`:
```bash
#!/bin/bash
export ENVIRONMENT=development
uv run streamlit run app/streamlit_app.py --server.port 8502 --server.runOnSave true
```

### D4: LLM Wrapper (Codex)

Implement `src/utils/llm.py` with:

```python
class LLMClient:
    """
    Unified Claude API client with:
    - Dual model routing (Opus for reasoning, Sonnet for bulk)
    - Response caching (disk-based, keyed by prompt hash)
    - Mock mode for unit tests
    - Retry with exponential backoff
    - Structured output parsing (JSON mode)
    - Token usage tracking
    """

    def __init__(self, config: Config):
        ...

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: Literal["reasoning", "bulk"] = "bulk",
        response_format: Literal["text", "json"] = "text",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        ...

    async def generate_batch(
        self,
        prompts: list[str],
        system: str = "",
        model: Literal["reasoning", "bulk"] = "bulk",
        max_concurrency: int = 5,
    ) -> list[LLMResponse]:
        """Batch generation with concurrency control."""
        ...
```

**Requirements**:
- Cache stored in `data/.llm_cache/` (gitignored)
- Cache key = SHA256 of (model + system + prompt + temperature)
- Mock mode returns deterministic responses from fixtures when `LLM_MOCK_ENABLED=true`
- Token usage tracked and logged via structlog
- All API errors wrapped in custom `LLMError` exception

### D5: Base Pydantic Models (Codex)

Implement initial stubs in `src/taxonomy/schema.py`:

```python
class DemographicAttributes(BaseModel):
    """Section 1 of the persona taxonomy. See ARCHITECTURE.md §4.3"""
    ...  # All demographic fields with types and validators

class Persona(BaseModel):
    """
    Complete synthetic persona. Three-layer architecture:
    - Identity (immutable): demographics, psychographics, values
    - Memory (mutable): episodic, semantic, brand memories
    - State (volatile): current awareness, consideration, purchase history
    """
    ...
```

This is a STUB in Sprint 0. Full implementation in PRD-001.

---

## Acceptance Criteria

- [ ] `git clone && uv sync && uv run pytest` passes on a fresh checkout
- [ ] `uv run ruff check .` returns 0 warnings
- [ ] `uv run mypy src/` passes (stubs may use `...` body)
- [ ] All module stubs exist with correct signatures
- [ ] LLM wrapper can make a test call to Claude API (integration test, skip in CI)
- [ ] LLM wrapper mock mode works for unit tests
- [ ] Staging script boots Streamlit (even if blank page)
- [ ] `.env.example` has all required env vars documented
- [ ] `.gitignore` covers all generated files

---

## Technical Notes

- Use `uv` as package manager (not pip, not poetry)
- Python 3.11+ for match/case, modern type unions
- Pydantic v2 for all data models
- structlog for all logging (never bare print)
- All file paths relative to project root, never absolute
