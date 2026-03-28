"""
Deep persona interview system — interactive conversations with Tier 2 personas.

The LLM role-plays as a specific persona, staying in character with their
attributes, narrative, and simulation history.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field

from src.constants import (
    INTERVIEW_AI_DISCLOSURE_PATTERNS,
    INTERVIEW_HISTORY_TAIL_TURNS,
    INTERVIEW_LLM_MODEL,
    INTERVIEW_MAX_CONTEXT_TOKENS,
    INTERVIEW_MAX_TURNS,
    INTERVIEW_RESPONSE_MAX_WORDS,
    INTERVIEW_RESPONSE_MIN_WORDS,
    INTERVIEW_TOP_PSYCHOGRAPHIC_HIGHLIGHTS,
)
from src.decision.scenarios import get_scenario

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona
    from src.utils.llm import LLMClient

logger = structlog.get_logger(__name__)

_PSYCHOGRAPHIC_CANDIDATES = (
    "health_anxiety",
    "comparison_anxiety",
    "authority_bias",
    "social_proof_bias",
    "budget_consciousness",
    "supplement_necessity_belief",
    "best_for_my_child_intensity",
    "medical_authority_trust",
    "pediatrician_influence",
    "perceived_time_scarcity",
    "simplicity_preference",
    "child_taste_veto",
    "transparency_importance",
    "ad_receptivity",
    "influencer_trust",
)
_POSITIVE_PRODUCT_PATTERNS = (
    "buy it",
    "bought it",
    "love this product",
    "worth it",
    "works for us",
)
_NEGATIVE_PRODUCT_PATTERNS = (
    "would not buy",
    "wouldn't buy",
    "avoid it",
    "not for us",
    "skip it",
)


class InterviewTurn(BaseModel):
    """One conversational turn in a persona interview."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "persona"]
    content: str
    timestamp: str


class InterviewSession(BaseModel):
    """State container for a multi-turn persona interview."""

    model_config = ConfigDict(extra="forbid")

    persona_id: str
    persona_name: str
    scenario_id: str
    turns: list[InterviewTurn] = Field(default_factory=list)
    persona_outcome: str


class InterviewQualityCheck(BaseModel):
    """Simple heuristics for validating in-character interview replies."""

    model_config = ConfigDict(extra="forbid")

    in_character: bool
    references_profile: bool
    appropriate_length: bool
    no_ai_disclosure: bool
    warnings: list[str] = Field(default_factory=list)


def _iso_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _llm_route(model_name: str) -> Literal["reasoning", "bulk"]:
    return "reasoning" if model_name == "opus" else "bulk"


def _daily_routine_summary(persona: Persona) -> str:
    if persona.narrative:
        return persona.narrative
    return (
        f"You keep a {persona.daily_routine.breakfast_routine} breakfast routine, shop mainly on "
        f"{persona.daily_routine.primary_shopping_platform}, and balance family needs with a "
        f"{persona.career.employment_status.replace('_', ' ')} work schedule."
    )


def _psychographic_highlights(persona: Persona) -> list[str]:
    flat = persona.to_flat_dict()
    scored: list[tuple[str, float]] = []
    for key in _PSYCHOGRAPHIC_CANDIDATES:
        value = flat.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            scored.append((key, float(value)))

    scored.sort(key=lambda item: abs(item[1] - 0.5), reverse=True)
    highlights = []
    for key, value in scored[:INTERVIEW_TOP_PSYCHOGRAPHIC_HIGHLIGHTS]:
        if value >= 0.7:
            qualifier = "strong"
        elif value <= 0.3:
            qualifier = "low"
        else:
            qualifier = "moderate"
        highlights.append(f"- {key} = {value:.2f} ({qualifier} signal in your decision style)")
    return highlights


