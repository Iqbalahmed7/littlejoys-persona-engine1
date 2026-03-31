# Sprint 26 — Goose (S6-04)
**Engineer:** Goose (Grok 4-1 Fast Reasoning)
**Theme:** Persona Segment Builder — Custom Cohort Slices

---

## Context

Phase 1 classifies all 200 personas into 5 fixed simulation cohorts. But users often want to ask questions like "show me only Metro + high-income households" or "show me households with children aged 3–6". This sprint adds a Segment Builder in Phase 1 that lets users create custom population slices and see their cohort distribution, for richer "who is my target?" analysis.

---

## Task A — Segment Builder UI

**File:** `app/pages/2_problem.py`

After the existing "Persona Journey Map" section, add:

```
## 🎯 Segment Builder
```

Caption: "Slice the population by demographics and see how cohort distribution shifts."

**Filters (each optional, multi-select or range):**

```python
col_f1, col_f2, col_f3, col_f4 = st.columns(4)
with col_f1:
    city_filter = st.multiselect("City Tier", ["Metro", "Tier 2 City", "Emerging City"])
with col_f2:
    income_filter = st.select_slider("Household Income (₹L/yr)",
                                      options=[3, 5, 8, 12, 18, 25, 40],
                                      value=(3, 40))
with col_f3:
    age_filter = st.select_slider("Child Age Range",
                                   options=[0,1,2,3,4,5,6,7,8,9,10,11,12,13],
                                   value=(0, 13))
with col_f4:
    health_filter = st.multiselect("Health Consciousness", ["Low", "Medium", "High"])
```

Add a "Apply Segment" button. On click:
1. Filter `pop.personas` by the selected criteria (AND logic — all filters must match)
2. Show the segment size: `st.metric("Segment Size", f"{n} personas ({pct}%)")`
3. Show a mini cohort breakdown for the filtered segment (same 5-tile layout from Phase 1, but computed only over filtered personas using `cohorts.memberships`)

**Zero results guard:** If segment is empty, show `st.warning("No personas match this combination. Try widening the filters.")`.

---

## Task B — Segment Cohort Comparison

When a segment is applied, show a side-by-side comparison:

```python
col_pop, col_seg = st.columns(2)
with col_pop:
    st.caption("📊 Full population (200)")
    # 5 cohort tiles — full population
with col_seg:
    st.caption(f"🎯 Your segment ({n} personas)")
    # 5 cohort tiles — filtered segment only
```

Below, add a plain-text insight generated from the comparison:

```python
# Compare lapse rates
full_lapse_rate = ...
seg_lapse_rate = ...
if seg_lapse_rate > full_lapse_rate * 1.2:
    st.info(f"💡 This segment has a higher lapse rate ({seg_lapse_rate:.0f}%) "
            f"than the full population ({full_lapse_rate:.0f}%). "
            "Retention-focused interventions may be especially effective here.")
elif seg_lapse_rate < full_lapse_rate * 0.8:
    st.info(f"💡 This segment has a lower lapse rate ({seg_lapse_rate:.0f}%) — "
            "it may represent a more loyal sub-population worth targeting for growth.")
```

Write at least one comparative insight for: lapse rate, adoption rate, never-aware rate. Show the most notable one (largest percentage-point deviation from population average).

---

## Task C — Persona Filter Lookup

**Data access:**
- `pop.personas` — full list
- `persona.demographics.city_tier` — "Metro" / "Tier 2 City" / "Emerging City"
- `persona.demographics.household_income_lpa` — float (₹ lakhs/year)
- `persona.children` — list of child objects, each with `.age_years`
- `persona.health_consciousness` — "Low" / "Medium" / "High"

For child age filter: a persona matches if ANY of their children falls within the `age_filter` range.

**Session key:** Store the filtered persona IDs as `st.session_state["segment_persona_ids"]` so other pages could theoretically use the segment. Do not use this key anywhere else yet — just establish the convention.

---

## Acceptance Criteria

- [ ] Segment Builder section appears in Phase 1 below Persona Journey Map
- [ ] All 4 filters work independently and in combination
- [ ] "Apply Segment" shows segment size + 5-cohort breakdown for the filtered subset
- [ ] Side-by-side comparison renders: full population vs segment cohort tiles
- [ ] At least one auto-generated insight appears comparing lapse/adoption/never-aware rates
- [ ] Empty segment shows warning (no crash)
- [ ] Segment persona IDs stored under `segment_persona_ids` key
- [ ] All existing tests pass
