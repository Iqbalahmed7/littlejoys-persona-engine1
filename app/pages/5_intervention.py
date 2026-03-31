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

# ── Configure & Launch Simulation ─────────────────────────────────────────────
st.divider()
st.subheader("Configure & Launch Simulation")
st.caption(
    "Select an intervention, review your pre-simulation population mix, then run a full "
    "counterfactual analysis. The system measures adoption lift vs. your baseline — and "
    "automatically explores micro-perturbations (price, messaging, distribution tweaks) "
    "on top of the selected intervention to surface compounding opportunities."
)

if interventions:
    # ── Intervention selector ──────────────────────────────────────────────────
    _scope_icon = {"general": "🟢", "cohort_specific": "🔵"}
    _temp_icon = {"non_temporal": "⚡", "temporal": "⏱"}
    _iv_label_map = {
        iv.id: (
            f"{_scope_icon.get(iv.scope, '⚪')} {_temp_icon.get(iv.temporality, '')}  "
            f"{iv.name}  "
            f"({'General' if iv.scope == 'general' else 'Cohort'} · "
            f"{'One-time' if iv.temporality == 'non_temporal' else 'Sustained'})"
        )
        for iv in interventions
    }

    _default_iv_idx = 0
    if recommended:
        _iv_ids = [iv.id for iv in interventions]
        if recommended.id in _iv_ids:
            _default_iv_idx = _iv_ids.index(recommended.id)

    _selected_iv_id = st.selectbox(
        "Choose an intervention to simulate",
        options=[iv.id for iv in interventions],
        format_func=lambda x: _iv_label_map[x],
        index=_default_iv_idx,
        key="configure_intervention_id",
    )
    _selected_iv = next(iv for iv in interventions if iv.id == _selected_iv_id)

    # ── Pre-simulation population snapshot ────────────────────────────────────
    st.markdown("**Pre-simulation population mix** *(from Phase 1 baseline)*")
    _cohorts_snap = st.session_state.get("baseline_cohorts")
    if _cohorts_snap is not None:
        _cohort_summary_snap: dict = (
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
        _total_pop_snap = sum(_cohort_summary_snap.values()) or 1
        _pop_snap_cols = st.columns(len(_cohort_display_map))
        for _i_snap, (_cid_snap, (_clabel_snap, _cicon_snap)) in enumerate(_cohort_display_map.items()):
            _count_snap = _cohort_summary_snap.get(_cid_snap, 0)
            _pct_snap = round(_count_snap / _total_pop_snap * 100)
            with _pop_snap_cols[_i_snap]:
                st.metric(f"{_cicon_snap} {_clabel_snap}", _count_snap, f"{_pct_snap}%")
    else:
        st.info("Population mix unavailable — return to Phase 1 to run the baseline simulation.")

    # ── Temporal duration slider ───────────────────────────────────────────────
    _sim_months = 12
    if _selected_iv.temporality == "temporal":
        _sim_months = st.slider(
            "Simulation duration (months)",
            min_value=3,
            max_value=24,
            value=12,
            step=3,
            key="sim_months_slider",
            help="How many months to model this sustained intervention across the population.",
        )
        st.caption(
            f"A {_sim_months}-month sustained programme — parameters are applied continuously "
            f"over {_sim_months * 30} simulated days."
        )
    else:
        st.caption(
            "One-time intervention — applied as a single modification to the population's "
            "decision environment. Equivalent to a permanent policy change."
        )

    # ── Run CTA ───────────────────────────────────────────────────────────────
    _cta_label = (
        f"▶  Run {_sim_months}-Month Simulation & Counterfactual Analysis"
        if _selected_iv.temporality == "temporal"
        else "▶  Run One-Time Simulation & Counterfactual Analysis"
    )

    if st.button(_cta_label, type="primary", use_container_width=True, key="launch_simulation_btn"):
        from src.decision.scenarios import get_scenario as _gs
        from src.simulation.counterfactual import (
            apply_scenario_modifications as _apply_mods,
            generate_default_counterfactuals as _gen_defaults,
            run_counterfactual as _run_cf,
        )

        _population = st.session_state.get("population")
        _base_scenario = _gs(scenario_id)

        with st.spinner("Running primary intervention simulation…"):
            _primary_result = _run_cf(
                population=_population,
                baseline_scenario=_base_scenario,
                modifications=_selected_iv.parameter_modifications,
                counterfactual_name=_selected_iv.name,
            )

        # Build intervention scenario (baseline + iv mods applied)
        _iv_scenario = _apply_mods(_base_scenario, _selected_iv.parameter_modifications)

        # Micro-perturbation analysis ON TOP of the intervention scenario
        _micro_tweaks = _gen_defaults(_iv_scenario)
        _micro_results: list[dict] = []

        _prog = st.progress(0.0, text="Analysing micro-perturbations…")
        for _mi, _tweak in enumerate(_micro_tweaks):
            try:
                _tweak_result = _run_cf(
                    population=_population,
                    baseline_scenario=_iv_scenario,
                    modifications=dict(_tweak.parameter_changes),
                    counterfactual_name=_tweak.label,
                )
                _micro_results.append({
                    "id": _tweak.id,
                    "label": _tweak.label,
                    "result": _tweak_result,
                })
            except Exception:  # noqa: BLE001
                pass
            _prog.progress((_mi + 1) / len(_micro_tweaks))

        _prog.empty()

        st.session_state["intervention_run"] = {
            "intervention": _selected_iv,
            "scenario_id": scenario_id,
            "sim_months": _sim_months,
            "primary_result": _primary_result,
            "micro_results": _micro_results,
            "baseline_cohorts": st.session_state.get("baseline_cohorts"),
        }

        st.switch_page("pages/6_intervention_results.py")
else:
    st.info("No interventions are available to simulate.")

# ── Export ────────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Export")

export_interventions = [
    {
        "id": iv.id,
        "name": iv.name,
        "description": iv.description,
        "scope": iv.scope,
        "temporality": iv.temporality,
        "target_cohort_id": iv.target_cohort_id,
        "parameter_modifications": iv.parameter_modifications,
        "expected_mechanism": iv.expected_mechanism,
    }
    for iv in interventions
]

export_data = {
    "scenario_id": scenario_id,
    "problem_id": problem_id,
    "dominant_hypothesis": dominant_hypothesis,
    "total_interventions": len(interventions),
    "recommended_intervention_id": recommended.id if recommended else None,
    "quadrant_counts": {
        key: len(bucket) for key, bucket in quadrant.quadrants.items()
    },
    "interventions": export_interventions,
}

st.download_button(
    label="Export Interventions (JSON)",
    data=json.dumps(export_data, indent=2, default=str),
    file_name=f"{scenario_id}_interventions.json",
    mime="application/json",
)
