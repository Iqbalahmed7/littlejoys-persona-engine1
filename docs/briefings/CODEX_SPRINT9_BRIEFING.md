# Codex — Sprint 9 Track B: Interview Guardrails System

**Branch:** `sprint-9-track-b-interview-guardrails`
**Base:** `main`

## Context

The persona interview system needs post-response validation to catch:
- Responses that contradict prior turns
- Brand/lifestyle references inconsistent with the persona's SEC class
- Answers that venture outside the study domain
- Personas that too readily agree with leading/loaded questions

**Design doc:** `docs/designs/INTERVIEW-PROMPT-ARCHITECTURE.md` — Sections 4.1-4.4

## Deliverables

### 1. Create `src/analysis/interview_guardrails.py` (NEW)

#### 1.1 Scope Violation Check

```python
OUT_OF_SCOPE_PATTERNS: list[str] = [
    # Politics
    "election", "vote", "political", "bjp", "congress", "modi", "parliament",
    "government policy",
    # Sports
    "cricket", "ipl", "football", "world cup",
    # Finance (non-family)
    "stock market", "mutual fund", "investment portfolio", "crypto", "shares",
    "trading",
    # Workplace
    "office politics", "promotion", "appraisal", "boss", "colleague",
    # Religion (controversial)
    "religion", "hindu", "muslim", "christian", "caste",
    # Entertainment
    "bollywood", "movie review", "celebrity gossip",
]

def check_scope_violation(response: str) -> list[str]:
    """Flag responses that venture outside the study domain.

    Returns list of warning strings, empty if clean.
    """
```

Logic: Lowercase the response, check for any OUT_OF_SCOPE_PATTERNS. Return `["scope_violation:{pattern}"]` for each match.

**Important edge cases:**
- "temple" could appear in "I contemplate buying" — check for word boundaries
- "cricket" could appear in "my son's cricket practice" which IS in-scope (child activities). Use a simple heuristic: if "child" or "kid" or "son" or "daughter" also appears in the same sentence, skip the flag.
- Keep patterns lowercase for case-insensitive matching

#### 1.2 SEC Coherence Check

```python
# Brand/experience references by socioeconomic tier
SEC_PREMIUM_REFERENCES: set[str] = {
    "organic harvest", "slurrp farm", "by gummies", "wholesome first",
    "the whole truth", "yoga bar", "raw pressery", "farm to fork",
    "imported", "artisanal", "curated", "subscription box",
    "nutritionist consultation", "private pediatrician",
}

SEC_BUDGET_MARKERS: set[str] = {
    "can't afford", "too expensive for us", "out of our budget",
    "government hospital", "free sample", "ration shop",
    "monthly ration", "stretching our budget",
}

SEC_SHOPPING_TIERS: dict[str, set[str]] = {
    "premium": {"blinkit", "bigbasket", "amazon fresh", "nature's basket",
                "organic store", "whole foods"},
    "mass": {"amazon", "flipkart", "dmart", "reliance fresh"},
    "budget": {"kirana", "local store", "medical shop", "weekly market"},
}

def check_sec_coherence(response: str, persona: Persona) -> list[str]:
    """Flag if persona references brands/experiences outside their SEC reality.

    Returns list of warning strings.
    """
```

Logic:
- Get persona's `socioeconomic_class` and `household_income_lpa`
- **C1/C2 personas** (income < ₹8L): Flag if response contains any `SEC_PREMIUM_REFERENCES`
- **A1 personas** (income > ₹25L): Flag if response contains `SEC_BUDGET_MARKERS` (unlikely to say "can't afford")
- **Shopping platform check:** If persona's `primary_shopping_platform` is "local_store" but response mentions Blinkit/BigBasket extensively, flag as `sec_incoherent_shopping_reference`

Return warnings like:
- `"sec_incoherent_premium_reference"` — C-class persona mentioning premium brands
- `"sec_incoherent_affordability_claim"` — A-class persona claiming can't afford
- `"sec_incoherent_shopping_reference"` — Shopping channel mismatch

#### 1.3 Anti-Reframing Check

```python
LEADING_QUESTION_PATTERNS: list[str] = [
    "don't you think",
    "wouldn't you agree",
    "isn't it true that",
    "surely you",
    "you must feel",
    "everyone knows that",
    "most parents think",
    "any good parent would",
    "you have to admit",
    "obviously",
]

AGREEMENT_MARKERS: list[str] = [
    "you're absolutely right",
    "yes, exactly",
    "i completely agree",
    "that's exactly what i think",
    "you took the words out of my mouth",
    "couldn't agree more",
    "you're so right",
    "absolutely, yes",
    "i was just thinking that",
]

def check_reframing_susceptibility(
    response: str,
    question: str,
) -> list[str]:
    """Flag if persona too readily agrees with a leading question.

    A real persona should push back on loaded framing, not parrot
    the interviewer's position.
    """
```

Logic:
1. Check if question contains any `LEADING_QUESTION_PATTERNS`
2. If NOT a leading question → return empty (no check needed)
3. If IS a leading question → check if response contains any `AGREEMENT_MARKERS`
4. If both match → return `["reframing_susceptibility_high"]`

#### 1.4 Cross-Turn Consistency Check

