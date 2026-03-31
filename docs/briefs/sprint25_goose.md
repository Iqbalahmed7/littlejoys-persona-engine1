# Sprint 25 — Goose (S5-04)
**Engineer:** Goose (Grok 4-1 Fast Reasoning)
**Theme:** Per-Persona Cohort Journey Map in Phase 1

---

## Context

Phase 1 shows aggregate cohort numbers (137 Never Aware, 37 Aware Not Tried, etc.) but gives no insight into individual persona journeys. A user wants to understand: "Which specific personas ended up lapsed, and why?" This sprint adds a cohort journey map — a persona-level breakdown that lets the user click into any cohort and see who is in it, with the key signal that placed them there.

---

## Task A — Cohort Journey Map Component

**File:** `app/pages/2_problem.py`

After the existing "Cohort Profiles" expanders section, add a new section:

```
## 🗺️ Persona Journey Map
```

Only show if `baseline_cohorts` is in session state.

**Layout:** A 5-column selector (one per cohort). The user clicks a cohort tile to expand the personas inside.

Use `st.radio` styled as button-group (or `st.segmented_control` if available in Streamlit 1.55) to select which cohort to inspect:
- 🔇 Never Aware (137)
- 👁️ Aware, Not Tried (37)
- 🛒 First-Time Buyer (1)
- ⭐ Current User (2)
- 💤 Lapsed User (23)

When a cohort is selected, render a table with one row per persona in that cohort:

| Persona | City | Income | Reason |
|---|---|---|---|
| Girish-Mumbai-Dad-34 | Mumbai | ₹12L | Never engaged — brand salience too low |
| ... | | | |

**Data source:**
- `baseline_cohorts.cohorts[cohort_id]` — list of persona_ids
- `baseline_cohorts.classifications` — list of `CohortClassification` objects with `persona_id`, `classification_reason`
- `population.get_persona(pid)` — for city and income

Cap the display at 50 personas. If more, show `st.caption("Showing first 50 of {n} personas.")`.

**Persona ID formatting:** Strip the internal UUID suffix if present. Display as-is if it's already a readable ID like `Girish-Mumbai-Dad-34`.

---

## Task B — Cohort Delta Insight

**File:** `app/pages/2_problem.py`

In the same section, below the table, add a compact insight card:

For the selected cohort, show the top 2 distinguishing attributes vs the overall population average. Pull from `persona.to_flat_dict()` for each persona in the cohort, compute mean per attribute, compare to population mean.

Format as:
```
This cohort scores higher on budget_consciousness (0.71 vs 0.52 avg)
and lower on health_anxiety (0.41 vs 0.63 avg) than the full population.
```

Only compute for cohorts with ≥5 personas (skip for First-Time Buyer if n=1).

Use `st.info()` styled callout for this insight.

---

## Task C — System Voice Narrative per Cohort

When a cohort is selected, render a `render_system_voice()` callout that narrates what the cohort represents and what the key signal was:

- **Never Aware**: "These {n} households never encountered the product through any channel. The primary driver is low brand salience — distribution and awareness investment are the unlock."
- **Aware, Not Tried**: "These {n} households know the product exists but didn't convert. Price, trust, and need clarity are the main blockers."
- **First-Time Buyer**: "These {n} households tried once but didn't return. The window between first purchase and habit formation is the critical intervention point."
- **Current User**: "These {n} households are your most valuable segment. Understanding what made them stick is the key to scaling."
- **Lapsed User**: "These {n} households were active buyers who stopped. Identifying their exit signal — often price, child rejection, or routine disruption — is the retention priority."

Fill `{n}` with the actual count.

---

## Acceptance Criteria

- [ ] Cohort Journey Map section appears in Phase 1 after existing cohort expanders
- [ ] Clicking a cohort shows table of personas with city, income, reason
- [ ] Delta insight shows top 2 distinguishing attributes for cohorts with ≥5 personas
- [ ] System Voice narrative renders per selected cohort
- [ ] Performance: table renders in <2s for cohorts of 137 personas
- [ ] All existing tests pass
