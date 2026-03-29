# Engineer Profiles & Performance System

> **Owner**: Technical Lead (Claude Opus)
> **Last Updated**: 2026-03-29

---

## TEAM STRUCTURE

```
                    ┌──────────────────────┐
                    │    TECHNICAL LEAD     │
                    │    (Claude Opus)      │
                    │  Day-to-day: Sonnet   │
                    │                       │
                    │  Orchestration        │
                    │  Architecture         │
                    │  Code Review          │
                    │  Documentation        │
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                       │
┌───────▼───────┐  ┌──────────▼──────┐  ┌────────────▼────────┐
│    CURSOR      │  │     CODEX       │  │    ANTIGRAVITY       │
│  Auto model   │  │ GPT-5.3-Codex   │  │  Gemini 3 Flash      │
│               │  │ (Medium)        │  │                      │
│  Architecture │  │ Backend logic   │  │  Tests               │
│  Complex pages│  │ Data models     │  │  Validation          │
│  Refactors    │  │ Pipelines       │  │  Support tasks       │
└───────────────┘  └─────────────────┘  └──────────────────────┘

┌───────────────┐  ┌─────────────────┐
│   OPENCODE    │  │     GOOSE       │
│ GPT-5.4 Nano  │  │  Grok-4-1-fast  │
│               │  │  -reasoning     │
│  UI/Streamlit │  │                 │
│  Frontend     │  │  Complex logic  │
│  UX polish    │  │  Reasoning tasks│
└───────────────┘  └─────────────────┘
```

---

## ENGINEER PROFILES

### Cursor — Senior Software Engineer

**Model**: Auto (Claude selects best model per task)
**Upgrade path**: N/A — already adaptive

**Strengths**:
- Architecture, complex multi-file refactors, system design
- Results/dashboard pages with intricate layout logic
- Cross-module integration work
- Best engineer for highest-complexity tasks

**Assigned Domains (Phase 2)**:
- Temporal results page (trajectory charts, behavioural segments)
- Event-driven simulation UI (Sprint 17+)
- Complex page refactors requiring deep context

**Work Style Notes**:
- Give full ARCHITECTURE.md context
- Best for tasks spanning multiple modules
- Watch for: occasionally over-engineers; keep scope tight

---

### Codex — Senior Software Engineer

**Model**: GPT-5.3-Codex (Medium)
**Upgrade path**: GPT-5.4 (High) for very complex tasks | GPT-5.4-mini (Low/Medium) for simpler ones
**When to upgrade**: Canonical State Model implementation (Sprint 17), counterfactual engine (Sprint 18)

**Strengths**:
- Backend algorithms, data pipelines, simulation engine logic
- Pydantic models, structured data transforms
- Wiring modules together (research runner, consolidator)
- Reliable delivery; needs well-specified briefs

**Assigned Domains (Phase 2)**:
- EventEngine + Canonical State Model (Sprint 17) — upgrade to GPT-5.4
- Counterfactual engine (Sprint 18)
- LLM-calibrated thresholds
- Executive summary generation

**Work Style Notes**:
- Give comprehensive specs — Codex executes well with detail
- Watch for: files not on disk on first attempt (re-export if needed)
- Review focus: Pydantic model completeness, edge cases

---

### Antigravity — Software Engineer

**Model**: Gemini 3 Flash
**Upgrade path**: Gemini 3.1 Pro (High or Low) for complex test logic
**When to upgrade**: Integration tests with multiple fixture dependencies, complex edge case debugging

**Strengths**:
- Tests, validation, well-bounded tasks
- Good at debugging test failures systematically (showed this in Sprint 16)
- Reliable for explicit, clearly-scoped work

**Assigned Domains (Phase 2)**:
- All unit + integration tests across sprints
- Upgrade to Pro when tests require deep fixture setup or complex assertions

**Work Style Notes**:
- Very explicit specifications — minimal ambiguity
- Watch for: edge case gaps in first pass
- Review focus: test coverage completeness, fixture reuse

---

### OpenCode — Software Engineer

**Model**: GPT-5.4 Nano
**Upgrade path**: GPT-5.4-mini | GPT-5.4 for more complex UI tasks
**When to upgrade**: Pages with complex state logic or multiple inter-dependent components

**Strengths**:
- UI/Streamlit pages, frontend polish
- Clean, fast delivery on well-defined UI tasks
- Good at mode indicators, banners, labels, layout tweaks

**Assigned Domains (Phase 2)**:
- Research Design page updates
- UI cleanup, mock banners, indicators
- UX polish tasks
- Upgrade to GPT-5.4-mini for pages with complex conditional rendering

**Work Style Notes**:
- Keep tasks UI-only — don't mix backend logic
- Watch for: may not handle complex conditional state well on Nano

---

### Goose — Software Engineer

**Model**: Grok-4-1-fast-reasoning
**Upgrade path**: N/A (reasoning model, already strong)

**Strengths**:
- Fast reasoning — good for tasks requiring logical deduction
- Can handle moderately complex backend tasks
- Good for well-scoped algorithmic problems

**Best Fit Tasks**:
- Rule derivation and threshold calibration logic
- Event grammar validation and firing rules
- Decision rule implementation (if/then logic heavy)
- Tasks where reasoning through edge cases matters more than broad context

**Work Style Notes**:
- PATH must be set: `export PATH="/Users/admin/.local/bin:$PATH"` in `.goosehints`
- Give precise, bounded tasks — reasoning models work best with clear constraints
- Good parallel option when Codex is on critical path

