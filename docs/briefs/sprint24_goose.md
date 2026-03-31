# Sprint 24 Brief — Goose
## S4-04: Phase 4 "Run All Simulations" + Full Intervention Comparison Table

> **Engineer**: Goose (OpenCode v2 → escalate to GPT 5.3 if parallel simulation loop proves complex)
> **Sprint**: 24
> **Ticket**: S4-04
> **Estimated effort**: Medium
> **Reference**: LittleJoys User Flow Document v2.0, Section 7.2, 7.3, 7.4, 7.5

---

### Context

Phase 4 currently works as: select ONE intervention → run counterfactual → see results on page 6. The v2.0 spec requires running **all interventions simultaneously** and showing a comparison table (Baseline vs every intervention) with complexity, time-to-market, and estimated cost columns.

The single-intervention "Configure & Launch" section in `5_intervention.py` needs to be replaced with a "Run All Simulations" approach. The results page (`6_intervention_results.py`) needs to become a full comparison dashboard.

**Important constraint**: The page currently switches to `6_intervention_results.py` after simulation. Keep that pattern — run all simulations on page 5, store in session state, display on page 6.

---

### Task 1: Replace Single-Intervention Launcher with "Run All"

File: `app/pages/5_intervention.py`

**Remove** the existing "Configure & Launch Simulation" section (from `# ── Configure & Launch Simulation` to `st.info("No interventions are available to simulate.")`).

**Replace with:**

```python
# ── Run All Simulations ───────────────────────────────────────────────────────
st.divider()
st.subheader("Run All Simulations")
st.caption(
    "The system will test every proposed intervention against your baseline population "
    "and show a full comparison — adoption lift, cohort impact, complexity, and time to market."
)

if interventions:
    # Pre-simulation population snapshot
    st.markdown("**Population going into simulation** *(Phase 1 baseline cohorts)*")
    _cohorts_snap = st.session_state.get("baseline_cohorts")
    if _cohorts_snap is not None:
        _cs = (
            _cohorts_snap.summary
            if hasattr(_cohorts_snap, "summary")
            else _cohorts_snap.get("summary", {})
        )
        _cohort_display_map = {
            "never_aware":      ("Never Aware",      "🔇"),
            "aware_not_tried":  ("Aware, Not Tried",  "👁️"),
            "first_time_buyer": ("First-Time Buyer",  "🛒"),
            "current_user":     ("Current User",      "⭐"),
            "lapsed_user":      ("Lapsed User",       "💤"),
        }
        _total_pop_snap = sum(_cs.values()) or 1
        _pop_snap_cols = st.columns(len(_cohort_display_map))
        for _i_s, (_cid_s, (_clabel_s, _cicon_s)) in enumerate(_cohort_display_map.items()):
            _cnt_s = _cs.get(_cid_s, 0)
            with _pop_snap_cols[_i_s]:
                st.metric(f"{_cicon_s} {_clabel_s}", _cnt_s, f"{round(_cnt_s / _total_pop_snap * 100)}%")

    if st.button(
        f"▶  Run All {len(interventions)} Simulations",
        type="primary",
        use_container_width=True,
        key="run_all_simulations_btn",
    ):
        from src.decision.scenarios import get_scenario as _gs
        from src.simulation.counterfactual import run_counterfactual as _run_cf

        _population = st.session_state.get("population")
        _base_scenario = _gs(scenario_id)

        _all_results = []
        _prog = st.progress(0.0, text="Running simulations…")
        for _si, _iv in enumerate(interventions):
            _prog.progress(_si / len(interventions), text=f"Simulating: {_iv.name}…")
            try:
                _r = _run_cf(
                    population=_population,
                    baseline_scenario=_base_scenario,
                    modifications=_iv.parameter_modifications,
                    counterfactual_name=_iv.name,
                )
                _all_results.append({"intervention": _iv, "result": _r})
            except Exception:  # noqa: BLE001
                pass
        _prog.progress(1.0, text="All simulations complete.")
        _prog.empty()

        st.session_state["intervention_run"] = {
            "all_results": _all_results,
            "scenario_id": scenario_id,
            "baseline_cohorts": st.session_state.get("baseline_cohorts"),
        }
        st.switch_page("pages/6_intervention_results.py")
else:
    st.info("No interventions available to simulate.")
```

---

### Task 2: Rewrite `6_intervention_results.py` as Full Comparison Dashboard

File: `app/pages/6_intervention_results.py`

