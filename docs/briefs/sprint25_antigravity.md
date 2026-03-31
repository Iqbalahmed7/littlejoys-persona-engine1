# Sprint 25 — Antigravity (S5-03)
**Engineer:** Antigravity (Gemini 3 Flash)
**Theme:** Per-Persona Interview Deep-Dive + Fix Duplicate Theme Clusters

---

## Context

Phase 2 and Phase 7 currently show interview evidence aggregated across all sampled personas. Users want to drill into a specific persona and see all their responses in one place — cohort membership, what probe questions they were asked, what they said, and what themes emerged. This sprint adds a persona-focused interview view and fixes a duplicate theme cluster display bug.

---

## Task A — Fix Duplicate Theme Clusters in Phase 7

**File:** `app/pages/7_interviews.py`

**Bug:** The "Cross-Hypothesis Themes" section shows duplicate theme entries — e.g. "Trust Concern — 30 personas (100%)" appears twice because the same 30 sampled personas appear in two different probes with the same dominant theme.

**Fix:** Deduplicate the cross-hypothesis theme list before rendering. Group by `(theme_label, evidence_summary)` and keep only the entry with the highest `persona_count`. Alternatively, group by `theme_label` and show the maximum count.

Deduplication logic should happen in the data preparation, not in the template rendering.

---

## Task B — Per-Persona Interview Deep-Dive View

**File:** `app/pages/7_interviews.py`

After the existing "Compare Personas" section, add a new section:

```
## 🔍 Single Persona Deep-Dive
```

Add a selectbox: `Select a persona to deep-dive` — populated from all personas who appeared in at least one interview probe.

When a persona is selected, render a persona profile card at the top:
- Name/ID, city, household income bracket, cohort (e.g. 💤 Lapsed User)
- One-sentence description from `persona.narrative` (first sentence only, truncated at 150 chars)

Below the card, for each probe question this persona was asked, render:
- The probe question text
- Which hypothesis it belongs to (e.g. "H1 — Price feels different on repeat")
- The persona's full response text
- The theme it was classified under (e.g. "Price Sensitivity")

Layout: use `st.expander` per hypothesis, with probes nested inside.

**Data source:** The probe responses are in `probe_results["probes"]` — each probe has `responses` which is a list of dicts with `persona_id`, `response_text`, `theme_label`, `theme_summary`. Filter by `persona_id == selected_persona_id`.

If a persona has no responses (wasn't sampled): show `st.info("This persona was not sampled in the interview phase.")`.

---

## Task C — Link from Phase 2 Probe Cards

**File:** `app/pages/3_decompose.py`

In each probe's response cluster expander, after the 3 preview quotes, add a small `st.caption` for each:

```
[View Girish-Mumbai-Dad-34's full interview →]
```

This should be a link that navigates to the Interviews page with the persona pre-selected. Use `st.page_link("pages/7_interviews.py", label="View full interview →")` — note: Streamlit doesn't support query params natively, so for now the link just takes the user to the interviews page. The pre-selection will be wired in a future sprint.

---

## Acceptance Criteria

- [ ] Duplicate theme clusters in Phase 7 Cross-Hypothesis section are deduplicated
- [ ] "Single Persona Deep-Dive" section appears in Phase 7 with persona selector
- [ ] Selecting a persona shows profile card + all their responses grouped by hypothesis
- [ ] Phase 2 probe cards have "View full interview" links
- [ ] All existing tests pass
