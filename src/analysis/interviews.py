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

from src.analysis.interview_guardrails import run_all_guardrails
from src.analysis.interview_prompts import assemble_system_prompt
from src.constants import (
    INTERVIEW_AI_DISCLOSURE_PATTERNS,
    INTERVIEW_HISTORY_TAIL_TURNS,
    INTERVIEW_LLM_MODEL,
    INTERVIEW_MAX_CONTEXT_TOKENS,
    INTERVIEW_MAX_TURNS,
    INTERVIEW_RESPONSE_MAX_WORDS,
    INTERVIEW_RESPONSE_MIN_WORDS,
)

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona
    from src.utils.llm import LLMClient

logger = structlog.get_logger(__name__)

_QUESTION_INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "price": ("price", "cost", "expensive", "afford", "budget", "worth", "value", "rupee"),
    "trust": ("trust", "believe", "doctor", "pediatrician", "recommend", "safe", "research"),
    "routine": ("morning", "routine", "daily", "breakfast", "cooking", "time", "schedule"),
    "product": ("product", "nutrimix", "gummies", "supplement", "brand", "taste", "ingredients"),
    "barrier": ("why not", "hesitate", "concern", "worry", "stop you", "prevent", "barrier"),
    "influence": ("friend", "family", "influencer", "group", "whatsapp", "social media", "heard"),
    "child": ("child", "kid", "son", "daughter", "picky", "eat", "refuse"),
}
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


def _natural_budget_description(budget_consciousness: float) -> str:
    if budget_consciousness >= 0.75:
        return "I'm very careful about what we spend — every rupee counts"
    if budget_consciousness >= 0.5:
        return "I keep a close eye on our budget but I'll spend when it matters"
    if budget_consciousness >= 0.25:
        return "money isn't the first thing I think about when shopping"
    return "I don't worry too much about price if the quality is right"


def _natural_health_description(health_anxiety: float) -> str:
    if health_anxiety >= 0.75:
        return "I worry a lot about whether my kids are getting proper nutrition"
    if health_anxiety >= 0.5:
        return "I try to stay on top of their health without overthinking it"
    if health_anxiety >= 0.25:
        return "I trust that a balanced diet covers most of their needs"
    return "I believe kids are naturally resilient and don't stress about it"


def _natural_trust_description(medical_authority_trust: float) -> str:
    if medical_authority_trust >= 0.75:
        return "I always check with our pediatrician before trying anything new"
    if medical_authority_trust >= 0.5:
        return "I value medical advice but also do my own research"
    if medical_authority_trust >= 0.25:
        return "I prefer to research things myself rather than just follow doctor's orders"
    return "I trust my own instincts more than medical recommendations"


