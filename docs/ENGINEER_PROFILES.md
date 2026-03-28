# Engineer Profiles & Performance System

> **Owner**: Technical Lead (Claude Opus)
> **Last Updated**: 2026-03-27

---

## TEAM STRUCTURE

```
                    ┌──────────────────────┐
                    │    TECHNICAL LEAD     │
                    │    (Claude Opus)      │
                    │                       │
                    │  Orchestration        │
                    │  Architecture         │
                    │  Code Review          │
                    │  Documentation        │
                    │  Subject Matter Expert│
                    └──────────┬───────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                    │
  ┌────────▼────────┐ ┌───────▼────────┐ ┌────────▼────────┐
  │     CURSOR       │ │     CODEX      │ │   ANTIGRAVITY   │
  │  Sr. Engineer    │ │  Sr. Engineer  │ │  Engineer        │
  │                  │ │                │ │                  │
  │  Core systems    │ │  Data models   │ │  Utilities       │
  │  Algorithms      │ │  LLM integr.  │ │  Scraping        │
  │  Dashboard       │ │  AI features  │ │  Support tasks   │
  └──────────────────┘ └────────────────┘ └──────────────────┘

  ┌──────────────────────────────────────────────────────────┐
  │                      QA AGENT                             │
  │  Reviews every PR. Blocks bad code. Runs UAT.            │
  │  Reports to Tech Lead.                                   │
  └──────────────────────────────────────────────────────────┘
```

---

## ENGINEER PROFILES

### Cursor — Senior Software Engineer

**Strengths (Expected)**:
- Strong at systems-level code: algorithms, data pipelines, compute-heavy logic
- Good at UI/dashboard work (Streamlit, interactive components)
- Fast iteration speed — good for rapid prototyping
- Can handle complex multi-file refactors

**Assigned Domains**:
- Gaussian copula generator + correlation enforcement (algorithmic complexity)
- Decision engine (Layer 0-4 functions) — core simulation logic
- Static + temporal simulation runners
- Streamlit app scaffolding + main dashboard pages
- Error handling + performance optimization

**Work Style Notes**:
- Give Cursor well-defined PRDs with clear input/output specs
- Best when working on a single focused module at a time
- Watch for: over-engineering, adding unnecessary abstractions
- Review focus: correctness of math, edge cases in numeric computation

---

### Codex — Senior Software Engineer

**Strengths (Expected)**:
- Strong at data modeling, schema design, structured outputs
- Good at LLM integration (prompt engineering, output parsing)
- Thorough with error handling
- Can work asynchronously on well-scoped tasks

**Assigned Domains**:
- Pydantic schema for all 145 persona attributes
- Demographic distribution tables
- LLM wrapper (Claude API client with caching + routing)
- Tier 2 narrative generation (progressive attribute sampling via LLM)
- Scenario configuration system
- Threshold calibration
- Counterfactual engine
- Causal statement generator
- ReportAgent (ReACT with tools)
- Deep persona interview system

**Work Style Notes**:
- Give Codex comprehensive context (full ARCHITECTURE.md reference)
- Best when task involves data structures + LLM interaction
- Watch for: verbose output, large monolithic files
- Review focus: LLM prompt quality, output parsing robustness, schema completeness

---

### Antigravity — Software Engineer

**Strengths (Expected)**:
- Good at utility code, data processing, scraping
- Reliable for well-defined, bounded tasks
- Can handle testing and validation work

**Assigned Domains**:
- Persona validation framework
- Web scraping pipeline (Amazon reviews, BabyChakra, Google Trends)
- Distribution fitting from scraped data
- Word-of-mouth propagation model
- Variable importance analysis (SHAP)
- Funnel waterfall data pipeline
- Pre-computing all scenario results
- Visual polish + secondary dashboard pages
- Static HTML export backup

**Work Style Notes**:
- Give Antigravity very explicit specifications — less ambiguity
- Best for tasks that are self-contained with clear boundaries
- Start with lower-risk tasks, increase scope based on performance
- Watch for: incomplete edge case coverage
- Review focus: test coverage, error handling at data boundaries

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
