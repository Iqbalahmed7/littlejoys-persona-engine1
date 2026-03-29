# ruff: noqa: N999
from __future__ import annotations

import copy

import streamlit as st

from src.config import Config, get_config
from src.constants import SCENARIO_IDS
from src.decision.scenarios import get_scenario
from src.probing.question_bank import get_questions_for_scenario, get_tree_for_question
from src.simulation.research_runner import ResearchRunner
from src.utils.display import CHANNEL_HELP
from src.utils.llm import LLMClient

# --- API key helpers (same pattern as app/pages/5_interviews.py) ---


def _resolve_api_key() -> str:
    """Read Anthropic API key from Streamlit secrets (cloud) or .env.local (local)."""
    try:
        if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
            return str(st.secrets["ANTHROPIC_API_KEY"]).strip()
    except Exception:
        pass
    key = get_config().anthropic_api_key.strip()
    if not key or key == "sk-ant-REPLACE_ME":
        return ""
    return key


def _has_api_key() -> bool:
    """Return True if a non-placeholder API key is available."""
    key = _resolve_api_key()
    return bool(key) and not key.startswith("sk-ant-REPLACE")


# --- Page ---

st.header("Research Design")
st.caption(
    "Design your research: pick a scenario, choose a business question, and run the hybrid pipeline."
)

if "population" not in st.session_state:
    st.warning("Load or generate a population from the home page first.")
    st.stop()

if "scenario_results" not in st.session_state:
    st.session_state.scenario_results = {}

scenario_id = st.selectbox(
    "Select Scenario",
    SCENARIO_IDS,
    format_func=lambda sid: f"{get_scenario(sid).name} ({sid})",
)
scenario = get_scenario(scenario_id)
st.markdown(f"**{scenario.description}**")
st.caption(
    f"Product: {scenario.product.name} · ₹{scenario.product.price_inr:.0f} · "
    f"Ages {scenario.target_age_range[0]}-{scenario.target_age_range[1]}"
)

questions = get_questions_for_scenario(scenario_id)
if not questions:
    st.error("No business questions are configured for this scenario.")
    st.stop()

question = st.selectbox(
    "Business Question",
    questions,
    format_func=lambda q: q.title,
)
if question:
    st.info(question.description)

# Custom scenario in session (same schema versioning as 2_scenario.py)
session_key = f"research_scenario_{scenario_id}"
_SCHEMA_VERSION = 2
_version_key = f"{session_key}_v"
if st.session_state.get(_version_key) != _SCHEMA_VERSION:
    st.session_state[session_key] = copy.deepcopy(scenario)
    st.session_state[_version_key] = _SCHEMA_VERSION
if session_key not in st.session_state:
    st.session_state[session_key] = copy.deepcopy(scenario)

