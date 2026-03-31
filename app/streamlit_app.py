"""
LittleJoys Persona Simulation Engine — Streamlit Dashboard.

Main entry point for the interactive presentation layer.
"""

import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

# Ensure repo root is on sys.path so src.* and app.* packages are importable
# regardless of how Streamlit or the cloud runner sets the working directory.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st  # noqa: E402

from src.constants import DEFAULT_SEED, SCENARIO_IDS  # noqa: E402
from src.decision.scenarios import get_scenario  # noqa: E402
from src.generation.population import Population  # noqa: E402
from src.simulation.static import run_static_simulation  # noqa: E402
from src.utils.display import city_tier_label  # noqa: E402

st.set_page_config(
    page_title="LittleJoys Persona Engine",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("LittleJoys Persona Simulation Engine")
st.caption("Synthetic persona engine for kids nutrition D2C in India.")
st.markdown("---")

demo_mode = False

pop_path = Path("data/population")

if "population" not in st.session_state:
    if pop_path.exists():
        with st.status("Initialising engine...", expanded=True) as status:
            st.write("Loading 200 synthetic household profiles...")
            st.session_state.population = Population.load(pop_path)
            st.write("Running baseline decision simulations across 4 scenarios...")
            st.session_state.scenario_results = {}
            for sid in SCENARIO_IDS:
                st.write(f"  · {get_scenario(sid).name}")
                st.session_state.scenario_results[sid] = run_static_simulation(
                    st.session_state.population,
                    get_scenario(sid),
                )
            status.update(label="Engine ready.", state="complete", expanded=False)
        st.rerun()
    else:
        st.info("No population data found. Generate a synthetic baseline population to begin.")
        if st.button("Generate Population", type="primary"):
            from src.generation.population import PopulationGenerator

            with st.spinner("Generating population..."):
                pop = PopulationGenerator().generate(seed=DEFAULT_SEED)
                pop.save(pop_path)
                st.session_state.population = pop
            st.toast("Population generated successfully!", icon="✅")
            st.rerun()

if "scenario_results" not in st.session_state:
    st.session_state.scenario_results = {}
    if "population" in st.session_state:
        for sid in SCENARIO_IDS:
            st.session_state.scenario_results[sid] = run_static_simulation(
                st.session_state.population,
                get_scenario(sid),
            )

if "population" in st.session_state:
    pop = st.session_state.population

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Personas", len(pop.personas))
    _with_narratives = sum(1 for p in pop.personas if p.narrative)
    # Only show "With Narratives" if more than 0, otherwise show a neutral label.
    if _with_narratives > 0:
        c2.metric("With Narratives", _with_narratives)
    else:
        c2.metric(
            "Persona Depth",
            "Deep Profiles",
            help="All personas have full demographic and behavioral profiles.",
        )
    c3.metric(
        "Business Problems",
        4,
        help="4 pre-configured business problems available to investigate.",
    )

    # ── Engine Status Strip ────────────────────────────────────────────────
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

    # ── Last Investigation Card (if Phase 3 done) ──────────────────────────
    _problem_labels = {
        "nutrimix_2_6": "Why is repeat purchase low despite high NPS? (Nutrimix 2-6)",
        "nutrimix_7_14": "How do we expand Nutrimix from 2-6 to the 7-14 age group?",
        "magnesium_gummies": "How do we grow sales of a niche supplement? (Magnesium Gummies)",
        "protein_mix": "The product requires cooking — how do we overcome the effort barrier? (Protein Mix)",
    }

    if "core_finding" in st.session_state:
        core_finding: dict = st.session_state["core_finding"]
        scenario_id = core_finding.get("scenario_id") or st.session_state.get(
            "baseline_scenario_id", ""
        )
        today = date.today().strftime("%d %b %Y")
        dominant_title = core_finding.get("dominant_hypothesis_title") or core_finding.get(
            "dominant_hypothesis", ""
        )
        overall_confidence = float(core_finding.get("overall_confidence", 0.0))

        all_iv_results = []
        top_iv_line = ""
        if "intervention_run" in st.session_state:
            _run = st.session_state["intervention_run"]
            all_iv_results = _run.get("all_results", []) or []
        if all_iv_results:
            sorted_iv = sorted(
                all_iv_results,
                key=lambda x: x["result"].absolute_lift,
                reverse=True,
            )
            top = sorted_iv[0]
            iv = top["intervention"]
            r = top["result"]
            top_iv_line = f"Top intervention: {iv.name} (+{r.absolute_lift:.1%} adoption lift)"

        card_html = (
            "<div style='border:1px solid #D0D7DE; background:#F0F4F8; "
            "padding:16px 18px; border-radius:10px; margin:14px 0;'>"
            "<div style='font-weight:800; color:#1F2937;'>🔍 Last Investigation</div>"
            "<div style='margin-top:4px; display:flex; justify-content:space-between; "
            "gap:12px;'>"
            f"<div style='color:#374151; font-weight:600;'>{_problem_labels.get(scenario_id, scenario_id)}</div>"
            f"<div style='color:#6B7280;'>{today}</div>"
            "</div>"
            "<div style='margin-top:10px; color:#374151;'>"
            "<div style='font-weight:700;'>Core Finding:</div>"
            f"<div style='margin-top:4px;'>{dominant_title} — {overall_confidence:.0%} confidence</div>"
            "</div>"
            + (
                f"<div style='margin-top:10px; color:#374151; font-weight:600;'>{top_iv_line}</div>"
                if top_iv_line
                else ""
            )
            + "</div>"
        )
        st.markdown(card_html, unsafe_allow_html=True)

        _dl_cols = st.columns(2)
        with _dl_cols[0]:
            st.page_link(
                "pages/8_synthesis_report.py",
                label="→ View Full Report",
            )
        with _dl_cols[1]:
            st.page_link(
                "pages/3_decompose.py",
                label="→ Re-run Investigation",
            )
    else:
        st.subheader("Getting Started")
        st.markdown(
            "1. **Browse personas** — Explore your synthetic population\n"
            "2. **Define your problem** — Pick a business question; the engine runs a 12-month simulation\n"
            "3. **Investigate** — Review hypotheses, run the probing tree, see evidence accumulate\n"
            "4. **Core Finding** — One synthesised insight with evidence chain\n"
            "5. **Interventions** — Compare solutions on effort, cost, and projected lift\n"
            "6. **Deep-dive interviews** — Read smart-sampled persona conversations"
        )

    # ── Population Archetype Cards ─────────────────────────────────────────
    if pop.personas:
        st.subheader("Who's in your population?")

        def _health_consciousness_score(persona: object) -> float:
            return (
                float(persona.health.diet_consciousness)
                + float(persona.health.child_health_proactivity)
                + float(persona.health.nutrition_gap_awareness)
            ) / 3.0

        def _health_band(score: float) -> str:
            # Match the binning used on the Personas page.
            if score < 0.4:
                return "Low"
            if score < 0.7:
                return "Medium"
            return "High"

        grouped: dict[tuple[str, str], list] = defaultdict(list)
        for p in pop.personas:
            grouped[(p.demographics.city_tier, p.demographics.socioeconomic_class)].append(p)

        top_groups = sorted(grouped.items(), key=lambda kv: len(kv[1]), reverse=True)[:3]

        arche_cols = st.columns(3)
        for idx, ((city_tier, sec_class), members) in enumerate(top_groups):
            score_bands = [_health_band(_health_consciousness_score(p)) for p in members]
            common_band = Counter(score_bands).most_common(1)[0][0] if score_bands else "Medium"
            count = len(members)
            with arche_cols[idx], st.container(border=True):
                st.markdown(
                    f"**{city_tier_label(city_tier)} · {sec_class}** ({count} personas)",
                )
                st.caption(f"Predominantly {common_band.lower()} health consciousness")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.page_link("pages/1_personas.py", label="🔍 Explore Population", icon="👥")
    with col2:
        st.page_link("pages/2_problem.py", label="💡 State a Problem", icon="🎯")
    with col3:
        st.page_link("pages/4_finding.py", label="📊 View Core Finding", icon="📋")
    with col4:
        st.page_link("pages/9_compare.py", label="⚖️ Compare Scenarios", icon="⚖️")
