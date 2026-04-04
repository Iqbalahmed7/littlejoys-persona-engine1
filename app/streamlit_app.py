"""
LittleJoys Persona Intelligence Platform — Streamlit application.

Navigation
----------
  Business Problems  — home: 3 scenario cards + open-ended question entry
  Run Scenario       — problem-specific runner (Journey A / B / C + pre-loaded results)
  Ask the Population — open-ended question engine (natural language → insight)
  Persona Explorer   — rich persona browser with segment-first view
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation.batch_runner import run_batch  # noqa: E402
from src.simulation.journey_config import (  # noqa: E402
    JourneyConfig,
    StimulusConfig,
)
from src.simulation.journey_presets import (  # noqa: E402
    PRESET_JOURNEY_A,
    PRESET_JOURNEY_B,
    PRESET_JOURNEY_C,
    list_presets,
)
from src.taxonomy.schema import Persona  # noqa: E402

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_all_personas() -> dict[str, dict]:
    """Load all personas via the Simulatte Persona Generator REST API.

    Primary path  : GET /cohort/{cohort_id}/personas on the deployed API.
    Local fallback: legacy JSON files in data/population/ (dev only).
    """
    import os as _os
    from src.simulatte_client import SIMULATTE_API_URL, load_personas

    # ── Primary: Persona Generator API ──────────────────────────────────────
    try:
        personas = load_personas()
        if personas:
            return personas
    except Exception as e:
        # Only warn if SIMULATTE_API_URL has been explicitly configured,
        # so dev machines without connectivity don't get noisy banners.
        if _os.environ.get("SIMULATTE_API_URL"):
            st.warning(f"Persona Generator API unavailable ({SIMULATTE_API_URL}): {e}. Using local data.")

    # ── Fallback: legacy local JSON (development / offline) ─────────────────
    candidates = [
        PROJECT_ROOT / "data" / "population" / "personas_generated.json",
        PROJECT_ROOT / "data" / "population" / "personas.json",
    ]
    for path in candidates:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return {str(p.get("id", i)): p for i, p in enumerate(data)}
            return {str(k): v for k, v in data.items()}
    return {}


@st.cache_data
def load_violations_report() -> dict[str, Any]:
    path = PROJECT_ROOT / "data" / "population" / "constraint_violations_report.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


@st.cache_data
def load_journey_results(journey_id: str) -> dict[str, Any]:
    path = PROJECT_ROOT / "data" / "population" / f"journey_{journey_id}_results.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_journey_results(journey_id: str, data: dict[str, Any]) -> None:
    """Save run results to disk and clear the cache so Results tab picks them up."""
    path = PROJECT_ROOT / "data" / "population" / f"journey_{journey_id}_results.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    load_journey_results.clear()


def _extract_journey_outcomes(result_dict: dict[str, Any]) -> dict[str, str]:
    """Build {persona_id: outcome} from journey simulation results.

    Outcome values:
      "adopt"  — bought first pack AND reordered
      "lapsed" — bought first pack but did NOT reorder
      "reject" — did not buy at all
    """
    outcomes: dict[str, str] = {}
    for log in result_dict.get("logs", []):
        if log.get("error"):
            continue
        pid = log.get("persona_id", "")
        if not pid:
            continue
        snaps = log.get("snapshots", []) or []
        first_buy = any(
            s.get("decision_result", {}).get("decision") in ("buy", "trial")
            for s in snaps
            if s.get("decision_result") and "error" not in (s.get("decision_result") or {})
        )
        reordered = bool(log.get("reordered", False))
        if first_buy:
            outcomes[pid] = "adopt" if reordered else "lapsed"
        else:
            outcomes[pid] = "reject"
    return outcomes


@st.cache_data
def parse_persona(p_dict_json: str) -> Persona | None:
    try:
        return Persona.model_validate(json.loads(p_dict_json))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

FIELD_LABELS: dict[str, str] = {
    "health_anxiety": "Health Anxiety",
    "information_need": "Information Need",
    "risk_tolerance": "Risk Tolerance",
    "analysis_paralysis_tendency": "Analysis Paralysis",
    "decision_speed": "Decision Speed",
    "social_proof_bias": "Social Proof Bias",
    "authority_bias": "Authority Bias",
    "loss_aversion": "Loss Aversion",
    "best_for_my_child_intensity": "Best-for-Child Drive",
    "supplement_necessity_belief": "Supplement Necessity Belief",
    "food_first_belief": "Food-First Belief",
    "brand_loyalty_tendency": "Brand Loyalty",
    "guilt_sensitivity": "Guilt Sensitivity",
    "budget_consciousness": "Budget Consciousness",
    "deal_seeking_intensity": "Deal Seeking",
    "digital_payment_comfort": "Digital Payment Comfort",
    "label_reading_habit": "Label Reading Habit",
    "organic_preference": "Organic Preference",
    "ayurveda_affinity": "Ayurveda Affinity",
    "western_brand_trust": "Western Brand Trust",
    "indie_brand_openness": "Indie Brand Openness",
    "peer_influence_strength": "Peer Influence",
    "influencer_trust": "Influencer Trust",
    "pediatrician_influence": "Pediatrician Influence",
    "elder_advice_weight": "Elder Advice Weight",
    "wom_transmitter_tendency": "WOM Transmitter",
    "immunity_concern": "Immunity Concern",
    "growth_concern": "Growth Concern",
    "emotional_persuasion_susceptibility": "Emotional Ad Susceptibility",
    "fear_appeal_responsiveness": "Fear Appeal Response",
    "impulse_purchase_tendency": "Impulse Purchase Tendency",
    "perceived_time_scarcity": "Perceived Time Scarcity",
}

EVENT_COLOURS: dict[str, str] = {
    "stimulus": "#3B82F6",
    "decision": "#F97316",
    "reflection": "#8B5CF6",
    "brand_touchpoint": "#10B981",
    "semantic": "#6B7280",
}


def _label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " ").title())


def _filter_by_age_band(
    all_personas: dict[str, dict], age_min: int | None, age_max: int | None
) -> dict[str, dict]:
    """Return persona subset where at least one child falls in [age_min, age_max]."""
    if age_min is None and age_max is None:
        return all_personas
    result = {}
    for pid, p in all_personas.items():
        ages: list[int] = p.get("demographics", {}).get("child_ages") or []
        lo = age_min if age_min is not None else 0
        hi = age_max if age_max is not None else 99
        if any(lo <= a <= hi for a in ages):
            result[pid] = p
    return result


# ---------------------------------------------------------------------------
# Calibration status badge (sidebar)
# ---------------------------------------------------------------------------

def _render_calibration_status_sidebar(all_personas: dict[str, dict]) -> None:
    """Show calibration status badge in sidebar."""
    try:
        from app.components.calibration_badge import render_calibration_badge
        # Read calibration status from API cohort metadata
        from src.simulatte_client import get_cohort_raw
        cal_status = None
        try:
            cohort_data = get_cohort_raw()
            cal_status = cohort_data.get("cohort", {}).get("calibration_state", {}).get("status")
        except Exception:
            pass
        with st.sidebar:
            st.markdown("**Cohort Status**")
            render_calibration_badge(cal_status)
    except Exception:
        pass  # Silent fail — badge is informational only


# ---------------------------------------------------------------------------
# Population snapshot (sidebar + home)
# ---------------------------------------------------------------------------

def _population_snapshot(all_personas: dict[str, dict]) -> dict[str, Any]:
    tiers: dict[str, int] = defaultdict(int)
    age_bands = {"2–6": 0, "7–14": 0, "both": 0}
    trust_anchors: dict[str, int] = defaultdict(int)
    price_sens: dict[str, int] = defaultdict(int)
    decision_styles: dict[str, int] = defaultdict(int)
    family_structures: dict[str, int] = defaultdict(int)
    employment_status: dict[str, int] = defaultdict(int)
    cities: set[str] = set()

    for p in all_personas.values():
        d = p.get("demographics", {})
        tiers[d.get("city_tier", "?")] += 1
        city = d.get("city_name")
        if city:
            cities.add(city)
        ages: list[int] = d.get("child_ages") or []
        has_young = any(a <= 6 for a in ages)
        has_older = any(7 <= a <= 14 for a in ages)
        if has_young and has_older:
            age_bands["both"] += 1
        elif has_young:
            age_bands["2–6"] += 1
        elif has_older:
            age_bands["7–14"] += 1
        pt = p.get("parent_traits") or {}
        ta = pt.get("trust_anchor")
        if ta:
            trust_anchors[ta] += 1
        ds = pt.get("decision_style")
        if ds:
            decision_styles[ds] += 1
        bp = p.get("budget_profile") or {}
        ps = bp.get("price_sensitivity")
        if ps:
            price_sens[ps] += 1
        fs = d.get("family_structure")
        if fs:
            family_structures[fs] += 1
        career = p.get("career", {})
        emp = career.get("employment_status") if career else None
        if emp:
            employment_status[emp] += 1

    return {
        "total": len(all_personas),
        "num_cities": len(cities),
        "tiers": dict(tiers),
        "age_bands": age_bands,
        "trust_anchors": dict(trust_anchors),
        "price_sensitivity": dict(price_sens),
        "decision_styles": dict(decision_styles),
        "family_structures": dict(family_structures),
        "employment_status": dict(employment_status),
    }


# ---------------------------------------------------------------------------
# Page: Business Problems (home)
# ---------------------------------------------------------------------------

SCENARIOS = {
    "A": {
        "title": "Nutrimix Repeat Purchase",
        "emoji": "📉",
        "problem": "Good NPS. Low reorders.",
        "question": "Why aren't parents who love the product coming back for a second pack?",
        "population": "All 200 personas — 60-day journey",
        "age_filter": (None, None),
        "journey_id": "A",
        "color": "#EF4444",
    },
    "C": {
        "title": "Nutrimix 7–14 Expansion",
        "emoji": "🎯",
        "problem": "Strong in 2–6. Invisible in 7–14.",
        "question": "How does the same Nutrimix product land with parents of older kids?",
        "population": "Personas with children aged 7–14",
        "age_filter": (7, 14),
        "journey_id": "C",
        "color": "#3B82F6",
    },
    "B": {
        "title": "Magnesium Gummies Growth",
        "emoji": "💊",
        "problem": "Great product. Near-zero awareness.",
        "question": "What triggers purchase in a category parents aren't actively seeking?",
        "population": "All 200 personas — 45-day journey",
        "age_filter": (None, None),
        "journey_id": "B",
        "color": "#10B981",
    },
}


def page_home(all_personas: dict[str, dict]) -> None:
    snap = _population_snapshot(all_personas)

    st.markdown(
        "<h1 style='font-size:2rem;font-weight:800;margin-bottom:0'>LittleJoys Persona Intelligence</h1>"
        "<p style='color:#6B7280;margin-top:4px;font-size:1.05rem'>"
        "200 psychologically grounded Indian parents — ready to answer your business questions."
        "</p>",
        unsafe_allow_html=True,
    )

    # Population at a glance — 3 clean insight tiles
    ab = snap["age_bands"]
    total = snap["total"]
    tiers = snap["tiers"]
    trust = snap["trust_anchors"]

    # Derive human-readable trust profile
    _trust_labels = {
        "self": "Independent researchers",
        "authority": "Doctor-driven",
        "peer": "Peer-influenced",
        "family": "Family-led",
    }
    trust_sorted = sorted(trust.items(), key=lambda x: -x[1])
    trust_line = "  ·  ".join(
        f"{_trust_labels.get(k, k.title())} {round(100*v/total)}%"
        for k, v in trust_sorted[:3]
    )

    # City breakdown as percentages (never truncates)
    tier_pcts = "  ·  ".join(
        f"{k} {round(100*v/total)}%" for k, v in sorted(tiers.items())
    )

    # Age mix as a readable sentence
    young = ab.get("2–6", 0)
    older = ab.get("7–14", 0)
    mixed = ab.get("both", 0)
    age_line = f"{young} under-7  ·  {older} school-age  ·  {mixed} both"

    g1, g2, g3 = st.columns(3)
    g1.metric("Population", f"{total} personas", help="Psychologically grounded Indian parents")
    g2.metric("Children covered", "Ages 2–14", help=age_line)

    # Show top trust type as a short readable label with % breakdown in tooltip
    short_labels = {"self": "Self-directed", "authority": "Doctor-driven", "peer": "Peer-led", "family": "Family-led"}
    if trust_sorted and total > 0 and len(trust_sorted[0]) >= 2:
        top_key = trust_sorted[0][0]
        top_pct = round(100 * trust_sorted[0][1] / total)
        g3.metric(
            "Dominant buyer type",
            f"{short_labels.get(top_key, top_key.title())} · {top_pct}%",
            help=f"How parents primarily make decisions:\n{trust_line}",
        )
    else:
        g3.metric("Dominant buyer type", "—")
    st.caption(f"City mix: {tier_pcts}  ·  Age mix: {age_line}")

    st.divider()
    st.subheader("Pick a Business Problem")
    st.caption("Each card runs a pre-configured simulation against the relevant persona segment.")

    cols = st.columns(3)
    for col, (sid, sc) in zip(cols, SCENARIOS.items()):
        with col:
            has_results = bool(load_journey_results(sc["journey_id"]))
            status_badge = (
                "📊 200 personas already simulated — results load instantly"
                if has_results
                else "▶️ Not yet run — click to configure and run"
            )
            status_color = "#059669" if has_results else "#D97706"

            st.markdown(
                f"""<div style="border:1px solid #E5E7EB;border-radius:12px;padding:20px;height:240px;
                    display:flex;flex-direction:column;justify-content:space-between;">
                  <div>
                    <span style="font-size:1.8rem">{sc['emoji']}</span>
                    <p style="font-weight:700;font-size:1rem;margin:8px 0 4px">{sc['title']}</p>
                    <p style="color:{sc['color']};font-weight:600;font-size:0.85rem;margin:0 0 8px">{sc['problem']}</p>
                    <p style="color:#6B7280;font-size:0.8rem;margin:0">{sc['question']}</p>
                  </div>
                  <div>
                    <p style="color:#9CA3AF;font-size:0.75rem;margin:8px 0 0">{sc['population']}</p>
                    <span style="color:{status_color};font-size:0.75rem">{status_badge}</span>
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )
            _btn_label = "See Results →" if has_results else "Run This →"
            if st.button(_btn_label, key=f"home_run_{sid}", use_container_width=True):
                st.session_state["nav_page"] = "Run Scenario"
                st.session_state["active_scenario"] = sid
                st.rerun()

    st.divider()

    # Open-ended question entry point
    st.subheader("Ask the Population")
    st.caption(
        "Ask any business question. The engine will probe your 200 personas and "
        "return a data-grounded answer — or propose a simulation to run."
    )
    q = st.text_input(
        "Your question",
        placeholder="e.g. What % of Tier 2 moms trust doctors over influencers?",
        key="home_question_input",
        label_visibility="collapsed",
    )
    col_ask, col_eg = st.columns([2, 3])
    with col_ask:
        if st.button("Ask the population →", type="primary", use_container_width=True):
            if q.strip():
                st.session_state["pending_question"] = q.strip()
                st.session_state["nav_page"] = "Ask the Population"
                st.rerun()
    with col_eg:
        with st.expander("Example questions"):
            examples = [
                "What % of Tier 2 moms trust doctors over influencers?",
                "Which decision style is most common among price-sensitive parents?",
                "How would adding a free-sample campaign affect Magnesium Gummies trial rate?",
                "What if we cut Nutrimix price to Rs 499 for the 7-14 segment?",
                "Which personas are most likely to lapse after first Nutrimix purchase?",
            ]
            for eg in examples:
                if st.button(eg, key=f"eg_{eg[:20]}", use_container_width=True):
                    st.session_state["pending_question"] = eg
                    st.session_state["nav_page"] = "Ask the Population"
                    st.rerun()


# ---------------------------------------------------------------------------
# Reason thematizer — collapses LLM-generated reason variants into themes
# ---------------------------------------------------------------------------

def _pre_cluster_reasons(raw: dict[str, int]) -> dict[str, int]:
    """Python-only prefix clustering — collapses obvious snake_case variants before LLM.

    Groups entries that share the same first 3 significant words (after normalising
    snake_case → space-separated). Keeps the shortest label per cluster.
    This handles the common case where the LLM emits e.g.
      no_discount_this_time / no_discount_this_time_slight_hesitation /
      no_discount_this_time_slightly_disappointing  →  all become one entry.
    """
    from collections import defaultdict

    def _sig_words(s: str, n: int = 3) -> str:
        tokens = s.lower().replace("_", " ").split()
        # Skip filler tokens so "a_bit_expensive" and "slightly_expensive" share "expensive"
        _skip = {"a", "an", "the", "this", "that", "slightly", "slight", "bit", "little",
                 "very", "quite", "some", "somewhat", "but", "not", "is", "its", "of"}
        sig = [t for t in tokens if t not in _skip]
        return " ".join(sig[:n])

    clusters: dict[str, int] = defaultdict(int)      # prefix_key → total count
    labels: dict[str, str] = {}                       # prefix_key → best label

    for key, count in raw.items():
        pk = _sig_words(key)
        clusters[pk] += count
        # Prefer the shortest / cleanest label (no trailing qualifier noise)
        if pk not in labels or len(key) < len(labels[pk]):
            labels[pk] = key

    return {labels[pk]: count for pk, count in clusters.items()}


