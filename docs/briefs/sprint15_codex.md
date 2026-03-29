# Sprint 15 Brief — Codex (GPT 5.3 Medium)
## Shared API Key Utility + Dead Code Cleanup

### Context
Sprint 15 polishes the codebase. Two tasks: (1) extract the duplicated API key resolution into a shared utility, and (2) remove dead imports/references to deleted pages in source modules.

### Task 1: Create `src/utils/api_keys.py`
**New file.**

Three pages (`2_research.py`, `5_interviews.py`, `6_report.py`) each have their own `_resolve_api_key()` and `_has_api_key()`. Two of those pages are being deleted this sprint (Cursor's job), but `2_research.py` still needs the utility. Extract it so future pages don't re-copy:

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

### Task 2: Update `app/pages/2_research.py`

- Remove the local `_resolve_api_key()` and `_has_api_key()` definitions
- Add: `from src.utils.api_keys import resolve_api_key, has_api_key`
- Replace all calls: `_resolve_api_key()` → `resolve_api_key()`, `_has_api_key()` → `has_api_key()`

### Task 3: Write Tests
**New file:** `tests/unit/test_api_keys.py`

```python
from src.utils.api_keys import resolve_api_key, has_api_key


def test_resolve_api_key_returns_string():
    result = resolve_api_key()
    assert isinstance(result, str)


def test_has_api_key_returns_bool():
    result = has_api_key()
    assert isinstance(result, bool)


def test_placeholder_key_rejected(monkeypatch):
    import src.utils.api_keys as mod
    class FakeConfig:
        anthropic_api_key = "sk-ant-REPLACE_ME"
    monkeypatch.setattr(mod, "get_config", lambda: FakeConfig())
    monkeypatch.setattr(mod, "st", type("FakeSt", (), {"secrets": {}})())
    assert resolve_api_key() == ""
    assert has_api_key() is False


def test_real_key_accepted(monkeypatch):
    import src.utils.api_keys as mod
    class FakeConfig:
        anthropic_api_key = "sk-ant-abc123realkey"
    monkeypatch.setattr(mod, "get_config", lambda: FakeConfig())
    monkeypatch.setattr(mod, "st", type("FakeSt", (), {"secrets": {}})())
    assert resolve_api_key() == "sk-ant-abc123realkey"
    assert has_api_key() is True
```

### Deliverables
1. `src/utils/api_keys.py` — shared utility
2. `app/pages/2_research.py` — updated to use shared utility
3. `tests/unit/test_api_keys.py` — 4 tests
4. All existing tests still pass

### Do NOT
- Modify other pages (Cursor is deleting them)
- Add new dependencies
- Change key resolution behavior