---

## PERFORMANCE SCORECARD SYSTEM

### Scoring Dimensions

Each engineer is rated on 6 dimensions after every sprint. Scale: 1-5.

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Code Quality** | 25% | Clean code, type hints, docstrings, no linting warnings, follows project conventions |
| **Correctness** | 25% | Does the code work? Match PRD spec? Handle edge cases? Bugs found post-merge? |
| **Delivery Speed** | 15% | Tasks completed on time relative to sprint plan? Blockers communicated early? |
| **Test Coverage** | 15% | Unit tests for all logic? Property-based tests for invariants? Integration tests where needed? |
| **Architecture Adherence** | 10% | Follows ARCHITECTURE.md? Correct module boundaries? No circular deps? |
| **Communication** | 10% | Clear PR descriptions? Assumptions documented? Questions asked early when blocked? |

### Rating Scale

| Score | Label | Meaning |
|-------|-------|---------|
| 5 | **Exceptional** | Exceeds expectations. Code is exemplary. Proactively catches issues. |
| 4 | **Strong** | Meets all expectations. Minor improvements possible. |
| 3 | **Adequate** | Meets most expectations. Some quality or completeness gaps. |
| 2 | **Below** | Significant issues. Multiple bugs, missing tests, or spec deviations. |
| 1 | **Critical** | Fundamental problems. Code unusable, needs complete rewrite. |

### Composite Score Calculation

```
composite_score = (
    code_quality * 0.25 +
    correctness * 0.25 +
    delivery_speed * 0.15 +
    test_coverage * 0.15 +
    architecture_adherence * 0.10 +
    communication * 0.10
)
```

### Work Assignment Based on Score

| Composite Score | Trust Level | Assignment Strategy |
|-----------------|-------------|-------------------|
| 4.0 - 5.0 | **High Trust** | Assigned P0 critical-path tasks. Less oversight needed. Can make architectural micro-decisions. |
| 3.0 - 3.9 | **Standard** | Assigned mix of P0 and P1 tasks. Normal review process. |
| 2.0 - 2.9 | **Supervised** | Assigned P1/P2 tasks only. Extra review passes. Paired with higher-trust engineer where possible. |
| < 2.0 | **Restricted** | Only utility/test tasks. All work double-reviewed. Consider reassignment. |

### Bug Tracking Impact

| Bug Severity | Score Penalty |
|-------------|--------------|
| **Critical** (blocks demo, data corruption) | -0.5 per bug |
| **Major** (incorrect results, crashes in staging) | -0.3 per bug |
| **Minor** (cosmetic, non-blocking) | -0.1 per bug |
| **Bugs caught by own tests** | No penalty (this is good!) |

### Sprint 0 Baseline

All engineers start at **3.5 (Standard+)**. Scores adjust based on actual Sprint 0-1 performance.

---

## SCORECARD TEMPLATE

```markdown
# Engineer Scorecard — [Sprint X]

## [Engineer Name]

### Tasks Assigned
| Task | PRD | Status | Notes |
|------|-----|--------|-------|
| ... | ... | ... | ... |

### Scores
| Dimension | Score (1-5) | Evidence |
|-----------|------------|----------|
| Code Quality | X.X | ... |
| Correctness | X.X | ... |
| Delivery Speed | X.X | ... |
| Test Coverage | X.X | ... |
| Architecture Adherence | X.X | ... |
| Communication | X.X | ... |

### Composite Score: X.X / 5.0
### Trust Level: [High / Standard / Supervised / Restricted]

### Bugs Introduced
| Bug | Severity | Sprint Detected | Penalty |
|-----|----------|----------------|---------|
| ... | ... | ... | ... |

### Strengths Observed
- ...

### Areas for Improvement
- ...

### Work Assignment Recommendation for Next Sprint
- ...
```

---

## INITIAL SPRINT 0-1 ASSIGNMENTS

Based on profiles and starting trust level:

### Cursor (Trust: Standard+ → 3.5)
```
Sprint 0:
  - PRD-000: Python project scaffold, CI pipeline, staging env setup
Sprint 1:
  - PRD-001: Gaussian copula generator + correlation enforcement
  - PRD-003: Population generator orchestration
  - PRD-003: Population validation report
```

### Codex (Trust: Standard+ → 3.5)
```
Sprint 0:
  - PRD-000: Shared LLM wrapper (Claude API client)
  - PRD-000: Base Pydantic model stubs
Sprint 1:
  - PRD-001: Full Pydantic schema (all 145 attributes)
  - PRD-001: Demographic distribution tables
  - PRD-003: Tier 2 narrative generation
```

### Antigravity (Trust: Standard+ → 3.5)
```
Sprint 1:
  - PRD-001: Persona validation framework
  - PRD-002: Web scraping pipeline
  - PRD-002: Distribution fitting from scraped data
```

---

## ESCALATION PROTOCOL

1. **Engineer blocked > 30 min**: Engineer flags in PR/commit message. Tech Lead reviews and unblocks.
2. **Engineer produces code that fails QA twice**: Tech Lead reviews the task scope. May reassign or pair.
3. **Engineer composite score drops below 2.5**: Task scope reduced. Only utility tasks. Full code review before any merge.
4. **Critical bug in staging**: All work pauses. Fix-forward or rollback. Post-mortem document.
5. **Sprint gate not met**: Tech Lead assesses. Can extend 1 day. If still not met, scope is cut (not timeline).