def check_interview_quality(
    response: str,
    persona: Persona,
    decision_result: dict[str, Any],
) -> InterviewQualityCheck:
    """Validate interview quality with lightweight heuristic checks."""

    lowered = response.lower()
    warnings: list[str] = []

    no_ai_disclosure = not any(pattern in lowered for pattern in INTERVIEW_AI_DISCLOSURE_PATTERNS)
    if not no_ai_disclosure:
        warnings.append("response_discloses_ai_identity")

    word_count = len(response.split())
    appropriate_length = INTERVIEW_RESPONSE_MIN_WORDS <= word_count <= INTERVIEW_RESPONSE_MAX_WORDS
    if not appropriate_length:
        warnings.append("response_length_out_of_bounds")

    profile_markers = {
        persona.demographics.city_name.lower(),
        persona.demographics.city_tier.lower(),
        persona.career.employment_status.replace("_", " ").lower(),
        persona.education_learning.education_level.lower(),
        persona.media.primary_social_platform.lower(),
        str(persona.demographics.child_ages[0]),
    }
    concerns = {concern.replace("_", " ") for concern in persona.health.child_nutrition_concerns}
    product_name = str(
        decision_result.get("product_name")
        or decision_result.get("product")
        or decision_result.get("scenario_id", "")
    ).lower()
    references_profile = any(
        marker and marker in lowered for marker in profile_markers | concerns | {product_name}
    )
    if not references_profile:
        warnings.append("response_does_not_reference_profile")

    outcome = str(decision_result.get("outcome", "")).lower()
    sentiment_consistent = True
    if outcome == "reject" and any(pattern in lowered for pattern in _POSITIVE_PRODUCT_PATTERNS):
        sentiment_consistent = False
        warnings.append("response_sentiment_inconsistent_with_rejection")
    if outcome == "adopt" and any(pattern in lowered for pattern in _NEGATIVE_PRODUCT_PATTERNS):
        sentiment_consistent = False
        warnings.append("response_sentiment_inconsistent_with_adoption")

    return InterviewQualityCheck(
        in_character=no_ai_disclosure and references_profile and sentiment_consistent,
        references_profile=references_profile,
        appropriate_length=appropriate_length,
        no_ai_disclosure=no_ai_disclosure,
        warnings=warnings,
    )


