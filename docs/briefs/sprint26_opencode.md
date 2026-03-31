# Sprint 26 — OpenCode (S6-05)
**Engineer:** OpenCode (GPT-5.4 Nano)
**Theme:** Home Page Narrative Dashboard

---

## Context

The home page currently shows 3 metrics (Total Personas, With Narratives, Business Problems) and a Getting Started list. For a POC demo, this is weak — a stakeholder landing on the home page should immediately understand what the engine found, not just that it exists. This sprint transforms the home page into a living narrative dashboard that surfaces the most interesting finding from the last completed investigation.

---

## Task A — "Last Investigation" Summary Card

**File:** `app/streamlit_app.py`

After the existing metrics row, add a conditional section that only shows if `core_finding` is in session state:

```python
if "core_finding" in st.session_state:
    _render_last_investigation_card()
```

**`_render_last_investigation_card()`** renders a card with:

```
┌─────────────────────────────────────────────────────────────┐
│  🔍  Last Investigation                                      │
│  [Business Problem name]                            [date]  │
│                                                             │
│  Core Finding:                                              │
│  [dominant_hypothesis_title] — [confidence]% confidence    │
│                                                             │
│  Top intervention: [name] (+X% adoption lift)              │
│                                                             │
│  [→ View Full Report]  [→ Re-run Investigation]            │
└─────────────────────────────────────────────────────────────┘
```

Style as a bordered card with a subtle blue-grey background (`#F0F4F8`). Use `st.markdown(..., unsafe_allow_html=True)`.

The "→ View Full Report" link uses `st.page_link("pages/8_synthesis_report.py", label="→ View Full Report")`.

The date should be today's date (from Python `datetime.date.today().strftime("%d %b %Y")`).

If `intervention_run` is not in session state, omit the "Top intervention" line.

---

## Task B — Population Archetype Cards

**File:** `app/streamlit_app.py`

After the Getting Started list (and before the quick-links), add a section that only shows if `population` is loaded:

```
### Who's in your population?
```

Show 3 archetype cards in columns — the 3 most numerically dominant persona archetypes inferred from the population.

**Archetype detection logic:**
1. Group personas by `(city_tier, socioeconomic_class)` pairs
2. Take the top 3 groups by count
3. For each group, generate a one-line description:
   - `f"{count} {city_tier} households, {sec_class} income bracket"`
4. Add the most common health_consciousness value for that group

Render each as a small `st.container(border=True)` with:
- Title: e.g. "Metro · High Income" (38 personas)
- Caption: "Predominantly high health consciousness"

Cap at 3 cards. Arrange in `st.columns(3)`.

---

## Task C — Engine Status Strip

**File:** `app/streamlit_app.py`

Replace the plain `st.markdown("---")` dividers with an Engine Status strip showing the state of all 5 phases for the current session. Only show if `population` is in session state.

```python
phases = [
    ("Population", "population"),
    ("Simulation", "baseline_cohorts"),
    ("Investigation", "probe_results"),
    ("Core Finding", "core_finding"),
    ("Interventions", "intervention_run"),
]
cols = st.columns(len(phases))
for i, (label, key) in enumerate(phases):
    done = key in st.session_state
    with cols[i]:
        st.markdown(
            f"<div style='text-align:center; padding:8px; "
            f"background:{'#D5F5E3' if done else '#FDFEFE'}; "
            f"border:1px solid {'#2ECC71' if done else '#D5D8DC'}; "
            f"border-radius:6px; font-size:0.85rem;'>"
            f"{'✅' if done else '○'} {label}</div>",
            unsafe_allow_html=True,
        )
```

This strip appears between the metrics row and the Last Investigation card (or Getting Started if no investigation yet).

---

## Acceptance Criteria

- [ ] Home page shows "Last Investigation" card if `core_finding` exists in session state
- [ ] Card shows business problem, dominant hypothesis, confidence %, top intervention (if available)
- [ ] "→ View Full Report" page_link navigates to Page 8
- [ ] Population archetype cards show top 3 groups with count + health consciousness summary
- [ ] Engine status strip shows 5 phase states with green/grey colouring
- [ ] No errors when session state is empty (fresh session)
- [ ] All existing tests pass
