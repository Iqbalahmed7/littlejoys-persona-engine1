# Sprint 26 — Antigravity (S6-03)
**Engineer:** Antigravity (Gemini 3 Flash)
**Theme:** PDF Export from Synthesis Report + Professional Memo View

---

## Context

The Synthesis Report (Page 8) currently exports `.txt` and `.json`. The `pdf_export.py` module already exists in `src/analysis/` but is not wired to the page. This sprint connects PDF export to the Synthesis Report and adds a "memo view" — a formatted HTML preview of how the findings would read in a professional brief, suitable for screenshots or sharing.

---

## Task A — Wire PDF Export to Synthesis Report

**File:** `app/pages/8_synthesis_report.py`

**Existing module:** `src/analysis/pdf_export.py` — check what it currently exports and what inputs it requires.

In the "Export" section of Page 8, add a third download button:
```python
st.download_button(
    label="⬇️ Download PDF Brief",
    data=pdf_bytes,
    file_name=f"{scenario_id}_synthesis_report.pdf",
    mime="application/pdf",
)
```

**To generate `pdf_bytes`:**
1. Import the relevant export function from `src/analysis/pdf_export.py`
2. Pass `core_finding`, `cohort_summary`, `scenario_id`, and `top_interventions` (top 5 by lift)
3. If the existing `pdf_export.py` doesn't support synthesis report format, add a new function `export_synthesis_pdf(...)` to that module

The PDF should contain (at minimum):
- Page header: "LittleJoys Persona Engine — Synthesis Report"
- Business Problem (scenario name + human-readable label)
- Population baseline (5 cohort metrics as a simple table)
- Core Finding (dominant hypothesis + confidence %)
- Top 5 interventions (name, adoption rate, lift)
- Footer: generated date

Use `reportlab` or `fpdf2` if either is already in the project dependencies. Do not add new dependencies — check `pyproject.toml` first.

---

## Task B — Professional Memo View

**File:** `app/pages/8_synthesis_report.py`

Above the Export section, add a collapsible "📄 Preview as Executive Memo" expander.

When expanded, render an HTML memo-style layout using `st.markdown(..., unsafe_allow_html=True)`:

```
MEMORANDUM

To:     Growth & Product Team
From:   LittleJoys Persona Engine
Re:     [Business Problem]
Date:   [Today's date]

EXECUTIVE SUMMARY
[1-2 sentence synthesis of the core finding]

POPULATION BASELINE
[Cohort breakdown as a clean table]

CORE FINDING
[Dominant hypothesis at X% confidence]
[Evidence summary from confirmed hypotheses]

RECOMMENDED INTERVENTIONS
1. [Top intervention] — projected +X% adoption lift
2. [2nd intervention] — projected +X% adoption lift
...

This analysis is based on a 200-persona synthetic population simulation.
```

Style the memo with:
- White background with 1px border
- Courier/monospace font for the header block
- Clean table for the cohort section
- Left-aligned text throughout

The memo view is read-only (no editing). It's just a shareable preview.

---

## Task C — Synthesis Report Page Gate Fix

**File:** `app/pages/8_synthesis_report.py`

Currently the page requires `core_finding` in session state. If a user navigates here directly without completing Phase 3, they see an error.

Add a proper gate:
```python
if "core_finding" not in st.session_state:
    st.warning("Complete the investigation through Phase 3 first to generate a synthesis report.", icon="🔒")
    st.page_link("pages/4_finding.py", label="→ Go to Phase 3: Core Finding")
    st.stop()
```

If `intervention_run` is NOT in session state (Phase 4 not run), the intervention section should show an info message instead of crashing:
```python
st.info("Run Phase 4 — Interventions to include intervention recommendations in this report.")
```

---

## Acceptance Criteria

- [ ] "Download PDF Brief" button appears and produces a valid PDF
- [ ] PDF contains all required sections (header, problem, baseline, finding, interventions, footer)
- [ ] No new dependencies added — uses existing packages in pyproject.toml
- [ ] "Preview as Executive Memo" expander renders clean memo-style HTML
- [ ] Page 8 gate shows helpful error + link if Phase 3 not complete
- [ ] Page 8 intervention section shows info message (not crash) if Phase 4 not run
- [ ] All existing tests pass
