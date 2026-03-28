# PRD-009: LLM ReportAgent

> **Sprint**: 3
> **Priority**: P0 (Critical Path)
> **Assignee**: Codex
> **Depends On**: PRD-008 (analysis deepening), PRD-005 (scenarios)
> **Status**: Ready for Development

---

## Objective

Build an LLM-powered ReportAgent that uses a ReACT (Reason + Act) loop to generate comprehensive, variable-grounded analysis reports for each business problem. The agent has access to analysis tools and can dig into data autonomously.

---

## Architecture Reference

See ARCHITECTURE.md section 9.2. The ReportAgent follows MiroFish's ReACT pattern.

---

## Deliverables

### D1: ReportAgent Tool Registry

**File**: `src/analysis/report_agent.py`

Define the tools the agent can call during report generation:

```python
REPORT_AGENT_TOOLS = {
    "query_segment": {
        "description": "Get adoption metrics for a filtered segment",
        "function": "_tool_query_segment",
    },
    "compare_segments": {
        "description": "Compare two segments head-to-head on any metric",
        "function": "_tool_compare_segments",
    },
    "explain_persona": {
        "description": "Get full decision trace for a specific persona",
        "function": "_tool_explain_persona",
    },
    "run_counterfactual": {
        "description": "Perturb a scenario parameter and get new results",
        "function": "_tool_run_counterfactual",
    },
    "get_barrier_distribution": {
        "description": "Get distribution of rejection reasons for a segment",
        "function": "_tool_get_barriers",
    },
    "get_variable_importance": {
        "description": "Get ranked list of attributes driving adoption",
        "function": "_tool_get_importance",
    },
}
```

### D2: Tool Implementations

Each tool wraps an existing analysis function with a string-in/string-out interface suitable for LLM tool use.

1. **`_tool_query_segment(group_by, value)`** — calls `analyze_segments()`, filters to the requested segment, returns JSON summary
2. **`_tool_compare_segments(group_by, value_a, value_b)`** — calls `analyze_segments()`, returns side-by-side comparison
3. **`_tool_explain_persona(persona_id)`** — looks up persona results, returns full funnel score breakdown and rejection reason
4. **`_tool_run_counterfactual(modification_key, modification_value)`** — runs a counterfactual with the given modification, returns adoption lift
5. **`_tool_get_barriers(scenario_id)`** — calls `analyze_barriers()`, returns formatted distribution
6. **`_tool_get_importance(scenario_id)`** — calls `compute_variable_importance()`, returns top 10 ranked variables

### D3: ReACT Loop

```python
class ReportAgent:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client
        self.tools = REPORT_AGENT_TOOLS
        self.max_iterations = REPORT_AGENT_MAX_ITERATIONS  # from constants

    async def generate_report(
        self,
        scenario_id: str,
        results: dict[str, dict[str, Any]],
        population: Population | None = None,
    ) -> ReportOutput:
```

ReACT loop:
1. **System prompt**: "You are an analyst generating a report for {scenario_name}. Use the available tools to investigate patterns, then write a structured report."
2. **Iteration**: LLM reasons about what to investigate next, calls a tool, gets results, repeats
3. **Max iterations**: `REPORT_AGENT_MAX_ITERATIONS` (default 8 from constants)
4. **Termination**: LLM outputs a `[REPORT_COMPLETE]` marker when done investigating
5. **Final generation**: LLM produces the structured report using all gathered evidence

### D4: Report Output Model

```python
class ReportSection(BaseModel):
    title: str
    content: str
    supporting_data: dict[str, Any] = Field(default_factory=dict)

class ReportOutput(BaseModel):
    scenario_id: str
    scenario_name: str
    sections: list[ReportSection]
    tool_calls_made: int
    raw_markdown: str
```

Required report sections:
1. **Executive Summary** — 3-5 bullet points, each grounded in a specific number
2. **Adoption Funnel Analysis** — where personas drop off and why (use waterfall + barrier data)
3. **Segment Deep Dive** — which segments adopt most/least, and the causal factors
4. **Key Drivers & Barriers** — variable importance with specific thresholds
5. **Counterfactual Insights** — what interventions would move the needle most
6. **Recommendations** — 3-5 actionable recommendations, each tied to a specific finding

### D5: Report Quality Constraints

Every statement in the report must meet these grounding rules:
- Reference a **specific variable name** from the persona schema (not "psychological factors")
- Include a **specific number** (adoption rate, SHAP value, lift ratio)
- When mentioning a segment, cite the **exact segment value** and **sample size**
- Recommendations must reference the counterfactual that supports them

The system prompt must enforce these constraints. Add a validation pass that checks the generated report for grounding markers.

```python
def validate_report_grounding(report: ReportOutput, schema_attributes: list[str]) -> list[str]:
    """Return list of ungrounded statements (warnings, not blocking)."""
```

---

## Constants

Add to `src/constants.py`:
```python
REPORT_AGENT_MAX_ITERATIONS = 8
REPORT_AGENT_MODEL = "opus"  # Use Opus for reasoning-heavy report generation
REPORT_MIN_SECTIONS = 6
REPORT_MAX_TOOL_CALLS = 15
```

---

## Tests

```python
# tests/unit/test_report_agent.py
test_report_agent_produces_all_required_sections()
test_report_agent_calls_tools_during_generation()
test_report_agent_respects_max_iterations()
test_report_output_contains_scenario_metadata()
test_report_agent_handles_empty_results()
test_report_grounding_validation_catches_generic_statements()
```

Note: Tests should use `LLMClient` in mock mode to avoid API calls.

---

## Acceptance Criteria

- [ ] ReportAgent generates reports with all 6 required sections
- [ ] Each section contains variable-grounded statements (specific names + numbers)
- [ ] ReACT loop calls at least 3 different tools per report
- [ ] Report generation works in LLM mock mode for testing
- [ ] No generic statements like "various factors influence adoption"
- [ ] Grounding validation identifies ungrounded statements
- [ ] All tests pass with mock LLM
- [ ] structlog logging at each ReACT iteration