with st.expander("Advanced: Tune Parameters", expanded=False):
    base_scenario = get_scenario(scenario_id)
    if st.button(
        "Reset to Defaults",
        key=f"research_reset_{scenario_id}",
        help="Restore all sliders and toggles to the built-in defaults for the selected scenario.",
    ):
        st.session_state[session_key] = copy.deepcopy(base_scenario)
        st.toast("Settings restored to defaults", icon="🔄")

    custom_scenario = st.session_state[session_key]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Product Parameters")
        custom_scenario.product.price_inr = st.slider(
            "Price (INR)",
            100.0,
            1500.0,
            float(custom_scenario.product.price_inr),
            step=50.0,
            key=f"research_price_{scenario_id}",
            help=(
                "Retail price of the product. Lower prices reduce the purchase barrier, "
                "especially for budget-conscious (SEC B2+) families. "
                "Reference: Nutrimix ₹599, Gummies ₹499, Protein Mix ₹699."
            ),
        )
        custom_scenario.product.taste_appeal = st.slider(
            "Taste Appeal",
            0.0,
            1.0,
            float(custom_scenario.product.taste_appeal),
            step=0.05,
            key=f"research_taste_{scenario_id}",
            help=(
                "How likely children are to accept the taste and format. "
                "0.0 = most kids refuse, 1.0 = kids ask for it. "
                "Gummy formats score 0.8+, powders 0.4-0.6."
            ),
        )
        custom_scenario.product.effort_to_acquire = st.slider(
            "Effort to Acquire",
            0.0,
            1.0,
            float(custom_scenario.product.effort_to_acquire),
            step=0.05,
            key=f"research_effort_{scenario_id}",
            help=(
                "Friction to obtain AND use the product. "
                "0.0 = buy and consume instantly (ready-to-drink), "
                "1.0 = requires multiple steps (cook into a recipe). "
                "High effort hurts busy parents most."
            ),
        )
        custom_scenario.product.clean_label_score = st.slider(
            "Clean Label Score",
            0.0,
            1.0,
            float(custom_scenario.product.clean_label_score),
            step=0.05,
            key=f"research_clean_{scenario_id}",
            help=(
                "How 'natural' the ingredient list looks to a parent scanning the pack. "
                "0.0 = synthetic-looking (E-numbers, preservatives), "
                "1.0 = recognisable whole ingredients."
            ),
        )
        custom_scenario.product.health_relevance = st.slider(
            "Health Relevance",
            0.0,
            1.0,
            float(custom_scenario.product.health_relevance),
            step=0.05,
            key=f"research_health_{scenario_id}",
            help=(
                "How clearly this product solves a perceived health need. "
                "0.0 = nice-to-have wellness, "
                "1.0 = doctor-recommended for a specific condition."
            ),
        )
        custom_scenario.lj_pass_available = st.toggle(
            "LJ Pass Available",
            custom_scenario.lj_pass_available,
            key=f"research_lj_pass_{scenario_id}",
            help=(
                "Whether a subscription/loyalty pass is offered. "
                "Reduces repeat-purchase friction and increases retention for habit-forming products."
            ),
        )

    with col2:
        st.subheader("Marketing Parameters")
        custom_scenario.marketing.awareness_budget = st.slider(
            "Awareness Budget",
            0.0,
            1.0,
            float(custom_scenario.marketing.awareness_budget),
            key=f"research_aware_budget_{scenario_id}",
            help=(
                "Marketing spend reaching target parents. "
                "0.0 = no marketing, 1.0 = saturated coverage. "
                "New products typically start at 0.2-0.3."
            ),
        )
        custom_scenario.marketing.awareness_level = st.slider(
            "Awareness Level",
            0.0,
            1.0,
            float(custom_scenario.marketing.awareness_level),
            key=f"research_aware_level_{scenario_id}",
            help=(
                "What fraction of target parents have heard of this product. "
                "Distinct from budget — a viral moment can create high awareness at low budget."
            ),
        )
        custom_scenario.marketing.trust_signal = st.slider(
            "Trust Signal",
            0.0,
            1.0,
            float(custom_scenario.marketing.trust_signal),
            key=f"research_trust_{scenario_id}",
            help=(
                "Overall brand credibility. Combines packaging quality, brand story, "
                "certifications, and social proof. New D2C brands start around 0.3-0.4."
            ),
        )
        custom_scenario.marketing.social_proof = st.slider(
            "Social Proof",
            0.0,
            1.0,
            float(custom_scenario.marketing.social_proof),
            key=f"research_social_{scenario_id}",
            help=(
                "Visible evidence that other parents use this product. "
                "Reviews, ratings, 'X mothers trust us' claims. "
                "Strongly influences community-oriented parents."
            ),
        )
        custom_scenario.marketing.expert_endorsement = st.slider(
            "Expert Endorsement",
            0.0,
            1.0,
            float(custom_scenario.marketing.expert_endorsement),
            key=f"research_expert_{scenario_id}",
            help=(
                "Professional credibility signals — doctor recommendations, clinical studies "
                "cited on packaging, dietitian partnerships."
            ),
        )
        custom_scenario.marketing.discount_available = float(
            st.slider(
                "Discount Available",
                0.0,
                0.5,
                float(custom_scenario.marketing.discount_available),
                key=f"research_discount_{scenario_id}",
                help=(
                    "Active promotional discount (0.0 = full price, 0.5 = 50% off). "
                    "Temporary discounts boost trial but may not sustain repeat purchase."
                ),
            )
        )

    st.subheader("Channel Mix")
    st.caption("Digital marketing spend allocation. Must sum to 1.0.")
    channels = ["instagram", "youtube", "whatsapp"]
    mix_cols = st.columns(3)
    mix_sum = 0.0

    for i, ch in enumerate(channels):
        with mix_cols[i]:
            val = st.slider(
                ch.title(),
                0.0,
                1.0,
                float(custom_scenario.marketing.channel_mix.get(ch, 0.0)),
                step=0.05,
                key=f"research_mix_{scenario_id}_{ch}",
                help=CHANNEL_HELP.get(ch, ""),
            )
            custom_scenario.marketing.channel_mix[ch] = val
            mix_sum += val

    if mix_sum > 1.05 or mix_sum < 0.95:
        st.error(f"Invalid mix sum ({mix_sum:.2f}). Please adjust sliders to sum to ~1.0.")

    st.subheader("Campaign Toggles")
    st.caption(
        "Offline partnerships and endorsements. These boost both trust and awareness "
        "independently of the digital channel mix."
    )
    t1, t2 = st.columns(2)
    t3, t4 = st.columns(2)
    with t1:
        custom_scenario.marketing.pediatrician_endorsement = st.toggle(
            "Pediatrician Endorsement",
            custom_scenario.marketing.pediatrician_endorsement,
            key=f"research_ped_{scenario_id}",
            help=(
                "Formal endorsement from pediatricians. "
                "The single strongest trust signal for health-anxious parents. "
                "Also boosts awareness through doctor-office reach."
            ),
        )
    with t2:
        custom_scenario.marketing.school_partnership = st.toggle(
            "School Partnership",
            custom_scenario.marketing.school_partnership,
            key=f"research_school_{scenario_id}",
            help=(
                "Product distributed or endorsed through schools. "
                "High-trust channel that bypasses digital ad skepticism. "
                "Especially effective for 7-14 age group."
            ),
        )
    with t3:
        custom_scenario.marketing.sports_club_partnership = st.toggle(
            "Sports Club Partnership",
            custom_scenario.marketing.sports_club_partnership,
            key=f"research_sports_{scenario_id}",
            help=(
                "Sports club and academy partnerships. "
                "Reaches active, fitness-oriented families. "
                "Strong credibility for protein and energy products."
            ),
        )
    with t4:
        custom_scenario.marketing.influencer_campaign = st.toggle(
            "Influencer Campaign",
            custom_scenario.marketing.influencer_campaign,
            key=f"research_influencer_{scenario_id}",
            help=(
                "Parenting influencer partnerships on Instagram/YouTube. "
                "Effective for digitally-active Tier 1 parents, less impact in Tier 2-3."
            ),
        )

