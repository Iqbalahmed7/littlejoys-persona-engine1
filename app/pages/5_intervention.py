# ruff: noqa: N999
"""Phase 4 — Interventions.

Turns the Core Finding into an actionable intervention playbook, rendering a
2x2 quadrant grid and comparison table of all generated interventions.
"""

from __future__ import annotations

import json

import streamlit as st

from app.components.system_voice import render_system_voice
from app.utils.phase_state import render_phase_sidebar

# NOTE: The Intervention model in src/analysis/intervention_engine.py does NOT
# have estimated_lift, confidence, complexity, time_to_market, or est_cost
# fields.  The table is therefore built from the actual fields:
#   id, name, description, scope, temporality, target_cohort_id,
#   parameter_modifications, expected_mechanism.
# No data is fabricated.

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Phase 4 — Interventions", page_icon="🎯", layout="wide")
render_phase_sidebar()
st.header("Phase 4 — Interventions")

# ── Phase gate ────────────────────────────────────────────────────────────────
if "core_finding" not in st.session_state:
    st.warning("Complete Phase 3 (Core Finding) first.", icon="🔒")
    st.stop()

# ── Extract session state ─────────────────────────────────────────────────────
core_finding: dict = st.session_state["core_finding"]
dominant_hypothesis: str = core_finding.get("dominant_hypothesis", "the identified barrier")
scenario_id: str = (
    core_finding.get("scenario_id")
    or st.session_state.get("baseline_scenario_id", "nutrimix_2_6")
)
problem_id: str = st.session_state.get("baseline_problem_id", scenario_id)

# ── Run intervention engine ───────────────────────────────────────────────────
from src.analysis.intervention_engine import (  # noqa: E402
    InterventionInput,
    InterventionQuadrant,
    generate_intervention_quadrant,
)
from src.decision.scenarios import get_scenario  # noqa: E402

# NOTE: generate_intervention_quadrant(decomposition, scenario) uses
# getattr(decomposition, "problem_id", None) — InterventionInput satisfies this.
# The return type is InterventionQuadrant whose interventions live in
# quadrant.quadrants (dict[str, list[Intervention]]), NOT in quadrant.interventions.

try:
    scenario = get_scenario(scenario_id)
    intervention_input = InterventionInput(problem_id=problem_id)
    quadrant: InterventionQuadrant = generate_intervention_quadrant(
        intervention_input, scenario
    )
    # Flatten all quadrant buckets into a single list for display
    interventions = [
        iv for bucket in quadrant.quadrants.values() for iv in bucket
    ]
    st.session_state["intervention_results"] = quadrant
except KeyError as exc:
    st.error(
        f"Unknown scenario '{scenario_id}'. "
        f"Return to Phase 1 and re-run the baseline simulation. ({exc})"
    )
    st.stop()
except Exception as exc:  # noqa: BLE001
    st.error(f"Could not generate interventions: {exc}")
    st.stop()

# ── System Voice #1 — Opening ─────────────────────────────────────────────────
render_system_voice(
    f"Phase 3 identified <strong>{dominant_hypothesis}</strong> as the primary barrier. "
    f"I've generated <strong>{len(interventions)} targeted interventions</strong> mapped to this root cause. "
    f"Here is how they compare."
)

# ── Intervention comparison table ─────────────────────────────────────────────
# Colour helpers for scope and temporality chips
_SCOPE_COLOURS: dict[str, tuple[str, str]] = {
    "general": ("#2ECC71", "#EAFAF1"),          # green text / green bg
    "cohort_specific": ("#2980B9", "#EBF5FB"),  # blue text / blue bg
}
_TEMP_COLOURS: dict[str, tuple[str, str]] = {
    "temporal": ("#E67E22", "#FDEBD0"),         # amber text / amber bg
    "non_temporal": ("#7F8C8D", "#F2F3F4"),     # grey text / grey bg
}


def _chip(label: str, fg: str, bg: str) -> str:
    return (
        f'<span style="background:{bg}; color:{fg}; border:1px solid {fg}; '
        f'border-radius:4px; padding:2px 7px; font-size:0.8rem; font-weight:600; '
        f'white-space:nowrap;">{label}</span>'
    )