def _classify_question_intents(question: str) -> set[str]:
    lowered = question.lower()
    found = {
        name
        for name, keys in _QUESTION_INTENT_KEYWORDS.items()
        if any(keyword in lowered for keyword in keys)
    }
    return found or {"general"}


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
        self._last_input_tokens: int = 0
        self._last_output_tokens: int = 0
        self._last_model: str = ""

    @property
    def last_input_tokens(self) -> int:
        """Input tokens from the last real LLM call (0 if mock or not yet called)."""

        return self._last_input_tokens

    @property
    def last_output_tokens(self) -> int:
        """Output tokens from the last real LLM call (0 if mock or not yet called)."""

        return self._last_output_tokens

    @property
    def last_model_name(self) -> str:
        """Resolved model id from the last real LLM call."""

        return self._last_model

    def build_system_prompt(
        self,
        persona: Persona,
        scenario_id: str,
        decision_result: dict[str, Any],
    ) -> str:
        """Construct the in-character system prompt from persona and decision context.

        NOTE: The full Persona object is passed here, so assemble_system_prompt (and
        _build_memory_context within it) has access to persona.semantic_memory,
        persona.purchase_history, and persona.state. No subset filtering occurs at
        this call site.
        """
        return assemble_system_prompt(persona, scenario_id, decision_result)

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
        intents = _classify_question_intents(question)
        product_name = str(
            decision_result.get("product_name") or decision_result.get("product") or "the product"
        )
        outcome = str(decision_result.get("outcome", "reject")).lower()
        stage_raw = decision_result.get("rejection_stage")
        stage_s = str(stage_raw).lower() if stage_raw else ""
        history_prefix = "As I mentioned earlier, " if conversation_history else ""

        d = persona.demographics
        city = d.city_name
        sec = d.socioeconomic_class
        plat = persona.daily_routine.primary_shopping_platform.replace("_", " ")
        diet = persona.cultural.dietary_culture.replace("_", " ")
        ages = ", ".join(str(a) for a in d.child_ages)
        discovery = persona.media.product_discovery_channel.replace("_", " ")
        social = persona.media.primary_social_platform
        name = persona.display_name or f"a parent in {city}"

        awareness_mode = outcome == "reject" and stage_s == "awareness"
        purchase_mode = outcome == "reject" and stage_s == "purchase"

        def _sec_flavor() -> str:
            if sec in ("A1", "A2"):
                return "We are comfortable trying newer formats when the story is clear, but I still compare before I commit."
            if sec in ("C1", "C2"):
                return "At our income band, anything new has to earn its place in the monthly list — no casual splurges."
            return "I balance quality with what the month allows — not stingy, but not careless either."

        def _mock_awareness_block() -> str:
            return (
                f"{history_prefix}Honestly, {product_name} barely showed up in my world. I live in {city}, "
                f"shop mostly through {plat}, and I discover most things via {discovery} — plus whatever surfaces on {social}. "
                f"If it is not in those places, school pickup chat, or the medical shop counter, it is almost invisible to me. "
                f"My children are {ages} years old, and we eat {diet} at home. "
                "So the blocker was not a detailed opinion — I simply did not encounter it where I actually look."
            )

        def _mock_price_block() -> str:
            budget_desc = _natural_budget_description(persona.daily_routine.budget_consciousness)
            if outcome == "adopt":
                return (
                    f"{history_prefix}Price had to clear the bar, but as a {sec} household in {city}, I could justify {product_name} "
                    f"once the benefit felt concrete. {budget_desc}. I still compared it to what we already spend on powders and snacks, "
                    "and I wanted the routine to stay simple for the kids."
                )
            return (
                f"{history_prefix}Money is where I stalled. {budget_desc}, and {product_name} felt like an extra line item "
                f"on top of what we already buy through {plat}. {_sec_flavor()} "
                "If trust or results feel fuzzy, I postpone rather than stretch."
            )

        def _mock_trust_block() -> str:
            trust_desc = _natural_trust_description(persona.health.medical_authority_trust)
            sources = (
                ", ".join(persona.health.health_info_sources[:2])
                if persona.health.health_info_sources
                else "friends and family"
            )
            if awareness_mode:
                return (
                    f"{history_prefix}Trust matters to me — I usually start from {sources}, and {trust_desc} — "
                    f"but with {product_name} I never got far enough into the story for trust to even become the question. "
                    f"In {city}, with {diet} meals at home and kids aged {ages}, I need something to show up in my normal channels first."
                )
            return (
                f"{history_prefix}I rarely buy on hype alone. I start with {sources}, and {trust_desc}. "
                f"For {product_name}, I wanted the label and claims to feel honest, not loud, and I needed it to fit our mornings in {city}."
            )

        def _mock_routine_block() -> str:
            health_desc = _natural_health_description(persona.psychology.health_anxiety)
            return (
                f"{history_prefix}Mornings are the real test for us in {city}. I keep a {persona.daily_routine.breakfast_routine} breakfast rhythm, "
                f"the kids are {ages}, and {health_desc}. {product_name} only works for me if it slips into that routine without a fight."
            )

        def _mock_influence_block() -> str:
            return (
                f"{history_prefix}Word of mouth still matters here — WhatsApp groups, relatives, other parents at school in {city}. "
                f"I hear about products through {discovery} and {social} too. "
                f"For {product_name}, what I needed was a mention in that everyday noise, not a billboard nobody in my circle discusses."
            )

        def _mock_child_block() -> str:
            taste = persona.relationships.child_taste_veto
            veto = "If they push back on taste, I drop it fast." if taste >= 0.6 else "I try to steer what they eat, but I pick battles."
            return (
                f"{history_prefix}With my kids at ages {ages}, taste and habit beat theory. We are {diet} at home. {veto} "
                f"So anything like {product_name} has to pass the real-child test, not just look good on the pack."
            )

        def _mock_barrier_block() -> str:
            if awareness_mode:
                return _mock_awareness_block()
            if stage_s == "need_recognition":
                return (
                    f"{history_prefix}It never felt like an urgent gap for my children ({ages}) in {city}. "
                    f"Our usual meals and what we already buy through {plat} seemed enough, so {product_name} felt optional from the start."
                )
            if stage_s == "consideration":
                return (
                    f"{history_prefix}I looked sideways at {product_name} but the story did not lock in — claims, taste risk for the kids, "
                    f"and whether it matched our {diet} routine in {city}. I buy through {plat}, so I also thought about hassle and repeats."
                )
            if purchase_mode:
                return _mock_price_block()
            return (
                f"{history_prefix}A mix of fit and doubt. In {city}, with kids aged {ages}, I need clarity, a clean routine fit, "
                f"and a price that matches our {sec} reality. {product_name} stumbled on at least one of those for me."
            )

        def _mock_product_block() -> str:
            if awareness_mode:
                return _mock_awareness_block()
            return (
                f"{history_prefix}I judge products on ingredients I can understand, whether my children will accept the taste, "
                f"and how it fits {diet} meals in {city}. For {product_name}, I thought about those pieces against what I already trust from {plat}."
            )

        def _mock_general_block() -> str:
            health_desc = _natural_health_description(persona.psychology.health_anxiety)
            if awareness_mode:
                return _mock_awareness_block()
            return (
                f"{history_prefix}For me, {name}, life is a juggle between work, school runs, and meals in {city}. "
                f"The kids are {ages}, we eat {diet}, I shop via {plat}, and {health_desc}. "
                f"When someone asks about {product_name}, I answer through that real weekly rhythm, not a marketing story."
            )

        # Intent precedence: awareness rejection suppresses price-led framing.
        if awareness_mode and "price" in intents:
            body = _mock_awareness_block()
        elif "price" in intents and not awareness_mode:
            body = _mock_price_block()
        elif "trust" in intents:
            body = _mock_trust_block()
        elif "routine" in intents:
            body = _mock_routine_block()
        elif "barrier" in intents:
            body = _mock_barrier_block()
        elif "influence" in intents:
            body = _mock_influence_block()
        elif "child" in intents:
            body = _mock_child_block()
        elif "product" in intents:
            body = _mock_product_block()
        else:
            body = _mock_general_block()

        if outcome == "adopt":
            closing = (
                f" That is why I felt okay moving ahead with {product_name} for our routine in {city}, "
                "once it cleared taste, trust, and practicality together."
            )
        elif awareness_mode:
            closing = (
                f" So with {product_name}, the honest reason I never bought is I hardly met it in the places I actually shop and hear from — "
                "not because I studied the price in detail."
            )
        elif purchase_mode:
            closing = (
                f" At the purchase step, {product_name} bumped into money and commitment for our {sec} household — "
                "that is where I stopped."
            )
        else:
            closing = (
                f" That is why my final call on {product_name} was to "
                f"{'buy it' if outcome == 'adopt' else 'hold back'} once I weighed trust, routine, and what the month allows."
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

        self._last_input_tokens = 0
        self._last_output_tokens = 0
        self._last_model = ""

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
            self._last_input_tokens = int(response.input_tokens)
            self._last_output_tokens = int(response.output_tokens)
            self._last_model = str(response.model)

        guardrail_warnings = run_all_guardrails(
            response=response_text,
            question=question,
            persona=persona,
            decision_result=decision_result,
            previous_turns=conversation_history,
        )
        if guardrail_warnings:
            logger.info(
                "interview_guardrail_warnings",
                persona_id=persona.id,
                warnings=guardrail_warnings,
            )

        quality = check_interview_quality(response_text, persona, decision_result)
        all_warnings = quality.warnings + guardrail_warnings
        if all_warnings:
            logger.info(
                "interview_quality_warnings",
                persona_id=persona.id,
                warnings=all_warnings,
            )

        return InterviewTurn(role="persona", content=response_text, timestamp=_iso_timestamp())
