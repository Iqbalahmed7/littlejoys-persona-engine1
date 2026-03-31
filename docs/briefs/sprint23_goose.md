# Sprint 23 Brief — Goose
## S3-03: Test Suite for Sprint 22 Deliverables

> **Engineer**: Goose (Grok 4-1 fast-reasoning)
> **Sprint**: 23
> **Ticket**: S3-03
> **Estimated effort**: Medium (test generation, no logic changes)
> **Note from S2-04 review**: Every backend edit must be accompanied by unit tests. This sprint closes that gap retroactively for S2-02 and S2-04, and adds import smoke tests for all new pages.

---

### Context

Sprints 21 and 22 produced four new backend modules with zero test coverage. This ticket writes the test suite so we can ship Sprint 23 with confidence.

---

### Test File 1: `tests/test_probe_orchestrator.py`

Test the `app/utils/probe_orchestrator.py` module.

```python
# Key cases to cover:

def test_effect_label_thresholds():
    """_effect_label() returns correct band for 0.2, 0.4, 0.6, 0.9"""

def test_confidence_label_thresholds():
    """_confidence_label() returns correct band for 0.3, 0.5, 0.8"""

def test_probe_chain_result_fields():
    """ProbeChainResult dataclass has all required fields"""

def test_orchestration_result_fields():
    """OrchestrationResult dataclass has all required fields"""

def test_describe_probe_result_fallback():
    """_describe_probe_result() returns evidence_summary when probe_type is None"""
```

Do NOT attempt to run `run_sequential_probing()` in tests — it requires a live engine. Test the helper functions in isolation only.

---

### Test File 2: `tests/test_interview_prompts_memory.py`

Test the `_build_memory_context()` function added to `src/analysis/interview_prompts.py`.

```python
def test_memory_context_empty_persona():
    """Returns graceful empty string (or minimal text) when persona has no semantic_memory or purchase_history"""

def test_memory_context_with_tier2_anchor():
    """Includes tier2_anchor text when present on persona"""

def test_memory_context_with_purchase_history():
    """Includes purchase history entries when present"""

def test_memory_context_combined():
    """All fields present → output contains all sections"""
```

Use minimal mock `Persona` objects (or `MagicMock` with the relevant attributes set).

---

### Test File 3: `tests/test_page_imports.py`

Smoke tests that all pages import without error.

```python
import importlib
import pytest

@pytest.mark.parametrize("module", [
    "app.components.system_voice",
    "app.utils.phase_state",
    "app.utils.probe_orchestrator",
])
def test_module_imports(module):
    """Module can be imported without raising"""
    importlib.import_module(module)
```

Note: Streamlit page files (`app/pages/*.py`) cannot be imported directly — skip those. Test the component and utility modules only.

---

### Test File 4: `tests/test_phase_state.py`

```python
def test_phase_complete_phase_0_always_true():
    """phase_complete(0) returns True regardless of session state"""

def test_phase_complete_missing_key():
    """phase_complete(1) returns False when 'population' not in session state"""

def test_phase_complete_key_present():
    """phase_complete(1) returns True when 'population' IS in session state"""
```

For Streamlit session_state tests, use `unittest.mock.patch` on `st.session_state` or pass a dict directly if `phase_complete()` accepts an optional state parameter. Check the implementation first.

---

### Acceptance Criteria

- [ ] All 4 test files created
- [ ] `pytest tests/test_probe_orchestrator.py` passes
- [ ] `pytest tests/test_interview_prompts_memory.py` passes
- [ ] `pytest tests/test_page_imports.py` passes
- [ ] `pytest tests/test_phase_state.py` passes
- [ ] No mocking of actual LLM calls — helper/utility functions only
- [ ] No new dependencies — use `pytest` + `unittest.mock` only

---

### Files to Create

| File | Tests for |
|------|-----------|
| `tests/test_probe_orchestrator.py` | `app/utils/probe_orchestrator.py` helpers |
| `tests/test_interview_prompts_memory.py` | `_build_memory_context()` in interview_prompts |
| `tests/test_page_imports.py` | Module import smoke tests |
| `tests/test_phase_state.py` | `phase_complete()` logic |

### Files NOT to modify

Any source files — tests only. If you find a bug while testing, document it in a `# BUG:` comment but do not fix the source.