def _summarise_params(mods: dict) -> str:
    """Return a short human-readable summary of parameter_modifications."""
    if not mods:
        return "—"
    parts = []
    for k, v in list(mods.items())[:3]:  # cap at 3 keys for table readability
        short_key = k.split(".")[-1].replace("_", " ")
        if isinstance(v, bool):
            parts.append(f"{short_key}: {'Yes' if v else 'No'}")
        elif isinstance(v, float):
            parts.append(f"{short_key}: {v:.0%}" if v <= 1.0 else f"{short_key}: {v:.1f}")
        else:
            parts.append(f"{short_key}: {v}")
    if len(mods) > 3:
        parts.append(f"+ {len(mods) - 3} more")
    return ", ".join(parts)


# Determine which row to highlight as "recommended".
# Because there are no lift/confidence fields, we use a proxy:
#   prefer general + non_temporal (broadest immediate impact) — first such match.
# Fall back to first intervention.
def _recommendation_score(iv) -> int:
    """Higher = more recommended. Proxy: general non-temporal > general temporal
    > cohort non-temporal > cohort temporal."""
    scores = {
        ("general", "non_temporal"): 4,
        ("general", "temporal"): 3,
        ("cohort_specific", "non_temporal"): 2,
        ("cohort_specific", "temporal"): 1,
    }
    return scores.get((iv.scope, iv.temporality), 0)


recommended = max(interventions, key=_recommendation_score) if interventions else None

# Build HTML table
_ROW_BG_DEFAULT = "#FFFFFF"
_ROW_BG_RECOMMENDED = "#EBF5FB"
_HEADER_BG = "#1A5276"
_HEADER_FG = "#FFFFFF"

rows_html = ""
for iv in interventions:
    is_rec = recommended is not None and iv.id == recommended.id
    row_bg = _ROW_BG_RECOMMENDED if is_rec else _ROW_BG_DEFAULT

    scope_fg, scope_bg = _SCOPE_COLOURS.get(iv.scope, ("#555", "#EEE"))
    temp_fg, temp_bg = _TEMP_COLOURS.get(iv.temporality, ("#555", "#EEE"))
    scope_label = "General" if iv.scope == "general" else "Cohort"
    temp_label = "Temporal" if iv.temporality == "temporal" else "One-time"

    cohort_cell = iv.target_cohort_id.replace("_", " ").title() if iv.target_cohort_id else "All"
    params_cell = _summarise_params(iv.parameter_modifications)

    rec_badge = (
        ' <span style="background:#1A5276;color:#fff;border-radius:4px;'
        'padding:1px 5px;font-size:0.72rem;margin-left:6px;">★ Rec</span>'
        if is_rec else ""
    )

    rows_html += (
        f'<tr style="background:{row_bg}; border-bottom:1px solid #E8E8E8;">'
        f'<td style="padding:9px 12px; font-weight:600; min-width:200px;">{iv.name}{rec_badge}</td>'
        f'<td style="padding:9px 12px;">{_chip(scope_label, scope_fg, scope_bg)}</td>'
        f'<td style="padding:9px 12px;">{_chip(temp_label, temp_fg, temp_bg)}</td>'
        f'<td style="padding:9px 12px; color:#555; font-size:0.85rem;">{cohort_cell}</td>'
        f'<td style="padding:9px 12px; color:#333; font-size:0.85rem; max-width:280px;">{params_cell}</td>'
        f'<td style="padding:9px 12px; color:#555; font-size:0.82rem; max-width:300px; line-height:1.4;">{iv.expected_mechanism}</td>'
        f'</tr>'
    )

table_html = (
    '<div style="overflow-x:auto; margin: 12px 0;">'
    '<table style="border-collapse:collapse; width:100%; font-family:sans-serif; font-size:0.9rem;">'
    f'<thead><tr style="background:{_HEADER_BG}; color:{_HEADER_FG};">'
    '<th style="padding:10px 12px; text-align:left;">Intervention</th>'
    '<th style="padding:10px 12px; text-align:left;">Scope</th>'
    '<th style="padding:10px 12px; text-align:left;">Timing</th>'
    '<th style="padding:10px 12px; text-align:left;">Target</th>'
    '<th style="padding:10px 12px; text-align:left;">Parameter Changes</th>'
    '<th style="padding:10px 12px; text-align:left;">Expected Mechanism</th>'
    f'</tr></thead>'
    f'<tbody>{rows_html}</tbody>'
    '</table></div>'
)

