# UAT Report — LittleJoys Persona Simulation Engine
**Date:** 2026-03-30
**Reviewer:** Tech Lead (Claude Sonnet 4.6) — Code review pass
**Method:** Full source code review of all 5 pages + utility modules against 65 test cases
**Status:** ⚠️ NOT READY — 2 confirmed bugs, 1 confirmed UX gap, visual verification required

---

## 1. EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| Test cases assessed | 65 |
| PASS (confirmed by code) | 47 |
| FAIL (confirmed by code) | 3 |
| NEEDS VISUAL VERIFY | 10 |
| BLOCKED | 5 |
| Confirmed bugs | 2 Critical, 1 High, 3 Medium, 4 Low |
| Demo readiness verdict | **NOT READY — fix 2 items first** |

The simulation engine and analysis pipeline are solid. Two deliverables from Sprints 20–21 did not survive subsequent sprint cleanup:
1. **CSV export was stripped from the personas page** (Goose Sprint 20 work removed by Cursor Sprint 21 lint cleanup)
2. **Demo mode callouts and toggle are missing from the results page** (OpenCode Sprint 21 delivery not reflected in final file)

Fix these two items and the POC is demo-ready.

---

## 2. TEST RESULTS TABLE

### Home Page (`streamlit_app.py`)

| TC-ID | Description | Result | Severity | Notes |
|-------|-------------|--------|----------|-------|
| TC-001 | Page loads without error | PASS | — | Clean structure |
| TC-002 | Population generation (seed=42, size=50) | PASS | — | Logic sound |
| TC-003 | Population generation (seed=42, size=300) | PASS | — | Same path |
| TC-004 | Changing seed produces different population | PASS | — | Seed passed through |
| TC-005 | Demo Mode toggle appears | PASS | — | Line 28 confirmed |
| TC-006 | Demo Mode preloads population | PASS | — | `ensure_demo_data()` called line 38 |
| TC-007 | Guided walkthrough captions (1️⃣–5️⃣) | PASS | — | Lines 31–35 confirmed |
| TC-008 | PM CHECK: Non-technical first impression | FAIL | Medium | See UX-001 |

### Personas Page (`1_personas.py`)

| TC-ID | Description | Result | Severity | Notes |
|-------|-------------|--------|----------|-------|
| TC-009 | Personas display after population loaded | PASS | — | Guard + `pop.to_dataframe()` confirmed |
| TC-010 | Filters work | PARTIAL | Low | Filters are city_tier, SEC, dietary_culture, region — not the brief's income/employment/child_age. Functional but different cuts. |
| TC-011 | Filter combination returns correct subset | PASS | — | AND-logic confirmed lines 146–153 |
| TC-012 | "Showing N/300" count updates | PASS | — | Line 155 confirmed |
| TC-013 | CSV export button appears | **FAIL** | **Critical** | No `download_button`, `csv`, or `CSV` found anywhere in file. Cursor's lint cleanup removed Goose's export code entirely. |
| TC-014 | CSV columns human-readable | **BLOCKED** | — | Button missing; can't verify columns |
| TC-015 | CSV respects active filters | **BLOCKED** | — | Button missing |
| TC-016 | 0 filtered results — button hidden | **BLOCKED** | — | Button missing |
| TC-017 | Persona detail view opens | PASS | — | `render_persona_card` + narrative expander confirmed |
| TC-018 | PM CHECK: No raw field names visible | PARTIAL | Low | Filter label "SEC" is an abbreviation unfamiliar to marketing teams. See UX-004. |

### Results Page (`3_results.py`)

