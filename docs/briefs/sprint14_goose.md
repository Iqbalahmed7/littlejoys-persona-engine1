# Sprint 14.5 Brief — Goose (GPT-4o) — Evaluation Task
## Shared API Key Utility + Tests

### Context
Three Streamlit pages (`2_research.py`, `5_interviews.py`, `6_report.py`) each contain their own copy-pasted `_resolve_api_key()` and `_has_api_key()` functions. This duplication creates a maintenance risk — if the key-resolution logic changes (e.g. adding a new secret provider), it must be updated in 3+ places. Your job is to extract these into a shared utility and update consumers.

### Task 1: Create `src/utils/api_keys.py`
**New file.**

Extract the common pattern into two public functions:

```python
"""Shared Anthropic API key resolution for Streamlit pages."""

from __future__ import annotations

import streamlit as st

from src.config import get_config


def resolve_api_key() -> str:
    """Read Anthropic API key from Streamlit secrets (cloud) or .env.local (local).

    Returns the key string, or empty string if none found / placeholder only.
    """
    try:
        if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
            return str(st.secrets["ANTHROPIC_API_KEY"]).strip()
    except Exception:
        pass
    key = get_config().anthropic_api_key.strip()
    if not key or key == "sk-ant-REPLACE_ME":
        return ""
    return key


def has_api_key() -> bool:
    """Return True if a non-placeholder API key is available."""
    key = resolve_api_key()
    return bool(key) and not key.startswith("sk-ant-REPLACE")
```

That's it — the logic is identical to the existing copies. Do **not** change behavior.

### Task 2: Update consumers

Update these 3 files to import from the shared utility instead of defining their own copies:

**`app/pages/2_research.py`:**
- Remove the `_resolve_api_key()` and `_has_api_key()` function definitions (lines 19-35 approximately)
- Add import: `from src.utils.api_keys import resolve_api_key, has_api_key`
- Replace all calls to `_resolve_api_key()` → `resolve_api_key()` and `_has_api_key()` → `has_api_key()`

**`app/pages/6_report.py`:**
- Remove the `_resolve_api_key()` and `_has_api_key()` function definitions (lines 51-67 approximately)
- Add import: `from src.utils.api_keys import resolve_api_key, has_api_key`
- Replace all calls to `_resolve_api_key()` → `resolve_api_key()` and `_has_api_key()` → `has_api_key()`

**`app/pages/5_interviews.py`:**
- Remove the module-level `_resolve_api_key()` and `_has_api_key()` function definitions (lines 64-80 approximately)
- Remove the **second** `_has_api_key()` defined inside the sidebar block (lines 138-149 approximately) — this is a duplicate that shadows the module-level one
- Add import: `from src.utils.api_keys import resolve_api_key, has_api_key`
- Replace all calls to `_resolve_api_key()` → `resolve_api_key()` and `_has_api_key()` → `has_api_key()`

### Task 3: Write tests
**New file:** `tests/unit/test_api_keys.py`

```python
"""Unit tests for shared API key utility."""

from __future__ import annotations

from src.utils.api_keys import resolve_api_key, has_api_key


def test_resolve_api_key_returns_string():
    """resolve_api_key() returns a string (may be empty in test environment)."""
    result = resolve_api_key()
    assert isinstance(result, str)


def test_has_api_key_returns_bool():
    """has_api_key() returns a boolean."""
    result = has_api_key()
    assert isinstance(result, bool)


def test_placeholder_key_rejected(monkeypatch):
    """Placeholder key 'sk-ant-REPLACE_ME' is treated as missing."""
    import src.utils.api_keys as mod

    class FakeConfig:
        anthropic_api_key = "sk-ant-REPLACE_ME"

    monkeypatch.setattr(mod, "get_config", lambda: FakeConfig())
    # Also ensure Streamlit secrets path doesn't interfere
    monkeypatch.setattr(mod, "st", type("FakeSt", (), {"secrets": {}})())
    assert resolve_api_key() == ""
    assert has_api_key() is False


def test_real_key_accepted(monkeypatch):
    """A real-looking key is accepted."""
    import src.utils.api_keys as mod

    class FakeConfig:
        anthropic_api_key = "sk-ant-abc123realkey"

    monkeypatch.setattr(mod, "get_config", lambda: FakeConfig())
    monkeypatch.setattr(mod, "st", type("FakeSt", (), {"secrets": {}})())
    assert resolve_api_key() == "sk-ant-abc123realkey"
    assert has_api_key() is True
```

### Verification Steps

Run these commands to verify your work:

```bash
# Lint the new and modified files
uv run ruff check src/utils/api_keys.py app/pages/2_research.py app/pages/5_interviews.py app/pages/6_report.py tests/unit/test_api_keys.py

# Run the new tests
uv run pytest tests/unit/test_api_keys.py -v

# Run the full test suite to ensure nothing broke
uv run pytest tests/ -v
```

### Deliverables
1. `src/utils/api_keys.py` — shared utility (2 functions)
2. `app/pages/2_research.py` — updated imports, removed local definitions
3. `app/pages/5_interviews.py` — updated imports, removed local definitions (both copies)
4. `app/pages/6_report.py` — updated imports, removed local definitions
5. `tests/unit/test_api_keys.py` — 4 tests
6. All existing tests still pass (522+ passed)

### Do NOT
- Change the behavior of key resolution (exact same logic, just moved)
- Modify source modules outside the 3 consumer pages
- Add new dependencies
- Touch any other pages or test files