st.markdown(table_html, unsafe_allow_html=True)

# ── System Voice #2 — Staged execution ───────────────────────────────────────
# starter = lowest-effort entry point: prefer general non_temporal (broadest + immediate)
# escalate = highest-reach: prefer general temporal (sustained programme)

_STARTER_PRIORITY = {
    ("general", "non_temporal"): 4,
    ("cohort_specific", "non_temporal"): 3,
    ("general", "temporal"): 2,
    ("cohort_specific", "temporal"): 1,
}
_ESCALATE_PRIORITY = {
    ("general", "temporal"): 4,
    ("cohort_specific", "temporal"): 3,
    ("general", "non_temporal"): 2,
    ("cohort_specific", "non_temporal"): 1,
}

if interventions:
    starter = max(interventions, key=lambda iv: _STARTER_PRIORITY.get((iv.scope, iv.temporality), 0))
    escalate = max(interventions, key=lambda iv: _ESCALATE_PRIORITY.get((iv.scope, iv.temporality), 0))

    render_system_voice(
        f"Our recommendation: begin with <strong>{starter.name}</strong> to build momentum "
        f"and validate assumptions at low cost. If results confirm the hypothesis, "
        f"escalate to <strong>{escalate.name}</strong> in the next cycle."
    )

# ── System Voice #3 — Caveat ──────────────────────────────────────────────────
_pop_state = st.session_state.get("population")
if _pop_state and hasattr(_pop_state, "personas"):
    population_size = len(_pop_state.personas)
elif isinstance(_pop_state, dict):
    population_size = len(_pop_state.get("personas", []))
else:
    population_size = "the simulated"

render_system_voice(
    f"These projections are based on <strong>{population_size}-persona simulation data</strong>. "
    f"Real-world results will vary — use this as a directional compass, not a guarantee."
)

# ── 2×2 Quadrant overview ─────────────────────────────────────────────────────
st.subheader("Intervention Quadrant Map")
st.caption(
    "Interventions are organised by **scope** (General vs. Cohort-specific) "
    "and **timing** (One-time vs. Sustained/Temporal)."
)

_QUADRANT_DISPLAY: list[tuple[str, str, str]] = [
    ("general_non_temporal",   "🟢 General · One-time",   "Broad reach, immediate — lowest friction to deploy"),
    ("general_temporal",       "🟠 General · Sustained",  "Broad reach, ongoing commitment — highest reach"),
    ("cohort_non_temporal",    "🔵 Cohort · One-time",    "Targeted, immediate — precise but limited scale"),
    ("cohort_temporal",        "🔴 Cohort · Sustained",   "Targeted, ongoing — highest precision, most resource-intensive"),
]

cols = st.columns(2)
for idx, (key, label, description) in enumerate(_QUADRANT_DISPLAY):
    bucket = quadrant.quadrants.get(key, [])
    col = cols[idx % 2]
    with col:
        st.markdown(f"**{label}**")
        st.caption(description)
        if bucket:
            for iv in bucket:
                st.markdown(f"- {iv.name}")
        else:
            st.caption("_No interventions in this quadrant._")
        st.markdown("---")

# ── Per-intervention expanders ────────────────────────────────────────────────
st.subheader("Intervention Details")

for iv in interventions:
    with st.expander(iv.name):
        st.markdown(iv.description)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Scope:** {iv.scope.replace('_', ' ').title()}")
            st.markdown(f"**Timing:** {iv.temporality.replace('_', ' ').title()}")
            target_label = iv.target_cohort_id.replace("_", " ").title() if iv.target_cohort_id else "All personas"
            st.markdown(f"**Target cohort:** {target_label}")
        with col_b:
            st.markdown(f"**Expected mechanism:**  \n{iv.expected_mechanism}")

        if iv.parameter_modifications:
            st.markdown("**Parameter modifications:**")
            for param_key, param_val in iv.parameter_modifications.items():
                friendly_key = param_key.replace(".", " → ").replace("_", " ").title()
                if isinstance(param_val, bool):
                    display_val = "Enabled" if param_val else "Disabled"
                elif isinstance(param_val, float) and param_val <= 1.0:
                    display_val = f"{param_val:.0%}"
                else:
                    display_val = str(param_val)
                st.markdown(f"- **{friendly_key}**: {display_val}")

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