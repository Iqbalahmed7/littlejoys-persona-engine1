# PRD-010: Deep Persona Interview System

> **Sprint**: 3
> **Priority**: P0 (Critical Path)
> **Assignee**: Codex (interview system), Antigravity (report generation for all 4 scenarios)
> **Depends On**: PRD-003 (Tier 2 personas), PRD-004 (decision engine), PRD-009 (ReportAgent)
> **Status**: Ready for Development

---

## Objective

Build an interactive interview system where users can converse with Tier 2 personas. The LLM role-plays as a specific persona, staying in character with all 145 attributes, their narrative, and their simulation outcome. This is the "wow factor" for client demos.

---

## Architecture Reference

See ARCHITECTURE.md section 9.3 for the interview system prompt template and character rules.

---

## Deliverables

### D1: Persona Interview Engine (Codex)

**File**: `src/analysis/interviews.py`

```python
class InterviewTurn(BaseModel):
    role: Literal["user", "persona"]
    content: str
    timestamp: str

class InterviewSession(BaseModel):
    persona_id: str
    persona_name: str
    scenario_id: str
    turns: list[InterviewTurn]
    persona_outcome: str  # "adopt" or "reject"

class PersonaInterviewer:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    async def interview(
        self,
        persona: Persona,
        question: str,
        scenario_id: str,
        decision_result: dict[str, Any],
        conversation_history: list[InterviewTurn] | None = None,
    ) -> InterviewTurn:

    def build_system_prompt(
        self,
        persona: Persona,
        scenario_id: str,
        decision_result: dict[str, Any],
    ) -> str:

    async def start_session(
        self,
        persona: Persona,
        scenario_id: str,
        decision_result: dict[str, Any],
    ) -> InterviewSession:
```

### D2: System Prompt Construction

The system prompt must include:
1. **Demographics**: name, age, city, tier, employment, education, income, family structure
2. **Children**: ages, number, specific concerns
3. **Psychographic highlights**: top 5 defining attributes with their actual values (e.g., "Your health_anxiety is 0.82 — you worry constantly about your children's health")
4. **Daily routine summary**: from the Tier 2 narrative
5. **Decision context**: which product, what happened at each funnel stage (scores), final outcome, rejection reason if applicable
6. **Character rules** (from ARCHITECTURE.md section 9.3):
   - Stay completely in character
   - Reference specific details from the profile
   - Relate price questions to actual income and spending patterns
   - Relate trust questions to actual information sources
   - Do not break character or acknowledge being AI
   - Use natural speech patterns appropriate to the persona (Hindi-English code-mixing if appropriate)

### D3: Conversation Management

Requirements:
1. **Stateful sessions**: maintain conversation history across turns
2. **Context window management**: if conversation exceeds token limits, summarize older turns
3. **Response length**: target 100-200 words per response (natural conversation length)
4. **Response time**: must respond within `INTERVIEW_MAX_RESPONSE_SECONDS` (5s from constants)
5. **Model routing**: use `INTERVIEW_LLM_MODEL` constant (Sonnet for speed, Opus for depth)

### D4: Interview Quality Guardrails

```python
class InterviewQualityCheck(BaseModel):
    in_character: bool
    references_profile: bool
    appropriate_length: bool
    no_ai_disclosure: bool
    warnings: list[str]

def check_interview_quality(
    response: str,
    persona: Persona,
    decision_result: dict[str, Any],
) -> InterviewQualityCheck:
```

Checks:
1. Response doesn't contain phrases like "as an AI", "I'm a language model", "I don't have feelings"
2. Response references at least one specific attribute from the persona profile
3. Response length is between 50-300 words
4. If persona rejected the product, response doesn't enthusiastically endorse it (and vice versa)

### D5: Generate Reports for All 4 Business Problems (Antigravity)

Use the ReportAgent (PRD-009) to generate analysis reports for each of the 4 scenarios.

**File**: `scripts/generate_reports.py`

```python
async def generate_all_reports(
    population_path: str = "data/population.parquet",
    output_dir: str = "data/results/reports",
) -> None:
```

Requirements:
1. Load saved population (or generate if not found)
2. Run static simulation for each of the 4 scenarios
3. Pass results through the ReportAgent
4. Save each report as markdown: `data/results/reports/{scenario_id}_report.md`
5. Save a combined summary: `data/results/reports/executive_summary.md`
6. Log timing for each report generation
7. Handle LLM mock mode for CI (generate placeholder reports)

---

## Constants

Add to `src/constants.py`:
```python
INTERVIEW_LLM_MODEL = "sonnet"  # Sonnet for speed in interactive mode
INTERVIEW_MAX_TURNS = 20
INTERVIEW_MAX_CONTEXT_TOKENS = 8000
INTERVIEW_RESPONSE_MIN_WORDS = 50
INTERVIEW_RESPONSE_MAX_WORDS = 300
INTERVIEW_AI_DISCLOSURE_PATTERNS = [
    "as an ai", "language model", "i don't have feelings",
    "i'm not a real person", "i was programmed",
]
```

---

## Tests

### Interview System (Codex)
```python
# tests/unit/test_interviews.py
test_system_prompt_includes_persona_demographics()
test_system_prompt_includes_decision_outcome()
test_system_prompt_includes_psychographic_highlights()
test_interview_returns_interview_turn()
test_interview_maintains_conversation_history()
test_interview_works_in_mock_mode()
test_quality_check_catches_ai_disclosure()
test_quality_check_validates_response_length()
test_quality_check_rejects_inconsistent_sentiment()
```

### Report Generation (Antigravity)
```python
# tests/unit/test_report_generation.py
test_generate_reports_creates_output_files()
test_generate_reports_handles_mock_mode()
test_executive_summary_covers_all_scenarios()
```

---

## Acceptance Criteria

- [ ] Interview system produces in-character responses for both adopters and rejectors
- [ ] System prompt includes all required persona context (demographics, psychographics, decision)
- [ ] Conversation history is maintained across turns
- [ ] Quality check catches obvious character breaks
- [ ] Reports generated for all 4 business problems
- [ ] Reports contain variable-grounded insights (not generic statements)
- [ ] Interview and report generation work in LLM mock mode
- [ ] All tests pass
- [ ] Response time < 5 seconds per interview turn (in non-mock mode)