def _humanise_reason(s: str) -> str:
    """Convert a snake_case or short reason string to a human-readable label."""
    return s.replace("_", " ").strip().capitalize()


def _thematize_reasons(raw: dict[str, int], label: str, cache_key: str) -> tuple[dict[str, int], bool]:
    """Collapse semantically similar reason strings into clean themes.

    Two-stage pipeline:
      1. Python prefix clustering — collapses obvious snake_case duplicates instantly.
      2. Claude Haiku LLM call — produces clean 2–4 word Title Case theme names
         from the pre-clustered entries (only called when ≥3 distinct clusters remain).

    Returns (thematized_dict, used_llm). Falls back to pre-clustered or raw on error.
    Caches in session_state so repeated renders don't re-call the API.
    """
    if not raw:
        return raw, False

    # Stage 1: Python prefix clustering (no API call needed)
    pre = _pre_cluster_reasons(raw)

    # v4 prefix busts caches from earlier prompt versions
    state_key = f"_thematized_v4_{cache_key}_{hash(frozenset(pre.items()))}"
    if state_key in st.session_state:
        return st.session_state[state_key], True

    # If pre-clustering already reduced to ≤2 distinct themes, humanise labels and done
    if len(pre) <= 2:
        result = {_humanise_reason(k): v for k, v in sorted(pre.items(), key=lambda x: -x[1])}
        st.session_state[state_key] = result
        return result, False

    # Stage 2: LLM collapse of remaining clusters into ≤4 clean themes
    try:
        import os, re as _re
        import anthropic as _anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            result = {_humanise_reason(k): v for k, v in sorted(pre.items(), key=lambda x: -x[1])}
            return result, False

        items_text = "\n".join(
            f'- "{_humanise_reason(k)}": {v} personas'
            for k, v in sorted(pre.items(), key=lambda x: -x[1])
        )
        prompt = (
            f"You are collating consumer research output. Collapse these {label} into at most 4 distinct themes.\n\n"
            "STRICT RULES — follow exactly:\n"
            "1. Be AGGRESSIVE about merging. Same underlying concern = ONE theme — regardless of wording.\n"
            "2. Sum the persona counts of merged entries.\n"
            "3. Use short, plain theme names: 2–4 words, Title Case (e.g. 'Price Too High', 'No Visible Results').\n"
            "4. Maximum 4 themes. If all entries are variants of the same idea, return exactly 1 theme.\n"
            "5. Return ONLY a JSON object: {\"Theme Name\": count, ...} — no markdown, no explanation.\n\n"
            f"Entries:\n{items_text}\n\nMerge aggressively. Fewer themes is better."
        )

        client = _anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        text = _re.sub(r"^```[a-z]*\n?", "", text)
        text = _re.sub(r"\n?```$", "", text)
        result = dict(sorted(json.loads(text).items(), key=lambda x: -x[1]))
        st.session_state[state_key] = result
        return result, True

    except Exception:
        # LLM failed — return humanised pre-clustered result (still much better than raw)
        result = {_humanise_reason(k): v for k, v in sorted(pre.items(), key=lambda x: -x[1])}
        st.session_state[state_key] = result
        return result, False


# ---------------------------------------------------------------------------
# Page: Run Scenario
# ---------------------------------------------------------------------------

def _render_results_panel(data: dict[str, Any], journey_id: str) -> None:
    """Render pre-loaded or freshly-run simulation results in business language."""
    aggregate = data.get("aggregate", {}) or {}
    logs = data.get("logs", []) or []

    first_dist = aggregate.get("first_decision_distribution", {}) or {}
    buy_pct = float(first_dist.get("buy", {}).get("pct", 0) or 0) + float(
        first_dist.get("trial", {}).get("pct", 0) or 0
    )
    # LP Pass = % who moved past initial rejection — reached trial/buy/research_more
    lp_pass_pct = buy_pct + float(first_dist.get("research_more", {}).get("pct", 0) or 0)
    reorder_pct = float(aggregate.get("reorder_rate_pct", 0) or 0)
    drop_off = round(buy_pct - reorder_pct, 1)

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Personas Simulated", data.get("total_personas", len(logs)))
    r2.metric("Engagement Rate", f"{lp_pass_pct:.1f}%", help="Personas who trialled, bought, or wanted to research further — did not immediately reject or defer")
    r3.metric("First Purchase", f"{buy_pct:.1f}%", help="Buy + trial at the first decision point")
    drop_delta = f"−{drop_off:.1f}pp vs baseline" if drop_off > 0 else f"+{abs(drop_off):.1f}pp vs baseline"
    r4.metric(
        "Reorder Rate",
        f"{reorder_pct:.1f}%",
        delta=drop_delta,
        delta_color="inverse" if drop_off > 0 else "normal",
        help="% of first-time buyers who reordered. Simulation reflects ideal-scenario engagement — real-world rates typically 20-40pp lower.",
    )
    result_errors = aggregate.get("errors", 0)
    if result_errors > 0:
        st.warning(f"⚠ {result_errors} simulation error(s) — some personas may not have completed the full journey.")

    st.divider()

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("What drives repurchase")
        _raw_drivers = (aggregate.get("second_decision_drivers") or {})
        drivers_themed, drivers_used_llm = _thematize_reasons(
            _raw_drivers, "purchase drivers", f"drivers_{journey_id}"
        )
        drivers = list(drivers_themed.items())[:5]
        if drivers:
            max_count = max(c for _, c in drivers) if drivers else 1
            for driver, count in drivers:
                label = driver.replace("_", " ").title()
                bar_pct = int(100 * count / max_count)
                st.markdown(
                    f"<div style='margin-bottom:6px'>"
                    f"<span style='font-size:0.85rem;font-weight:600'>{label}</span>"
                    f"<div style='background:#E5E7EB;border-radius:4px;height:8px;margin-top:3px'>"
                    f"<div style='background:#3B82F6;width:{bar_pct}%;height:8px;border-radius:4px'></div>"
                    f"</div>"
                    f"<span style='color:#6B7280;font-size:0.75rem'>{count} personas</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No driver data available.")
        if drivers_used_llm:
            st.caption("Thematized by AI · similar reasons combined")

    with col_r:
        st.subheader("Why some don't come back")
        _raw_obj = (aggregate.get("second_decision_objections") or {})
        obj_themed, obj_used_llm = _thematize_reasons(
            _raw_obj, "lapse objections", f"objections_{journey_id}"
        )
        objections = list(obj_themed.items())[:5]
        if objections:
            max_count = max(c for _, c in objections) if objections else 1
            for obj, count in objections:
                label = obj.replace("_", " ").title()
                bar_pct = int(100 * count / max_count)
                st.markdown(
                    f"<div style='margin-bottom:6px'>"
                    f"<span style='font-size:0.85rem;font-weight:600'>{label}</span>"
                    f"<div style='background:#E5E7EB;border-radius:4px;height:8px;margin-top:3px'>"
                    f"<div style='background:#EF4444;width:{bar_pct}%;height:8px;border-radius:4px'></div>"
                    f"</div>"
                    f"<span style='color:#6B7280;font-size:0.75rem'>{count} personas</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No objection data available.")
        if obj_used_llm:
            st.caption("Thematized by AI · similar reasons combined")

    st.divider()

    # Brand trust trajectory
    trust_by_tick = aggregate.get("trust_by_tick", {}) or {}
    if trust_by_tick:
        st.subheader("Brand trust over time")
        trust_df = pd.DataFrame(
            [{"Day": int(t), "Mean Trust": round(float(v), 4)}
             for t, v in sorted(trust_by_tick.items(), key=lambda x: int(x[0]))]
        )
        st.line_chart(trust_df.set_index("Day"), use_container_width=True)
        st.caption("Population mean brand trust — 0.0 (none) to 1.0 (full). Tracks across all 200 simulation days.")
    else:
        st.info("Brand trust trajectory not available for this journey.")

    st.divider()

    # Per-persona drill-down
    if logs:
        st.subheader("Who reorders — who lapses")
        rows: list[dict] = []
        for log in logs:
            if log.get("error"):
                continue
            snaps = log.get("snapshots", []) or []
            # Derive the first decision from snapshots (earliest decision-bearing snapshot)
            first_dec = "—"
            reorder_dec = "—"
            dec_snaps = [
                s for s in snaps
                if s.get("decision_result")
                and isinstance(s.get("decision_result"), dict)
                and "error" not in s["decision_result"]
            ]
            dec_snaps_sorted = sorted(dec_snaps, key=lambda s: s.get("tick", 0))
            if dec_snaps_sorted:
                first_dec = str(dec_snaps_sorted[0]["decision_result"].get("decision", "—"))
            if len(dec_snaps_sorted) > 1:
                reorder_dec = str(dec_snaps_sorted[-1]["decision_result"].get("decision", "—"))
            elif len(dec_snaps_sorted) == 1:
                # Only one decision captured — reorder decision silently errored
                reorder_dec = "error / not captured"
            last_trust = 0.0
            if snaps:
                brand_trust = snaps[-1].get("brand_trust", {}) or {}
                last_trust = max(brand_trust.values()) if brand_trust else 0.0
            reordered = log.get("reordered", False)
            rows.append({
                "Persona": log.get("display_name", log.get("persona_id", "?")),
                "Outcome": "✅ Reordered" if reordered else "❌ Lapsed",
                "Trial Decision": first_dec,
                "Reorder Decision": reorder_dec,
                "Brand Trust": round(float(last_trust), 3),
                "Memories": int((snaps[-1].get("memories_count", 0) if snaps else 0)),
            })

        if rows:
            df = pd.DataFrame(rows)

            f1, f2 = st.columns(2)
            show = f1.selectbox("Filter by outcome", ["All", "✅ Reordered", "❌ Lapsed"], key="scenario_outcome_filter")
            trial_opts = sorted(df["Trial Decision"].unique().tolist())
            trial_filter = f2.selectbox("Filter by trial decision", ["all", *trial_opts], key="scenario_decision_filter")

            if show == "✅ Reordered":
                df = df[df["Outcome"] == "✅ Reordered"]
            elif show == "❌ Lapsed":
                df = df[df["Outcome"] == "❌ Lapsed"]
            if trial_filter != "all":
                df = df[df["Trial Decision"] == trial_filter]

            # Single table with row-selection (Styler + selection_mode is not compatible in Streamlit)
            selection = st.dataframe(
                df.reset_index(drop=True),
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun",
                key="persona_table_select",
                hide_index=True,
                column_config={
                    "Outcome": st.column_config.TextColumn("Outcome", width="small"),
                    "Trial Decision": st.column_config.TextColumn("Trial (1st)", help="What the persona decided at the first purchase moment"),
                    "Reorder Decision": st.column_config.TextColumn("Reorder (2nd)", help="What the persona decided when given the chance to reorder"),
                    "Brand Trust": st.column_config.NumberColumn("Brand Trust", format="%.3f"),
                    "Memories": st.column_config.NumberColumn("Memories", help="Episodic memories accumulated by end of journey"),
                },
            )
            st.caption(f"{len(df)} personas shown — click a row to see full decision reasoning.")
            sel_rows = (selection.selection or {}).get("rows", [])
            if sel_rows:
                sel_persona = df.iloc[sel_rows[0]]["Persona"]
                sel_log = next((l for l in logs if (l.get("display_name") or l.get("persona_id")) == sel_persona), None)
                if sel_log:
                    with st.expander(f"Decision detail — {sel_persona}", expanded=True):
                        snaps = sel_log.get("snapshots", []) or []
                        dps = [s for s in snaps if s.get("decision_result") and "error" not in (s.get("decision_result") or {})]
                        for snap in dps:
                            dr = snap["decision_result"]
                            conf = float(dr.get("confidence", 0) or 0)
                            st.markdown(f"**Day {snap.get('tick')}: {dr.get('decision','?')}** (confidence {conf:.0%})")
                            for step in (dr.get("reasoning_trace") or [])[:3]:
                                st.caption(f"  {step}")
                            if dr.get("key_drivers"):
                                st.caption("Drivers: " + ", ".join(str(d) for d in dr["key_drivers"][:3]))
                            if dr.get("objections"):
                                st.caption("Objections: " + ", ".join(str(o) for o in dr["objections"][:3]))

        # Persona tick-by-tick drill-down
        persona_ids = [log.get("persona_id") for log in logs if not log.get("error")]
        if persona_ids:
            with st.expander("Individual persona deep-dive"):
                sel_pid = st.selectbox("Select persona", options=persona_ids, key="scenario_drilldown")
                sel_log = next((l for l in logs if l.get("persona_id") == sel_pid), None)
                if sel_log:
                    snaps = sel_log.get("snapshots", []) or []
                    if snaps:
                        trust_rows = []
                        for snap in snaps:
                            for brand, trust in (snap.get("brand_trust", {}) or {}).items():
                                trust_rows.append({"Day": snap.get("tick"), "Brand": brand, "Trust": trust})
                        if trust_rows:
                            pivot = pd.DataFrame(trust_rows).pivot_table(
                                index="Day", columns="Brand", values="Trust", aggfunc="first"
                            )
                            st.line_chart(pivot)
                    dps = [s for s in snaps if s.get("decision_result")]
                    for snap in dps:
                        dr = snap.get("decision_result") or {}
                        if "error" not in dr:
                            conf = float(dr.get("confidence", 0) or 0)
                            st.write(
                                f"Day {snap.get('tick')}: **{dr.get('decision','?')}** "
                                f"(confidence: {conf:.0%})"
                            )


def page_run_scenario(all_personas: dict[str, dict]) -> None:
    sid = st.session_state.get("active_scenario", "A")
    sc = SCENARIOS.get(sid, SCENARIOS["A"])

    st.markdown(
        f"<h2 style='font-size:1.6rem;font-weight:800'>{sc['emoji']} {sc['title']}</h2>"
        f"<p style='color:{sc['color']};font-weight:600;margin-top:-8px'>{sc['problem']}</p>"
        f"<p style='color:#4B5563'>{sc['question']}</p>",
        unsafe_allow_html=True,
    )

    # Scenario selector
    sc_labels = {k: f"{v['emoji']} {v['title']}" for k, v in SCENARIOS.items()}
    chosen = st.radio(
        "Scenario",
        options=list(sc_labels.keys()),
        format_func=lambda k: sc_labels[k],
        horizontal=True,
        index=list(SCENARIOS.keys()).index(sid),
        key="scenario_radio",
    )
    if chosen != sid:
        st.session_state["active_scenario"] = chosen
        st.rerun()

    # Population filter for this scenario
    age_min, age_max = sc["age_filter"]
    filtered_personas = _filter_by_age_band(all_personas, age_min, age_max)
    n_filtered = len(filtered_personas)

    if age_min is not None or age_max is not None:
        if n_filtered == 0:
            st.warning(
                "⚠️ No personas matched the age filter for this scenario. "
                "Child age data may still be loading — try refreshing in a moment.",
                icon="⚠️",
            )
        else:
            st.info(
                f"Running against **{n_filtered} personas** with children aged {age_min}–{age_max}",
                icon="👥",
            )
    else:
        st.info(
            f"Running against **{n_filtered} personas** ({sc['population']})",
            icon="👥",
        )

    _jid = sc["journey_id"]
    _has_results = bool(
        st.session_state.get(f"last_run_{_jid}") or load_journey_results(_jid)
    )

    tab_results, tab_builder = st.tabs(["Results", "Configure & Run"])

    with tab_results:
        # Check in-memory run first (from Tweak & Compare tab), then fall back to file
        jid = sc["journey_id"]
        from_session = bool(st.session_state.get(f"last_run_{jid}"))
        data = (
            st.session_state.get(f"last_run_{jid}")
            or load_journey_results(jid)
        )
        if data:
            if not from_session:
                st.info(
                    "📊 **Pre-loaded results** — these are the base journey results run on "
                    "the standard stimulus sequence. Head to **Configure & Run** to adjust "
                    "price, channels, or stimuli and re-run."
                )
            _render_results_panel(data, jid)
            # Cross-page bridge → Investigate
            _problem_map = {
                "A": "repeat_purchase_low",
                "B": "magnesium_gummies_growth",
                "C": "nutrimix_7_14_expansion",
            }
            if jid in _problem_map:
                st.divider()
                outcomes = _extract_journey_outcomes(data)
                adopters = sum(1 for v in outcomes.values() if v == "adopt")
                lapsed = sum(1 for v in outcomes.values() if v == "lapsed")
                rejectors = sum(1 for v in outcomes.values() if v == "reject")
                st.caption(
                    f"Cohort breakdown — {adopters} reordered · {lapsed} lapsed · "
                    f"{rejectors} didn't buy"
                )
                if st.button(
                    "🔬 Investigate these results →",
                    key=f"investigate_link_{jid}",
                    help="Open the Investigate page pre-loaded with this journey's cohort segments",
                ):
                    st.session_state["investigate_problem_id"] = _problem_map[jid]
                    st.session_state["investigate_journey_id"] = jid
                    st.session_state["nav_page"] = "Investigate"
                    st.rerun()
        else:
            st.info(
                "▶️ **No simulation results yet.**\n\n"
                "Switch to the **Configure & Run** tab to configure the stimulus sequence, "
                "set a price, choose your channels, and click **Run Simulation**."
            )

    with tab_builder:
        if not _has_results:
            st.info(
                "This scenario has pre-configured stimuli — click **Run Simulation** below "
                "to see results, or adjust the parameters first."
            )
        page_simulation_builder_inline(filtered_personas, sc["journey_id"])


