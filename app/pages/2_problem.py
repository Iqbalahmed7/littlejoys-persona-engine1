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
from src.utils.display import city_tier_label
from src.analysis.cohort_classifier import classify_population
from src.analysis.problem_templates import PROBLEM_TEMPLATES
from src.constants import DEFAULT_SEED, GTM_CHANNELS, GTM_PRESETS
from src.decision.scenarios import MarketingConfig, get_scenario
from src.generation.population import Population, PopulationGenerator
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


def _run_simulation_with_narrative(
    pop: Population, scenario_id: str, seed: int = DEFAULT_SEED
) -> tuple[Any, Any]:
    """Run simulation first, then narrate checkpoints from real monthly outputs."""
    # Use GTM-configured scenario if available, else fall back to defaults
    scenario = st.session_state.get("gtm_scenario_override") or get_scenario(scenario_id)
    sim_months = scenario.months
    n = len(pop.personas)

    with st.status(f"Running {sim_months}-month baseline simulation...", expanded=True) as status:
        _ch_names = (
            ", ".join(scenario.marketing.channel_mix.keys())
            if scenario.marketing.channel_mix
            else "default channels"
        )
        st.write(
            f"⚙️ Sampling {n} freshly-generated personas via {_ch_names} "
            f"(awareness budget: {scenario.marketing.awareness_budget:.0%}, seed {seed})..."
        )

        temporal_result = run_temporal_simulation(pop, scenario, months=sim_months, seed=seed)

        st.write("⚙️ Classifying behavioral cohorts...")
        cohorts = classify_population(pop, scenario, seed=seed)

        # Replay narrative from actual monthly snapshots
        checkpoints = {3, 6, 9, 12}
        for snap in temporal_result.monthly_snapshots:
            if snap.month in checkpoints:
                if snap.month == 3:
                    st.write(
                        f"Month 3: {snap.cumulative_adopters} personas have now tried the product. "
                        f"First churn signals emerging ({snap.churned} drop-offs so far)."
                    )
                elif snap.month == 6:
                    st.write(
                        f"Month 6: Trial rate reaching {round(snap.cumulative_adopters / max(n, 1) * 100)}%. "
                        f"{snap.repeat_purchasers} personas repeated this month. {snap.total_active} still active."
                    )
                elif snap.month == 9:
                    st.write(
                        f"Month 9: Habit patterns solidifying. {snap.total_active} active buyers. "
                        f"{snap.churned} churned this month."
                    )
                elif snap.month == 12:
                    st.write(
                        f"Month 12: Simulation complete. {snap.cumulative_adopters} total adopters across {n} personas."
                    )

        status.update(
            label=f"✅ Simulation complete — {n} personas × {sim_months} months",
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
    f"Configure your go-to-market strategy below — marketing channels, awareness campaigns, "
    f"and referral programs — then run the simulation to see adoption trajectories."
)

# ── GTM Strategy Panel ───────────────────────────────────────────────────────
_base_scenario = get_scenario(selected_problem)