```python
def check_cross_turn_consistency(
    current_response: str,
    previous_turns: list[InterviewTurn],
    persona: Persona,
) -> list[str]:
    """Detect contradictions between current response and prior turns.

    Checks:
    1. Sentiment flip on the product (positive → negative or vice versa)
    2. Contradictory brand claims
    3. Income/lifestyle inconsistency
    """
```

Logic:
- Extract prior persona responses (role == "persona")
- **Sentiment flip:** Check if current response has positive product patterns (`"love it"`, `"would buy"`, `"works for us"`) while a prior response had negative patterns (`"would not buy"`, `"waste of money"`, `"don't need it"`), or vice versa. Flag as `"sentiment_flip_detected"`
- **Brand contradiction:** If a prior response says `"I use Horlicks"` and current says `"I've never used Horlicks"`, flag as `"brand_reference_contradiction"`. Check for patterns like `"I use {brand}"` vs `"never used {brand}"` or `"don't use {brand}"`
- Keep this lightweight — keyword-based, not LLM-based

#### 1.5 Master Guardrail Runner

```python
def run_all_guardrails(
    response: str,
    question: str,
    persona: Persona,
    decision_result: dict[str, Any],
    previous_turns: list[InterviewTurn] | None = None,
) -> list[str]:
    """Run all guardrail checks and return aggregated warnings.

    This is the single entry point for post-response validation.
    Called after every interview response (both interactive and probing tree).
    """
    warnings: list[str] = []
    warnings.extend(check_scope_violation(response))
    warnings.extend(check_sec_coherence(response, persona))
    warnings.extend(check_reframing_susceptibility(response, question))
    if previous_turns:
        warnings.extend(
            check_cross_turn_consistency(response, previous_turns, persona)
        )
    return warnings
```

### 2. Integrate Guardrails into `src/analysis/interviews.py`

Modify the `interview()` method in `PersonaInterviewer` to run guardrails after generating the response:

```python
from src.analysis.interview_guardrails import run_all_guardrails

# After getting response_text (line ~406):
guardrail_warnings = run_all_guardrails(
    response=response_text,
    question=question,
    persona=persona,
    decision_result=decision_result,
    previous_turns=conversation_history,
)
if guardrail_warnings:
    logger.info(
        "interview_guardrail_warnings",
        persona_id=persona.id,
        warnings=guardrail_warnings,
    )
```

The existing `check_interview_quality()` function stays unchanged — guardrails are additive. Merge warnings:

```python
quality = check_interview_quality(response_text, persona, decision_result)
all_warnings = quality.warnings + guardrail_warnings
if all_warnings:
    logger.info("interview_quality_warnings", persona_id=persona.id, warnings=all_warnings)
```

### 3. Display Guardrail Warnings in Interview UI

Modify `app/pages/5_interviews.py` to show guardrail warnings distinctly:

After line 211 (where quality is checked), add:

```python
from src.analysis.interview_guardrails import run_all_guardrails

guardrail_warnings = run_all_guardrails(
    response=reply.content,
    question=question,
    persona=selected_persona,
    decision_result=decision_result,
    previous_turns=history,
)

if guardrail_warnings:
    scope_violations = [w for w in guardrail_warnings if "scope" in w]
    sec_issues = [w for w in guardrail_warnings if "sec" in w]
    reframing = [w for w in guardrail_warnings if "reframing" in w]
    consistency = [w for w in guardrail_warnings if "flip" in w or "contradiction" in w]

    if scope_violations:
        st.warning("⚠️ Response may have ventured outside the study scope.")
    if sec_issues:
        st.warning("⚠️ Some references may not match this persona's socioeconomic profile.")
    if reframing:
        st.warning("⚠️ Persona may have agreed too readily with a leading question.")
    if consistency:
        st.warning("⚠️ Response may contradict something said earlier in this conversation.")
```

## Files to Read Before Starting

1. `src/analysis/interviews.py` — **full file** (416 lines) — you're integrating into this
2. `app/pages/5_interviews.py` — **full file** (219 lines) — interview UI page
3. `src/taxonomy/schema.py` — Persona model, especially DemographicAttributes (SEC, income, city)
4. `docs/designs/INTERVIEW-PROMPT-ARCHITECTURE.md` — Sections 4.1-4.4

## Constraints

- Python 3.11+
- `InterviewTurn` model is imported from `src.analysis.interviews` — use `TYPE_CHECKING` to avoid circular imports if needed
- Do NOT modify `PersonaInterviewer`'s public API
- Do NOT modify `check_interview_quality()` — guardrails are separate and additive
- Guardrail checks must be fast (no LLM calls, pure string/keyword matching)
- Each check function must return `list[str]` (empty = clean)
- No new pip dependencies

## Acceptance Criteria

- [ ] `interview_guardrails.py` created with 4 check functions + 1 runner
- [ ] Scope violation catches political, sports, finance, religion patterns
- [ ] Scope violation handles edge cases (child's cricket = OK, IPL cricket = flag)
- [ ] SEC coherence catches C-class premium references and A-class poverty claims
- [ ] Anti-reframing detects leading questions + agreement patterns
- [ ] Cross-turn consistency catches sentiment flips
- [ ] `run_all_guardrails()` aggregates all warnings
- [ ] Warnings logged in `interviews.py` after each response
- [ ] Warnings displayed in interview UI page
- [ ] All existing tests still pass