# ---------------------------------------------------------------------------
# Simulation Builder (inline, called from Run Scenario)
# ---------------------------------------------------------------------------

def page_simulation_builder_inline(
    all_personas: dict[str, dict], default_journey_id: str = "A"
) -> None:
    presets = list_presets()
    preset_labels = {"A": "A — Nutrimix Repeat Purchase", "B": "B — Magnesium Gummies", "C": "C — Nutrimix 7–14 Expansion"}

    col_preset, col_pop = st.columns([2, 1])
    # Key is scenario-specific so builder state doesn't bleed between scenarios
    jid = col_preset.selectbox(
        "Base journey",
        options=list(preset_labels.keys()),
        format_func=lambda k: preset_labels[k],
        index=list(preset_labels.keys()).index(default_journey_id),
        key=f"builder_journey_select_{default_journey_id}",
    )
    base_config = presets[jid]
    population_size = col_pop.slider("Population size", 10, 200, min(200, len(all_personas)), step=10)

    st.divider()
    st.subheader("Product & Channels")
    _channel_labels = {
        "bigbasket": "BigBasket", "blinkit": "Blinkit (10-min)", "zepto": "Zepto",
        "swiggy_instamart": "Swiggy Instamart", "firstcry_online": "FirstCry Online",
        "amazon": "Amazon", "d2c": "D2C Website", "pharmacy": "Pharmacy",
        "hospital_pharmacy": "Hospital Pharmacy", "dmart": "D-Mart / Big Bazaar",
        "kirana_local": "Kirana / Local Store", "modern_trade": "Modern Trade",
    }
    col1, col2 = st.columns([1, 2])
    price = col1.slider("Price (Rs)", 200, 1500, int(base_config.decisions[0].price_inr), step=50)
    cur_ch = base_config.decisions[0].channel
    channels = col2.multiselect(
        "Purchase channel(s) — select all that apply",
        options=list(_channel_labels.keys()),
        default=[cur_ch] if cur_ch in _channel_labels else ["bigbasket"],
        format_func=lambda k: _channel_labels.get(k, k),
        key=f"builder_channels_{default_journey_id}",
    )
    if not channels:
        channels = [cur_ch if cur_ch in _channel_labels else "bigbasket"]
    # Primary channel used in JourneyConfig decisions
    channel = channels[0]

    st.divider()
    st.subheader("Awareness Channels")
    st.caption("All channels through which personas can encounter the brand")
    _awareness_opts = {
        "pediatrician": "Paediatrician endorsement",
        "instagram_influencer": "Instagram / YouTube influencer",
        "whatsapp_friend": "WhatsApp peer WOM",
        "tv_ad": "TV / OTT ad",
        "facebook_ad": "Facebook / Instagram feed ad",
        "google_search": "Google Search / YouTube pre-roll",
        "school_event": "School / PTA event",
        "print_ad": "Print (newspaper / magazine)",
    }
    _base_awareness = set()
    for _s in base_config.stimuli:
        for _k in _awareness_opts:
            if _k in _s.source:
                _base_awareness.add(_k)
    selected_awareness = st.multiselect(
        "Awareness channels",
        options=list(_awareness_opts.keys()),
        default=sorted(_base_awareness) or ["pediatrician", "instagram_influencer", "whatsapp_friend"],
        format_func=lambda k: _awareness_opts.get(k, k),
        key=f"builder_awareness_{default_journey_id}",
        label_visibility="collapsed",
    )

    st.divider()
    st.subheader("Campaigns")
    st.caption("Promotional and activation campaigns layered on top of awareness")
    _campaign_opts = {
        "free_sample": "Free sample / trial sachet",
        "cashback_offer": "Discount / cashback (15%+)",
        "subscription_bundle": "Subscription bundle (3-month deal)",
        "school_sampling": "School / community sampling event",
        "instore_demo": "In-store demo / display stand",
        "loyalty_program": "Loyalty program entry reward",
        "doctor_gift": "Paediatrician office gifting / placement",
        "referral_reward": "Referral reward (₹100 for friend signup)",
    }
    _base_campaigns: set[str] = set()
    for _s in base_config.stimuli:
        for _k in _campaign_opts:
            if _k in _s.source:
                _base_campaigns.add(_k)
    selected_campaigns = st.multiselect(
        "Active campaigns",
        options=list(_campaign_opts.keys()),
        default=sorted(_base_campaigns),
        format_func=lambda k: _campaign_opts.get(k, k),
        key=f"builder_campaigns_{default_journey_id}",
        label_visibility="collapsed",
    )

    # Derive flags used by stimulus injection logic
    has_ped = "pediatrician" in selected_awareness
    has_inf = "instagram_influencer" in selected_awareness
    has_wom = "whatsapp_friend" in selected_awareness
    has_tv = "tv_ad" in selected_awareness
    has_sampling = "free_sample" in selected_campaigns
    has_cashback = "cashback_offer" in selected_campaigns
    has_facebook = "facebook_ad" in selected_awareness
    has_google = "google_search" in selected_awareness
    has_school_event = "school_event" in selected_awareness or "school_sampling" in selected_campaigns
    has_subscription = "subscription_bundle" in selected_campaigns
    has_loyalty = "loyalty_program" in selected_campaigns

    # Compute preview stim_rows from current toggle state so the table stays in sync
    _first_tick = base_config.decisions[0].tick if base_config.decisions else 20
    _early = max(1, _first_tick - 14)
    _mid = max(2, _first_tick - 7)
    _brand = base_config.primary_brand
    _existing_srcs: set[str] = set()
    _preview_rows: list[dict] = []
    for _s in base_config.stimuli:
        _src = _s.source
        if not has_ped and _src in ("pediatrician", "pediatrician_followup"):
            continue
        if not has_inf and "influencer" in _src:
            continue
        if not has_wom and "whatsapp" in _src:
            continue
        if not has_tv and _src in ("tv_ad", "ott_ad", "youtube_ad"):
            continue
        if not has_sampling and _src in ("free_sample", "trial_kit", "sampling_event"):
            continue
        if not has_cashback and _src in ("cashback_offer", "coupon", "discount_ad"):
            continue
        _preview_rows.append({"tick": _s.tick, "type": _s.type, "source": _src, "content": _s.content})
        _existing_srcs.add(_src)
    # Inject newly-enabled channels not already in the base
    _injections: list[tuple[int, str, str, str]] = []
    if has_ped and "pediatrician" not in _existing_srcs:
        _injections.append((_early, "social_event", "pediatrician", "At routine checkup, paediatrician mentions child nutrition gaps and recommends a paediatric drink mix."))
    if has_inf and not any("influencer" in _x for _x in _existing_srcs):
        _injections.append((_mid, "ad", "instagram_influencer", f"Parenting influencer (450K followers) reviews {_brand} — highlights taste, clean ingredients, child's improved energy."))
    if has_wom and not any("whatsapp" in _x for _x in _existing_srcs):
        _injections.append((_early + 2, "wom", "whatsapp_friend", f"Close friend: 'We've been using {_brand} for 3 weeks, my daughter loves it and is eating better.'"))
    if has_tv and "tv_ad" not in _existing_srcs:
        _injections.append((_early, "ad", "tv_ad", f"TV commercial prime-time: {_brand} — 'Complete nutrition for growing children'."))
    if has_facebook and "facebook_ad" not in _existing_srcs:
        _injections.append((_early + 1, "ad", "facebook_ad", f"Facebook carousel ad: {_brand} — mother testimonial, ingredient highlights, shop link."))
    if has_google and "google_search" not in _existing_srcs:
        _injections.append((_mid - 2, "ad", "google_search", f"Google search ad: '{_brand} children nutrition' — parent clicked after searching 'best health drink for kids'."))
    if has_school_event and "school_event" not in _existing_srcs:
        _injections.append((_early + 3, "social_event", "school_event", f"School PTA meeting: {_brand} stall — free sample sachets distributed, nutritionist Q&A."))
    if has_sampling and "free_sample" not in _existing_srcs:
        _injections.append((_early + 1, "product", "free_sample", f"Free trial sachet of {_brand} arrived via sampling. Child tries it at breakfast."))
    if has_cashback and "cashback_offer" not in _existing_srcs:
        _injections.append((_mid - 1, "price_change", "cashback_offer", f"Limited offer: Buy {_brand} and get 15% cashback via Paytm + free delivery."))
    if has_subscription and "subscription_bundle" not in _existing_srcs:
        _injections.append((_mid, "price_change", "subscription_bundle", f"Subscribe & save: {_brand} 3-month bundle at ₹1,799 (save ₹300) with auto-delivery."))
    if has_loyalty and "loyalty_program" not in _existing_srcs:
        _injections.append((_mid + 2, "social_event", "loyalty_program", f"You've earned 150 LittleJoys points — redeem for a free sachet pack or ₹50 discount."))
    for _tick, _type, _src, _content in _injections:
        _preview_rows.append({"tick": _tick, "type": _type, "source": _src, "content": _content})
        _existing_srcs.add(_src)
    _preview_rows.sort(key=lambda _r: _r["tick"])

    # Toggle-state hash used to reset the data editor when mix changes
    _mix_hash = abs(hash((tuple(sorted(selected_awareness)), tuple(sorted(selected_campaigns)), tuple(sorted(channels)))))

    st.divider()
    st.subheader("Stimulus Sequence")
    st.caption("Reflects your current mix selection. Edit cells or add rows to customise further.")
    edited_stim = st.data_editor(
        pd.DataFrame(_preview_rows) if _preview_rows else pd.DataFrame(columns=["tick", "type", "source", "content"]),
        use_container_width=True,
        num_rows="dynamic",
        key=f"builder_stim_editor_{default_journey_id}_{_mix_hash}",
        column_config={
            "tick": st.column_config.NumberColumn("Day", min_value=0, max_value=200),
            "type": st.column_config.SelectboxColumn(
                "Type", options=["ad", "wom", "price_change", "social_event", "product"]
            ),
            "source": st.column_config.TextColumn("Source"),
            "content": st.column_config.TextColumn("Content", width="large"),
        },
    )

    def _build_config() -> JourneyConfig:
        new_stimuli: list[StimulusConfig] = []
        first_decision_tick = base_config.decisions[0].tick if base_config.decisions else 20

        # --- filter existing stimuli based on toggle state ---
        for i, row in edited_stim.iterrows():
            src = str(row.get("source", ""))
            # Filter out stimuli for disabled channels
            if not has_ped and src in ("pediatrician", "pediatrician_followup"):
                continue
            if not has_inf and "influencer" in src:
                continue
            if not has_wom and "whatsapp" in src:
                continue
            if not has_tv and src in ("tv_ad", "ott_ad", "youtube_ad"):
                continue
            if not has_facebook and src == "facebook_ad":
                continue
            if not has_google and src == "google_search":
                continue
            if not has_school_event and src in ("school_event", "school_sampling"):
                continue
            if not has_sampling and src in ("free_sample", "trial_kit", "sampling_event"):
                continue
            if not has_cashback and src in ("cashback_offer", "coupon", "discount_ad"):
                continue
            if not has_subscription and src == "subscription_bundle":
                continue
            if not has_loyalty and src == "loyalty_program":
                continue
            new_stimuli.append(StimulusConfig(
                id=f"custom-{i}",
                tick=int(row.get("tick", 0)),
                type=str(row.get("type", "ad")),
                source=src,
                content=str(row.get("content", "")),
            ))

        existing_sources = {s.source for s in new_stimuli}
        _brand = base_config.primary_brand
        early_tick = max(1, first_decision_tick - 14)
        mid_tick = max(2, first_decision_tick - 7)

        # Inject stimuli for newly-enabled channels not yet in the sequence
        _to_inject = []
        if has_ped and "pediatrician" not in existing_sources:
            _to_inject.append((early_tick, "social_event", "pediatrician", "At routine checkup, paediatrician recommends considering a paediatric drink mix for nutrition gaps.", "inject-ped"))
        if has_inf and not any("influencer" in s for s in existing_sources):
            _to_inject.append((mid_tick, "ad", "instagram_influencer", f"Parenting influencer (450K followers) reviews {_brand} — taste, clean ingredients, child's improved energy.", "inject-inf"))
        if has_wom and not any("whatsapp" in s for s in existing_sources):
            _to_inject.append((early_tick + 2, "wom", "whatsapp_friend", f"Close friend: 'We've used {_brand} for 3 weeks, my daughter loves it and eats better.'", "inject-wom"))
        if has_tv and "tv_ad" not in existing_sources:
            _to_inject.append((early_tick, "ad", "tv_ad", f"TV commercial: {_brand} — 'Complete nutrition for growing children'.", "inject-tv"))
        if has_facebook and "facebook_ad" not in existing_sources:
            _to_inject.append((early_tick + 1, "ad", "facebook_ad", f"Facebook carousel ad: {_brand} — mother testimonial, ingredient highlights, shop link.", "inject-fb"))
        if has_google and "google_search" not in existing_sources:
            _to_inject.append((mid_tick - 2, "ad", "google_search", f"Google search ad: parent searching 'best health drink for kids' clicks {_brand} result.", "inject-gg"))
        if has_school_event and "school_event" not in existing_sources:
            _to_inject.append((early_tick + 3, "social_event", "school_event", f"School PTA: {_brand} stall with free sachets and nutritionist Q&A.", "inject-school"))
        if has_sampling and "free_sample" not in existing_sources:
            _to_inject.append((early_tick + 1, "product", "free_sample", f"Free trial sachet of {_brand} arrived. Child tries it at breakfast.", "inject-sample"))
        if has_cashback and "cashback_offer" not in existing_sources:
            _to_inject.append((mid_tick - 1, "price_change", "cashback_offer", f"Limited: Buy {_brand} and get 15% cashback via Paytm + free delivery.", "inject-cashback"))
        if has_subscription and "subscription_bundle" not in existing_sources:
            _to_inject.append((mid_tick, "price_change", "subscription_bundle", f"Subscribe & save: {_brand} 3-month bundle ₹1,799 (save ₹300) with auto-delivery.", "inject-sub"))
        if has_loyalty and "loyalty_program" not in existing_sources:
            _to_inject.append((mid_tick + 2, "social_event", "loyalty_program", f"You've earned 150 LittleJoys points — redeem for a free sachet or ₹50 off.", "inject-loyalty"))
        for _tick, _type, _src, _content, _id in _to_inject:
            new_stimuli.append(StimulusConfig(id=_id, tick=_tick, type=_type, source=_src, content=_content, brand=_brand))

        new_stimuli.sort(key=lambda s: s.tick)
        new_decisions = [
            d.model_copy(update={"price_inr": price, "channel": channel})
            for d in base_config.decisions
        ]
        return JourneyConfig(
            journey_id=jid,
            total_ticks=base_config.total_ticks,
            primary_brand=base_config.primary_brand,
            stimuli=new_stimuli,
            decisions=new_decisions,
        )

    st.divider()
    tier = st.radio(
        "Simulation tier",
        options=["SIGNAL", "DEEP", "VOLUME"],
        index=0,
        horizontal=True,
        help="DEEP: full cognitive loop (most accurate, slowest) | SIGNAL: balanced | VOLUME: fast screening",
    )
    tier_str = tier.lower()
    col_run, col_sa, col_sb = st.columns([2, 1, 1])
    run_clicked = col_run.button("Run Simulation", type="primary", use_container_width=True)
    save_a = col_sa.button("Save as Scenario A", use_container_width=True)
    save_b = col_sb.button("Save as Scenario B", use_container_width=True)

    if save_a:
        st.session_state["scenario_a_config"] = _build_config().model_dump()
        st.success("Saved as Scenario A")
    if save_b:
        st.session_state["scenario_b_config"] = _build_config().model_dump()
        st.success("Saved as Scenario B")

    if run_clicked:
        config = _build_config()
        valid: list[tuple[str, Persona]] = []
        for pid, p_dict in list(all_personas.items())[:population_size]:
            persona = parse_persona(json.dumps(p_dict))
            if persona is not None:
                valid.append((pid, persona))

        if not valid:
            st.error("No valid personas loaded.")
            return

        progress = st.progress(0, text="Starting simulation...")

        def _cb(done: int, total: int, log_dict: dict) -> None:
            pct = done / max(total, 1)
            name = log_dict.get("display_name") or log_dict.get("persona_id") or "?"
            progress.progress(pct, text=f"[{done}/{total}] {name}")

        with st.spinner(f"Running journey {jid} across {len(valid)} personas..."):
            # Simulation always runs locally via LittleJoys' own engine.
            # (Simulatte cognitive loop migration is Phase 2.)
            result = run_batch(
                journey_config=config,
                personas=valid,
                concurrency=5,
                progress_callback=_cb,
            )

        progress.progress(1.0, text=f"Done — {result.personas_run} personas in {result.elapsed_seconds:.0f}s")
        result_dict = result.to_dict()
        st.session_state[f"last_run_{jid}"] = result_dict
        # Persist to disk so the Results tab can read it even after page switches
        _save_journey_results(jid, result_dict)

        agg = result.aggregate
        first_dist = agg.first_decision_distribution
        buy_pct = float(first_dist.get("buy", {}).get("pct", 0) or 0) + float(
            first_dist.get("trial", {}).get("pct", 0) or 0
        )
        st.divider()
        st.subheader("Results")
        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Personas Run", result.personas_run)
        rc2.metric("Errors", result.errors)
        rc3.metric("Buy + Trial", f"{buy_pct:.1f}%")
        rc4.metric("Reorder Rate", f"{agg.reorder_rate_pct:.1f}%")

        st.write("**First decision distribution:**")
        for dec, stats in sorted(first_dist.items(), key=lambda x: -x[1].get("count", 0)):
            pct = float(stats.get("pct", 0) or 0)
            count = int(stats.get("count", 0) or 0)
            st.write(f"- **{dec}**: {count} ({pct:.1f}%)")

        st.write("**Top reorder drivers:**")
        for driver, count in list(agg.second_decision_drivers.items())[:5]:
            st.write(f"- {driver.replace('_', ' ').title()}: {count}")

        st.write("**Top lapse objections:**")
        for obj, count in list(agg.second_decision_objections.items())[:5]:
            st.write(f"- {obj.replace('_', ' ').title()}: {count}")

    # A/B comparison
    if (
        "last_run_A" in st.session_state
        and "last_run_B" in st.session_state
        and st.button("Compare saved Scenario A vs B")
    ):
        result_a = st.session_state.get("last_run_A")
        result_b = st.session_state.get("last_run_B")
        if not result_a or not result_b:
            st.warning("Both scenarios must be run before comparing.")
            return

        agg_a = result_a.get("aggregate", {}) or {}
        agg_b = result_b.get("aggregate", {}) or {}

        first_a = agg_a.get("first_decision_distribution", {}) or {}
        first_b = agg_b.get("first_decision_distribution", {}) or {}

        buy_pct_a = float(first_a.get("buy", {}).get("pct", 0) or 0) + float(
            first_a.get("trial", {}).get("pct", 0) or 0
        )
        buy_pct_b = float(first_b.get("buy", {}).get("pct", 0) or 0) + float(
            first_b.get("trial", {}).get("pct", 0) or 0
        )

        comp_df = pd.DataFrame({
            "Metric": ["Buy + Trial %", "Reorder Rate %", "Errors"],
            "Scenario A": [
                round(buy_pct_a, 1),
                round(float(agg_a.get("reorder_rate_pct", 0) or 0), 1),
                int(result_a.get("errors", 0) or 0),
            ],
            "Scenario B": [
                round(buy_pct_b, 1),
                round(float(agg_b.get("reorder_rate_pct", 0) or 0), 1),
                int(result_b.get("errors", 0) or 0),
            ],
        })
        comp_df["Delta"] = comp_df["Scenario B"] - comp_df["Scenario A"]
        st.divider()
        st.subheader("Scenario Comparison")
        st.dataframe(comp_df, use_container_width=True)

        # AI-generated comparison headline (rule-based)
        sc_a = result_a
        sc_b = result_b
        if sc_a and sc_b:
            buy_a = buy_pct_a
            buy_b = buy_pct_b
            reorder_a = float(agg_a.get("reorder_rate_pct", 0) or 0)
            reorder_b = float(agg_b.get("reorder_rate_pct", 0) or 0)
            buy_diff = buy_b - buy_a
            reorder_diff = reorder_b - reorder_a
            direction = "improved" if buy_diff > 0 else "reduced"
            headline = (
                f"Scenario B {direction} first purchase by **{abs(buy_diff):.1f}pp** "
                f"({'↑' if buy_diff > 0 else '↓'}) and "
                f"{'increased' if reorder_diff > 0 else 'decreased'} reorder rate by **{abs(reorder_diff):.1f}pp** "
                f"({'↑' if reorder_diff > 0 else '↓'}) vs Scenario A."
            )
            st.info(f"📊 **What changed:** {headline}")


