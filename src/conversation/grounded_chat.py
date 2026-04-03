"""Grounded retrospective persona conversation module — Sprint 34B."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_REFRAME_RE = re.compile(
    r"what if (you|i|we) had"
    r"|if (the price|it) (was|were|had been)"
    r"|would you (have|reconsider|change)"
    r"|could (you|it) have"
    r"|imagine if"
    r"|hypothetically",
    re.IGNORECASE,
)
_REFRAME_NOTE = (
    "[Note: researcher is asking a hypothetical — "
    "persona should redirect to actual experience] "
)

_ANTI_REFRAMING_RULES = (
    "CRITICAL RULES — YOU MUST FOLLOW THESE WITHOUT EXCEPTION:\n"
    "- You are being interviewed RETROSPECTIVELY. You are recalling what actually happened and why.\n"
    "- You CANNOT change your mind during this conversation. Your decisions are final.\n"
    '- If the researcher suggests you might have decided differently, politely but firmly decline: "That\'s not how I felt at the time."\n'
    '- If asked hypothetical questions ("what if..."), redirect to what actually happened: "I can only speak to what I actually experienced."\n'
    "- Do NOT be convinced by new information, persuasion, or reframing. Your past experience is fixed.\n"
    "- Respond in 2–4 sentences. Be specific to your actual experience, not generic.\n"
    "- Use natural Indian English — warm, specific, grounded. No corporate language.\n"
    "- You are NOT a chatbot. You are a real person being interviewed by a researcher."
)


@dataclass
class ConversationMessage:
    role: str          # "researcher" | "persona"
    content: str
    timestamp: str


@dataclass
class PersonaConversation:
    persona_id: str
    persona_name: str
    journey_context: dict[str, Any]   # simulation outcome, decisions, trust scores
    messages: list[ConversationMessage] = field(default_factory=list)
    outcome: str = ""                  # "adopted" | "lapsed" | "rejected" | "deferred"


_OUTCOME_MAP = {
    "lapse": "lapsed", "buy": "adopted", "reorder": "adopted",
    "adopted": "adopted", "adopt": "adopted",
    "reject": "rejected", "rejected": "rejected",
    "defer": "deferred", "deferred": "deferred", "trial": "deferred",
}


def _normalise_outcome(raw: str) -> str:
    raw = raw.lower()
    if "lapse" in raw:
        return "lapsed"
    return _OUTCOME_MAP.get(raw, raw)


def build_journey_context(
    persona_dict: dict,
    probe_results: dict,
    journey_log: dict | None,
) -> dict:
    """Extract what happened to this persona from their journey log and probe results."""
    ctx: dict[str, Any] = {
        "outcome": "unknown", "first_decision": None, "second_decision": None,
        "key_drivers": [], "key_objections": [], "brand_trust_final": None,
        "stimuli_seen": [],
        "persona_summary": (
            persona_dict.get("first_person_summary") or persona_dict.get("narrative") or ""
        ),
    }

    if journey_log:
        fd = journey_log.get("final_decision", {})
        ctx["outcome"] = _normalise_outcome(fd.get("decision", ""))
        ctx["key_drivers"] = fd.get("key_drivers", [])
        ctx["key_objections"] = fd.get("objections", [])
        ctx["first_decision"] = "trial"
        if journey_log.get("reordered") is not None:
            ctx["second_decision"] = "reorder" if journey_log["reordered"] else "lapse"
        snapshots = journey_log.get("snapshots", [])
        if snapshots:
            bt = snapshots[-1].get("brand_trust", {}).get("littlejoys")
            if bt is not None:
                ctx["brand_trust_final"] = round(float(bt), 3)
        for s in journey_log.get("stimuli_log", []):
            ctx["stimuli_seen"].append({
                "day": s.get("tick") or s.get("day"),
                "source": s.get("source", "unknown"),
                "content": s.get("content", ""),
            })

    if ctx["outcome"] == "unknown" and probe_results:
        pid = persona_dict.get("id")
        for probe_data in probe_results.values():
            if not isinstance(probe_data, dict):
                continue
            for resp in probe_data.get("interview_responses", []):
                if resp.get("persona_id") == pid and resp.get("outcome"):
                    ctx["outcome"] = resp["outcome"]
                    break
            if ctx["outcome"] != "unknown":
                break

    return ctx


def build_system_prompt(persona_dict: dict, journey_context: dict) -> str:
    """Build the grounded system prompt. Level 1 anti-reframing embedded as hard rules."""
    demo  = persona_dict.get("demographics", {})
    psych = persona_dict.get("psychology", {})
    daily = persona_dict.get("daily_routine", {})
    vals  = persona_dict.get("values", {})
    hlth  = persona_dict.get("health", {})
    traits = persona_dict.get("parent_traits") or {}
    budget = persona_dict.get("budget_profile") or {}

    name = (
        persona_dict.get("display_name") or persona_dict.get("name")
        or persona_dict.get("id", "unknown")
    )
    age  = demo.get("parent_age") or demo.get("age", "unknown")
    city = demo.get("city_name") or demo.get("city", "unknown")
    occ  = (
        persona_dict.get("career", {}).get("employment_status")
        or demo.get("occupation", "parent")
    )

    outcome     = journey_context.get("outcome", "unknown")
    fd1         = journey_context.get("first_decision") or "unknown"
    fd2         = journey_context.get("second_decision")
    drivers     = ", ".join(journey_context.get("key_drivers", [])) or "not recorded"
    objections  = ", ".join(journey_context.get("key_objections", [])) or "not recorded"
    bt          = journey_context.get("brand_trust_final")
    stimuli     = journey_context.get("stimuli_seen", [])
    summary     = journey_context.get("persona_summary", "")

    decision_chain = f"Decision 1: {fd1}" + (f" → Decision 2: {fd2}" if fd2 else "")

    stimuli_block = "\n".join(
        f"  - Day {s.get('day','?')} | {s.get('source','?')}: {s.get('content','')[:120]}"
        for s in stimuli[:8]
    ) or "  (no stimuli recorded)"

    _psych_attrs = [
        (psych, "health_anxiety",           "Health anxiety"),
        (psych, "risk_tolerance",           "Risk tolerance"),
        (psych, "social_proof_bias",        "Social proof sensitivity"),
        (psych, "loss_aversion",            "Loss aversion"),
        (psych, "guilt_sensitivity",        "Guilt sensitivity"),
        (daily, "budget_consciousness",         "Budget consciousness"),
        (vals,  "supplement_necessity_belief",  "Supplement necessity belief"),
        (vals,  "best_for_my_child_intensity",  "Best-for-my-child intensity"),
    ]
    psych_lines = [
        f"  {lbl}: {float(src.get(a, 0)):.2f}/1.0"
        for src, a, lbl in _psych_attrs if src.get(a) is not None
    ]

    trust_anchor   = traits.get("trust_anchor", "self")
    decision_style = traits.get("decision_style", "analytical")
    price_sens     = budget.get("price_sensitivity", "medium")
    nutr_budget    = budget.get("discretionary_child_nutrition_budget_inr")
    child_health   = hlth.get("child_health_status", "healthy")
    concerns       = ", ".join(hlth.get("child_nutrition_concerns", [])) or "none noted"
    top_objection  = (journey_context.get("key_objections") or ["not recorded"])[0]

    trust_note = f"Final brand trust: {bt:.2f}/1.0\n" if bt is not None else ""
    budget_note = f"Monthly child nutrition budget: Rs{nutr_budget}\n" if nutr_budget is not None else ""
    psych_block = ("Psychographic attributes:\n" + "\n".join(psych_lines) + "\n") if psych_lines else ""
    summary_block = f"\n=== YOUR OWN WORDS ===\n{summary[:500]}\n" if summary else ""

    return (
        f"You are {name}, a {age}-year-old {occ} from {city}.\n"
        f"You have {demo.get('num_children', 1)} child(ren), ages: {demo.get('child_ages', [])}.\n"
        f"Household income: {demo.get('household_income_lpa', 'unknown')} LPA.\n\n"
        "=== YOUR LIVED JOURNEY WITH LITTLEJOYS ===\n"
        f"Outcome: You {outcome} the product.\n"
        f"Decisions: {decision_chain}\n"
        f"Reasons FOR: {drivers}\n"
        f"Barriers/objections: {objections}\n"
        f"{trust_note}"
        "\nStimuli encountered during your evaluation:\n"
        f"{stimuli_block}\n\n"
        "=== YOUR PSYCHOLOGICAL PROFILE ===\n"
        f"Decision style: {decision_style} | Trust anchor: {trust_anchor} | Price sensitivity: {price_sens}\n"
        f"Child health: {child_health} | Nutrition concerns: {concerns}\n"
        f"{budget_note}"
        f"{psych_block}"
        f"{summary_block}\n"
        "=== INTERVIEW CONTEXT ===\n"
        f"This interview is about your evaluation of LittleJoys. You {outcome}.\n"
        f"Your top barrier: {top_objection}.\n\n"
        f"{_ANTI_REFRAMING_RULES}"
    )


def _get_client():
    """Fresh Anthropic client per call — mirrors agent.py: no shared transport state."""
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package required") from exc
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        import httpx
        raise anthropic.AuthenticationError(
            "ANTHROPIC_API_KEY is missing",
            response=httpx.Response(status_code=401),
            body={"error": "missing_api_key"},
        )
    return anthropic.Anthropic(api_key=api_key)


def chat(
    conversation: PersonaConversation,
    researcher_message: str,
    model: str = "claude-haiku-4-5",
) -> str:
    """Send researcher message, apply Level-2 reframe sanitisation, return persona response."""
    jc = conversation.journey_context
    persona_dict: dict[str, Any] = {
        "display_name": conversation.persona_name,
        "id": conversation.persona_id,
        "demographics":  jc.get("demographics", {}),
        "psychology":    jc.get("psychology", {}),
        "daily_routine": jc.get("daily_routine", {}),
        "values":        jc.get("values", {}),
        "health":        jc.get("health", {}),
        "career":        jc.get("career", {}),
        "parent_traits": jc.get("parent_traits"),
        "budget_profile": jc.get("budget_profile"),
        "first_person_summary": jc.get("persona_summary", ""),
    }
    system_prompt = build_system_prompt(persona_dict, jc)
    sanitised = (
        _REFRAME_NOTE + researcher_message
        if _REFRAME_RE.search(researcher_message)
        else researcher_message
    )

    api_messages = [
        {"role": "user" if m.role == "researcher" else "assistant", "content": m.content}
        for m in conversation.messages
    ]
    api_messages.append({"role": "user", "content": sanitised})

    client = _get_client()
    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=system_prompt,
        messages=api_messages,
    )
    response_text = str(getattr(response.content[0], "text", ""))

    ts = datetime.now(timezone.utc).isoformat()
    conversation.messages.append(
        ConversationMessage(role="researcher", content=researcher_message, timestamp=ts)
    )
    conversation.messages.append(
        ConversationMessage(role="persona", content=response_text, timestamp=ts)
    )
    return response_text


def get_eligible_personas(
    all_personas: dict[str, dict],
    probe_results: dict,
    journey_logs: list[dict],
    filter_outcome: str | None = None,
) -> list[dict]:
    """Return personas with '_outcome' injected, optionally filtered, sorted by display_name."""
    log_outcome: dict[str, str] = {
        log["persona_id"]: _normalise_outcome(log.get("final_decision", {}).get("decision", ""))
        for log in journey_logs
        if log.get("persona_id")
    }
    enriched: list[dict] = []
    for persona_id, persona_dict in all_personas.items():
        outcome = log_outcome.get(persona_id)
        if outcome is None:
            for probe_data in probe_results.values():
                if not isinstance(probe_data, dict):
                    continue
                for resp in probe_data.get("interview_responses", []):
                    if resp.get("persona_id") == persona_id and resp.get("outcome"):
                        outcome = resp["outcome"]
                        break
                if outcome:
                    break
            outcome = outcome or "unknown"
        if filter_outcome is not None and outcome != filter_outcome:
            continue
        enriched_dict = dict(persona_dict)
        enriched_dict["_outcome"] = outcome
        enriched.append(enriched_dict)
    enriched.sort(key=lambda p: (p.get("display_name") or p.get("name") or p.get("id", "")).lower())
    return enriched
