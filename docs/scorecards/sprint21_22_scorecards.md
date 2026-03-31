# Sprint Scorecards — Sprints 21 & 22 (UX Redesign Phase)

> **Reviewer**: Tech Lead (Claude Opus)
> **Date**: 2026-03-31
> **Sprint Theme**: Option C UX Redesign — 5-Phase Pipeline (Problem → Simulation → Decomposition → Finding → Interventions)

---

## Sprint 21: UX Redesign Foundation (S1-01 → S1-05)

**Goal**: Replace scenario-first flow with problem-first flow. Add System Voice, Phase Gating, Problem Page with temporal simulation narrative, purchase history population.

**Executed by**: Tech Lead (direct implementation — no engineer delegation)

| Ticket | File | Status | Quality | Notes |
|--------|------|--------|---------|-------|
| S1-01 | `app/components/system_voice.py` | ✅ Delivered | A | Three-variant callout system (blue/green/orange). Clean inline CSS, reusable API. No third-party deps. |
| S1-02 | `app/utils/phase_state.py` | ✅ Delivered | A- | Phase sentinel pattern is clean. `render_phase_sidebar()` emits 🟢/🔒 icons correctly. Minor: could benefit from a `require_phase()` helper to reduce boilerplate in pages. |
| S1-03/04 | `app/pages/2_problem.py` | ✅ Delivered | A | Problem cards (2×2 grid), narrative simulation with monthly updates, cohort dashboard (5-col metrics + 4-col KPIs). Hides all scenario IDs from user. |
| S1-05 | `src/simulation/temporal.py` | ✅ Delivered | A | Targeted PurchaseEvent injection at adoption and repeat purchase. Non-invasive edit, zero regression risk. |

**Sprint Outcome**: All 5 deliverables complete. Foundation solid for Sprint 22.

**Process Note**: Sprint 21 lacked formal briefs and scorecard at time of execution. Retroactive review conducted. **Going forward: all engineer briefs must be written and linked before work begins.**

---

## Sprint 22: Decomposition & Probing (S2-01, S2-02, S2-04 complete — S2-03, S1-Cleanup pending)

**Goal**: Phase 2 Decomposition page, Sequential Probe Orchestrator, Semantic Memory in interviews, Reactive Probing Tree Viz, Navigation Cleanup.

### Completed Deliverables

| Ticket | Engineer | File | Status | Quality | Notes |
|--------|----------|------|--------|---------|-------|
| S2-01 | **Cursor** | `app/pages/3_decompose.py` | ✅ Delivered | A- | Phase guard ✅, System Voice ✅, hypothesis checkbox table ✅, verdict badge config ✅, indicator attribute chips ✅. Slight concern: uses `os.environ.get()` directly for mock flag instead of routing through `Config` — inconsistency with the rest of the codebase. |
| S2-02 | **Codex** | `app/utils/probe_orchestrator.py` | ✅ Delivered | A | `ProbeChainResult` + `OrchestrationResult` dataclasses are clean. Effect size labelling (`_effect_label`) and per-probe-type formatters (`_format_interview_detail`, `_format_attribute_detail`, `_format_simulation_detail`) are all correctly differentiated. Realistic reasoning narrative generation is solid. Risk: `structlog` dependency — verify it's in `pyproject.toml`. |
| S2-04 | **Goose** | `src/analysis/interview_prompts.py` | ✅ Delivered | A- | `_build_memory_context()` helper at line 559, injected at line 681. Correct fields: `tier2_anchor`, `tier2_stories`, `purchase_history`. Targeted, low-risk edit. Deduction: no unit test added for the memory context assembly. |

### Pending Deliverables

| Ticket | Engineer | File | Status |
|--------|----------|------|--------|
| S2-03 | **Antigravity** | `app/components/probing_tree_viz.py` | 🔲 Brief written — not yet launched |
| S1-Cleanup | **OpenCode** | `app/streamlit_app.py` + page archiving | 🔲 Brief written — not yet launched |

**Sprint 22 Outcome (partial)**: 3 of 5 deliverables complete. Quality high across the board. Two tasks awaiting brief-first launch.

---

## Engineer Performance Summary (Sprints 21–22)

| Engineer | Tickets | Avg Quality | Strengths | Watch Points |
|----------|---------|-------------|-----------|--------------|
| **Cursor** | S2-01 | A- | Frontend Streamlit fluency. Correct phase-guard pattern, good UX detail (chips, badges). | Config object bypass (used env var directly). Keep on frontend pages. |
| **Codex** | S2-02 | A | Backend data architecture. Clean dataclasses, well-typed, good narrative generation. | Verify dependency list stays in sync (`structlog`). Best fit: complex backend logic. |
| **Goose** | S2-04 | A- | Targeted surgical edits. Correctly identified injection point (line 681) without disrupting surrounding code. | No tests added with change. Flag for next sprint: every backend edit needs a corresponding unit test. |
| **Antigravity** | S2-03 | TBD | Previously strong on reactive UI (spider chart, etc). | — |
| **OpenCode** | S1-Cleanup | TBD | Previously reliable on low-risk cleanup/wiring. | — |

---

## Role Decisions for Sprint 23

| Engineer | Sprint 23 Role | Rationale |
|----------|---------------|-----------|
| **Cursor** | S3-01 `4_finding.py` (Core Finding page) | Best Streamlit frontend author. One correction needed: always use `Config` object, never raw env vars. |
| **Codex** | S3-02 `5_intervention.py` (Interventions + comparison table) | Strongest on structured data + table rendering logic. |
| **Antigravity** | S2-03 carry-over (reactive viz) | Speciality in reactive UI. If delivers S2-03 cleanly, promote to more complex reactive state work in S3. |
| **Goose** | S3 test suite | Add tests for `_build_memory_context`, `probe_orchestrator` early-exit logic, and Phase 2 page import checks. Fast reasoning model is well-suited to test generation. |
| **OpenCode** | S1-Cleanup carry-over | Nano model — keep on deterministic, low-ambiguity cleanup tasks. |