# ---------------------------------------------------------------------------
# Page: Ask the Population
# ---------------------------------------------------------------------------

def page_ask_population(all_personas: dict[str, dict]) -> None:
    st.title("Ask the Population")
    st.caption(
        "Ask any business question in plain English. "
        "The engine probes 200 personas and returns a grounded answer — "
        "or proposes a simulation to run."
    )

    # Pre-fill from home page navigation (popped so it only fires once)
    _pending_q = st.session_state.pop("pending_question", "")
    default_q = _pending_q

    question = st.text_input(
        "Your question",
        value=default_q,
        placeholder="e.g. What % of Tier 2 moms trust doctors over influencers?",
        key="ask_question_input",
    )

    # Example prompts
    with st.expander("Example questions to try"):
        examples = [
            "What % of Tier 2 moms trust doctors over influencers?",
            "Which decision style is most common among price-sensitive parents?",
            "How open are joint-family households to indie brands like LittleJoys vs legacy brands?",
            "What if we cut Nutrimix price to Rs 499 for the 7-14 segment?",
            "How would adding a pediatrician follow-up call affect Magnesium Gummies trial rate?",
            "Which personas are most likely to lapse after first Nutrimix purchase?",
            "Compare trust anchors between Tier 1 and Tier 2 parents",
        ]
        for eg in examples:
            if st.button(eg, key=f"ask_eg_{eg[:25]}", use_container_width=True):
                st.session_state["ask_prefill"] = eg
                st.rerun()
    _auto_ask = bool(_pending_q)  # auto-submit when navigated from home page
    if "ask_prefill" in st.session_state:
        question = st.session_state.pop("ask_prefill")
        _auto_ask = True  # example button was clicked — auto-submit

    ask_clicked = st.button("Ask →", type="primary")

    if not (ask_clicked or _auto_ask) or not question.strip():
        _render_question_engine_explainer()
        return

    # Run the question engine
    personas_list = list(all_personas.values())
    with st.spinner("Thinking..."):
        try:
            from app.question_engine import answer_question
            result = answer_question(question.strip(), personas_list)
        except Exception as exc:
            st.error(f"Question engine error: {exc}")
            return

    if result.error:
        st.error(result.error)
        if "ANTHROPIC_API_KEY" in result.error:
            st.code("export ANTHROPIC_API_KEY=sk-ant-...")
        return

    # ── Result display ───────────────────────────────────────────────────────
    st.divider()
    st.markdown(f"**Interpreting:** _{result.interpretation}_")
    st.caption(
        f"Population analysed: **{result.filtered_count} personas** "
        f"({result.persona_filter.description()})"
    )

    if result.mode.value == "population_stat":
        # Narrative answer
        if result.narrative_answer:
            st.markdown(
                f"<div style='background:#F0FDF4;border-left:4px solid #10B981;"
                f"padding:16px;border-radius:4px;font-size:0.95rem'>"
                f"{result.narrative_answer}</div>",
                unsafe_allow_html=True,
            )

        # Supporting stats
        if result.attribute_stats:
            st.divider()
            st.subheader("Supporting data")
            for stat in result.attribute_stats:
                with st.expander(stat.label, expanded=False):
                    if stat.distribution:
                        df = pd.DataFrame(
                            [{"Value": k, "Count": v, "Share (%)": round(100 * v / stat.count, 1)}
                             for k, v in stat.distribution.items()]
                        )
                        st.dataframe(df, use_container_width=True)
                    elif stat.mean is not None:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Mean", f"{stat.mean:.2f}")
                        c2.metric("Median", f"{stat.median:.2f}")
                        c3.metric("High (>0.7)", f"{stat.high_pct:.0f}%")
                        c4.metric("Low (<0.3)", f"{stat.low_pct:.0f}%")

    else:
        # Scenario proposal
        st.markdown(
            f"<div style='background:#EFF6FF;border-left:4px solid #3B82F6;"
            f"padding:16px;border-radius:4px'>"
            f"<strong>Proposed simulation</strong><br>"
            f"Base journey: <strong>Journey {result.base_journey}</strong><br>"
            f"Intervention: {result.intervention_description}<br>"
            f"Hypothesis: <em>{result.hypothesis}</em>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.caption("Review the proposal, then run it in the Simulation Builder.")
        if st.button("Open in Simulation Builder →"):
            st.session_state["nav_page"] = "Run Scenario"
            st.session_state["active_scenario"] = result.base_journey
            st.rerun()


def _render_question_engine_explainer() -> None:
    st.divider()
    st.markdown(
        """
**How it works:**

1. You type a plain-English business question
2. The engine classifies it as either:
   - **Population probe** — answered instantly from 200 persona attributes (no simulation)
   - **Scenario proposal** — generates a simulation proposal you can review and run
3. For population probes, you get a data-grounded narrative answer + supporting statistics
4. For scenarios, you see the proposed journey configuration and can launch it directly

**What makes this different from a query tool:**
The 200 personas aren't a static database you query. They're a *population* you run experiments against.
A question like "what if we cut price to Rs 499?" doesn't look up an answer — it proposes a simulation,
runs it against the relevant persona segment, and returns how the *population actually behaves*.
        """
    )


# ---------------------------------------------------------------------------
# Page: Persona Explorer  (Population + Deep Dive + How Built)
# ---------------------------------------------------------------------------

# Labels for trust anchor values
_TRUST_ANCHOR_LABELS = {
    "self": "Self-directed",
    "peer": "Peer-influenced",
    "authority": "Authority-driven",
    "family": "Family-guided",
}

# Colours for trait pills
_TRAIT_COLOURS = {
    "analytical": "#3B82F6",
    "emotional": "#EC4899",
    "habitual": "#8B5CF6",
    "social": "#10B981",
    "self": "#6366F1",
    "peer": "#F59E0B",
    "authority": "#EF4444",
    "family": "#14B8A6",
    "low": "#10B981",
    "medium": "#F59E0B",
    "high": "#EF4444",
}


def _trait_pill(label: str, value: str, colour: str | None = None) -> str:
    col = colour or _TRAIT_COLOURS.get(str(value).lower(), "#6B7280")
    return (
        f"<span style='background:{col};color:#fff;padding:2px 10px;"
        f"border-radius:12px;font-size:0.75rem;font-weight:600;margin:2px'>"
        f"{label}: {value.replace('_',' ').title()}</span>"
    )


def _bar_html(value: float, colour: str = "#3B82F6") -> str:
    pct = int(value * 100)
    return (
        f"<div style='background:#E5E7EB;border-radius:4px;height:8px;width:100%'>"
        f"<div style='background:{colour};border-radius:4px;height:8px;width:{pct}%'></div>"
        f"</div><div style='font-size:0.7rem;color:#9CA3AF;text-align:right'>{pct}%</div>"
    )


def page_persona_explorer(all_personas: dict[str, dict]) -> None:
    st.title("Meet Your Consumers")
    if not all_personas:
        st.error("No personas found in data/population/.")
        return

    tab_pop, tab_profile, tab_built = st.tabs(
        ["Population Snapshot", "Persona Profiles", "How We Built Them"]
    )

    with tab_pop:
        _render_population_tab(all_personas)

    with tab_profile:
        _render_persona_profiles_tab(all_personas)

    with tab_built:
        _render_how_built_tab()


def _render_population_tab(all_personas: dict[str, dict]) -> None:
    """Static + filterable population charts."""
    snap = _population_snapshot(all_personas)
    total = snap["total"]

    # ── Summary metrics ──────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Personas", total)
    m2.metric("Cities", snap.get("num_cities", "—"))

    ab = snap["age_bands"]
    m3.metric("Early-Stage (2–6)", ab.get("2–6", 0), help="Children aged 2–6 only")
    m4.metric("School-Age (7–14)", ab.get("7–14", 0), help="Children aged 7–14 only")
    m5.metric("Mixed Ages", ab.get("both", 0), help="Family has both age bands")

    st.divider()

    # ── Charts: Row 1 ────────────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("**City Tier Mix**")
        tier_df = pd.DataFrame([
            {"Tier": k, "Personas": v, "Share": f"{round(100*v/total)}%"}
            for k, v in sorted(snap["tiers"].items())
        ])
        st.bar_chart(tier_df.set_index("Tier")["Personas"], use_container_width=True, height=200)
        for _, row in tier_df.iterrows():
            st.caption(f"{row['Tier']}: {row['Personas']} personas ({row['Share']})")

    with col_b:
        st.markdown("**Decision Style**")
        ds = snap.get("decision_styles", {})
        ds_df = pd.DataFrame([
            {"Style": k.title(), "Count": v}
            for k, v in sorted(ds.items(), key=lambda x: -x[1])
        ])
        if not ds_df.empty:
            st.bar_chart(ds_df.set_index("Style")["Count"], use_container_width=True, height=200)
            for _, row in ds_df.iterrows():
                st.caption(f"{row['Style']}: {row['Count']} ({round(100*row['Count']/total)}%)")

    with col_c:
        st.markdown("**Trust Anchor**")
        ta_df = pd.DataFrame([
            {"Anchor": _TRUST_ANCHOR_LABELS.get(k, k.title()), "Count": v}
            for k, v in sorted(snap["trust_anchors"].items(), key=lambda x: -x[1])
        ])
        if not ta_df.empty:
            st.bar_chart(ta_df.set_index("Anchor")["Count"], use_container_width=True, height=200)
            for _, row in ta_df.iterrows():
                st.caption(f"{row['Anchor']}: {row['Count']} ({round(100*row['Count']/total)}%)")

    # ── Charts: Row 2 ────────────────────────────────────────────────────────
    col_d, col_e, col_f = st.columns(3)

    with col_d:
        st.markdown("**Price Sensitivity**")
        ps = snap.get("price_sensitivity", {})
        ps_df = pd.DataFrame([
            {"Sensitivity": k.title(), "Count": v}
            for k, v in sorted(ps.items(), key=lambda x: -x[1])
        ])
        if not ps_df.empty:
            st.bar_chart(ps_df.set_index("Sensitivity")["Count"], use_container_width=True, height=200)

    with col_e:
        st.markdown("**Family Structure**")
        fs = snap.get("family_structures", {})
        fs_df = pd.DataFrame([
            {"Structure": k.replace("_", " ").title(), "Count": v}
            for k, v in sorted(fs.items(), key=lambda x: -x[1])
        ])
        if not fs_df.empty:
            st.bar_chart(fs_df.set_index("Structure")["Count"], use_container_width=True, height=200)

    with col_f:
        st.markdown("**Employment**")
        emp = snap.get("employment_status", {})
        emp_df = pd.DataFrame([
            {"Status": k.replace("_", " ").title(), "Count": v}
            for k, v in sorted(emp.items(), key=lambda x: -x[1])
        ])
        if not emp_df.empty:
            st.bar_chart(emp_df.set_index("Status")["Count"], use_container_width=True, height=200)


def _render_persona_profiles_tab(all_personas: dict[str, dict]) -> None:
    """Filter panel → persona table → rich detail view."""

    # ── Build table rows ──────────────────────────────────────────────────────
    rows = []
    for pid, p in all_personas.items():
        d = p.get("demographics", {})
        pt = p.get("parent_traits") or {}
        bp = p.get("budget_profile") or {}
        h = p.get("health", {})
        ages = d.get("child_ages") or []
        youngest = min(ages) if ages else 99
        oldest = max(ages) if ages else 0
        if oldest <= 6:
            age_band = "2–6 only"
        elif youngest >= 7:
            age_band = "7–14 only"
        else:
            age_band = "Mixed"

        rows.append({
            "_id": pid,
            "Name": p.get("display_name") or pid,
            "Age": d.get("parent_age", "—"),
            "City": d.get("city_name", "—"),
            "Tier": d.get("city_tier", "—"),
            "Child Ages": ", ".join(str(a) for a in sorted(ages)) if ages else "—",
            "Age Band": age_band,
            "Decision Style": (pt.get("decision_style") or "—").title(),
            "Trust Anchor": _TRUST_ANCHOR_LABELS.get(pt.get("trust_anchor", ""), (pt.get("trust_anchor") or "—").title()),
            "Price Sensitivity": (bp.get("price_sensitivity") or "—").title(),
            "Family": (d.get("family_structure") or "—").replace("_", " ").title(),
            "Employment": (p.get("career", {}).get("employment_status") or "—").replace("_", " ").title(),
            "Pediatrician Visits": h.get("pediatrician_visit_frequency", "—").replace("_", " ").title() if isinstance(h.get("pediatrician_visit_frequency"), str) else "—",
        })

    df_full = pd.DataFrame(rows)

    # ── Filter controls ───────────────────────────────────────────────────────
    st.markdown("**Filter the population**")
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)
    tier_f = fc1.selectbox("City Tier", ["All", "Tier1", "Tier2", "Tier3"], key="pop_f_tier")
    style_f = fc2.selectbox("Decision Style", ["All", "Analytical", "Emotional", "Habitual", "Social"], key="pop_f_style")
    trust_f = fc3.selectbox("Trust Anchor", ["All", "Self-directed", "Peer-influenced", "Authority-driven", "Family-guided"], key="pop_f_trust")
    ps_f = fc4.selectbox("Price Sensitivity", ["All", "Low", "Medium", "High"], key="pop_f_ps")
    ab_f = fc5.selectbox("Child Age Band", ["All", "2–6 only", "7–14 only", "Mixed"], key="pop_f_ab")

    df = df_full.copy()
    if tier_f != "All":
        df = df[df["Tier"] == tier_f]
    if style_f != "All":
        df = df[df["Decision Style"] == style_f]
    if trust_f != "All":
        df = df[df["Trust Anchor"] == trust_f]
    if ps_f != "All":
        df = df[df["Price Sensitivity"] == ps_f]
    if ab_f != "All":
        df = df[df["Age Band"] == ab_f]

    st.caption(f"**{len(df)}** personas match your filter{' (all)' if len(df) == len(df_full) else ''}.")

    if df.empty:
        st.warning("No personas match these filters. Try broadening your selection.")
        return

    # ── Persona table ─────────────────────────────────────────────────────────
    display_cols = ["Name", "Age", "City", "Tier", "Child Ages", "Decision Style",
                    "Trust Anchor", "Price Sensitivity", "Family", "Employment"]
    st.dataframe(df[display_cols], use_container_width=True, height=300,
                 hide_index=True)

    st.divider()

    # ── Persona selector → detail ─────────────────────────────────────────────
    st.markdown("**Select a persona to explore**")
    name_options = df["Name"].tolist()
    id_options = df["_id"].tolist()

    default_id = st.session_state.get("selected_persona_id", id_options[0])
    if default_id not in id_options:
        default_id = id_options[0]
    default_idx = id_options.index(default_id)

    sel_name = st.selectbox(
        "Choose persona",
        options=name_options,
        index=default_idx,
        key="pop_persona_selector",
        label_visibility="collapsed",
    )
    sel_id = id_options[name_options.index(sel_name)]
    st.session_state["selected_persona_id"] = sel_id

    st.divider()
    _render_persona_deep_dive(all_personas, sel_id)


