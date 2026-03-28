# LittleJoys Persona Engine — Product Roadmap

> **Owner**: Technical Lead (Claude Opus)
> **Last Updated**: 2026-03-27
> **Status**: Planning Complete — Ready for Sprint 0

---

## ROADMAP OVERVIEW

```
SPRINT 0 (Day 0)     ░░ Project Setup & Infrastructure
SPRINT 1 (Days 1-2)  ██ Persona Taxonomy & Generation Engine
SPRINT 2 (Days 3-4)  ██ Decision Engine & Simulation Core
SPRINT 3 (Days 5-6)  ██ Analysis, Reporting & Interviews
SPRINT 4 (Days 7-8)  ██ Presentation Layer (Streamlit)
SPRINT 5 (Days 9-10) ██ Hardening, QA & Demo Prep
```

---

## SPRINT 0: PROJECT SETUP & INFRASTRUCTURE

**Goal**: Every engineer can start coding immediately on Day 1 with a working dev environment, CI pipeline, and clear assignments.

| Task | PRD | Assignee | Priority |
|------|-----|----------|----------|
| Git repo init + branching strategy | — | Tech Lead | P0 |
| Python project scaffold (pyproject.toml, uv, src layout) | PRD-000 | Cursor | P0 |
| CI pipeline (lint, type-check, test on every push) | PRD-000 | Cursor | P0 |
| Staging environment setup | PRD-000 | Cursor | P0 |
| Shared LLM wrapper (Claude API client) | PRD-000 | Codex | P0 |
| Base Pydantic models (persona schema stubs) | PRD-000 | Codex | P0 |

**Exit Criteria**: `uv run pytest` passes. `uv run ruff check .` passes. All engineers can push to feature branches. Staging env boots.

---

## SPRINT 1: PERSONA TAXONOMY & GENERATION ENGINE

**Goal**: Generate a validated population of 300 Tier 1 + 30 Tier 2 personas grounded in real data.

| Task | PRD | Assignee | Priority | Depends On |
|------|-----|----------|----------|------------|
| Demographic distribution tables (India-specific) | PRD-001 | Codex | P0 | — |
| Persona Pydantic schema (all 145 attributes) | PRD-001 | Codex | P0 | — |
| Gaussian copula generator + correlation enforcement | PRD-001 | Cursor | P0 | Schema |
| Conditional distribution rules engine | PRD-001 | Cursor | P0 | Schema |
| Persona validation framework | PRD-001 | Antigravity | P0 | Schema |
| Web scraping pipeline (Amazon, BabyChakra, Trends) | PRD-002 | Antigravity | P1 | — |
| Distribution fitting from scraped data | PRD-002 | Antigravity | P1 | Scraping |
| Tier 2 narrative generation (LLM progressive fill) | PRD-003 | Codex | P0 | Schema + LLM wrapper |
| Population generator (orchestrates Tier 1 + Tier 2) | PRD-003 | Cursor | P0 | Copula + Schema |
| Population validation report (distribution checks) | PRD-003 | Cursor | P1 | Generator |
| **QA Gate**: Full population review + correlation audit | — | QA Agent | P0 | All above |

**Exit Criteria**: 300 Tier 1 personas pass all validation checks. 30 Tier 2 personas have coherent narratives. Population distributions match targets within tolerance. Correlation matrix matches specification.

---

## SPRINT 2: DECISION ENGINE & SIMULATION CORE

**Goal**: Run all 4 business scenarios and produce raw results.

| Task | PRD | Assignee | Priority | Depends On |
|------|-----|----------|----------|------------|
| Layer 0-3 decision functions (need → awareness → consideration → purchase) | PRD-004 | Cursor | P0 | Persona schema |
| Layer 4 repeat purchase model | PRD-004 | Cursor | P0 | Layers 0-3 |
| Scenario configuration system + 4 scenario configs | PRD-005 | Codex | P0 | Decision functions |
| Threshold calibration (Nutrimix 2-6 baseline) | PRD-005 | Codex | P0 | Decision + Scenarios |
| Static simulation runner (Mode A) | PRD-006 | Cursor | P0 | Decision + Scenarios |
| Temporal simulation runner (Mode B, monthly steps) | PRD-006 | Cursor | P0 | Repeat model |
| Word-of-mouth propagation model | PRD-006 | Antigravity | P1 | Temporal runner |
| Counterfactual engine | PRD-007 | Codex | P0 | Static runner |
| LJ Pass modeling (within temporal simulation) | PRD-007 | Codex | P0 | Temporal runner |
| **QA Gate**: Simulation sanity checks + edge case testing | — | QA Agent | P0 | All above |

**Exit Criteria**: All 4 scenarios run without errors. Nutrimix 2-6 baseline produces plausible adoption rate (8-20%). Counterfactuals show expected directional changes. Temporal simulation shows month-over-month dynamics. No NaN/Inf in any output.

---

## SPRINT 3: ANALYSIS, REPORTING & INTERVIEWS

**Goal**: Turn raw simulation data into causal insights and interactive persona conversations.

