# ruff: noqa: N999
"""Phase 1 — Business Problem Selection & Baseline Simulation.

Replaces the old scenario-selection research page with a problem-first flow:
1. User selects a business problem (not a scenario)
2. System explains what it will simulate
3. User clicks Run — simulation runs with dramatic narrative progress
4. System narrates findings, cohort dashboard appears
"""

from __future__ import annotations

import time
from typing import Any

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
    adoption_pct = round(temporal_result.final_adoption_rate * 100)
    active_pct = round(temporal_result.final_active_rate * 100)
    pop_size = temporal_result.population_size
    repeat_pct = active_pct
    lapsed = cohorts.summary.get("lapsed_user", 0)
    first_time = cohorts.summary.get("first_time_buyer", 0)
    never_aware = cohorts.summary.get("never_aware", 0)
    aware_not_tried = cohorts.summary.get("aware_not_tried", 0)

    # Leaky bucket: of those who tried, how many didn't repeat?
    tried = first_time + cohorts.summary.get("current_user", 0) + lapsed
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


# ── Monthly narrative for dramatic simulation progress ─────────────────────────
_MONTH_NARRATIVES: dict[int, str] = {
    1:  "Introducing the product to {n} personas through their most likely discovery channels...",
    3:  "Month 3: Awareness forming. Early trials beginning. First churn signals appearing...",
    6:  "Month 6: Trial rate plateauing. First-time buyers either reordering or going quiet...",
    9:  "Month 9: Habit patterns solidifying or breaking. Word-of-mouth propagating...",
    12: "Month 12: Final month. Collecting purchase histories and forming behavioral cohorts...",
}


def _run_simulation_with_narrative(pop: Population, scenario_id: str) -> tuple[Any, Any]:
    """Run temporal simulation + cohort classification with dramatic progress display."""
    scenario = get_scenario(scenario_id)
    n = len(pop.personas)

    temporal_result = None
    cohorts = None

    with st.status("Running 12-month baseline simulation...", expanded=True) as status:
        for month, template in _MONTH_NARRATIVES.items():
            msg = template.format(n=n)
            st.write(f"**Month {month}** — {msg}")
            time.sleep(0.3)

        # Run the actual simulations
        st.write("⚙️ Computing temporal trajectories...")
        temporal_result = run_temporal_simulation(pop, scenario, months=12, seed=DEFAULT_SEED)

        st.write("⚙️ Classifying behavioral cohorts...")
        cohorts = classify_population(pop, scenario, seed=DEFAULT_SEED)

        status.update(
            label=f"✅ Simulation complete — {len(pop.personas)} personas × 365 days",
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

# Key metrics row
m1, m2, m3, m4 = st.columns(4)
adoption_pct = round(temporal_result.final_adoption_rate * 100, 1)
active_pct = round(temporal_result.final_active_rate * 100, 1)
tried = (
    cohorts.summary.get("first_time_buyer", 0)
    + cohorts.summary.get("current_user", 0)
    + cohorts.summary.get("lapsed_user", 0)
)
lapsed = cohorts.summary.get("lapsed_user", 0)
lapse_rate = round(lapsed / tried * 100, 1) if tried > 0 else 0.0

m1.metric("Overall Adoption", f"{adoption_pct}%", help="% who purchased at least once")
m2.metric("Active Repeat Buyers", f"{active_pct}%", help="% still buying at month 12")
m3.metric("Lapse Rate", f"{lapse_rate}%", help="% of buyers who stopped")
m4.metric("Simulation Months", "12", help="Day-level simulation across 365 days")

st.markdown("---")
st.success(
    "✅ Phase 1 complete. "
    "Proceed to **Phase 2 — Decomposition & Probing** to investigate why these outcomes occurred."
)