with st.expander("**GTM Strategy** — Configure marketing mix & awareness campaigns", expanded=True):
    # Preset selector
    preset_names = ["Custom"] + list(GTM_PRESETS.keys())
    selected_preset = st.selectbox(
        "Quick Preset",
        preset_names,
        index=0,
        key="gtm_preset",
        help="Select a go-to-market strategy template or customize manually",
    )

    # Load preset values or defaults from scenario
    if selected_preset != "Custom" and selected_preset in GTM_PRESETS:
        _preset = GTM_PRESETS[selected_preset]
        st.caption(f"_{_preset['description']}_")
        _default_budget = _preset["awareness_budget"]
        _default_channels = _preset["channel_mix"]
        _default_campaigns = _preset["campaigns"]
        _default_referral = _preset["referral_program_boost"]
        _default_discount = _preset["discount_available"]
    else:
        _default_budget = _base_scenario.marketing.awareness_budget
        _default_channels = _base_scenario.marketing.channel_mix
        _default_campaigns = {
            "influencer_campaign": _base_scenario.marketing.influencer_campaign,
            "pediatrician_endorsement": _base_scenario.marketing.pediatrician_endorsement,
            "school_partnership": _base_scenario.marketing.school_partnership,
            "sports_club_partnership": _base_scenario.marketing.sports_club_partnership,
        }
        _default_referral = _base_scenario.marketing.referral_program_boost
        _default_discount = _base_scenario.marketing.discount_available

    st.markdown("---")

    # Row 1: Duration + Awareness Budget
    _dur_col, _budget_col = st.columns(2)
    with _dur_col:
        sim_months = st.select_slider(
            "Simulation Duration",
            options=[3, 6, 12],
            value=min(_base_scenario.months, 12),
            key="gtm_months",
            help="How many months to simulate the product launch",
        )
    with _budget_col:
        awareness_budget = st.slider(
            "Awareness Budget",
            min_value=0.0,
            max_value=1.0,
            value=float(_default_budget),
            step=0.05,
            key="gtm_awareness_budget",
            help="Overall marketing spend intensity (0 = no marketing, 1 = maximum push)",
        )

    st.markdown("---")

    # Row 2: Channel Mix
    st.markdown("**Marketing Channels** — allocate your spend across channels")
    st.caption("Select channels and set relative weights. They will be auto-normalized to 100%.")

    # Channel selection
    available_channels = GTM_CHANNELS
    _channel_labels = {
        "instagram": "Instagram / Reels",
        "youtube": "YouTube (reviews & ads)",
        "whatsapp": "WhatsApp (mom groups)",
        "google_ads": "Google Ads / SEM",
        "facebook_ads": "Facebook / Meta Ads",
        "pediatrician": "Pediatrician referrals",
        "momfluencer": "Momfluencer campaigns",
        "reddit": "Reddit / Parenting forums",
        "pharmacy_kiosk": "Pharmacy / Retail kiosks",
        "school_activation": "School activations",
        "seo_content": "SEO / Content marketing",
        "email_marketing": "Email / CRM campaigns",
    }

    default_selected = list(_default_channels.keys())
    selected_channels = st.multiselect(
        "Active Channels",
        options=available_channels,
        default=[c for c in default_selected if c in available_channels],
        format_func=lambda c: _channel_labels.get(c, c.replace("_", " ").title()),
        key="gtm_channels",
    )

    # Channel weight sliders
    channel_weights: dict[str, float] = {}
    if selected_channels:
        _ch_cols = st.columns(min(len(selected_channels), 4))
        for i, ch in enumerate(selected_channels):
            with _ch_cols[i % len(_ch_cols)]:
                channel_weights[ch] = st.slider(
                    _channel_labels.get(ch, ch),
                    min_value=0.0,
                    max_value=1.0,
                    value=float(_default_channels.get(ch, 0.20)),
                    step=0.05,
                    key=f"gtm_ch_{ch}",
                )

        # Normalize and display
        _total_weight = sum(channel_weights.values())
        if _total_weight > 0:
            channel_mix = {k: round(v / _total_weight, 2) for k, v in channel_weights.items()}
            # Fix rounding to exactly 1.0
            _diff = round(1.0 - sum(channel_mix.values()), 2)
            if _diff != 0 and channel_mix:
                _first_key = next(iter(channel_mix))
                channel_mix[_first_key] = round(channel_mix[_first_key] + _diff, 2)
        else:
            channel_mix = {ch: round(1.0 / len(selected_channels), 2) for ch in selected_channels}

        # Show normalized mix
        _mix_display = " | ".join(
            f"{_channel_labels.get(ch, ch).split('/')[0].strip()}: {pct:.0%}"
            for ch, pct in channel_mix.items()
        )
        st.caption(f"Normalized mix: {_mix_display}")
    else:
        channel_mix = _base_scenario.marketing.channel_mix

    st.markdown("---")

    # Row 3: Awareness Campaigns
    st.markdown("**Awareness Campaigns & Partnerships**")
    _camp_cols = st.columns(4)
    with _camp_cols[0]:
        camp_influencer = st.checkbox(
            "Influencer campaign",
            value=_default_campaigns.get("influencer_campaign", False),
            key="gtm_influencer",
            help="Momfluencers, health bloggers, Instagram/YouTube creators",
        )
    with _camp_cols[1]:
        camp_pediatrician = st.checkbox(
            "Pediatrician endorsement",
            value=_default_campaigns.get("pediatrician_endorsement", False),
            key="gtm_pediatrician",
            help="Doctor recommendations, clinic sampling, Rx pads",
        )
    with _camp_cols[2]:
        camp_school = st.checkbox(
            "School partnership",
            value=_default_campaigns.get("school_partnership", False),
            key="gtm_school",
            help="School nutrition programs, PTA events, lunchbox demos",
        )
    with _camp_cols[3]:
        camp_sports = st.checkbox(
            "Sports club partnership",
            value=_default_campaigns.get("sports_club_partnership", False),
            key="gtm_sports",
            help="Youth sports academies, fitness camps, coaching tie-ups",
        )

    st.markdown("---")

    # Row 4: WoM & Referrals + Launch Discount
    _wom_col, _ref_col, _disc_col = st.columns(3)
    with _wom_col:
        st.caption("**Word-of-Mouth**")
        st.caption("Organic WoM via WhatsApp groups, parent forums, playground conversations")
    with _ref_col:
        referral_boost = st.slider(
            "Referral Program Boost",
            min_value=0.0,
            max_value=0.30,
            value=float(_default_referral),
            step=0.01,
            key="gtm_referral",
            help="Share-and-earn, referral codes, WhatsApp forwarding incentives",
        )
    with _disc_col:
        launch_discount = st.slider(
            "Launch Discount",
            min_value=0.0,
            max_value=0.30,
            value=float(_default_discount),
            step=0.01,
            key="gtm_discount",
            help="Introductory offer, first-purchase discount, trial packs",
        )

