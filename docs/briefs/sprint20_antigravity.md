# Sprint 20 Brief — Antigravity
## Tests for PDF Export, Scenario Comparison, CSV Export

### Context

Sprint 20 delivers 3 features: PDF export (Cursor), scenario comparison (Codex + OpenCode), persona CSV export (Goose). You test all of them.

### Dependency
Wait for Cursor, Codex, and Goose to deliver before writing tests.

### Task 1: PDF Export Tests (`tests/unit/test_pdf_export.py` — new)

```python
def test_pdf_export_returns_bytes():
    """generate_pdf_report should return non-empty bytes."""
    # Build a minimal ConsolidatedReport (use mock_mode fixtures)
    # Call generate_pdf_report(report, scenario)
    # Assert result is bytes and len > 0

def test_pdf_export_contains_scenario_name():
    """PDF should contain the scenario name somewhere in the text."""
    # Generate PDF, decode bytes to look for text markers
    # (fpdf2 PDFs can be searched for text strings)

def test_pdf_export_with_no_temporal():
    """PDF should generate without errors when temporal data is None."""
    # Build report with temporal_snapshots=None, event_monthly_rollup=None

def test_pdf_export_with_counterfactuals():
    """PDF should include counterfactual table when data is present."""

def test_pdf_export_performance():
    """PDF generation should complete in < 5 seconds."""
    import time
    start = time.time()
    # Generate PDF
    assert time.time() - start < 5.0
```

### Task 2: Scenario Comparison Tests (`tests/unit/test_scenario_comparison.py` — new)

```python
def test_compare_same_scenario_zero_delta():
    """Comparing a scenario with itself should produce zero deltas."""
    # compare_scenarios(pop, scenario_a, scenario_a) → adoption_delta ≈ 0

def test_compare_different_scenarios():
    """Comparing nutrimix_2_6 vs protein_mix should produce non-zero deltas."""

def test_comparison_result_structure():
    """Result should have all required fields populated."""

def test_comparison_barrier_deltas():
    """Barrier comparison should include stage + barrier + counts from both sides."""

def test_comparison_determinism():
    """Same seed should produce identical comparison results."""
```

### Task 3: Update Any Broken Tests

If Sprint 20 changes to `app/pages/3_results.py` (polish, label changes) break existing tests, update them.

### Files to Create
- `tests/unit/test_pdf_export.py`
- `tests/unit/test_scenario_comparison.py`

### Files to Modify
- Any test file that breaks from Sprint 20 changes

### Constraints
- Use mock mode for all tests (no LLM calls)
- Use small populations (10-20 personas)
- All tests must pass: `uv run pytest tests/ -x -q`
- Run `uv run ruff check .` before delivery