**Replace the entire file** with the following (keep the page config and sidebar calls, replace all content below them):

```python
# ── Phase gate ────────────────────────────────────────────────────────────────
if "intervention_run" not in st.session_state:
    st.warning("No simulation results yet. Go to Phase 4 — Interventions and click Run All Simulations.", icon="🔒")
    if st.button("← Back to Interventions"):
        st.switch_page("pages/5_intervention.py")
    st.stop()

_run = st.session_state["intervention_run"]
all_results: list[dict] = _run.get("all_results", [])
scenario_id: str = _run.get("scenario_id", "")
baseline_cohorts = _run.get("baseline_cohorts")

if not all_results:
    st.warning("No simulation results found. Please re-run the simulations.")
    if st.button("← Back to Interventions"):
        st.switch_page("pages/5_intervention.py")
    st.stop()

# Baseline adoption rate (same for all — from first result)
_baseline_rate = all_results[0]["result"].baseline_adoption_rate if all_results else 0.0

# System Voice
from app.components.system_voice import render_system_voice
render_system_voice(
    f"I simulated all <strong>{len(all_results)} interventions</strong> against your baseline population. "
    f"Baseline adoption: <strong>{_baseline_rate:.1%}</strong>. "
    f"The table below ranks every intervention by adoption lift — and flags the best trade-off between impact and execution effort."
)
```

**Complexity and Time-to-Market inference** (derive from intervention fields, not user input):

```python
def _infer_complexity(iv) -> str:
    if iv.scope == "cohort_specific" and iv.temporality == "temporal":
        return "High"
    if iv.temporality == "temporal":
        return "Medium"
    return "Low"

def _infer_ttm(iv) -> str:
    if iv.scope == "cohort_specific" and iv.temporality == "temporal":
        return "3–4 months"
    if iv.temporality == "temporal":
        return "4–6 weeks"
    return "1–2 weeks"

def _infer_cost(iv) -> str:
    if iv.scope == "cohort_specific" and iv.temporality == "temporal":
        return "High"
    if iv.temporality == "temporal":
        return "Medium"
    return "Low"

_COMPLEXITY_COLOR = {"Low": "#2ECC71", "Medium": "#F39C12", "High": "#E74C3C"}
```

**Comparison table** (sort by absolute_lift descending):

```python
sorted_results = sorted(all_results, key=lambda x: x["result"].absolute_lift, reverse=True)

_HEADER_BG = "#1A5276"
_HEADER_FG = "#FFFFFF"
_TOP_BG = "#EBF5FB"
_DEFAULT_BG = "#FFFFFF"

_rows_html = ""
for _ri, _row in enumerate(sorted_results):
    _iv = _row["intervention"]
    _r = _row["result"]
    _lift = _r.absolute_lift
    _rel = _r.relative_lift_percent
    _sign = "+" if _lift >= 0 else ""
    _lift_color = "#27AE60" if _lift > 0.01 else ("#E74C3C" if _lift < 0 else "#7F8C8D")
    _row_bg = _TOP_BG if _ri == 0 else _DEFAULT_BG
    _top_badge = (
        ' <span style="background:#1A5276;color:#fff;border-radius:4px;padding:1px 5px;font-size:0.72rem;margin-left:6px;">★ Top</span>'
        if _ri == 0 else ""
    )
    _cx = _infer_complexity(_iv)
    _cx_color = _COMPLEXITY_COLOR.get(_cx, "#555")
    _scope_label = "General" if _iv.scope == "general" else "Cohort"
    _temp_label = "One-time" if _iv.temporality == "non_temporal" else "Sustained"

    _rows_html += (
        f'<tr style="background:{_row_bg}; border-bottom:1px solid #E8E8E8;">'
        f'<td style="padding:9px 12px; font-weight:600; min-width:180px;">{_iv.name}{_top_badge}</td>'
        f'<td style="padding:9px 12px; text-align:center;">{_scope_label} · {_temp_label}</td>'
        f'<td style="padding:9px 12px; text-align:right;">{_r.counterfactual_adoption_rate:.1%}</td>'
        f'<td style="padding:9px 12px; text-align:right; font-weight:700; color:{_lift_color};">{_sign}{_lift:.1%}</td>'
        f'<td style="padding:9px 12px; text-align:right; color:{_lift_color};">{_sign}{_rel:.1f}%</td>'
        f'<td style="padding:9px 12px; text-align:center; color:{_cx_color}; font-weight:600;">{_cx}</td>'
        f'<td style="padding:9px 12px; text-align:center; color:#555;">{_infer_ttm(_iv)}</td>'
        f'<td style="padding:9px 12px; text-align:center; color:#555;">{_infer_cost(_iv)}</td>'
        f'</tr>'
    )

_table_html = (
    '<div style="overflow-x:auto; margin:12px 0;">'
    '<table style="border-collapse:collapse; width:100%; font-family:sans-serif; font-size:0.88rem;">'
    f'<thead><tr style="background:{_HEADER_BG}; color:{_HEADER_FG};">'
    '<th style="padding:10px 12px; text-align:left;">Intervention</th>'
    '<th style="padding:10px 12px; text-align:center;">Type</th>'
    '<th style="padding:10px 12px; text-align:right;">Adoption Rate</th>'
    '<th style="padding:10px 12px; text-align:right;">Lift (pp)</th>'
    '<th style="padding:10px 12px; text-align:right;">Relative Lift</th>'
    '<th style="padding:10px 12px; text-align:center;">Complexity</th>'
    '<th style="padding:10px 12px; text-align:center;">Time to Market</th>'
    '<th style="padding:10px 12px; text-align:center;">Est. Cost</th>'
    '</tr></thead>'
    f'<tbody>{_rows_html}</tbody>'
    '</table></div>'
)

st.subheader("Intervention Comparison")
st.caption(f"Baseline adoption: **{_baseline_rate:.1%}** · All interventions ranked by adoption lift.")
st.markdown(_table_html, unsafe_allow_html=True)
```

