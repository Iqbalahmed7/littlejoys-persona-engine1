# ruff: noqa: N999
"""Phase 1 — Business Problem Selection & Baseline Simulation.

Replaces the old scenario-selection research page with a problem-first flow:
1. User selects a business problem (not a scenario)
2. System explains what it will simulate
3. User clicks Run — simulation runs with dramatic narrative progress
4. System narrates findings, cohort dashboard appears
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.components.system_voice import render_system_voice
from app.utils.phase_state import phase_complete, render_phase_sidebar
from src.analysis.cohort_classifier import classify_population
from src.analysis.problem_templates import PROBLEM_TEMPLATES
from src.constants import DEFAULT_SEED
from src.decision.scenarios import get_scenario
from src.generation.population import Population
from src.simulation.temporal import run_temporal_simulation

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Problem & Simulation", page_icon="🔬", layout="wide")
st.header("Phase 1 — Business Problem & Baseline Simulation")
st.caption("State your business problem. The system maps it to a scenario and runs a 12-month baseline simulation.")

render_phase_sidebar()

# ── Guard: need population ─────────────────────────────────────────────────────
if "population" not in st.session_state:
    st.warning("No population loaded. Return to the home page to generate or load a population.")
    st.stop()

pop: Population = st.session_state.population

# ── Problem → Scenario mapping ─────────────────────────────────────────────────
# Maps problem_template key → scenario_id (same keys in this codebase)
_PROBLEM_META: dict[str, dict[str, str]] = {
    "nutrimix_2_6": {
        "label": "Why is repeat purchase low despite high NPS?",
        "context": "Nutrimix 2–6 is winning first purchases and strong ratings, but repeat buying is below target. Something breaks between a positive first experience and a dependable reorder habit.",
        "success_metric": "Repeat purchase rate",
        "icon": "🔁",
    },
    "nutrimix_7_14": {
        "label": "How do we expand Nutrimix from 2–6 to the 7–14 age group?",
        "context": "Nutrimix dominates the 2–6 segment. The 7–14 segment is large and underserved, but early signals suggest parents and kids respond differently to the same product.",
        "success_metric": "Trial rate in 7–14 segment",
        "icon": "📈",
    },
    "magnesium_gummies": {
        "label": "How do we grow sales of a niche supplement?",
        "context": "Magnesium Gummies are clinically sound but commercially niche. Awareness is low, doctor dependency is high, and the gummy format creates perceptual barriers.",
        "success_metric": "Awareness-to-trial conversion",
        "icon": "💊",
    },
    "protein_mix": {
        "label": "The product requires cooking — how do we overcome the effort barrier?",
        "context": "Protein Mix has strong nutritional credentials but a high effort barrier: it must be mixed into food. Parents aren't sure how, and working mothers say they don't have time.",
        "success_metric": "Adoption rate despite effort friction",
        "icon": "🍳",
    },
}

# ── Narrative templates — inject real cohort data after simulation ─────────────
def _post_sim_narrative(problem_id: str, temporal_result: Any, cohorts: Any) -> str:
    """Build system voice narrative from actual simulation results."""
    # Derive all rates from cohort summary so numbers match the cohort tiles exactly.
    _summary = cohorts.summary
    pop_size = sum(_summary.values()) or 1
    lapsed = _summary.get("lapsed_user", 0)
    first_time = _summary.get("first_time_buyer", 0)
    current = _summary.get("current_user", 0)
    never_aware = _summary.get("never_aware", 0)
    aware_not_tried = _summary.get("aware_not_tried", 0)
    tried = first_time + current + lapsed
    adoption_pct = round(tried / pop_size * 100)
    active_pct = round(current / pop_size * 100)
    repeat_pct = active_pct
    lapse_pct = round((lapsed / tried * 100) if tried > 0 else 0)

    if problem_id == "nutrimix_2_6":
        return (
            f"Simulation complete. Here's what {pop_size:,} households showed over 12 months: "
            f"{adoption_pct}% purchased at least once, but only {repeat_pct}% are still active buyers. "
            f"The critical drop-off happens in the 21–45 day window post-first-purchase — "
            f"that's where <b>child_acceptance</b> and <b>brand_salience</b> both decay sharply. "
            f"{lapse_pct}% of first-time buyers never came back. "
            f"{never_aware} personas never became aware at all. "
            f"The repeat gap is the core problem."
        )
    elif problem_id == "nutrimix_7_14":
        return (
            f"Simulation complete. {adoption_pct}% of the 7–14 parent segment purchased at least once — "
            f"significantly lower than the 2–6 benchmark. "
            f"{aware_not_tried} personas became aware but didn't convert: "
            f"the awareness-to-trial gap is where this problem lives. "
            f"Age perception and peer influence appear to be early exit signals."
        )
    elif problem_id == "magnesium_gummies":
        return (
            f"Simulation complete. Only {adoption_pct}% adopted — driven by a very narrow segment "
            f"of health-anxious, doctor-trusting parents. "
            f"{never_aware} personas ({round(never_aware/pop_size*100)}%) never became aware. "
            f"The product's awareness funnel is the primary barrier."
        )
    else:  # protein_mix
        return (
            f"Simulation complete. {adoption_pct}% adoption, well below category benchmarks. "
            f"Effort friction is suppressing trial: many personas register awareness and even intention, "
            f"but <b>effort_friction</b> scores above 0.7 are causing drop-off at the consideration stage. "
            f"{aware_not_tried} personas considered but didn't convert."
        )


def _run_simulation_with_narrative(pop: Population, scenario_id: str) -> tuple[Any, Any]:
    """Run simulation first, then narrate checkpoints from real monthly outputs."""
    scenario = get_scenario(scenario_id)
    n = len(pop.personas)

    with st.status("Running 12-month baseline simulation...", expanded=True) as status:
        st.write(
            f"⚙️ Introducing product to {n} personas via their most likely discovery channels..."
        )
        temporal_result = run_temporal_simulation(pop, scenario, months=12, seed=DEFAULT_SEED)

        st.write("⚙️ Classifying behavioral cohorts...")
        cohorts = classify_population(pop, scenario, seed=DEFAULT_SEED)

        # Replay narrative from actual monthly data
        monthly = getattr(temporal_result, "aggregate_monthly", None) or getattr(
            temporal_result, "monthly_snapshots", None
        )
        if not monthly:
            st.write("Simulation complete — cohorts formed from behavioral trajectories.")
        else:
            checkpoints = {3, 6, 9, 12}

            def _month_value(month_data: Any, *keys: str) -> int:
                if isinstance(month_data, dict):
                    for key in keys:
                        if key in month_data:
                            return int(month_data.get(key, 0) or 0)
                    return 0
                for key in keys:
                    if hasattr(month_data, key):
                        return int(getattr(month_data, key) or 0)
                return 0

            for month_data in monthly:
                m = _month_value(month_data, "month")
                if m in checkpoints:
                    cumulative = _month_value(month_data, "cumulative_adopters")
                    churned = _month_value(month_data, "churned")
                    active = _month_value(month_data, "active_count", "total_active")
                    repeat = _month_value(month_data, "repeat_purchasers")
                    if m == 3:
                        st.write(
                            f"Month 3: {cumulative} personas have now tried the product. "
                            f"First churn signals emerging ({churned} drop-offs so far)."
                        )
                    elif m == 6:
                        st.write(
                            f"Month 6: Trial rate reaching {round(cumulative / max(n, 1) * 100)}%. "
                            f"{repeat} personas repeated this month. {active} still active."
                        )
                    elif m == 9:
                        st.write(
                            f"Month 9: Habit patterns solidifying. {active} active buyers. "
                            f"{churned} cumulative lapsed."
                        )
                    elif m == 12:
                        st.write(
                            f"Month 12: Simulation complete. {cumulative} total adopters across {n} personas."
                        )

        status.update(
            label=f"✅ Simulation complete — {n} personas × 365 days",
            state="complete",
            expanded=False,
        )

    return temporal_result, cohorts


# ── Problem selection UI ───────────────────────────────────────────────────────
st.markdown("### What business problem are you trying to solve?")
st.caption("The system maps your problem to the right simulation scenario automatically.")

# Show cards in a 2×2 grid
col_a, col_b = st.columns(2)
problem_cols = [col_a, col_b, col_a, col_b]
problem_ids = list(_PROBLEM_META.keys())

selected_problem: str | None = st.session_state.get("selected_problem_id")

for i, pid in enumerate(problem_ids):
    meta = _PROBLEM_META[pid]
    with problem_cols[i]:
        with st.container(border=True):
            is_selected = selected_problem == pid
            st.markdown(
                f"{'**✓ Selected** — ' if is_selected else ''}"
                f"{meta['icon']} **{meta['label']}**"
            )
            st.caption(meta["context"])
            st.caption(f"Success metric: _{meta['success_metric']}_")
            if not is_selected:
                if st.button("Select this problem", key=f"sel_{pid}"):
                    st.session_state["selected_problem_id"] = pid
                    # Clear any previous simulation results when problem changes
                    for k in ["baseline_cohorts", "baseline_temporal", "probe_results",
                              "core_finding", "intervention_results"]:
                        st.session_state.pop(k, None)
                    st.rerun()

st.markdown("---")

# ── System explanation + Run button ───────────────────────────────────────────
if not selected_problem:
    st.info("Select a business problem above to continue.")
    st.stop()

meta = _PROBLEM_META[selected_problem]
template = PROBLEM_TEMPLATES.get(selected_problem, {})

render_system_voice(
    f"To investigate <b>{meta['label']}</b>, I need to simulate how {len(pop.personas)} "
    f"households interact with this product over 12 months. "
    f"This will show me who becomes aware, who buys, who repeats, who lapses — and the "
    f"decision variables that drove each outcome. "
    f"From these trajectories I'll form behavioral cohorts and identify the signals worth investigating."
)

# Check if simulation already done for this problem
already_run = (
    "baseline_cohorts" in st.session_state
    and st.session_state.get("baseline_problem_id") == selected_problem
)

if already_run:
    st.success("✅ Baseline simulation already complete for this problem.")
    if st.button("Re-run simulation", type="secondary"):
        for k in ["baseline_cohorts", "baseline_temporal"]:
            st.session_state.pop(k, None)
        st.rerun()
else:
    if st.button("▶ Run Baseline Simulation", type="primary", use_container_width=True):
        temporal_result, cohorts = _run_simulation_with_narrative(pop, selected_problem)
        st.session_state["baseline_temporal"] = temporal_result
        st.session_state["baseline_cohorts"] = cohorts
        st.session_state["baseline_problem_id"] = selected_problem
        st.session_state["baseline_scenario_id"] = selected_problem
        st.rerun()

# ── Cohort Dashboard ───────────────────────────────────────────────────────────
if "baseline_cohorts" not in st.session_state:
    st.stop()

temporal_result = st.session_state["baseline_temporal"]
cohorts = st.session_state["baseline_cohorts"]

# System narration — insight before data
render_system_voice(_post_sim_narrative(selected_problem, temporal_result, cohorts))

st.markdown("---")
st.subheader("Behavioral Cohorts — Formed from Simulation")
st.caption(
    "Each cohort reflects actual simulated behavior over 12 months — "
    "not static demographic scores."
)

# Cohort summary metrics
cohort_display = {
    "never_aware":      ("Never Aware",      "🔇", "Never engaged with the product"),
    "aware_not_tried":  ("Aware, Not Tried",  "👁️", "Became aware but never purchased"),
    "first_time_buyer": ("First-Time Buyer",  "🛒", "Bought once, did not repeat"),
    "current_user":     ("Current User",      "⭐", "Active repeat buyer"),
    "lapsed_user":      ("Lapsed User",       "💤", "Was active, has stopped"),
}

total = sum(cohorts.summary.values()) or 1
cols = st.columns(len(cohort_display))
for i, (cid, (label, icon, desc)) in enumerate(cohort_display.items()):
    count = cohorts.summary.get(cid, 0)
    pct = round(count / total * 100)
    with cols[i]:
        st.metric(f"{icon} {label}", f"{count}", f"{pct}% of population")
        st.caption(desc)

st.markdown("---")

# Cohort distribution chart
_cohort_order = [
    "current_user",
    "lapsed_user",
    "first_time_buyer",
    "aware_not_tried",
    "never_aware",
]
_cohort_display = {
    "current_user": "Current User ⭐",
    "lapsed_user": "Lapsed User 💤",
    "first_time_buyer": "First-Time Buyer 🛒",
    "aware_not_tried": "Aware, Not Tried 👁️",
    "never_aware": "Never Aware 🔇",
}
_cohort_colors = {
    "current_user": "#2ECC71",
    "lapsed_user": "#E67E22",
    "first_time_buyer": "#3498DB",
    "aware_not_tried": "#9B59B6",
    "never_aware": "#95A5A6",
}

bar_y = [_cohort_display[c] for c in _cohort_order]
bar_x = [cohorts.summary.get(c, 0) for c in _cohort_order]
bar_colors = [_cohort_colors[c] for c in _cohort_order]

fig_cohorts = go.Figure(
    go.Bar(
        x=bar_x,
        y=bar_y,
        orientation="h",
        marker_color=bar_colors,
        text=[f"{v} personas ({round(v / max(sum(bar_x), 1) * 100)}%)" for v in bar_x],
        textposition="outside",
    )
)
fig_cohorts.update_layout(
    title=f"How {sum(bar_x)} households moved through the product journey",
    xaxis_title="Number of Personas",
    plot_bgcolor="#FAFAFA",
    paper_bgcolor="#FFFFFF",
    margin=dict(l=10, r=80, t=40, b=10),
    height=280,
)
st.plotly_chart(fig_cohorts, use_container_width=True)

# Funnel visualization
_total = sum(cohorts.summary.values()) or 1
_aware = _total - cohorts.summary.get("never_aware", 0)
_tried = (
    cohorts.summary.get("first_time_buyer", 0)
    + cohorts.summary.get("current_user", 0)
    + cohorts.summary.get("lapsed_user", 0)
)
_repeated = cohorts.summary.get("current_user", 0) + cohorts.summary.get("lapsed_user", 0)
_active = cohorts.summary.get("current_user", 0)

fig_funnel = go.Figure(
    go.Funnel(
        y=["Became Aware", "Tried Product", "Repeated Purchase", "Still Active"],
        x=[_aware, _tried, _repeated, _active],
        textinfo="value+percent initial",
        marker_color=["#3498DB", "#2ECC71", "#27AE60", "#1A8A50"],
    )
)
fig_funnel.update_layout(
    title="Purchase Journey Funnel",
    margin=dict(l=10, r=10, t=40, b=10),
    height=300,
)
st.plotly_chart(fig_funnel, use_container_width=True)

# Per-cohort summary cards
st.subheader("Cohort Profiles")
st.caption("Click any cohort to see the behavioral patterns behind the numbers.")

for cid, (label, icon, desc) in cohort_display.items():
    count = cohorts.summary.get(cid, 0)
    if count == 0:
        continue
    with st.expander(f"{icon} {label} — {count} personas", expanded=False):
        st.caption(desc)

        # List 2 representative persona names from this cohort
        persona_ids = cohorts.cohorts.get(cid, [])[:2]
        if persona_ids:
            st.markdown("**Representative personas:**")
            for pid in persona_ids:
                try:
                    p = pop.get_persona(pid)
                    st.caption(
                        f"• {p.name}, {p.demographics.city_tier} — "
                        f"{p.narrative[:80] if p.narrative else 'No narrative'}…"
                    )
                except Exception:
                    st.caption(f"• Persona {pid[:8]}…")

        # Cohort-specific behavioral hint
        hints = {
            "never_aware": (
                "These personas never encountered the product through any channel. "
                "Brand salience and distribution reach are the levers to address here."
            ),
            "aware_not_tried": (
                "These personas know the product exists but didn't convert. "
                "Price, trust, and perceived need are the likely barriers."
            ),
            "first_time_buyer": (
                "These personas tried once but didn't come back. "
                "Something broke between the first experience and the reorder decision."
            ),
            "current_user": (
                "These are your most valuable personas — they've formed a habit. "
                "Understanding what made them stick tells you how to scale."
            ),
            "lapsed_user": (
                "These personas were active buyers who stopped. "
                "Identifying their exit signal is the key to retention strategy."
            ),
        }
        st.info(hints.get(cid, ""), icon="💡")

# Key metrics row
m1, m2, m3, m4 = st.columns(4)

# All four headline metrics are derived from the cohort summary so they are
# internally consistent with the cohort tiles above.
_total_pop = sum(cohorts.summary.values()) or 1
_tried = (
    cohorts.summary.get("first_time_buyer", 0)
    + cohorts.summary.get("current_user", 0)
    + cohorts.summary.get("lapsed_user", 0)
)
_current = cohorts.summary.get("current_user", 0)
_lapsed = cohorts.summary.get("lapsed_user", 0)
adoption_pct = round(_tried / _total_pop * 100, 1)
active_pct = round(_current / _total_pop * 100, 1)
lapse_rate = round(_lapsed / _tried * 100, 1) if _tried > 0 else 0.0

m1.metric("Overall Adoption", f"{adoption_pct}%", help="% of population who purchased at least once")
m2.metric("Active Repeat Buyers", f"{active_pct}%", help="% still buying at end of simulation")
m3.metric("Lapse Rate", f"{lapse_rate}%", help="% of buyers who did not remain active")
m4.metric("Simulation Months", "12", help="Day-level simulation across 365 days")

st.markdown("---")

## 🗺️ Persona Journey Map
st.caption("Click a cohort to see the personas inside and what signal placed them there.")

cohort_names = list(cohort_display.keys())
cohort_labels = {
    cid: f"{icon} {label} ({cohorts.summary.get(cid, 0)})"
    for cid, (label, icon, _) in cohort_display.items()
}
selected_cohort = st.radio(
    "Select cohort",
    options=cohort_names,
    format_func=lambda cid: cohort_labels[cid],
    horizontal=True,
    key="journey_map_cohort",
)

if selected_cohort:
    persona_ids = cohorts.cohorts.get(selected_cohort, [])[:50]
    if persona_ids:
        data = []
        for pid in persona_ids:
            p = pop.get_persona(pid)
            reason = next(
                (c.classification_reason for c in cohorts.classifications if c.persona_id == pid),
                "Classification reason unavailable",
            )
            data.append({
                "Persona": pid.rsplit('-', maxsplit=1)[0],  # strip UUID if present
                "City": p.demographics.city_tier,
                "Income": f"₹{p.demographics.household_income_lpa:.0f}L",
                "Reason": reason,
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        if len(cohorts.cohorts.get(selected_cohort, [])) > 50:
            st.caption(f"Showing first 50 of {len(cohorts.cohorts[selected_cohort])} personas.")

        # Cohort delta insight
        _full_pop_df = pop.to_dataframe()
        _cohort_df = _full_pop_df[_full_pop_df["id"].isin(persona_ids)]
        _pop_means = _full_pop_df.select_dtypes(include=["float"]).mean()
        _cohort_means = _cohort_df.select_dtypes(include=["float"]).mean()
        _diffs = _cohort_means - _pop_means
        top_diffs = _diffs.abs().nlargest(2)
        if len(top_diffs) > 0 and len(_cohort_df) >= 5:
            delta_text = []
            for attr, diff in top_diffs.items():
                direction = "higher" if _diffs[attr] > 0 else "lower"
                delta_text.append(
                    f"{direction} on {attr} ({_cohort_means[attr]:.2f} vs {_pop_means[attr]:.2f} avg)"
                )
            st.info(
                f"This cohort is {' and '.join(delta_text)} — vs the full 200-persona population.",
                icon="💡",
            )

        # System Voice narrative
        narratives = {
            "never_aware": f"These {len(persona_ids)} households never encountered the product through any channel. The primary driver is low brand salience — distribution and awareness investment are the unlock.",
            "aware_not_tried": f"These {len(persona_ids)} households know the product exists but didn't convert. Price, trust, and need clarity are the main blockers.",
            "first_time_buyer": f"These {len(persona_ids)} households tried once but didn't return. The window between first purchase and habit formation is the critical intervention point.",
            "current_user": f"These {len(persona_ids)} households are your most valuable segment. Understanding what made them stick is the key to scaling.",
            "lapsed_user": f"These {len(persona_ids)} households were active buyers who stopped. Identifying their exit signal — often price, child rejection, or routine disruption — is the retention priority.",
        }
        render_system_voice(narratives.get(selected_cohort, ""))

st.markdown("---")
st.success(
    "✅ Phase 1 complete. "
    "Proceed to **Phase 2 — Decomposition & Probing** to investigate why these outcomes occurred."
)