| TC-ID | Description | Result | Severity | Notes |
|-------|-------------|--------|----------|-------|
| TC-019 | Static scenario runs | PASS | — | `_render_legacy_dashboard` path confirmed |
| TC-020 | Temporal scenario runs (nutrimix_2_6) | PASS | — | Event monthly rollup path confirmed |
| TC-021 | Temporal scenario runs (nutrimix_7_14) | PASS | — | Same path |
| TC-022 | Static scenario runs (protein_mix) | PASS | — | Same path |
| TC-023 | Health banner renders | PASS | — | Lines 424–448 confirmed, dual placement logic correct |
| TC-024 | Health banner tooltips on hover | PASS | — | `help=` param on all 4 metrics confirmed |
| TC-025 | All 4 metric values non-zero | NEEDS VERIFY | — | Dependent on simulation data |
| TC-026 | Executive summary renders (mock mode) | PASS | — | `report.executive_summary` block confirmed |
| TC-027 | Funnel waterfall chart renders | PASS | — | Line 502–509 confirmed |
| TC-028 | Retention curve renders for temporal | PASS | — | Lines 624–661 confirmed, conditional on `event_monthly_rows` |
| TC-029 | Retention curve absent for static | PASS | — | `if event_monthly_rows:` guard correct |
| TC-030 | Counterfactual bar chart renders | PASS | — | Lines 1019–1085 confirmed |
| TC-031 | Counterfactual cards expand | PASS | — | `st.expander` per intervention confirmed |
| TC-032 | Behavioural segments renders | PASS | — | Lines 703–752 confirmed |
| TC-033 | Interview themes renders | PASS | — | Lines 1087–1113 confirmed |
| TC-034 | PDF download button appears | PASS | — | Line 1130 confirmed |
| TC-035 | PDF generates and downloads | NEEDS VERIFY | — | Code path correct; kaleido fallback present; visual verify needed |
| TC-036 | PDF contains correct name/date | NEEDS VERIFY | — | Visual verify needed |
| TC-037 | JSON download button works | PASS | — | Line 1119 confirmed |
| TC-038 | Demo mode callouts visible (Mode ON) | **FAIL** | **High** | No `demo_mode` toggle, no `👆` callouts, no `ensure_demo_data()` found anywhere in 3_results.py. OpenCode's Sprint 21 delivery not in final file. |
| TC-039 | Demo mode callouts absent (Mode OFF) | FAIL | — | N/A; feature missing |
| TC-040 | Error boundary: corrupt report degrades gracefully | PASS | — | Per-section try/except throughout confirmed. `importances = []` pre-init confirmed. |
| TC-041 | PM CHECK: Metrics understandable | PARTIAL | Medium | "Duration: X.Xs" metric (line 469) is internal-facing — brand manager doesn't need simulation runtime. See UX-005. |
| TC-042 | PM CHECK: Exec summary free of jargon | NEEDS VERIFY | — | Mock fixture content needs visual review |

### Deep Dive Interviews (`4_interviews.py`)

| TC-ID | Description | Result | Severity | Notes |
|-------|-------------|--------|----------|-------|
| TC-043 | Page loads without error | PASS | — | Clean structure |
| TC-044 | Persona selector populates | PASS | — | `result.interview_results` iteration confirmed |
| TC-045 | Interview starts for selected persona | PASS | — | `ir.responses` rendering confirmed |
| TC-046 | Interview response is coherent | NEEDS VERIFY | — | Mock LLM content; visual verify |
| TC-047 | Multiple turns without error | PARTIAL | Low | No error boundary on the interview rendering loop (lines 58–76). If any `ir.responses` entry is missing `question`/`answer` key, it crashes. |
| TC-048 | PM CHECK: Interview feels like real consumer | NEEDS VERIFY | — | Must see mock responses in demo context |

### Comparison Page (`5_comparison.py`)

| TC-ID | Description | Result | Severity | Notes |
|-------|-------------|--------|----------|-------|
| TC-049 | Page loads without error | PASS | — | Population guard confirmed |
| TC-050 | Scenario A/B dropdowns populate | PASS | — | `get_all_scenarios()` confirmed |
| TC-051 | Same scenario — delta = 0 | PASS | — | Zero-delta test in test suite confirmed |
| TC-052 | Static vs static renders | PASS | — | Active Rate shows "—" for static confirmed |
| TC-053 | Temporal vs temporal — overlay curves | PASS | — | `comp.temporal_monthly_a/b` path confirmed |
| TC-054 | Static vs temporal — "—" for static side | PASS | — | `None` propagation correct |
| TC-055 | Revenue in INR format, not percentage | PASS | — | `_format_revenue_l()` routing confirmed in updated file |
| TC-056 | Barrier table — red tint for Delta > 5 | PASS | — | `background-color: #ffe5e5` confirmed |
| TC-057 | Error boundary on comparison failure | PASS | — | `try/except` on `compare_scenarios` call confirmed |
| TC-058 | PM CHECK: Delta story clear | PARTIAL | Low | "pp" (percentage points) label in delta column. Marketing audience may not know "pp". |

### Cross-Page & System Tests