def _render_persona_deep_dive(all_personas: dict[str, dict], persona_id: str) -> None:
    """Rich individual persona detail — backstory, motivations, anchor traits, full profile."""
    p = all_personas.get(persona_id)
    if not p:
        st.error("Persona not found.")
        return

    persona = parse_persona(json.dumps(p))
    if persona is None:
        st.error(f"Could not parse persona {persona_id}")
        return

    d = persona.demographics
    name = persona.display_name or persona.id
    pt = persona.parent_traits
    bp = persona.budget_profile

    # ── Hero row ──────────────────────────────────────────────────────────────
    avatar_initial = name[0].upper() if name else "?"
    decision_style_val = str(pt.decision_style) if pt else "—"
    trust_anchor_val = str(pt.trust_anchor) if pt else "—"
    price_sens_val = str(bp.price_sensitivity) if bp else "—"

    pills_html = " ".join([
        _trait_pill("Decision", decision_style_val),
        _trait_pill("Trust", _TRUST_ANCHOR_LABELS.get(trust_anchor_val, trust_anchor_val.title())),
        _trait_pill("Price", price_sens_val),
    ])

    child_ages = d.child_ages
    age_str = ", ".join(str(a) for a in sorted(child_ages)) if child_ages else "—"
    budget_str = f"Rs {bp.discretionary_child_nutrition_budget_inr:,.0f}/mo nutrition budget" if bp else ""

    st.markdown(
        f"""<div style='background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);
        color:#fff;border-radius:12px;padding:24px;margin-bottom:16px'>
        <div style='display:flex;align-items:center;gap:20px'>
          <div style='background:rgba(255,255,255,0.2);border-radius:50%;width:64px;height:64px;
          display:flex;align-items:center;justify-content:center;font-size:2rem;font-weight:700'>
          {avatar_initial}</div>
          <div>
            <div style='font-size:1.6rem;font-weight:700'>{name}</div>
            <div style='opacity:0.8;font-size:0.9rem'>{d.parent_age} yrs · {d.city_name} ({d.city_tier}) ·
            {d.family_structure.replace("_"," ").title()} · Children: {age_str}</div>
            <div style='opacity:0.7;font-size:0.8rem;margin-top:4px'>{budget_str} ·
            Rs {d.household_income_lpa:.0f}L/yr · {d.socioeconomic_class}</div>
          </div>
        </div>
        <div style='margin-top:12px'>{pills_html}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── 4 anchor trait cards ──────────────────────────────────────────────────
    psy = persona.psychology
    vals = persona.values

    anchor_cards = [
        {
            "icon": "🧠",
            "title": "Buying Mindset",
            "lines": [
                f"Decision style: **{decision_style_val.title()}**",
                f"Trust anchor: **{_TRUST_ANCHOR_LABELS.get(trust_anchor_val, trust_anchor_val.title())}**",
                f"Risk appetite: **{(pt.risk_appetite or '—').title() if pt else '—'}**",
                f"Coping: **{(pt.coping_mechanism_type or '').replace('_',' ').title() if pt else '—'}**",
            ],
        },
        {
            "icon": "💰",
            "title": "Financial Lens",
            "lines": [
                f"Price sensitivity: **{price_sens_val.title()}**",
                f"Brand switch tolerance: **{(bp.brand_switch_tolerance or '—').title() if bp else '—'}**",
                f"Primary value driver: **{(pt.primary_value_orientation or '—').replace('_',' ').title() if pt else '—'}**",
                f"Shopping platform: **{(lambda v: v.replace('_',' ').title() if v and v != '—' else '—')(getattr(getattr(persona, 'daily_routine', None), 'primary_shopping_platform', '—') or '—')}**",
            ],
        },
        {
            "icon": "❤️",
            "title": "Parenting Lens",
            "lines": [
                f"Parenting style: **{(lambda v: v.replace('_',' ').title() if v and v != '—' else '—')(getattr(getattr(persona, 'lifestyle', None), 'parenting_philosophy', '—') or '—')}**",
                f"Child need focus: **{(pt.child_need_orientation or '—').replace('_',' ').title() if pt else '—'}**",
                f"Child pester power: **{f'{_v:.0%}' if (_v := getattr(getattr(persona, 'relationships', None), 'child_pester_power', None)) is not None else '—'}**",
                f"Health proactivity: **{f'{_v:.0%}' if (_v := getattr(getattr(persona, 'health', None), 'child_health_proactivity', None)) is not None else '—'}**",
            ],
        },
        {
            "icon": "📱",
            "title": "Media & Influence",
            "lines": [
                f"Platform: **{(lambda v: v.replace('_',' ').title() if v and v != '—' else '—')(getattr(getattr(persona, 'media', None), 'primary_social_platform', '—') or '—')}**",
                f"Influencer trust: **{f'{_v:.0%}' if (_v := getattr(getattr(persona, 'relationships', None), 'influencer_trust', None)) is not None else '—'}**",
                f"Pediatrician influence: **{f'{_v:.0%}' if (_v := getattr(getattr(persona, 'relationships', None), 'pediatrician_influence', None)) is not None else '—'}**",
                f"WOM openness: **{f'{_v:.0%}' if (_v := getattr(getattr(persona, 'relationships', None), 'wom_receiver_openness', None)) is not None else '—'}**",
            ],
        },
    ]

    cols = st.columns(4)
    for col, card in zip(cols, anchor_cards):
        with col:
            st.markdown(
                f"<div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;"
                f"padding:16px;height:100%'>"
                f"<div style='font-size:1.4rem'>{card['icon']}</div>"
                f"<div style='font-weight:700;font-size:0.85rem;color:#1E3A5F;margin:4px 0 8px'>"
                f"{card['title']}</div>",
                unsafe_allow_html=True,
            )
            for line in card["lines"]:
                st.markdown(f"<div style='font-size:0.8rem;color:#374151;margin-bottom:3px'>{line}</div>",
                            unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # ── Tabs: Story | Motivations | Psychology | Memory ───────────────────────
    t_story, t_motiv, t_psych, t_mem = st.tabs(
        ["Backstory", "What Drives Them", "Full Profile", "Simulation Memory"]
    )

    with t_story:
        col_narr, col_voice = st.columns([1, 1])
        with col_narr:
            st.markdown("#### Their Story")
            if persona.narrative:
                st.markdown(persona.narrative)
            else:
                st.caption("No narrative generated yet.")
        with col_voice:
            st.markdown("#### In Their Own Words")
            if persona.first_person_summary:
                st.markdown(
                    f"<div style='background:#FFFBEB;border-left:4px solid #F59E0B;"
                    f"padding:16px;border-radius:4px;font-style:italic;color:#374151;"
                    f"font-size:0.9rem;line-height:1.6'>{persona.first_person_summary}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("No first-person summary available.")

    with t_motiv:
        st.markdown("#### Purchase Decision Drivers")
        if persona.purchase_decision_bullets:
            for i, bullet in enumerate(persona.purchase_decision_bullets, 1):
                icon = "🔴" if i == 1 else "🟡" if i == 2 else "🟢"
                st.markdown(
                    f"<div style='background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;"
                    f"padding:12px 16px;margin-bottom:8px;font-size:0.9rem'>"
                    f"{icon} {bullet}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No purchase decision bullets available.")

        # Key trait bars
        st.markdown("#### Psychological Fingerprint")
        traits = {
            "Social Proof Bias": psy.social_proof_bias,
            "Authority Bias": psy.authority_bias,
            "Loss Aversion": psy.loss_aversion,
            "Risk Tolerance": psy.risk_tolerance,
            "Health Anxiety": psy.health_anxiety,
            "Supplement Necessity": vals.supplement_necessity_belief,
            "Food-First Belief": vals.food_first_belief,
            "Indie Brand Openness": vals.indie_brand_openness,
            "Brand Loyalty": vals.brand_loyalty_tendency,
        }
        bar_colours = {
            "Social Proof Bias": "#8B5CF6",
            "Authority Bias": "#EF4444",
            "Loss Aversion": "#F59E0B",
            "Risk Tolerance": "#10B981",
            "Health Anxiety": "#EC4899",
            "Supplement Necessity": "#3B82F6",
            "Food-First Belief": "#14B8A6",
            "Indie Brand Openness": "#6366F1",
            "Brand Loyalty": "#F97316",
        }
        tc1, tc2 = st.columns(2)
        items = list(traits.items())
        for i, (trait_name, val) in enumerate(items):
            col = tc1 if i % 2 == 0 else tc2
            with col:
                st.markdown(
                    f"<div style='margin-bottom:10px'>"
                    f"<div style='font-size:0.8rem;font-weight:600;color:#374151;margin-bottom:3px'>"
                    f"{trait_name}</div>"
                    f"{_bar_html(float(val), bar_colours.get(trait_name,'#3B82F6'))}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    with t_psych:
        # Group into meaningful sections
        category_groups = {
            "Demographics & Career": ["demographics", "career", "education_learning"],
            "Psychology & Values": ["psychology", "values", "emotional"],
            "Health & Lifestyle": ["health", "lifestyle", "daily_routine"],
            "Social & Cultural": ["cultural", "relationships", "media"],
        }
        for group_name, cats in category_groups.items():
            with st.expander(group_name, expanded=(group_name == "Psychology & Values")):
                for cat_name in cats:
                    category = getattr(persona, cat_name, None)
                    if category is None:
                        continue
                    st.markdown(f"**{cat_name.replace('_', ' ').title()}**")
                    cat_data = category.model_dump()
                    cols = st.columns(3)
                    for i, (field, value) in enumerate(cat_data.items()):
                        label = _label(field)
                        with cols[i % 3]:
                            if isinstance(value, float):
                                st.metric(label, f"{value:.2f}")
                            elif isinstance(value, list):
                                st.metric(label, ", ".join(str(v) for v in value) if value else "—")
                            else:
                                st.metric(label, str(value) if value is not None else "—")
                    st.markdown("---")

    with t_mem:
        st.markdown("#### Simulation Memory")
        if persona.episodic_memory:
            mem_data = [
                {
                    "Time": m.timestamp[:19].replace("T", " "),
                    "Event": m.event_type,
                    "Content": (m.content[:100] + "…" if len(m.content) > 100 else m.content),
                    "Salience": round(float(m.salience), 2),
                    "Valence": round(float(m.emotional_valence), 2),
                }
                for m in reversed(persona.episodic_memory)
            ]
            df_mem = pd.DataFrame(mem_data)

            def _highlight(row: pd.Series) -> list[str]:
                c = EVENT_COLOURS.get(str(row.get("Event")), "#6B7280")
                return [f"background-color: {c}22"] * len(row)

            st.dataframe(df_mem.style.apply(_highlight, axis=1),
                         use_container_width=True, height=350, hide_index=True)
        else:
            st.info("This persona has not been through a simulation yet.")

        if persona.brand_memories:
            st.markdown("#### Brand Relationships")
            for brand, bm in persona.brand_memories.items():
                with st.expander(f"{brand.title()} — trust {float(bm.trust_level):.0%}"):
                    bc1, bc2, bc3 = st.columns(3)
                    bc1.metric("Trust Level", f"{float(bm.trust_level):.0%}")
                    bc2.metric("Purchases", int(bm.purchase_count))
                    bc3.metric("WOM Received", len(bm.word_of_mouth_received))
                    st.progress(float(bm.trust_level))


def _render_how_built_tab() -> None:
    """Visual explainer: how the LittleJoys population was constructed."""

    st.markdown(
        """
<div style='background:linear-gradient(135deg,#0F172A 0%,#1E3A5F 100%);color:#fff;
border-radius:12px;padding:32px;margin-bottom:24px'>
<h2 style='margin:0 0 8px;font-size:1.6rem'>How the LittleJoys Population was Built</h2>
<p style='opacity:0.8;margin:0;font-size:1rem'>
200 synthetic Indian parents built on three research foundations — not template-filled profiles,
but psychologically grounded agents with memory and agency.
</p>
</div>
""",
        unsafe_allow_html=True,
    )

    # ── 3 Foundation Papers ───────────────────────────────────────────────────
    st.markdown("### Three Research Foundations")
    f1, f2, f3 = st.columns(3)
    papers = [
        {
            "col": f1,
            "icon": "📄",
            "title": "DeepPersona (NeurIPS 2025)",
            "subtitle": "Deep attribute coverage",
            "body": (
                "A 12-category Human-Attribute Tree with 8,496 unique nodes, mined from real "
                "human-ChatGPT conversations. Each persona is built by progressively sampling "
                "attributes across near/middle/far strata — 200–250 attributes per person — "
                "validated against World Values Survey and Big Five distributions."
            ),
            "stat": "32% higher coverage vs PersonaHub",
            "colour": "#3B82F6",
        },
        {
            "col": f2,
            "icon": "🤖",
            "title": "Generative Agents (UIST 2023)",
            "subtitle": "Memory, reflection, agency",
            "body": (
                "Park et al.'s cognitive architecture: a memory stream of all experiences, "
                "a retrieval function scoring recency + importance + relevance, and periodic "
                "reflection that synthesises observations into higher-level insights. "
                "Agents remember what happened to them and act accordingly."
            ),
            "stat": "8σ improvement vs no-memory baseline",
            "colour": "#8B5CF6",
        },
        {
            "col": f3,
            "icon": "🐟",
            "title": "MiroFish (2024)",
            "subtitle": "Business-grounded environment",
            "body": (
                "End-to-end pipeline from brand seed documents to multi-agent simulation. "
                "Knowledge graph memory, behavioral parameters per agent (activity level, "
                "sentiment bias, stance positions), and a ReACT report agent for "
                "post-simulation analysis."
            ),
            "stat": "Full pipeline: seed → simulate → analyse",
            "colour": "#10B981",
        },
    ]
    for paper in papers:
        with paper["col"]:
            st.markdown(
                f"<div style='background:{paper['colour']}18;border:1px solid {paper['colour']}44;"
                f"border-radius:10px;padding:20px;height:100%'>"
                f"<div style='font-size:1.8rem'>{paper['icon']}</div>"
                f"<div style='font-weight:700;font-size:0.9rem;color:{paper['colour']};margin:6px 0 2px'>"
                f"{paper['title']}</div>"
                f"<div style='font-size:0.75rem;color:#6B7280;margin-bottom:10px'>{paper['subtitle']}</div>"
                f"<div style='font-size:0.82rem;color:#374151;line-height:1.5;margin-bottom:12px'>"
                f"{paper['body']}</div>"
                f"<div style='background:{paper['colour']};color:#fff;border-radius:6px;"
                f"padding:4px 10px;font-size:0.72rem;font-weight:600;display:inline-block'>"
                f"{paper['stat']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Generation pipeline ───────────────────────────────────────────────────
    st.markdown("### The Generation Pipeline")

    steps = [
        {
            "num": "1",
            "title": "Population Seeding",
            "desc": (
                "200 personas seeded with demographically realistic anchors: "
                "city tier (Tier1/2/3 at ~46/34/20% split), parent age, income, "
                "family structure, and child ages — sampled from India-calibrated "
                "distributions, not LLM guesses."
            ),
            "detail": "100 Tier1 · 67 Tier2 · 33 Tier3 · Age 25–42 · Income Rs 4–80L",
        },
        {
            "num": "2",
            "title": "12-Layer Identity Construction",
            "desc": (
                "Each persona built across 12 attribute categories: Demographics, Health, "
                "Psychology, Cultural, Relationships, Career, Education, Lifestyle, "
                "Daily Routine, Values, Emotional, and Media. "
                "Every attribute conditioned on the growing profile — not generated in isolation."
            ),
            "detail": "~200 attributes per persona · Progressive BFS traversal of attribute tree",
        },
        {
            "num": "3",
            "title": "Adversarial Critique & Consistency Scoring",
            "desc": (
                "A second LLM pass reviews each persona for internal contradictions: "
                "income vs spending patterns, trust anchor vs purchase behaviour, "
                "education vs information-seeking. Personas with low consistency scores "
                "are regenerated."
            ),
            "detail": "Consistency scored 0–100 · Hard violations trigger regeneration",
        },
        {
            "num": "4",
            "title": "Derived Insight Layer",
            "desc": (
                "Raw psychometric floats (0–1) converted to actionable enumerations: "
                "Decision Style (analytical/emotional/habitual/social), Trust Anchor "
                "(self/peer/authority/family), Risk Appetite (low/medium/high). "
                "These drive simulation decisions."
            ),
            "detail": "parent_traits · budget_profile · decision_rights",
        },
        {
            "num": "5",
            "title": "First-Person Narratives",
            "desc": (
                "Each persona receives a third-person backstory and a first-person "
                "diary-voice summary — written in character, mixing Hindi/English "
                "as appropriate for the persona's language profile. "
                "Plus skimmable purchase-driver bullets for product team use."
            ),
            "detail": "narrative · first_person_summary · purchase_decision_bullets",
        },
        {
            "num": "6",
            "title": "Cognitive Agent Architecture",
            "desc": (
                "Personas are not static profiles. During simulation, each perceives "
                "stimuli (ads, WOM, price changes), stores experiences in a memory stream, "
                "and retrieves relevant memories when making decisions. "
                "Memory entries are scored on recency × importance × relevance."
            ),
            "detail": "episodic_memory · semantic_memory · brand_memories",
        },
    ]

    for step in steps:
        st.markdown(
            f"""<div style='display:flex;gap:16px;margin-bottom:16px;
            background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:16px'>
              <div style='background:#1E3A5F;color:#fff;border-radius:50%;
              width:36px;height:36px;display:flex;align-items:center;justify-content:center;
              font-weight:700;font-size:1rem;flex-shrink:0'>{step['num']}</div>
              <div>
                <div style='font-weight:700;font-size:0.95rem;color:#0F172A;margin-bottom:4px'>
                {step['title']}</div>
                <div style='font-size:0.85rem;color:#374151;line-height:1.5;margin-bottom:6px'>
                {step['desc']}</div>
                <code style='font-size:0.75rem;color:#6B7280'>{step['detail']}</code>
              </div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── What makes these different ────────────────────────────────────────────
    st.markdown("### Why These Are Not Typical Personas")
    d1, d2, d3 = st.columns(3)
    diffs = [
        ("❌ Template-filled profiles", "✅ Progressive attribute sampling conditioned on growing profile — each attribute aware of all previous ones"),
        ("❌ Static JSON objects", "✅ Cognitive agents that perceive, remember, reflect, and act — behaviour changes with accumulated experience"),
        ("❌ LLM-hallucinated demographics", "✅ Demographics seeded from India-calibrated distributions, validated against World Values Survey"),
        ("❌ Uniform decision-making", "✅ 4 decision styles × 4 trust anchors × 3 price sensitivities = 48 behavioural archetypes"),
        ("❌ No business grounding", "✅ Budget profiles, purchase history, brand memories — all tied to the LittleJoys product landscape"),
        ("❌ Untestable claims", "✅ Consistency scores, constraint validation, A/B counterfactuals — every finding is auditable"),
    ]
    for i, (before, after) in enumerate(diffs):
        col = [d1, d2, d3][i % 3]
        with col:
            st.markdown(
                f"<div style='background:#FFF7ED;border:1px solid #FED7AA;border-radius:8px;"
                f"padding:12px;margin-bottom:12px;font-size:0.82rem'>"
                f"<div style='color:#9A3412;margin-bottom:6px'>{before}</div>"
                f"<div style='color:#166534'>{after}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Page: Data Quality (hidden from main nav)
# ---------------------------------------------------------------------------

def page_data_quality(report: dict[str, Any]) -> None:
    st.title("Data Quality")
    st.caption("Internal constraint validation — not shown in client view.")
    if not report:
        st.warning("No violations report found at data/population/constraint_violations_report.json")
        st.code("python3 scripts/validate_personas.py --fix-report")
        return

    summary = report.get("summary", {})
    total = int(report.get("total_personas", 0))
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Personas", total)
    col2.metric("Clean", f"{summary.get('clean', 0)} ({summary.get('pct_clean', 0)}%)")
    col3.metric("Hard Violations", summary.get("hard_violations", 0), delta_color="inverse")
    col4.metric("Soft Only", summary.get("soft_violations", 0))

    rule_hits = report.get("rule_hit_counts", {})
    violations_by_persona = report.get("violations_by_persona", {})

    if rule_hits:
        import plotly.graph_objects as go
        hard_rule_counts: dict[str, int] = defaultdict(int)
        soft_rule_counts: dict[str, int] = defaultdict(int)
        for _, viols in violations_by_persona.items():
            for v in viols:
                if v["severity"] == "hard":
                    hard_rule_counts[v["rule_id"]] += 1
                else:
                    soft_rule_counts[v["rule_id"]] += 1
        df_rules = pd.DataFrame([{"rule_id": k, "count": v} for k, v in list(rule_hits.items())[:50]])
        df_rules["severity"] = df_rules["rule_id"].apply(
            lambda rid: "hard" if hard_rule_counts.get(rid, 0) else "soft"
        )
        df_top = df_rules.sort_values("count", ascending=True).tail(15)
        colours = ["#EF4444" if s == "hard" else "#F59E0B" for s in df_top["severity"].tolist()]
        fig = go.Figure(go.Bar(x=df_top["count"], y=df_top["rule_id"], orientation="h", marker_color=colours))
        st.subheader("Rule Hit Counts (top 15)")
        st.plotly_chart(fig, use_container_width=True)

    all_rows: list[dict] = []
    for pid, viols in violations_by_persona.items():
        for v in viols:
            all_rows.append({
                "persona_id": pid, "rule_id": v["rule_id"], "severity": v["severity"],
                "attribute_a": v.get("attribute_a"), "attribute_b": v.get("attribute_b"),
                "message": v.get("message", ""),
            })
    if not all_rows:
        st.success("No violations found.")
        return

    df = pd.DataFrame(all_rows)
    col1, col2 = st.columns(2)
    sf = col1.selectbox("Severity", ["all", "hard", "soft"])
    rf = col2.selectbox("Rule", ["all", *sorted(df["rule_id"].unique().tolist())])
    if sf != "all":
        df = df[df["severity"] == sf]
    if rf != "all":
        df = df[df["rule_id"] == rf]

    persona_ids = sorted(df["persona_id"].unique().tolist())
    selected_pid = st.selectbox("Persona to inspect", persona_ids)
    if st.button("Inspect selected persona"):
        st.session_state["selected_persona_id"] = selected_pid
        st.session_state["nav_page"] = "Meet Your Consumers"
        st.rerun()
    st.dataframe(df[["persona_id", "rule_id", "severity", "attribute_a", "attribute_b", "message"]],
                 use_container_width=True)


# ---------------------------------------------------------------------------
# Page: Investigate (probing tree / hypothesis investigation)
# ---------------------------------------------------------------------------

_INVESTIGATE_PROBLEMS = [
    {
        "id": "repeat_purchase_low",
        "title": "How can Nutrimix convert high NPS into a reliable repeat purchase habit?",
        "context": "Trial satisfaction is strong — the opportunity is to turn that goodwill into a dependable reorder cycle. Identify the moments and motivators that close the loop.",
    },
    {
        "id": "nutrimix_7_14_expansion",
        "title": "How can Nutrimix unlock the school-age (7–14) segment where penetration is low?",
        "context": "Nutrimix has a loyal under-7 base. The school-age segment is an adjacent growth opportunity — find the proposition shifts and channel plays that make the crossover happen.",
    },
    {
        "id": "magnesium_gummies_growth",
        "title": "How can Magnesium Gummies break through in a low-awareness category and reach its next growth stage?",
        "context": "An innovative product with strong product-market fit signals. The opportunity is to translate early adopter momentum into mainstream category creation.",
    },
    {
        "id": "protein_mix_launch",
        "title": "How can Protein Mix accelerate early trial and build its first loyal cohort?",
        "context": "ProteinMix is entering a new routine-formation space. The opportunity is to find the hook — the right trigger, taste story, or social proof — that seeds its first wave of loyal users.",
    },
]


def _confidence_badge(confidence: float) -> str:
    """Return an HTML confidence badge coloured green / amber / red with plain-language label."""
    if confidence >= 0.65:
        bg, text_color, signal = "#D1FAE5", "#065F46", "🟢 Strong signal"
    elif confidence >= 0.45:
        bg, text_color, signal = "#FEF3C7", "#92400E", "🟡 Moderate signal"
    else:
        bg, text_color, signal = "#FEE2E2", "#991B1B", "🔴 Weak signal"
    return (
        f"<span style='background:{bg};color:{text_color};padding:2px 10px;"
        f"border-radius:12px;font-size:0.75rem;font-weight:600'"
        f" title='Confidence prior: {confidence:.0%}'>"
        f"{signal}</span>"
    )


def _cohort_pill(key: str, value: Any) -> str:
    label = f"{key.replace('_', ' ').title()}: {str(value).replace('_', ' ').title()}"
    return (
        f"<span style='background:#EFF6FF;color:#1D4ED8;padding:2px 8px;"
        f"border-radius:10px;font-size:0.72rem;font-weight:500;margin:2px'>"
        f"{label}</span>"
    )


def page_investigate(all_personas: dict[str, dict]) -> None:
    st.title("Investigate")
    st.caption(
        "Choose a business problem, explore the hypothesis tree, run probes "
        "across the population, and synthesise findings."
    )

    # ── Section A: Problem Selection ─────────────────────────────────────────
    problem_id = st.session_state.get("investigate_problem_id")

    if not problem_id:
        st.subheader("What do you want to investigate?")
        st.caption("Select a predefined problem or describe your own")

        col_a, col_b = st.columns(2)
        cols = [col_a, col_b, col_a, col_b]
        for i, prob in enumerate(_INVESTIGATE_PROBLEMS):
            with cols[i]:
                st.markdown(
                    f"<div style='background:#F8FAFC;border:1px solid #E2E8F0;"
                    f"border-radius:10px;padding:16px;margin-bottom:12px'>"
                    f"<p style='font-weight:700;font-size:0.95rem;margin:0 0 6px 0'>{prob['title']}</p>"
                    f"<p style='color:#6B7280;font-size:0.82rem;margin:0 0 12px 0'>{prob['context']}</p>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Investigate this problem",
                    key=f"inv_select_{prob['id']}",
                    use_container_width=True,
                ):
                    st.session_state["investigate_problem_id"] = prob["id"]
                    st.rerun()

        st.divider()
        st.subheader("Custom Problem")
        custom_text = st.text_area(
            "Describe your business problem",
            placeholder=(
                "E.g. Why are parents in Tier 2 cities not reordering after the first purchase?"
            ),
            key="custom_problem_text",
            height=100,
        )
        if st.button("Generate Hypothesis Tree", key="inv_custom_generate"):
            if not custom_text.strip():
                st.warning("Enter a problem description first.")
            else:
                st.session_state["investigate_problem_id"] = "custom"
                st.rerun()
        return

    # Problem is selected — show compact banner with change option
    banner_label = (
        next(
            (p["title"] for p in _INVESTIGATE_PROBLEMS if p["id"] == problem_id),
            "Custom problem",
        )
        if problem_id != "custom"
        else st.session_state.get("custom_problem_text", "Custom problem")[:80]
    )
    banner_col, btn_col = st.columns([5, 1])
    with banner_col:
        st.markdown(
            f"<div style='background:#EFF6FF;border-left:4px solid #3B82F6;"
            f"padding:10px 16px;border-radius:4px'>"
            f"<span style='color:#6B7280;font-size:0.8rem;font-weight:600;text-transform:uppercase;"
            f"letter-spacing:0.05em'>Currently investigating</span><br>"
            f"<strong style='font-size:0.95rem'>{banner_label}</strong>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with btn_col:
        st.markdown("<div style='padding-top:8px'></div>", unsafe_allow_html=True)
        if st.button("Change problem", key="inv_change_problem"):
            st.session_state.pop("investigate_problem_id", None)
            st.rerun()

    st.divider()

    # ── Section B: Hypothesis Tree ───────────────────────────────────────────
    st.subheader("Hypothesis Tree")

    # Load tree
    if problem_id == "custom":
        custom_text_val = st.session_state.get("custom_problem_text", "")
        if not custom_text_val.strip():
            st.warning("Enter a problem description first, then click Generate Hypothesis Tree.")
            return
        tree_key = f"custom_tree_{abs(hash(custom_text_val))}"
        if tree_key not in st.session_state:
            with st.spinner("Building hypothesis tree..."):
                try:
                    import threading as _threading
                    from src.probing.dynamic_generator import generate_hypothesis_tree  # type: ignore

                    _tree_result: list[Any] = []
                    _tree_error: list[Exception] = []

                    def _run_tree() -> None:
                        try:
                            _tree_result.append(generate_hypothesis_tree(custom_text_val))
                        except Exception as _e:
                            _tree_error.append(_e)

                    _t = _threading.Thread(target=_run_tree, daemon=True)
                    _t.start()
                    _t.join(timeout=60)
                    if _t.is_alive():
                        st.error("Failed to generate hypothesis tree. Please try again.")
                        return
                    if _tree_error:
                        raise _tree_error[0]
                    tree_def = _tree_result[0]
                    st.session_state[tree_key] = tree_def
                except Exception as exc:
                    st.error("Failed to generate hypothesis tree. Please try again.")
                    return
        tree_def = st.session_state[tree_key]
        problem = tree_def.problem
        hypotheses = tree_def.hypotheses
        probes = tree_def.probes
    else:
        from src.probing.predefined_trees import get_problem_tree
        problem, hypotheses, probes = get_problem_tree(problem_id)

    # Problem context header
    st.markdown(
        f"<div style='background:#F8FAFC;border-left:3px solid #94A3B8;"
        f"padding:12px 16px;border-radius:4px;margin-bottom:16px'>"
        f"<span style='color:#4B5563;font-size:0.88rem'>{problem.context}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Group hypotheses: top-level first, sub-hypotheses nested
    top_hyps = [
        h for h in hypotheses
        if getattr(h, "why_level", 1) == 1 or getattr(h, "parent_hypothesis_id", None) is None
    ]
    sub_hyps_by_parent: dict[str, list] = {}
    for h in hypotheses:
        parent_id = getattr(h, "parent_hypothesis_id", None)
        if parent_id and parent_id != h.id:
            sub_hyps_by_parent.setdefault(parent_id, []).append(h)

    # Probe lookup by hypothesis
    probes_by_hyp: dict[str, list] = {}
    for p in probes:
        probes_by_hyp.setdefault(p.hypothesis_id, []).append(p)

    probe_type_labels = {"interview": "Interview", "simulation": "Simulation", "attribute": "Attribute"}

    with st.expander("💡 What are probes? (click to learn)", expanded=False):
        st.markdown(
            "**Probes** are structured questions or mini-simulations run across the synthetic population to test each hypothesis.\n\n"
            "- **Interview probes** ask each persona an open question about their experience — returns verbatim quotes.\n"
            "- **Attribute probes** compare psychological trait scores (e.g. health anxiety, trust in authority) between adopters and lapsers.\n"
            "- **Simulation probes** run a before/after scenario to measure lift from a specific change.\n\n"
            "Running probes takes 1–4 minutes depending on population size."
        )

    # Top run button (duplicate — also appears below the hypothesis tree)
    _enabled_h_ids_top = {
        h.id for h in top_hyps if st.session_state.get(f"h_enabled_{h.id}", True)
    }
    _enabled_probes_top = [p for p in probes if p.hypothesis_id in _enabled_h_ids_top]
    _n_personas_top = len(all_personas)
    _run_label_top = f"Run {len(_enabled_probes_top)} probes across {_n_personas_top} personas"
    if st.button(_run_label_top, type="primary", key="inv_run_probes_top"):
        st.session_state["_trigger_run_probes"] = True
        st.rerun()

    for i, h in enumerate(top_hyps):
        conf_prior = getattr(h, "confidence_prior", None)
        edge_case = getattr(h, "edge_case", False)
        expander_label = h.title
        if edge_case:
            expander_label += "  ⚠"

        with st.expander(expander_label, expanded=(i == 0)):
            # Enable / disable checkbox
            enabled = st.checkbox(
                "Include in probe run",
                value=st.session_state.get(f"h_enabled_{h.id}", True),
                key=f"h_enabled_{h.id}",
            )

            st.markdown(h.rationale)

            # Confidence prior badge
            if conf_prior is not None:
                st.markdown(
                    _confidence_badge(conf_prior),
                    unsafe_allow_html=True,
                )

            # Real-world analogy
            analogy = getattr(h, "real_world_analogy", "")
            if analogy:
                st.info(f"💡 {analogy}")

            # Cohort filter pills
            cohort = getattr(h, "cohort_filter", {}) or {}
            if cohort:
                pills_html = " ".join(_cohort_pill(k, v) for k, v in cohort.items())
                st.markdown(f"**Cohort scope:** {pills_html}", unsafe_allow_html=True)

            # Edge-case badge
            if edge_case:
                st.markdown(
                    "<span style='background:#FEF3C7;color:#92400E;padding:2px 8px;"
                    "border-radius:10px;font-size:0.75rem;font-weight:600'>⚠ Edge case</span>",
                    unsafe_allow_html=True,
                )

            # Sub-hypotheses
            sub_list = sub_hyps_by_parent.get(h.id, [])
            if sub_list:
                st.markdown("**Sub-hypotheses:**")
                for sh in sub_list:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• _{sh.title}_")

            # Probes list
            h_probes = probes_by_hyp.get(h.id, [])
            if h_probes:
                st.markdown("**Probes:**")
                for p in h_probes:
                    ptype = probe_type_labels.get(str(p.probe_type), str(p.probe_type))
                    if p.question_template:
                        st.markdown(f"- [{ptype}] _{p.question_template}_")
                    elif p.scenario_modifications:
                        mods_str = ", ".join(
                            f"{k.split('.')[-1].replace('_', ' ')} → {v}"
                            for k, v in p.scenario_modifications.items()
                        )
                        st.markdown(f"- [{ptype}] {mods_str}")
                    else:
                        attrs = ", ".join(
                            a.replace("_", " ") for a in (p.analysis_attributes or [])[:3]
                        )
                        st.markdown(f"- [{ptype}] {attrs}")

            # Inline results if already run
            results_key = f"probe_results_{problem_id}"
            existing_results = st.session_state.get(results_key, {})
            h_results = {
                pid: res
                for pid, res in existing_results.items()
                if any(p.id == pid for p in h_probes)
            }
            if h_results:
                st.divider()
                st.caption("Probe results")
                for probe_id, res in h_results.items():
                    # Interview responses — top 3 quotes
                    interview_responses = getattr(res, "interview_responses", None) or []
                    if interview_responses:
                        st.markdown("**Sample responses:**")
                        for ir in interview_responses[:3]:
                            name = getattr(ir, "persona_name", getattr(ir, "persona_id", "?"))
                            content = getattr(ir, "content", "")
                            st.markdown(
                                f"<div style='background:#F9FAFB;border-left:3px solid #D1D5DB;"
                                f"padding:8px 12px;border-radius:4px;margin:4px 0;"
                                f"font-size:0.85rem;color:#374151'>"
                                f"<strong>{name}:</strong> {content}"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                        clusters = getattr(res, "response_clusters", None) or []
                        if clusters:
                            st.caption(f"Theme: {clusters[0].description} ({clusters[0].percentage:.0%})")

                    # Attribute splits — bar chart
                    attribute_splits = getattr(res, "attribute_splits", None) or []
                    if attribute_splits:
                        split_rows = [
                            {
                                "Attribute": s.attribute.replace("_", " ").title(),
                                "Adopters": round(s.adopter_mean, 3),
                                "Rejectors": round(s.rejector_mean, 3),
                            }
                            for s in attribute_splits[:6]
                        ]
                        if len(split_rows) == 1:
                            row = split_rows[0]
                            st.markdown(
                                f"**{row['Attribute']}** — Adopters: {row['Adopters']}, "
                                f"Rejectors: {row['Rejectors']}"
                            )
                        else:
                            st.bar_chart(
                                pd.DataFrame(split_rows).set_index("Attribute"),
                                use_container_width=True,
                            )
                    else:
                        st.info("No data available")

                    # Simulation result
                    baseline = getattr(res, "baseline_metric", None)
                    modified = getattr(res, "modified_metric", None)
                    if baseline is not None and modified is not None:
                        lift = getattr(res, "lift", modified - baseline)
                        sc1, sc2, sc3 = st.columns(3)
                        sc1.metric("Baseline", f"{baseline:.1%}")
                        sc2.metric("With Change", f"{modified:.1%}")
                        sc3.metric("Lift", f"{lift:+.1%}")

                    st.caption(
                        f"Confidence: {res.confidence:.0%} — {getattr(res, 'evidence_summary', '')}"
                    )

    st.divider()

    # ── Journey context selector ─────────────────────────────────────────────
    # Determine which journey's segment outcomes to use for targeted probing.
    _journey_problem_map = {
        "A": "repeat_purchase_low",
        "B": "magnesium_gummies_growth",
        "C": "nutrimix_7_14_expansion",
    }
    _available_journeys: dict[str, tuple[str, dict, int]] = {}
    for _jid, _jlabel in [
        ("A", "Journey A — Nutrimix Repeat Purchase"),
        ("B", "Journey B — Magnesium Gummies"),
        ("C", "Journey C — Nutrimix 7–14 Expansion"),
    ]:
        _jdata = load_journey_results(_jid)
        if _jdata and _jdata.get("logs"):
            _n = len([l for l in _jdata["logs"] if not l.get("error")])
            _available_journeys[_jid] = (_jlabel, _jdata, _n)

    _context_labels = ["🌐 Full population (all personas — no journey filter)"] + [
        f"📊 {v[0]} ({v[2]} personas who ran the journey)"
        for v in _available_journeys.values()
    ]
    _context_keys = [None] + list(_available_journeys.keys())

    # Pre-select the journey that was passed from Run Scenario if available
    _preselect_jid = st.session_state.get("investigate_journey_id")
    _default_ctx_idx = 0
    if _preselect_jid and _preselect_jid in _available_journeys:
        _default_ctx_idx = _context_keys.index(_preselect_jid)

    _ctx_choice_idx = _context_labels.index(
        st.selectbox(
            "Probe context",
            _context_labels,
            index=_default_ctx_idx,
            key="inv_journey_context",
            help="Choose 'Full population' for broad awareness questions. Choose a Journey cohort to probe only the personas who ran that simulation — their answers are grounded in lived journey memory.",
        )
    )
    _selected_jid = _context_keys[_ctx_choice_idx]

    # Build journey_outcomes + filter probe personas
    journey_outcomes: dict[str, str] = {}
    probe_persona_pool: dict[str, dict] = all_personas

    if _selected_jid and _selected_jid in _available_journeys:
        _jdata = _available_journeys[_selected_jid][1]
        journey_outcomes = _extract_journey_outcomes(_jdata)
        # Restrict probe pool to personas who ran the journey
        probe_persona_pool = {
            pid: all_personas[pid]
            for pid in journey_outcomes
            if pid in all_personas
        }
        _adopters = sum(1 for v in journey_outcomes.values() if v == "adopt")
        _lapsed = sum(1 for v in journey_outcomes.values() if v == "lapsed")
        _rejectors = sum(1 for v in journey_outcomes.values() if v == "reject")
        st.caption(
            f"Journey cohort: **{len(probe_persona_pool)} personas** — "
            f"{_adopters} reordered · {_lapsed} lapsed · {_rejectors} didn't buy  "
            f"_(probes target the relevant segment automatically)_"
        )

    # Run button
    enabled_h_ids = {
        h.id for h in top_hyps if st.session_state.get(f"h_enabled_{h.id}", True)
    }
    enabled_probes = [p for p in probes if p.hypothesis_id in enabled_h_ids]
    n_personas = len(probe_persona_pool)
    context_label = (
        f"Journey {_selected_jid} cohort" if _selected_jid else "full population"
    )
    run_label = f"Run {len(enabled_probes)} probes across {n_personas} personas ({context_label})"

    if n_personas == 0:
        st.warning(
            "No personas available for this journey context. "
            "Select a different journey or use 'Full population'."
        )
        # do not render the run button
    else:
        _trigger_from_top = st.session_state.pop("_trigger_run_probes", False)
        if st.button(run_label, type="primary", key="inv_run_probes") or _trigger_from_top:
            from src.probing.engine import ProbingTreeEngine

            # Build Persona objects from the journey-filtered pool
            persona_objects = []
            for _pid, p_dict in probe_persona_pool.items():
                try:
                    persona_objects.append(Persona.model_validate(p_dict))
                except Exception:
                    pass

            if not persona_objects:
                st.error("No valid personas available to probe.")
                return

            # Lightweight duck-typed population — ProbingTreeEngine only calls .personas
            class _PopWrapper:
                def __init__(self, ps: list) -> None:
                    self.personas = ps
                    self.tier1_personas = ps  # engine may also access this directly
            pop = _PopWrapper(persona_objects)

            # Initialise LLM client
            try:
                import os as _os
                from src.config import Config as _Config
                from src.utils.llm import LLMClient
                _cfg = _Config(anthropic_api_key=_os.environ.get("ANTHROPIC_API_KEY", ""), llm_mock_enabled=False)
                llm_client = LLMClient(config=_cfg)
            except Exception as llm_exc:
                st.error(f"Could not initialise LLM client: {llm_exc}")
                return

            results: dict[str, Any] = {}
            progress_bar = st.progress(0, text="Starting probes...")
            _probe_done_count: list[int] = [0]  # mutable counter accessible inside closure

            def _on_probe_done(hyp_id: str, probe_result: Any) -> None:
                # Increment first — the callback fires before results dict is updated
                _probe_done_count[0] += 1
                done = _probe_done_count[0]
                total_probes = max(len(enabled_probes), 1)
                progress_bar.progress(
                    min(done / total_probes, 1.0),
                    text=f"Probed {done}/{total_probes}",
                )

            with st.spinner(f"Running {len(enabled_probes)} probes across {n_personas} personas..."):
                try:
                    engine = ProbingTreeEngine(
                        population=pop,
                        scenario_id=problem.scenario_id,
                        llm_client=llm_client,
                        on_probe_complete=_on_probe_done,
                        journey_outcomes=journey_outcomes if journey_outcomes else None,
                    )
                    # Run probes grouped by hypothesis so we can build verdicts
                    probes_by_h: dict[str, list] = {}
                    for probe in enabled_probes:
                        probes_by_h.setdefault(probe.hypothesis_id, []).append(probe)

                    for h in top_hyps:
                        if not st.session_state.get(f"h_enabled_{h.id}", True):
                            continue
                        h_probes = probes_by_h.get(h.id, [])
                        for probe in h_probes:
                            try:
                                res = engine.execute_probe(probe)
                                results[probe.id] = res
                            except Exception as probe_exc:
                                st.warning(f"Probe {probe.id} failed: {probe_exc}")
                        # Build verdict for this hypothesis so synthesis has data
                        if h_probes:
                            try:
                                engine.verdicts[h.id] = engine._build_hypothesis_verdict(h, h_probes)
                            except Exception:
                                pass

                except Exception as engine_exc:
                    st.error(f"Engine error: {engine_exc}")
                    import traceback
                    st.code(traceback.format_exc())
                    return

            progress_bar.progress(1.0, text="Done")
            st.session_state[f"probe_results_{problem_id}"] = results
            # Invalidate stale report cache so findings rebuild from fresh probe results
            st.session_state.pop(f"report_data_{problem_id}", None)

            # Build synthesis now that verdicts are populated
            try:
                # Pass the enabled hypotheses so synthesis only covers what was run
                enabled_hyps = [h for h in top_hyps if st.session_state.get(f"h_enabled_{h.id}", True)]
                synthesis = engine._build_tree_synthesis(problem, enabled_hyps, probes)
                st.session_state[f"synthesis_{problem_id}"] = synthesis
            except Exception:
                pass

            st.success(f"Completed {len(results)} probes.")
            st.rerun()

    # ── Section C: Findings + Downloads + Interventions + Conversations ────────
    results_key = f"probe_results_{problem_id}"
    _has_probe_results = results_key in st.session_state

    if not _has_probe_results:
        # Section E teaser — always visible even before probes run
        st.divider()
        st.subheader("💬 Talk to the Population")
        st.caption("Interview any synthetic persona in-character about their experience with LittleJoys.")
        st.info(
            "Run probes above to unlock grounded conversations — personas will respond based on "
            "their actual simulation journey and decisions."
        )
        return

    st.divider()

    # ── Build ReportData (cached per run) ────────────────────────────────────
    report_key = f"report_data_{problem_id}"
    if report_key not in st.session_state:
        try:
            from src.reporting import build_report, ReportData
            from src.probing.models import TreeSynthesis as _TreeSynthesis
            synthesis_obj = st.session_state.get(f"synthesis_{problem_id}")
            # Guard: build_report requires a valid TreeSynthesis — create a minimal
            # fallback when the synthesis step was skipped or failed.
            if synthesis_obj is None:
                synthesis_obj = _TreeSynthesis(
                    problem_id=problem.id,
                    hypotheses_tested=len(top_hyps),
                    hypotheses_confirmed=0,
                    dominant_hypothesis="",
                    confidence_ranking=[],
                    synthesis_narrative="",
                    recommended_actions=[],
                    overall_confidence=0.0,
                )
            probe_results = st.session_state.get(results_key, {})
            rd = build_report(
                problem=problem,
                hypotheses=top_hyps,
                probes=probes,
                probe_results=probe_results,
                synthesis=synthesis_obj,
            )
            st.session_state[report_key] = rd
        except Exception as _re:
            st.session_state[report_key] = None

    report_data = st.session_state.get(report_key)

    # ── Header + download buttons ────────────────────────────────────────────
    hc1, hc2, hc3 = st.columns([3, 1, 1])
    hc1.subheader("Research Findings")
    if report_data:
        try:
            from src.reporting import render_pdf, report_to_json
            pdf_bytes = render_pdf(report_data)
            hc2.download_button(
                "⬇ Download PDF",
                data=pdf_bytes,
                file_name=f"littlejoys_research_{problem_id}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            json_str = report_to_json(report_data)
            hc3.download_button(
                "⬇ Download JSON",
                data=json_str,
                file_name=f"littlejoys_research_{problem_id}.json",
                mime="application/json",
                use_container_width=True,
            )
        except Exception:
            pass

    synthesis = st.session_state.get(f"synthesis_{problem_id}")

    # ── Key narrative ────────────────────────────────────────────────────────
    if synthesis:
        narrative = getattr(synthesis, "synthesis_narrative", "") or ""
        if narrative:
            st.markdown(
                f"<div style='background:#F0FDF4;border-left:4px solid #10B981;"
                f"padding:16px;border-radius:4px;margin-bottom:12px'>"
                f"{narrative}</div>",
                unsafe_allow_html=True,
            )
        mc1, mc2, mc3 = st.columns(3)
        overall_conf = float(getattr(synthesis, "overall_confidence", 0.0) or 0.0)
        h_confirmed = int(getattr(synthesis, "hypotheses_confirmed", 0) or 0)
        h_tested = int(getattr(synthesis, "hypotheses_tested", 0) or 0)
        mc1.metric("Overall Confidence", f"{overall_conf * 100:.0f}%")
        mc2.metric("Hypotheses Confirmed", f"{h_confirmed}/{h_tested}")
        mc3.metric("Personas Analysed", len(st.session_state.get(results_key, {})))

    # ── Hypothesis cards ─────────────────────────────────────────────────────
    if report_data and report_data.hypotheses:
        st.markdown("#### Hypothesis Findings")
        for hr in report_data.hypotheses:
            conf = hr.confidence
            if conf >= 0.65:
                badge_bg, badge_color, status_label = "#D1FAE5", "#065F46", "CONFIRMED"
            elif conf >= 0.4:
                badge_bg, badge_color, status_label = "#FEF3C7", "#92400E", "INCONCLUSIVE"
            else:
                badge_bg, badge_color, status_label = "#FEE2E2", "#991B1B", "REJECTED"

            with st.expander(f"{hr.title}  —  {conf*100:.0f}% confidence", expanded=False):
                st.markdown(
                    f"<span style='background:{badge_bg};color:{badge_color};"
                    f"padding:2px 10px;border-radius:10px;font-size:0.75rem;"
                    f"font-weight:700'>{status_label}</span>",
                    unsafe_allow_html=True,
                )
                st.progress(conf, text=f"Confidence: {conf*100:.0f}%")
                st.markdown(hr.evidence_summary)

                if hr.key_quotes:
                    st.markdown("**What personas said:**")
                    for q in hr.key_quotes[:3]:
                        st.markdown(
                            f"<div style='border-left:3px solid #D1D5DB;padding:8px 12px;"
                            f"margin:6px 0;background:#F9FAFB;border-radius:0 4px 4px 0;"
                            f"font-style:italic;color:#374151;font-size:0.85rem'>{q}</div>",
                            unsafe_allow_html=True,
                        )

                if hr.attribute_splits:
                    st.markdown("**Adopters vs lapsers:**")
                    split_rows_hr = [
                        {"Attribute": s["attribute"].replace("_", " ").title(),
                         "Adopters": round(s["adopter"], 3),
                         "Rejectors": round(s["rejector"], 3)}
                        for s in hr.attribute_splits[:5]
                    ]
                    if len(split_rows_hr) == 1:
                        row = split_rows_hr[0]
                        st.markdown(
                            f"**{row['Attribute']}** — Adopters: {row['Adopters']}, "
                            f"Rejectors: {row['Rejectors']}"
                        )
                    else:
                        split_df = pd.DataFrame(split_rows_hr).set_index("Attribute")
                        st.bar_chart(split_df, use_container_width=True)
                else:
                    st.info("No data available")

                st.markdown(
                    f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;"
                    f"padding:10px 14px;border-radius:6px;margin-top:8px;"
                    f"font-size:0.85rem'><strong>Recommended action:</strong> {hr.recommended_action}</div>",
                    unsafe_allow_html=True,
                )
    elif synthesis:
        # Fallback: just show ranking
        ranking = getattr(synthesis, "confidence_ranking", []) or []
        if ranking:
            st.markdown("**Hypothesis Confidence Ranking**")
            for hyp_id, confidence in ranking:
                st.progress(float(confidence),
                    text=f"{hyp_id.replace('_', ' ').title()}: {confidence * 100:.0f}%")
        actions = getattr(synthesis, "recommended_actions", []) or []
        if actions:
            st.markdown("**Recommended Actions**")
            for action in actions:
                st.markdown(f"- {action}")
    else:
        raw_results = st.session_state.get(results_key, {})
        if raw_results:
            rows = [{"Probe": pid.replace("_", " ").title(),
                     "Confidence": f"{getattr(res, 'confidence', 0):.0%}",
                     "Summary": getattr(res, "evidence_summary", "")}
                    for pid, res in raw_results.items()]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("No results available yet.")

    # ── Section D: Interventions ─────────────────────────────────────────────
    st.divider()
    st.subheader("Interventions")
    st.caption("Proposed based on confirmed hypotheses. Run simulations to measure expected lift.")

    proposals_key = f"proposals_{problem_id}"
    if proposals_key not in st.session_state and synthesis:
        try:
            from src.interventions import propose_interventions
            _proposals = propose_interventions(
                synthesis=synthesis, hypotheses=top_hyps, problem=problem
            )
            st.session_state[proposals_key] = _proposals
        except Exception as _pe:
            st.session_state[proposals_key] = []

    proposals = st.session_state.get(proposals_key, [])
    iv_runs_key = f"iv_runs_{problem_id}"
    if iv_runs_key not in st.session_state:
        st.session_state[iv_runs_key] = {}

    if not proposals:
        st.info("Run probes above to generate intervention proposals.")
    else:
        # Run-all button
        _n_pending = sum(1 for p in proposals if p.id not in st.session_state.get(iv_runs_key, {}))
        if _n_pending and st.button(
            f"Run all {len(proposals)} intervention simulations",
            key="inv_run_all",
            type="primary",
        ):
            from src.interventions import run_intervention
            from src.simulation.journey_presets import list_presets
            _presets = list_presets()
            _base_cfg = _presets.get(problem.scenario_id.upper()[:1], list(_presets.values())[0])
            _persona_pairs = []
            for _pid, _pdict in all_personas.items():
                try:
                    _persona_pairs.append((_pid, Persona.model_validate(_pdict)))
                except Exception:
                    pass

            # Compute baseline metric
            _baseline_first = st.session_state.get(f"last_run_{problem.scenario_id.upper()[:1]}")
            if _baseline_first:
                _agg = _baseline_first.get("aggregate", {}) or {}
                _fd = _agg.get("first_decision_distribution", {}) or {}
                _baseline = (float(_fd.get("buy", {}).get("pct", 0) or 0) +
                             float(_fd.get("trial", {}).get("pct", 0) or 0)) / 100
            else:
                _baseline = 0.3  # conservative default

            iv_runs = st.session_state[iv_runs_key]
            prog = st.progress(0, text="Starting intervention queue...")
            for _i, _prop in enumerate(proposals):
                if _prop.id in iv_runs:
                    continue
                prog.progress((_i) / len(proposals), text=f"Running: {_prop.title[:40]}...")
                try:
                    run = run_intervention(
                        proposal=_prop,
                        base_config=_base_cfg,
                        personas=_persona_pairs[:50],
                        baseline_metric=_baseline,
                    )
                    iv_runs[_prop.id] = run
                except Exception as _ie:
                    from src.interventions.runner import InterventionRun
                    import datetime
                    iv_runs[_prop.id] = InterventionRun(
                        intervention_id=_prop.id, intervention_title=_prop.title,
                        status="failed", started_at=None, completed_at=None,
                        baseline_metric=_baseline, intervention_metric=None,
                        lift_pct=None, personas_run=0, result_dict=None,
                        error=str(_ie),
                    )
            prog.progress(1.0, text="All interventions complete")
            st.session_state[iv_runs_key] = iv_runs
            st.rerun()

        # Proposal cards
        for prop in proposals:
            run = st.session_state.get(iv_runs_key, {}).get(prop.id)
            _pri_color = "#059669" if prop.priority == 1 else "#D97706"
            _pri_label = "High priority" if prop.priority == 1 else "Pilot"
            with st.expander(
                f"{prop.title}  —  Expected +{prop.expected_lift_pct:.0f}% lift",
                expanded=(run is None),
            ):
                pc1, pc2 = st.columns([3, 1])
                with pc1:
                    st.markdown(prop.rationale)
                    st.markdown(
                        f"<span style='background:{_pri_color}20;color:{_pri_color};"
                        f"padding:2px 8px;border-radius:8px;font-size:0.75rem;"
                        f"font-weight:600'>{_pri_label}</span>&nbsp;"
                        f"<span style='color:#6B7280;font-size:0.8rem'>"
                        f"Type: {prop.intervention_type.title()}</span>",
                        unsafe_allow_html=True,
                    )
                with pc2:
                    if run is None:
                        if st.button("Run simulation", key=f"iv_run_{prop.id}"):
                            from src.interventions import run_intervention
                            from src.simulation.journey_presets import list_presets
                            _presets = list_presets()
                            _base_cfg = _presets.get(
                                problem.scenario_id.upper()[:1], list(_presets.values())[0]
                            )
                            _persona_pairs = []
                            for _pid, _pdict in list(all_personas.items())[:50]:
                                try:
                                    _persona_pairs.append((_pid, Persona.model_validate(_pdict)))
                                except Exception:
                                    pass
                            _baseline = 0.3
                            with st.spinner(f"Running {prop.title[:30]}..."):
                                try:
                                    run = run_intervention(
                                        proposal=prop, base_config=_base_cfg,
                                        personas=_persona_pairs, baseline_metric=_baseline,
                                    )
                                    st.session_state[iv_runs_key][prop.id] = run
                                except Exception as _ie:
                                    from src.interventions.runner import InterventionRun
                                    st.session_state[iv_runs_key][prop.id] = InterventionRun(
                                        intervention_id=prop.id, intervention_title=prop.title,
                                        status="failed", started_at=None, completed_at=None,
                                        baseline_metric=0.3, intervention_metric=None,
                                        lift_pct=None, personas_run=0, result_dict=None,
                                        error=str(_ie),
                                    )
                            st.rerun()
                    elif run.status == "complete":
                        lift = run.lift_pct or 0.0
                        delta_color = "normal" if lift >= 0 else "inverse"
                        st.metric("Observed Lift", f"+{lift:.1f}%", delta=f"{lift:.1f}pp", delta_color=delta_color)
                        st.caption(f"{run.personas_run} personas")
                        if st.button("🔄 Re-run", key=f"iv_rerun_{prop.id}", type="secondary"):
                            st.session_state[iv_runs_key].pop(prop.id, None)
                            st.rerun()
                    elif run.status == "failed":
                        st.error(f"Failed: {run.error or 'unknown'}")
                        if st.button("🔄 Re-run", key=f"iv_rerun_{prop.id}", type="secondary"):
                            st.session_state[iv_runs_key].pop(prop.id, None)
                            st.rerun()

        # Download results PDF if any runs are complete
        _complete_runs = [r for r in st.session_state.get(iv_runs_key, {}).values()
                          if r.status == "complete"]
        if _complete_runs and report_data:
            st.divider()
            try:
                from src.reporting import render_pdf, report_to_json
                # Enrich report with intervention results
                import dataclasses as _dc
                _iv_summaries = [
                    {"title": r.intervention_title,
                     "type": next((p.intervention_type for p in proposals if p.id == r.intervention_id), ""),
                     "expected_lift_pct": next((p.expected_lift_pct for p in proposals if p.id == r.intervention_id), 0),
                     "observed_lift_pct": r.lift_pct or 0,
                     "personas_run": r.personas_run,
                     "rationale": next((p.rationale for p in proposals if p.id == r.intervention_id), "")}
                    for r in _complete_runs
                ]
                _enriched = _dc.replace(report_data, recommended_interventions=_iv_summaries)
                iv_pdf = render_pdf(_enriched)
                iv_json = report_to_json(_enriched)
                _dc1, _dc2 = st.columns(2)
                _dc1.download_button(
                    "⬇ Download Intervention Results PDF",
                    data=iv_pdf,
                    file_name=f"littlejoys_interventions_{problem_id}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
                _dc2.download_button(
                    "⬇ Download Intervention Results JSON",
                    data=iv_json,
                    file_name=f"littlejoys_interventions_{problem_id}.json",
                    mime="application/json",
                    use_container_width=True,
                )
            except Exception:
                pass

    # ── Section E: Persona Conversations ────────────────────────────────────
    st.divider()
    st.subheader("💬 Talk to the Population")
    st.caption(
        "Interview any synthetic persona in-character about their experience with LittleJoys. "
        "They will answer from their actual simulation journey — decisions are fixed and cannot be reframed."
    )

    _conv_module_ready = False
    try:
        from src.conversation import (
            PersonaConversation, build_journey_context, build_system_prompt,
            chat as _grounded_chat, get_eligible_personas,
        )
        _conv_module_ready = True
    except Exception:
        st.info("Persona conversation module loading...")

    if _conv_module_ready:
        _outcome_filter = st.selectbox(
            "Filter by outcome",
            ["All", "Adopted", "Lapsed", "Rejected", "Deferred"],
            key=f"conv_filter_{problem_id}",
        )
        _filter_val = None if _outcome_filter == "All" else _outcome_filter.lower()

        # Get probe results as journey_logs proxy
        _probe_results_raw = st.session_state.get(results_key, {})
        _journey_logs = []  # populated from journey results if available
        _jid = problem.scenario_id.upper()[:1]
        _journey_data = st.session_state.get(f"last_run_{_jid}") or {}
        _journey_logs = _journey_data.get("logs", []) or []

        try:
            _eligible = get_eligible_personas(
                all_personas=all_personas,
                probe_results=_probe_results_raw,
                journey_logs=_journey_logs,
                filter_outcome=_filter_val,
            )
        except Exception:
            _eligible = [{"id": k, "display_name": v.get("display_name", k), "outcome": "unknown"}
                         for k, v in list(all_personas.items())[:20]]

        if not _eligible:
            st.info("No personas match this filter.")
        else:
            _persona_options = {
                p.get("display_name", p.get("id", "?")): p for p in _eligible[:30]
            }
            _sel_name = st.selectbox(
                f"Choose a persona ({len(_eligible)} available)",
                options=list(_persona_options.keys()),
                key=f"conv_persona_sel_{problem_id}",
            )
            _sel_persona = _persona_options.get(_sel_name, {})
            _sel_id = _sel_persona.get("id", _sel_name)
            _outcome_label = _sel_persona.get("outcome", "unknown")

            st.markdown(
                f"<div style='background:#F3F4F6;padding:10px 14px;border-radius:6px;"
                f"font-size:0.85rem;margin-bottom:8px'>"
                f"<strong>{_sel_name}</strong> — outcome: <strong>{_outcome_label}</strong>"
                f"</div>",
                unsafe_allow_html=True,
            )

            _conv_key = f"conv_{problem_id}_{_sel_id}"
            if _conv_key not in st.session_state:
                _full_persona = all_personas.get(_sel_id, _sel_persona)
                _j_log = next(
                    (l for l in _journey_logs if l.get("persona_id") == _sel_id), None
                )
                try:
                    _ctx = build_journey_context(_full_persona, _probe_results_raw, _j_log)
                    st.session_state[_conv_key] = PersonaConversation(
                        persona_id=_sel_id,
                        persona_name=_sel_name,
                        journey_context=_ctx,
                        outcome=_ctx.get("outcome", "unknown"),
                    )
                except Exception as _ce:
                    st.error(f"Could not build conversation context: {_ce}")

            conv = st.session_state.get(_conv_key)
            if conv:
                # Render conversation history
                for msg in conv.messages:
                    role_label = "You" if msg.role == "researcher" else _sel_name
                    align = "right" if msg.role == "researcher" else "left"
                    bg = "#EFF6FF" if msg.role == "researcher" else "#F9FAFB"
                    st.markdown(
                        f"<div style='text-align:{align};margin:6px 0'>"
                        f"<div style='display:inline-block;background:{bg};padding:10px 14px;"
                        f"border-radius:12px;max-width:80%;text-align:left;"
                        f"font-size:0.87rem'><strong>{role_label}:</strong> {msg.content}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                # Input
                st.caption("💡 Try asking: \"Why didn't you reorder after the first pack?\" · \"What would have made you try it sooner?\" · \"What did you tell your family about this product?\"")
                with st.form(key=f"conv_form_{_conv_key}", clear_on_submit=True):
                    _q = st.text_input(
                        "Ask a question",
                        placeholder="What made you hesitate before reordering?",
                        label_visibility="collapsed",
                    )
                    _send = st.form_submit_button("Send", use_container_width=False)

                if _send and _q.strip():
                    with st.spinner(f"{_sel_name} is thinking..."):
                        try:
                            _resp = _grounded_chat(conv, _q.strip())
                            st.rerun()
                        except Exception as _ce:
                            st.error(f"Could not get response: {_ce}")

                if conv.messages and st.button(
                    "Clear conversation", key=f"conv_clear_{_conv_key}"
                ):
                    del st.session_state[_conv_key]
                    st.rerun()


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="LittleJoys Persona Intelligence",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Business Problems"

    all_personas = load_all_personas()
    violations_report = load_violations_report()
    snap = _population_snapshot(all_personas)

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## LittleJoys\n**Persona Intelligence**")
        st.divider()

        page = st.radio(
            "Navigate",
            ["Business Problems", "Run Scenario", "Investigate", "Ask the Population", "Meet Your Consumers"],
            index={
                "Business Problems": 0,
                "Run Scenario": 1,
                "Investigate": 2,
                "Ask the Population": 3,
                "Meet Your Consumers": 4,
            }.get(st.session_state["nav_page"], 0),
        )
        if page != st.session_state["nav_page"]:
            st.session_state["nav_page"] = page
            st.rerun()

        st.divider()
        st.caption(f"**{snap['total']}** personas loaded")
        ab = snap["age_bands"]
        st.caption(
            f"Under-7: {ab.get('2–6',0)}  ·  "
            f"School-age: {ab.get('7–14',0)}  ·  "
            f"Mixed: {ab.get('both',0)}"
        )
        tiers = snap["tiers"]
        total = snap["total"]
        tier_pct = "  ·  ".join(f"{k} {round(100*v/total)}%" for k, v in sorted(tiers.items()))
        st.caption(tier_pct)

        # Quality indicator
        clean = violations_report.get("summary", {}).get("clean", "?")
        hard = violations_report.get("summary", {}).get("hard_violations", "?")
        if isinstance(clean, int) and isinstance(hard, int):
            pct = int(100 * clean / max(clean + hard, 1))
            st.caption(f"Population quality: {pct}% clean")
        st.divider()

    _render_calibration_status_sidebar(all_personas)

    # ── Route ────────────────────────────────────────────────────────────────
    nav = st.session_state["nav_page"]

    if nav == "Business Problems":
        page_home(all_personas)
    elif nav == "Run Scenario":
        page_run_scenario(all_personas)
    elif nav == "Investigate":
        page_investigate(all_personas)
    elif nav == "Ask the Population":
        page_ask_population(all_personas)
    elif nav == "Meet Your Consumers":
        page_persona_explorer(all_personas)
    elif nav == "_quality":
        page_data_quality(violations_report)


if __name__ == "__main__":
    main()