# Use tuned scenario from session (expander may not have run this run — read key again)
custom_scenario = st.session_state[session_key]

with st.expander("Probing Tree", expanded=True):
    st.caption("Review the hypotheses that will be tested. Toggle branches to include/exclude.")

    tree = get_tree_for_question(question.id)
    enabled_hypotheses = []
    for hyp in tree.hypotheses:
        col1, col2 = st.columns([0.1, 0.9])
        with col1:
            enabled = st.checkbox(
                "",
                value=hyp.enabled,
                key=f"hyp_{question.id}_{hyp.id}",
            )
        with col2:
            st.markdown(f"**{hyp.title}**")
            st.caption(hyp.rationale)
            probe_count = sum(1 for p in tree.probes if p.hypothesis_id == hyp.id)
            st.caption(f"{probe_count} probes")
        if enabled:
            enabled_hypotheses.append(hyp)

    st.caption(f"{len(enabled_hypotheses)} of {len(tree.hypotheses)} hypotheses enabled")
    # Hypothesis toggles are for review only; ResearchRunner uses the full catalog tree.

st.subheader("Run Research")

pop = st.session_state.population
n_personas = len(pop.personas)

sample_size = 18
alternative_count = 50

summary_cols = st.columns(3)
summary_cols[0].metric("Personas", f"{n_personas}")
summary_cols[1].metric("Deep Interviews", f"~{sample_size}")
summary_cols[2].metric("Alternative Scenarios", f"{alternative_count}")

api_available = _has_api_key()
if api_available:
    mock_mode = st.toggle("Mock Mode", value=False, help="Use real LLM for deep interviews")
    if not mock_mode:
        st.caption(f"Estimated cost: ~$0.15-0.30 for {sample_size} interviews")
else:
    mock_mode = True
    st.info("No API key configured. Running in mock mode.")

run_clicked = st.button("Run Research", type="primary", use_container_width=True)

if run_clicked:
    channels = ["instagram", "youtube", "whatsapp"]
    mix_sum = sum(float(custom_scenario.marketing.channel_mix.get(ch, 0.0)) for ch in channels)
    if mix_sum > 1.05 or mix_sum < 0.95:
        st.error("Cannot run research with unbalanced channel mix. Adjust channel mix in Advanced.")
    else:
        llm = LLMClient(
            Config(
                llm_mock_enabled=mock_mode,
                llm_cache_enabled=not mock_mode,
                anthropic_api_key="" if mock_mode else _resolve_api_key(),
            )
        )

        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def on_progress(message: str, progress: float) -> None:
            progress_bar.progress(min(progress, 1.0))
            status_text.caption(message)

        runner = ResearchRunner(
            population=pop,
            scenario=custom_scenario,
            question=question,
            llm_client=llm,
            mock_mode=mock_mode,
            alternative_count=alternative_count,
            sample_size=sample_size,
            progress_callback=on_progress,
        )

        result = runner.run()
        st.session_state["research_result"] = result
        st.session_state.scenario_results[scenario_id] = result.primary_funnel

        progress_bar.progress(1.0)
        status_text.empty()

        done_cols = st.columns(4)
        done_cols[0].metric("Decision Pathway", f"{n_personas} personas")
        done_cols[1].metric("Deep Interviews", f"{len(result.interview_results)} personas")
        done_cols[2].metric("Alternatives", f"{len(result.alternative_runs)} scenarios")
        done_cols[3].metric("Duration", f"{result.metadata.duration_seconds:.1f}s")

        st.success("Research complete!")
        st.page_link("pages/3_results.py", label="View Results →", icon="📊")

prev = st.session_state.get("research_result")
if prev and not run_clicked:
    st.divider()
    st.caption(
        f"Previous run: {prev.metadata.scenario_id} · {prev.metadata.question_id} · "
        f"{prev.metadata.timestamp}"
    )
    st.page_link("pages/3_results.py", label="View Previous Results →", icon="📊")