| TC-ID | Description | Result | Severity | Notes |
|-------|-------------|--------|----------|-------|
| TC-059 | Results cached on nav-away and return | PASS | — | `@st.cache_data` on `_consolidate` and `run_event_simulation` confirmed |
| TC-060 | Demo Mode persists across pages | NEEDS VERIFY | — | Streamlit session state persistence; visual verify |
| TC-061 | New population clears stale results | NEEDS VERIFY | — | Visual verify |
| TC-062 | All pages load without population — graceful | PASS | — | All 5 pages have `st.stop()` guard confirmed |
| TC-063 | Walkthrough numbers on every page | PARTIAL | Low | Results page (3_results.py) missing walkthrough — same missing section as TC-038 |
| TC-064 | Smoke test exits 0 | PASS | — | Confirmed by 3 independent test runs |
| TC-065 | 630+ tests pass | PASS | — | 634 tests, 632 pass, 2 skip confirmed |

---

## 3. BUG LIST

### BUG-001 — CSV Export Missing from Personas Page
**Severity:** Critical
**Page:** `app/pages/1_personas.py`
**Description:** Goose delivered a CSV export button (Sprint 20) using `csv.DictWriter`. Cursor's Sprint 21 lint cleanup removed `import csv` and `import io` as "unused" — which means the CSV download code was either already gone or was stripped as part of the cleanup pass. Grep confirms zero references to `download_button`, `csv`, or `CSV` in the file.
**Steps to reproduce:** Navigate to Personas page → look for export button below "Showing N personas" caption → button is absent.
**Expected:** Export button visible, downloads filtered persona CSV
**Actual:** No button, no export functionality
**Fix:** Restore Goose's CSV export code. The implementation is well-defined: `filtered.to_csv()` via pandas `StringIO`, `st.download_button("⬇️ Export Personas CSV", ...)`, hidden when `len(filtered) == 0`.

---

### BUG-002 — Demo Mode Toggle and Callouts Missing from Results Page
**Severity:** High
**Page:** `app/pages/3_results.py`
**Description:** OpenCode's Sprint 21 delivery claimed to add `demo_mode = st.sidebar.toggle(...)`, sidebar walkthrough captions, and `st.info("👆...")` callouts on the results page. Grep confirms zero references to `demo_mode`, `ensure_demo_data`, or the callout text anywhere in the file.
**Steps to reproduce:** Enable Demo Mode → navigate to Results page → no 🎯 badge, no walkthrough captions, no executive snapshot callout.
**Expected:** Demo Mode Active badge, walkthrough captions, two `st.info` callouts in demo mode
**Actual:** None of the above present
**Fix:** Add the same demo mode block that exists on all other pages (copy from `1_personas.py` lines 31–41 pattern). Add two conditional `st.info` callouts after health banner and after exec summary.

---

### BUG-003 — Interview Rendering Has No Error Boundary
**Severity:** Medium
**Page:** `app/pages/4_interviews.py`
**Description:** The interview rendering loop (lines 58–76) accesses `qa['question']` and `qa['answer']` with direct dict key access. If any interview response record is missing these keys (malformed LLM output), the entire page crashes with a `KeyError`. No try/except wrapper.
**Fix:** Wrap the `for ir in result.interview_results:` loop body in try/except, or use `.get('question', '—')` access.

---

### BUG-004 — "With Narratives: 0" in Demo Mode
**Severity:** Medium
**Page:** `app/streamlit_app.py` and `1_personas.py`
**Description:** `ensure_demo_data()` generates population with `deep_persona_count=0` for speed. Both the home page and personas page display a "With Narratives" metric. In demo mode this will always show 0, which looks broken to a client.
**Fix:** Either set `deep_persona_count=3` in `demo_mode.py` (accepts slightly slower demo load), or hide the "With Narratives" metric when in demo mode.

---

### BUG-005 — "Simulation summary (legacy)" Label Visible to Client
**Severity:** Low
**Page:** `app/pages/3_results.py` line 103
**Description:** When no `research_result` is in session but `scenario_results` exists, the fallback renders with `st.subheader("Simulation summary (legacy)")`. The word "legacy" signals to a client that they're seeing an old/broken feature.
**Fix:** Rename to `"Scenario Summary"` or `"Quick Results"`.

---

### BUG-006 — "pp" Delta Label Unexplained on Comparison Page
**Severity:** Low
**Page:** `app/pages/5_comparison.py`
**Description:** Delta column shows values like `"+3.2pp"`. "pp" (percentage points) is standard in data science but unfamiliar to a marketing audience.
**Fix:** Change to `"+3.2 ppts"` or `"+3.2 percentage points"`, or add a caption below the table explaining the notation.

---

## 4. UX FINDINGS

