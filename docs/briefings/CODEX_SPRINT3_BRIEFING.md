# Codex — Sprint 3 Briefing

> **Sprint**: 3 (Days 5-6)
> **Branch**: `feat/PRD-009-report-agent` from `staging`
> **PRDs**: PRD-008 (causal statements), PRD-009 (ReportAgent), PRD-010 (interviews)

---

## Your Assignments

### Task 1: Causal Statement Generator (P0)

**File**: `src/analysis/causal.py` — implement `generate_causal_statements()`

The stub currently raises `NotImplementedError`. Replace with full implementation.

Input: `list[VariableImportance]` + raw results dict + optional `scenario_id` + `top_n` (default 8)
Output: `list[CausalStatement]` sorted by `evidence_strength` descending

Logic:
1. Take top `top_n` variables by SHAP importance
2. For each variable, split results at the median value
3. Compute adoption rate for above-median vs below-median groups
4. Compute lift ratio and direction
5. Generate `CausalStatement` with:
   - `statement`: natural language referencing variable name + threshold + lift
   - `supporting_variables`: list of variable names
   - `evidence_strength`: normalized SHAP value (0 to 1 scale)
   - `segment`: None for overall, or segment value if segment-specific
6. For high-importance variables (SHAP > 2x mean), check segment variation across `city_tier` and `income_bracket` — add segment-specific statements if lift differs > 1.5x across segments

Tests to extend in `tests/unit/test_causal.py`:
- `test_causal_statements_reference_specific_variables`
- `test_causal_statements_sorted_by_evidence_strength`
- `test_causal_statements_include_threshold_values`
- `test_causal_statements_empty_input_returns_empty`
- `test_segment_specific_statements_generated_when_lift_differs`

### Task 2: ReportAgent with ReACT Loop (P0)

**File**: `src/analysis/report_agent.py` — replace stub with full implementation

See PRD-009 for complete specification. Key requirements:
1. Define 6 tools wrapping existing analysis functions (segments, barriers, importance, counterfactual, persona lookup, segment comparison)
2. Implement ReACT loop: LLM reasons -> calls tool -> gets result -> repeats (max `REPORT_AGENT_MAX_ITERATIONS` from constants)
3. Final output: `ReportOutput` with 6 required sections (Executive Summary, Funnel Analysis, Segment Deep Dive, Key Drivers, Counterfactual Insights, Recommendations)
4. Every statement must be grounded — reference specific variable names and numbers
5. Add `validate_report_grounding()` function that checks for ungrounded statements

Add constants to `src/constants.py`:
```python
REPORT_AGENT_MAX_ITERATIONS = 8
REPORT_AGENT_MODEL = "opus"
REPORT_MIN_SECTIONS = 6
REPORT_MAX_TOOL_CALLS = 15
```

Tests in `tests/unit/test_report_agent.py`:
- `test_report_agent_produces_all_required_sections`
- `test_report_agent_calls_tools_during_generation`
- `test_report_agent_respects_max_iterations`
- `test_report_output_contains_scenario_metadata`
- `test_report_agent_handles_empty_results`
- `test_report_grounding_validation_catches_generic_statements`

**Important**: All tests must use `LLMClient` in mock mode. No real API calls in tests.

### Task 3: Deep Persona Interview System (P0)

**File**: `src/analysis/interviews.py` — replace stub with full implementation

See PRD-010 for complete specification. Key requirements:
1. `build_system_prompt()` — construct the character prompt from persona attributes, narrative, and decision result. Must include demographics, top 5 psychographic attributes with values, daily routine, and decision context.
2. `interview()` — send question to LLM with system prompt + conversation history, return `InterviewTurn`
3. `start_session()` — create a new `InterviewSession` with metadata
4. `check_interview_quality()` — validate response is in-character, appropriate length, no AI disclosure

Add constants to `src/constants.py`:
```python
INTERVIEW_LLM_MODEL = "sonnet"
INTERVIEW_MAX_TURNS = 20
INTERVIEW_MAX_CONTEXT_TOKENS = 8000
INTERVIEW_RESPONSE_MIN_WORDS = 50
INTERVIEW_RESPONSE_MAX_WORDS = 300
INTERVIEW_AI_DISCLOSURE_PATTERNS = [
    "as an ai", "language model", "i don't have feelings",
    "i'm not a real person", "i was programmed",
]
```

Tests in `tests/unit/test_interviews.py`:
- `test_system_prompt_includes_persona_demographics`
- `test_system_prompt_includes_decision_outcome`
- `test_system_prompt_includes_psychographic_highlights`
- `test_interview_returns_interview_turn`
- `test_interview_maintains_conversation_history`
- `test_interview_works_in_mock_mode`
- `test_quality_check_catches_ai_disclosure`
- `test_quality_check_validates_response_length`
- `test_quality_check_rejects_inconsistent_sentiment`

---

## Standards Reminder

- Pydantic `BaseModel` with `ConfigDict(extra="forbid")` for all new models
- `structlog.get_logger(__name__)` for logging — especially important for ReACT iterations
- No magic numbers — constants file for all thresholds
- Use `LLMClient` mock mode in tests (never hit real API)
- Use `DEFAULT_SEED` not `seed=42`
- Run before submitting:
  ```
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest tests/unit/ -q
  ```

---

## Sprint 2 Feedback

Composite was **7.8/10** — solid delivery. Three fixes requested:
1. `Final` annotations on constants (mypy) — applied promptly
2. Module-level import-time side effect — watch for this pattern in ReportAgent
3. Hardcoded `seed=42` — use `DEFAULT_SEED` everywhere

For Sprint 3: This is your heaviest sprint (3 substantial tasks). Prioritize Task 1 (causal statements) and Task 3 (interviews) first — Task 2 (ReportAgent) builds on both. The ReportAgent is the most complex module in the project; take extra care with the tool registry and ReACT loop termination.