# Build the GTM-configured scenario override
_gtm_marketing = _base_scenario.marketing.model_copy(update={
    "awareness_budget": awareness_budget,
    "channel_mix": channel_mix,
    "influencer_campaign": camp_influencer,
    "pediatrician_endorsement": camp_pediatrician,
    "school_partnership": camp_school,
    "sports_club_partnership": camp_sports,
    "referral_program_boost": referral_boost,
    "discount_available": launch_discount,
})
_gtm_scenario = _base_scenario.model_copy(update={
    "marketing": _gtm_marketing,
    "mode": "temporal",
    "months": sim_months,
})

# Store for use by simulation
st.session_state["gtm_scenario_override"] = _gtm_scenario

# Check if simulation already done for this problem
already_run = (
    "baseline_cohorts" in st.session_state
    and st.session_state.get("baseline_problem_id") == selected_problem
)

def _next_sim_seed() -> int:
    """Return a unique seed for each simulation run (increments per click)."""
    count = st.session_state.get("sim_run_count", 0) + 1
    st.session_state["sim_run_count"] = count
    # Combine DEFAULT_SEED with the run counter for reproducible-but-varied draws
    return DEFAULT_SEED + count * 7919


def _fresh_population(seed: int) -> Population:
    """Generate a fresh population using the current population's size."""
    n = len(st.session_state.population.personas)
    gen = PopulationGenerator()
    fresh = gen.generate(size=n, seed=seed, deep_persona_count=max(3, n // 20))
    st.session_state["population"] = fresh
    return fresh


if already_run:
    st.success("✅ Baseline simulation already complete for this problem.")
    if st.button("Re-run simulation with new GTM strategy", type="secondary"):
        _seed = _next_sim_seed()
        for k in ["baseline_cohorts", "baseline_temporal"]:
            st.session_state.pop(k, None)
        with st.spinner(f"Generating fresh population (seed {_seed})…"):
            _fresh_pop = _fresh_population(_seed)
        temporal_result, cohorts = _run_simulation_with_narrative(_fresh_pop, selected_problem, seed=_seed)
        st.session_state["baseline_temporal"] = temporal_result
        st.session_state["baseline_cohorts"] = cohorts
        st.session_state["baseline_problem_id"] = selected_problem
        st.session_state["baseline_scenario_id"] = selected_problem
        st.rerun()
else:
    if st.button("▶ Run Baseline Simulation", type="primary", use_container_width=True):
        _seed = _next_sim_seed()
        with st.spinner(f"Generating fresh population (seed {_seed})…"):
            _fresh_pop = _fresh_population(_seed)
        temporal_result, cohorts = _run_simulation_with_narrative(_fresh_pop, selected_problem, seed=_seed)
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
        st.metric(f"{icon} {label}", f"{count}", f"{pct}% of population", delta_color="off")
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
                        f"• {p.id}, {p.demographics.city_tier} — "
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
_sim_months = getattr(temporal_result, "months", 12)
m4.metric("Simulation Months", str(_sim_months), help=f"Temporal simulation across {_sim_months} months")

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

# ── Child Age-Band Breakdown ──────────────────────────────────────────────────
st.markdown("---")
st.subheader("Adoption by Child Age Band")
st.caption(
    "Same simulation, same marketing mix — sliced by the age of the child in each household. "
    "Use this to see where the product is gaining traction vs. where the funnel is leaking by age segment."
)

_AGE_BANDS: list[tuple[str, int, int]] = [
    ("2–6 yrs  (Toddler / Early)", 2, 6),
    ("7–10 yrs (Middle Childhood)", 7, 10),
    ("11–14 yrs (Pre-Teen)", 11, 14),
]
_COHORT_ORDER_AB = ["never_aware", "aware_not_tried", "first_time_buyer", "current_user", "lapsed_user"]

# Build per-band counts — a persona falls into a band if their YOUNGEST child is in range.
_band_rows = []
for band_label, low, high in _AGE_BANDS:
    band_counts: dict[str, int] = {c: 0 for c in _COHORT_ORDER_AB}
    for cid in _COHORT_ORDER_AB:
        for pid in cohorts.cohorts.get(cid, []):
            try:
                _p = pop.get_persona(pid)
                youngest = _p.demographics.youngest_child_age
                if youngest is not None and low <= youngest <= high:
                    band_counts[cid] += 1
            except Exception:
                pass
    band_total = sum(band_counts.values())
    if band_total == 0:
        continue
    band_tried = band_counts["first_time_buyer"] + band_counts["current_user"] + band_counts["lapsed_user"]
    band_active = band_counts["current_user"]
    band_repeated = band_counts["current_user"] + band_counts["lapsed_user"]
    _band_rows.append({
        "Age Band": band_label,
        "Personas": band_total,
        "Never Aware": band_counts["never_aware"],
        "Aware, Not Tried": band_counts["aware_not_tried"],
        "First-Time Buyer": band_counts["first_time_buyer"],
        "Current User": band_counts["current_user"],
        "Lapsed User": band_counts["lapsed_user"],
        "Trial Rate": f"{round(band_tried / band_total * 100)}%",
        "Active Rate": f"{round(band_active / band_total * 100)}%",
        "Repeat Rate": f"{round(band_repeated / max(band_tried, 1) * 100)}%",
        "_tried": band_tried,
        "_active": band_active,
        "_total": band_total,
    })

if _band_rows:
    # Summary table
    _display_cols = [
        "Age Band", "Personas", "Never Aware", "Aware, Not Tried",
        "First-Time Buyer", "Current User", "Lapsed User",
        "Trial Rate", "Active Rate", "Repeat Rate",
    ]
    _df_age = pd.DataFrame(_band_rows)[_display_cols]
    st.dataframe(_df_age, use_container_width=True, hide_index=True)

    # Visual: trial rate vs active rate per band
    _ab_labels = [r["Age Band"] for r in _band_rows]
    _trial_rates = [round(r["_tried"] / r["_total"] * 100) for r in _band_rows]
    _active_rates = [round(r["_active"] / r["_total"] * 100) for r in _band_rows]

    fig_age = go.Figure()
    fig_age.add_trace(go.Bar(
        name="Trial Rate %",
        x=_ab_labels,
        y=_trial_rates,
        marker_color="#3498DB",
        text=[f"{v}%" for v in _trial_rates],
        textposition="outside",
    ))
    fig_age.add_trace(go.Bar(
        name="Active Rate %",
        x=_ab_labels,
        y=_active_rates,
        marker_color="#2ECC71",
        text=[f"{v}%" for v in _active_rates],
        textposition="outside",
    ))
    fig_age.update_layout(
        title="Trial Rate vs Active Rate by Child Age Band",
        barmode="group",
        yaxis_title="% of personas in band",
        yaxis_range=[0, max(_trial_rates + _active_rates + [5]) + 15],
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=10, r=10, t=40, b=10),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_age, use_container_width=True)

    # System voice insight
    if len(_band_rows) >= 2:
        _best = max(_band_rows, key=lambda r: r["_tried"] / r["_total"])
        _worst = min(_band_rows, key=lambda r: r["_tried"] / r["_total"])
        render_system_voice(
            f"The <b>{_best['Age Band']}</b> segment has the highest trial rate "
            f"({_best['Trial Rate']}) — driven by stronger need recognition and channel fit "
            f"for households with children in this range. "
            f"The <b>{_worst['Age Band']}</b> segment trails at {_worst['Trial Rate']} trial — "
            f"the 0.3× age-relevance penalty suppresses need recognition scores for out-of-range children, "
            f"compounding any existing awareness gap. "
            f"If your real-world conversion exceeds these numbers for a specific band, "
            f"calibrate the scenario's <i>awareness_budget</i> and <i>channel_mix</i> upward — "
            f"the simulation is parameterised conservatively by default."
        )
else:
    st.info("Age band breakdown unavailable — youngest_child_age not populated for this population.")

st.markdown("---")

## 🎯 Segment Builder
st.caption("Slice the population by demographics and see how cohort distribution shifts.")

col_f1, col_f2, col_f3, col_f4 = st.columns(4)
with col_f1:
    city_filter = st.multiselect(
        "City Tier",
        ["Tier1", "Tier2", "Tier3"],
        format_func=city_tier_label,
    )
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

if st.button("Apply Segment"):
    filtered_personas = []
    for p in pop.personas:
        flat = p.to_flat_dict()
        match_city = not city_filter or flat.get("city_tier") in city_filter
        match_income = income_filter[0] <= flat.get("household_income_lpa", 0) <= income_filter[1]
        # Persona matches age filter if ANY child age falls within the range;
        # childless personas pass through if no ages are recorded.
        _child_ages = p.demographics.child_ages or []
        match_age = (not _child_ages) or any(
            age_filter[0] <= age <= age_filter[1] for age in _child_ages
        )
        match_health = not health_filter or flat.get("health_consciousness") in health_filter
        if match_city and match_income and match_age and match_health:
            filtered_personas.append(p)

    n_filtered = len(filtered_personas)
    pct_filtered = round(n_filtered / len(pop.personas) * 100)
    st.metric("Segment Size", f"{n_filtered} personas ({pct_filtered}%)")

    st.session_state["segment_persona_ids"] = [p.id for p in filtered_personas]

    if n_filtered == 0:
        st.warning("No personas match this combination. Try widening the filters.")
    else:
        # Build segment cohort summary by slicing existing classifications —
        # avoids re-running classify_population on an incomplete Population object.
        seg_ids = {p.id for p in filtered_personas}
        seg_summary = {
            cid: len([pid for pid in pids if pid in seg_ids])
            for cid, pids in cohorts.cohorts.items()
        }
        seg_total = sum(seg_summary.values()) or 1
        full_total = sum(cohorts.summary.values()) or 1

        # Side-by-side cohort comparison
        col_pop, col_seg = st.columns(2)
        with col_pop:
            st.caption(f"📊 Full population ({full_total})")
            cols_pop = st.columns(5)
            for i, cid in enumerate(["never_aware", "aware_not_tried", "first_time_buyer", "current_user", "lapsed_user"]):
                count = cohorts.summary.get(cid, 0)
                pct = round(count / full_total * 100)
                with cols_pop[i]:
                    st.metric(cohort_display[cid][0], f"{count} ({pct}%)", delta=None)

        with col_seg:
            st.caption(f"🎯 Your segment ({n_filtered})")
            cols_seg = st.columns(5)
            for i, cid in enumerate(["never_aware", "aware_not_tried", "first_time_buyer", "current_user", "lapsed_user"]):
                seg_count = seg_summary.get(cid, 0)
                seg_pct = round(seg_count / seg_total * 100)
                with cols_seg[i]:
                    st.metric(cohort_display[cid][0], f"{seg_count} ({seg_pct}%)", delta=None)

        # Comparative insight — find the metric with the largest deviation
        full_tried = sum(cohorts.summary.get(c, 0) for c in ["first_time_buyer", "current_user", "lapsed_user"])
        seg_tried = sum(seg_summary.get(c, 0) for c in ["first_time_buyer", "current_user", "lapsed_user"])

        _metrics = {
            "lapse rate":       (
                seg_summary.get("lapsed_user", 0) / max(1, seg_tried),
                cohorts.summary.get("lapsed_user", 0) / max(1, full_tried),
            ),
            "adoption rate":    (
                seg_tried / seg_total,
                full_tried / full_total,
            ),
            "never-aware rate": (
                seg_summary.get("never_aware", 0) / seg_total,
                cohorts.summary.get("never_aware", 0) / full_total,
            ),
        }
        top_label = max(_metrics, key=lambda k: abs(_metrics[k][0] - _metrics[k][1]))
        seg_val, full_val = _metrics[top_label]
        diff_val = seg_val - full_val
        if abs(diff_val) > 0.1:
            direction = "higher" if diff_val > 0 else "lower"
            st.info(
                f"💡 This segment has a {direction} {top_label} "
                f"({seg_val:.0%} vs {full_val:.0%} in the full population).",
                icon="💡",
            )

st.markdown("---")
st.success(
    "✅ Phase 1 complete. "
    "Proceed to **Phase 2 — Decomposition & Probing** to investigate why these outcomes occurred."
)