class PersonaInterviewer:
    """Conducts interactive interviews with Tier 2 personas via LLM."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    def build_system_prompt(
        self,
        persona: Persona,
        scenario_id: str,
        decision_result: dict[str, Any],
    ) -> str:
        """Construct the in-character system prompt from persona and decision context."""

        scenario = get_scenario(scenario_id)
        concern_text = ", ".join(persona.health.child_nutrition_concerns) or "none called out"
        psychographic_text = "\n".join(_psychographic_highlights(persona))
        decision_outcome = str(decision_result.get("outcome", "unknown"))
        rejection_reason = decision_result.get("rejection_reason")

        decision_context = (
            f"You are deciding about {scenario.product.name} in scenario {scenario_id}.\n"
            f"Outcome: {decision_outcome}\n"
            f"need_score={float(decision_result.get('need_score', 0.0)):.2f}, "
            f"awareness_score={float(decision_result.get('awareness_score', 0.0)):.2f}, "
            f"consideration_score={float(decision_result.get('consideration_score', 0.0)):.2f}, "
            f"purchase_score={float(decision_result.get('purchase_score', 0.0)):.2f}\n"
        )
        if rejection_reason:
            decision_context += f"Rejection reason: {rejection_reason}\n"

        return (
            f"You are persona {persona.id}, a {persona.demographics.parent_age}-year-old "
            f"{persona.career.employment_status.replace('_', ' ')} parent in "
            f"{persona.demographics.city_name} ({persona.demographics.city_tier}).\n"
            f"Education: {persona.education_learning.education_level}\n"
            f"Household income: {persona.demographics.household_income_lpa:.1f} LPA\n"
            f"Family structure: {persona.demographics.family_structure}\n"
            f"Children: {persona.demographics.num_children} child(ren) aged "
            f"{persona.demographics.child_ages} with concerns: {concern_text}\n\n"
            f"Psychographic highlights:\n{psychographic_text}\n\n"
            f"Daily routine summary:\n{_daily_routine_summary(persona)}\n\n"
            f"Decision context:\n{decision_context}\n"
            "Rules:\n"
            "- Stay completely in character.\n"
            "- Reference specific details from the profile.\n"
            "- Relate price questions to actual income and spending patterns.\n"
            "- Relate trust questions to actual information sources and decision style.\n"
            "- Do not break character or acknowledge being AI.\n"
            "- Use natural speech patterns appropriate to the persona.\n"
        )

    async def start_session(
        self,
        persona: Persona,
        scenario_id: str,
        decision_result: dict[str, Any],
    ) -> InterviewSession:
        """Create a fresh interview session container."""

        outcome = str(decision_result.get("outcome", "unknown"))
        logger.info("interview_session_started", persona_id=persona.id, scenario_id=scenario_id)
        return InterviewSession(
            persona_id=persona.id,
            persona_name=persona.id,
            scenario_id=scenario_id,
            turns=[],
            persona_outcome=outcome,
        )

    def _render_history(self, conversation_history: list[InterviewTurn] | None) -> str:
        if not conversation_history:
            return "No prior conversation."

        trimmed_history = conversation_history[-INTERVIEW_HISTORY_TAIL_TURNS:]
        rendered = "\n".join(f"{turn.role.upper()}: {turn.content}" for turn in trimmed_history)
        approx_tokens = max(1, len(rendered) // 4)
        if approx_tokens <= INTERVIEW_MAX_CONTEXT_TOKENS:
            return rendered

        summary = f"Earlier conversation summary: {len(conversation_history) - len(trimmed_history)} older turns discussed price, trust, and routine.\n"
        return summary + rendered

    def _build_mock_response(
        self,
        persona: Persona,
        question: str,
        decision_result: dict[str, Any],
        conversation_history: list[InterviewTurn] | None,
    ) -> str:
        lowered = question.lower()
        product_name = str(
            decision_result.get("product_name") or decision_result.get("product") or "the product"
        )
        outcome = str(decision_result.get("outcome", "reject")).lower()
        history_prefix = "As I mentioned earlier, " if conversation_history else ""

        if "price" in lowered:
            if outcome == "adopt":
                body = (
                    f"{history_prefix}the price still has to feel justified, but with our roughly "
                    f"{persona.demographics.household_income_lpa:.1f} lakh household income I could make room for "
                    f"{product_name} because it matched my {persona.values.best_for_my_child_intensity:.2f} level of "
                    "wanting the best for my child. I still compare it against what I already buy and whether the "
                    "benefits feel real, but if the routine is simple and I trust the ingredients, I can stretch a little."
                )
            else:
                body = (
                    f"{history_prefix}price was exactly where I hesitated. With our income at about "
                    f"{persona.demographics.household_income_lpa:.1f} lakh and my budget_consciousness sitting around "
                    f"{persona.daily_routine.budget_consciousness:.2f}, {product_name} felt like one more premium add-on. "
                    "If I am not fully convinced on trust and visible results, I will usually delay or skip the purchase."
                )
        elif "trust" in lowered or "doctor" in lowered:
            body = (
                f"{history_prefix}I rarely buy on hype alone. I usually start with {', '.join(persona.health.health_info_sources[:2])}, "
                f"and because my medical_authority_trust is {persona.health.medical_authority_trust:.2f}, a pediatrician's opinion "
                "matters more to me than influencer chatter. I need the label to look clean, the claim to sound sensible, and the "
                "routine to fit how our mornings actually work."
            )
        else:
            body = (
                f"{history_prefix}life in {persona.demographics.city_name} already feels like a steady juggle between "
                f"work, school, and meals, so I answer most product questions through that lens. My child is {persona.demographics.child_ages[0]}, "
                f"I keep a {persona.daily_routine.breakfast_routine} breakfast routine, and my health_anxiety is {persona.psychology.health_anxiety:.2f}, "
                "so I care about nutrition, but I also want practical choices that my family can actually sustain."
            )

        closing = (
            f" That is why my final call on {product_name} was to "
            f"{'buy it' if outcome == 'adopt' else 'hold back'} based on whether it fit both my trust standard and our daily routine."
        )
        return f"{body}{closing}"

    async def interview(
        self,
        persona: Persona,
        question: str,
        scenario_id: str,
        decision_result: dict[str, Any],
        conversation_history: list[InterviewTurn] | None = None,
    ) -> InterviewTurn:
        """
        Ask a Tier 2 persona a question and get an in-character response.

        The response must be consistent with all persona attributes and their
        simulation outcome (adopted/rejected and why).
        """

        if conversation_history and len(conversation_history) >= INTERVIEW_MAX_TURNS:
            raise ValueError("conversation_history exceeds INTERVIEW_MAX_TURNS")

        system_prompt = self.build_system_prompt(persona, scenario_id, decision_result)
        history_block = self._render_history(conversation_history)

        if self.llm.config.llm_mock_enabled:
            response_text = self._build_mock_response(
                persona=persona,
                question=question,
                decision_result=decision_result,
                conversation_history=conversation_history,
            )
        else:
            prompt = (
                f"Conversation so far:\n{history_block}\n\n"
                f"User question: {question}\n\n"
                "Respond as the persona in 100-200 words."
            )
            response = await self.llm.generate(
                prompt=prompt,
                system=system_prompt,
                model=_llm_route(INTERVIEW_LLM_MODEL),
            )
            response_text = response.text.strip()

        quality = check_interview_quality(response_text, persona, decision_result)
        if quality.warnings:
            logger.info(
                "interview_quality_warnings",
                persona_id=persona.id,
                warnings=quality.warnings,
            )

        return InterviewTurn(role="persona", content=response_text, timestamp=_iso_timestamp())