| Task | PRD | Assignee | Priority | Depends On |
|------|-----|----------|----------|------------|
| Segment analysis engine (group-by any attribute) | PRD-008 | Cursor | P0 | Simulation results |
| Barrier distribution analyzer | PRD-008 | Cursor | P0 | Simulation results |
| Variable importance (logistic regression + SHAP) | PRD-008 | Antigravity | P0 | Simulation results |
| Causal statement generator (variable-grounded) | PRD-008 | Codex | P0 | Variable importance |
| Funnel waterfall data pipeline | PRD-008 | Antigravity | P1 | Simulation results |
| LLM ReportAgent (ReACT with tools) | PRD-009 | Codex | P0 | Analysis engine |
| ReportAgent tool implementations | PRD-009 | Codex | P0 | All analysis |
| Deep persona interview system | PRD-010 | Codex | P0 | Tier 2 personas |
| Generate reports for all 4 business problems | PRD-010 | Antigravity | P1 | ReportAgent |
| **QA Gate**: Report quality review + interview realism audit | — | QA Agent | P0 | All above |

**Exit Criteria**: Each business problem has a structured report with causal insights grounded in specific variables. Interview mode produces realistic, in-character responses. No generic/hand-wavy statements in any output.

---

## SPRINT 4: PRESENTATION LAYER

**Goal**: Interactive Streamlit dashboard that tells a compelling story.

| Task | PRD | Assignee | Priority | Depends On |
|------|-----|----------|----------|------------|
| Streamlit app scaffolding + navigation | PRD-011 | Cursor | P0 | — |
| Population explorer page (scatter, distributions) | PRD-011 | Cursor | P0 | Population data |
| Scenario configurator page | PRD-011 | Antigravity | P1 | Scenario system |
| Results dashboard (funnel, heatmaps, barriers) | PRD-011 | Cursor | P0 | Analysis engine |
| Counterfactual comparison page | PRD-011 | Antigravity | P1 | Counterfactual engine |
| Persona interview chat interface | PRD-011 | Codex | P0 | Interview system |
| ReportAgent interactive page | PRD-011 | Codex | P1 | ReportAgent |
| "What-if" live mode (client changes params) | PRD-011 | Cursor | P1 | All engines |
| Visual polish + loading states | PRD-011 | Antigravity | P2 | All pages |
| **QA Gate**: Full UI walkthrough + edge case testing | — | QA Agent | P0 | All above |

**Exit Criteria**: Complete demo flow works end-to-end. All charts render correctly. No crashes on parameter edge cases. Interview mode responds in < 5 seconds. Pre-computed results load instantly.

---

## SPRINT 5: HARDENING, QA & DEMO PREP

**Goal**: Bulletproof demo. Zero chance of failure during client presentation.

| Task | PRD | Assignee | Priority | Depends On |
|------|-----|----------|----------|------------|
| Pre-compute all 4 scenario results + counterfactuals | — | Antigravity | P0 | All engines |
| Error handling + graceful fallbacks | — | Cursor | P0 | All code |
| Security audit (no API keys in code, input sanitization) | — | QA Agent | P0 | All code |
| Performance optimization (< 30s for 300 persona sim) | — | Cursor | P1 | Simulation |
| Demo script document (exact click-by-click flow) | — | Tech Lead | P0 | Dashboard |
| Methodology document for client | — | Tech Lead | P0 | — |
| Full end-to-end QA pass | — | QA Agent | P0 | Everything |
| Backup: static HTML export of all results | — | Antigravity | P1 | Dashboard |
| Record demo video as backup | — | Tech Lead | P1 | Dashboard |
| **Final Gate**: Full dry-run of presentation | — | All | P0 | Everything |

**Exit Criteria**: Demo runs flawlessly 3 times in a row. Static backup exists. Methodology doc is clear and client-ready. Zero known bugs.

---

## MILESTONES & GO/NO-GO GATES

| Milestone | Day | Gate Criteria | Decision Maker |
|-----------|-----|--------------|-----------------|
| **M0: Dev Ready** | 0 | CI passes, env works, all branches created | Tech Lead |
| **M1: Population Generated** | 2 | 300+30 personas, validated, distributions match | Tech Lead + QA |
| **M2: Simulation Complete** | 4 | All 4 scenarios run, results plausible | Tech Lead + QA |
| **M3: Insights Ready** | 6 | Reports generated, interviews work | Tech Lead |
| **M4: Demo Ready** | 8 | Full dashboard operational | Tech Lead + QA |
| **M5: Ship It** | 10 | Dry run passed, backups ready | Tech Lead |

At each gate, if criteria not met → we don't advance. Fix first, then proceed.

---

## RISK REGISTER

| Risk | Probability | Impact | Mitigation | Owner |
|------|------------|--------|-----------|-------|
| LLM API rate limits during bulk generation | Medium | High | Batch with exponential backoff. Cache all results. | Codex |
| Copula generator produces unrealistic edge cases | Medium | Medium | Validation framework catches these. Regenerate outliers. | Cursor |
| Scraping gets blocked | Medium | Low | Use fallback distributions from published market research. | Antigravity |
| Streamlit can't handle complex visualizations | Low | Medium | Pre-render charts as Plotly HTML. Serve as iframes. | Cursor |
| Demo breaks during live presentation | Low | Critical | Pre-computed static results as backup. Recorded video. | Tech Lead |
| Engineer produces buggy code that cascades | Medium | High | QA Agent reviews every PR. No direct merges to main. | QA Agent |