**System recommendation callout** (after the table):

```python
if sorted_results:
    _top = sorted_results[0]
    _top_iv = _top["intervention"]
    _top_r = _top["result"]
    _top_cx = _infer_complexity(_top_iv)
    _top_ttm = _infer_ttm(_top_iv)

    # Find best low-complexity option
    _low_cx = next(
        (x for x in sorted_results if _infer_complexity(x["intervention"]) == "Low"),
        sorted_results[-1],
    )

    render_system_voice(
        f"The highest-lift option is <strong>{_top_iv.name}</strong> (+{_top_r.absolute_lift:.1%} adoption), "
        f"but it carries <strong>{_top_cx}</strong> complexity and a <strong>{_top_ttm}</strong> time to market. "
        + (
            f"For a faster path to impact, start with <strong>{_low_cx['intervention'].name}</strong> "
            f"(+{_low_cx['result'].absolute_lift:.1%} lift, Low complexity) to validate assumptions "
            f"before committing to the larger programme."
            if _low_cx["intervention"].id != _top_iv.id else
            f"This is also your fastest-to-market option — an ideal starting point."
        )
    )
```

**Navigation:**

```python
st.divider()
_nav = st.columns([1, 1])
with _nav[0]:
    if st.button("← Re-run Simulations", use_container_width=True):
        st.switch_page("pages/5_intervention.py")
with _nav[1]:
    if st.button("→ Interview Deep-Dive", use_container_width=True):
        st.switch_page("pages/7_interviews.py")
```

---

### Acceptance Criteria

- [ ] "Run All Simulations" button on page 5 runs `run_counterfactual()` for every intervention in the list
- [ ] Progress bar shows per-intervention status during the run
- [ ] `session_state["intervention_run"]` contains `all_results` (list of dicts with `intervention` and `result` keys)
- [ ] Comparison table on page 6 shows all interventions sorted by adoption lift (highest first)
- [ ] `★ Top` badge on the highest-lift row
- [ ] Complexity and Time to Market columns derived from intervention scope + temporality (no hardcoded values)
- [ ] System recommendation identifies both the highest-lift AND the lowest-complexity option
- [ ] Page 6 phase gate gracefully redirects when no results exist
- [ ] Navigation buttons work correctly

---

### Files to Modify

| File | Change |
|------|--------|
| `app/pages/5_intervention.py` | Replace single-intervention launcher with "Run All" block |
| `app/pages/6_intervention_results.py` | Rewrite as full comparison dashboard |

### Files NOT to Modify

`src/simulation/counterfactual.py`, `src/analysis/intervention_engine.py` — do not change backend.

---

### Escalation Rule

If `run_counterfactual()` raises KeyError on certain interventions (because `parameter_modifications` contains paths not in the scenario config), wrap each call in try/except and skip the failing intervention. Log the error to `st.warning()` after the loop — do not crash the page.
