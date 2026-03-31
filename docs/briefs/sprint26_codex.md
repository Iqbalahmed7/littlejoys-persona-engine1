# Sprint 26 — Codex (S6-02)
**Engineer:** Codex (GPT-5.3)
**Theme:** Intervention Counterfactual Deep-Dive

---

## Context

Phase 4 currently shows a ranked comparison table with aggregate lift numbers. Users want to click into any intervention and see the micro-perturbation analysis — what happens if you tweak the intervention parameters slightly up or down? The engine already has `generate_default_counterfactuals()` which produces 9 standard micro-tweaks. This sprint wires that analysis into the results page.

---

## Task A — Counterfactual Analysis Per Intervention

**File:** `app/pages/6_intervention_results.py`

Below the comparison table, add a section:

```
## 🔬 Counterfactual Analysis
```

Add a selectbox populated with all 12 interventions (sorted by lift, same order as table):
```python
selected_iv_name = st.selectbox("Select an intervention to analyse", ...)
```

When an intervention is selected, run `generate_default_counterfactuals(intervention_scenario)` to produce the 9 standard micro-tweaks. Then run `run_counterfactual()` for each tweak.

Display results as a horizontal bar chart (Plotly `go.Bar`, horizontal):
- Y-axis: micro-tweak label (e.g. "Price −15%", "Pediatrician endorsement", "Taste +0.1")
- X-axis: adoption rate (%)
- Bars coloured green if > baseline, red if ≤ baseline
- Baseline shown as a vertical reference line

Below the chart, show a 3-column summary table:
| Tweak | Adoption | Lift vs Baseline | Lift vs Intervention |
|---|---|---|---|

**Data source:**
- `generate_default_counterfactuals(iv)` — from `src/analysis/counterfactual.py`
- `run_counterfactual(scenario, population)` — from same module
- `st.session_state["intervention_run"]["baseline_cohorts"]` for baseline rate

**Performance:** 9 `run_counterfactual()` calls are fast (<500ms total — static funnel). No spinner needed, but wrap in `st.cache_data` keyed on `(scenario_id, intervention_id)`.

---

## Task B — System Voice Insight per Counterfactual

After the chart, render a `render_system_voice()` callout that narrates the strongest and weakest tweaks:

```
"For [Intervention Name], the strongest sensitivity is to [top tweak]
(+X.X% vs baseline), and the weakest lever is [bottom tweak].
This suggests [interpretation based on parameter type]."
```

Build the interpretation string from the top tweak's parameter:
- If it involves price: "price sensitivity is the primary driver — a discount approach may outperform parameter changes alone"
- If it involves pediatrician/endorsement: "trust signals are the key unlock for this intervention"
- If it involves taste/recipe: "child acceptance remains the key friction even with this intervention in place"
- Default: "targeted parameter adjustments can further improve this intervention's impact"

---

## Task C — Cache and State Management

Use `st.session_state` to cache counterfactual results per intervention:
- Key: `f"cf_results_{scenario_id}_{intervention_id}"`
- Only compute when the selectbox changes to a new intervention
- Show a `st.spinner("Running 9 micro-perturbation scenarios…")` on first compute

---

## Acceptance Criteria

- [ ] Counterfactual section appears in Phase 4 Results below comparison table
- [ ] Selecting an intervention triggers 9 micro-tweak runs and shows bar chart
- [ ] Baseline reference line correctly placed on chart
- [ ] 3-column summary table shows tweak name, adoption, and both lift columns
- [ ] System Voice narrates strongest/weakest tweak with parameter interpretation
- [ ] Results cached per intervention — second selection of same intervention is instant
- [ ] All existing tests pass