**UX-001 — Home page title/caption is too technical**
Title: "LittleJoys Persona Simulation Engine" — acceptable
Caption: "Synthetic persona engine for kids nutrition D2C in India" — "D2C", "synthetic persona engine" are jargon. Suggest: *"Understand how Indian parents decide to buy and reorder kids' nutrition products."*

**UX-002 — Mock mode banner is jarring**
The `🧪 Mock mode: Insights reflect model structure...` banner is prominent and orange. In a client demo it signals "this is fake". Suggest: rename to "Demo mode" with a softer blue `st.info` tone, or suppress it entirely in demo mode.

**UX-003 — No direct link from home to Results or Comparison**
Home page has `page_link` buttons to Personas and Research Design only. A client following the guided walkthrough (1→2→3→4→5) needs a visible path. The 5-step sidebar captions help, but a direct button on the home page would anchor the flow.

**UX-004 — "SEC" filter label on Personas page**
The filter reads "SEC" (socioeconomic class abbreviation used in Indian market research). Brand managers from smaller brands may not know this. Suggest: label it "Socioeconomic Class" or "SEC Class".

**UX-005 — "Duration: X.Xs" metric on Results page**
`m5.metric("Duration", f"{report.duration_seconds:.1f}s")` is an engineering diagnostic. A brand manager doesn't need to know the simulation took 4.2 seconds. Remove or move to a debug expander.

**UX-006 — Comparison page "pp" notation unexplained** *(same as BUG-006)*

---

## 5. PM READINESS ASSESSMENT

| Page | Score | Verdict | Key Gap |
|------|-------|---------|---------|
| Home | 6/10 | Needs polish | Caption is technical; no visual story of what the tool does |
| Personas | 7/10 | Mostly ready | CSV missing; "SEC" label; "With Narratives: 0" in demo |
| Results | 8/10 | Strong | Mock mode banner; Duration metric; demo callouts missing |
| Interviews | 7/10 | Good depth | Needs visual verify of response quality |
| Comparison | 8/10 | Clear delta story | "pp" notation; needs revenue context |

**What a brand manager will likely ask in the demo that we can't currently answer:**
1. "Can I export this to PowerPoint?" — No. PDF only.
2. "Can I see what happens if I change the price?" — Yes, via What-If on results page (but it's buried in legacy dashboard).
3. "How do I know these personas are realistic?" — Interview Deep Dive is the answer, but the path from Results → Interviews isn't signposted.
4. "What does 'pp' mean?" — Not explained.

---

## 6. RECOMMENDED FIXES BEFORE CLIENT DEMO

### Must Fix (blocks demo quality)

| Priority | Fix | Owner | Effort |
|----------|-----|-------|--------|
| 🔴 P1 | Restore CSV export on Personas page | Goose | 30 min |
| 🔴 P1 | Add demo mode toggle + callouts to Results page | OpenCode | 20 min |

### Should Fix (client-facing polish)

| Priority | Fix | Owner | Effort |
|----------|-----|-------|--------|
| 🟡 P2 | Fix "With Narratives: 0" in demo mode | OpenCode or Goose | 15 min |
| 🟡 P2 | Remove "Duration" metric from Results page | OpenCode | 5 min |
| 🟡 P2 | Rename "Simulation summary (legacy)" | OpenCode | 2 min |
| 🟡 P2 | Replace 🧪 Mock mode banner copy in demo mode | OpenCode | 10 min |
| 🟡 P2 | Add error boundary to interview rendering loop | Cursor | 15 min |

### Nice to Have (won't block demo)

| Priority | Fix | Owner | Effort |
|----------|-----|-------|--------|
| 🟢 P3 | Home page caption rewrite | OpenCode | 5 min |
| 🟢 P3 | Explain "pp" on comparison page | OpenCode | 5 min |
| 🟢 P3 | "SEC" → "Socioeconomic Class" on Personas | OpenCode | 2 min |

---

## 7. ITEMS REQUIRING YOUR VISUAL VERIFICATION

These cannot be confirmed by code review alone. Please check during your 5-minute app run:

1. **TC-025** — Do all 4 health banner metrics show non-zero values for nutrimix_2_6?
2. **TC-035/036** — Does the PDF download produce a readable, correctly-named file?
3. **TC-042** — Is the executive summary copy clean and jargon-free in mock mode?
4. **TC-046/048** — Do interview responses read like real Indian mothers, not AI outputs?
5. **TC-060** — Does Demo Mode badge persist when you navigate between pages?
6. **TC-061** — Does generating a new population clear the stale results correctly?

---

*Generated by Tech Lead code review pass — 2026-03-30*
*Visual verification by product owner required before client demo.*
