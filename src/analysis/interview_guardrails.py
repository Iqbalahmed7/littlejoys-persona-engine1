"""Interview quality guardrails for post-response validation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.analysis.interviews import InterviewTurn
    from src.taxonomy.schema import Persona

OUT_OF_SCOPE_PATTERNS: list[str] = [
    "election",
    "vote",
    "political",
    "bjp",
    "congress",
    "modi",
    "parliament",
    "government policy",
    "cricket",
    "ipl",
    "football",
    "world cup",
    "stock market",
    "mutual fund",
    "investment portfolio",
    "crypto",
    "shares",
    "trading",
    "office politics",
    "promotion",
    "appraisal",
    "boss",
    "colleague",
    "religion",
    "hindu",
    "muslim",
    "christian",
    "caste",
    "bollywood",
    "movie review",
    "celebrity gossip",
]

SEC_PREMIUM_REFERENCES: set[str] = {
    "organic harvest",
    "slurrp farm",
    "by gummies",
    "wholesome first",
    "the whole truth",
    "yoga bar",
    "raw pressery",
    "farm to fork",
    "imported",
    "artisanal",
    "curated",
    "subscription box",
    "nutritionist consultation",
    "private pediatrician",
}

SEC_BUDGET_MARKERS: set[str] = {
    "can't afford",
    "too expensive for us",
    "out of our budget",
    "government hospital",
    "free sample",
    "ration shop",
    "monthly ration",
    "stretching our budget",
}

SEC_SHOPPING_TIERS: dict[str, set[str]] = {
    "premium": {
        "blinkit",
        "bigbasket",
        "amazon fresh",
        "nature's basket",
        "organic store",
        "whole foods",
    },
    "mass": {"amazon", "flipkart", "dmart", "reliance fresh"},
    "budget": {"kirana", "local store", "medical shop", "weekly market"},
}

LEADING_QUESTION_PATTERNS: list[str] = [
    "don't you think",
    "wouldn't you agree",
    "isn't it true that",
    "surely you",
    "you must feel",
    "everyone knows that",
    "most parents think",
    "any good parent would",
    "you have to admit",
    "obviously",
]

AGREEMENT_MARKERS: list[str] = [
    "you're absolutely right",
    "yes, exactly",
    "i completely agree",
    "that's exactly what i think",
    "you took the words out of my mouth",
    "couldn't agree more",
    "you're so right",
    "absolutely, yes",
    "i was just thinking that",
]

_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")
_CHILD_CONTEXT_MARKERS = ("child", "kid", "son", "daughter")
_SENTIMENT_POSITIVE = (
    "love it",
    "love using",
    "would buy",
    "works for us",
    "buy it",
    "worth it",
)
_SENTIMENT_NEGATIVE = (
    "would not buy",
    "wouldn't buy",
    "never buy",
    "waste of money",
    "don't need it",
    "not for us",
)
_BRANDS = ("horlicks", "bournvita", "pediasure", "complan", "nutrimix", "littlejoys")


def _pattern_regex(pattern: str) -> re.Pattern[str]:
    escaped = re.escape(pattern).replace(r"\ ", r"\s+")
    return re.compile(rf"\b{escaped}\b", flags=re.IGNORECASE)


def _normalize(text: str) -> str:
    return text.lower().strip()


def check_scope_violation(response: str) -> list[str]:
    """Flag responses that venture outside the study domain."""

    lowered = _normalize(response)
    if not lowered:
        return []

    warnings: list[str] = []
    sentences = [sentence.strip() for sentence in _SENTENCE_SPLIT_RE.split(lowered) if sentence.strip()]
    for pattern in OUT_OF_SCOPE_PATTERNS:
        regex = _pattern_regex(pattern)
        for sentence in sentences:
            if not regex.search(sentence):
                continue
            # Child sports context can still be in-domain (for routines/taste/parenting context).
            if pattern in {"cricket", "football"} and any(
                marker in sentence for marker in _CHILD_CONTEXT_MARKERS
            ):
                continue
            warnings.append(f"scope_violation:{pattern}")
            break
    return warnings


def check_sec_coherence(response: str, persona: Persona) -> list[str]:
    """Flag if persona references brands/experiences outside their SEC reality."""

    lowered = _normalize(response)
    if not lowered:
        return []

    warnings: list[str] = []
    sec = persona.demographics.socioeconomic_class
    income = float(persona.demographics.household_income_lpa)
    primary_platform = persona.daily_routine.primary_shopping_platform.lower()

    if sec in {"C1", "C2"} and income < 8.0 and any(
        reference in lowered for reference in SEC_PREMIUM_REFERENCES
    ):
        warnings.append("sec_incoherent_premium_reference")

    if sec == "A1" and income > 25.0 and any(marker in lowered for marker in SEC_BUDGET_MARKERS):
        warnings.append("sec_incoherent_affordability_claim")

    premium_platform_mentions = sum(
        1 for platform in SEC_SHOPPING_TIERS["premium"] if platform in lowered
    )
    if primary_platform == "local_store" and premium_platform_mentions > 0:
        warnings.append("sec_incoherent_shopping_reference")

    return warnings


def check_reframing_susceptibility(
    response: str,
    question: str,
) -> list[str]:
    """Flag if persona too readily agrees with a leading question."""

    lowered_question = _normalize(question)
    lowered_response = _normalize(response)
    is_leading = any(pattern in lowered_question for pattern in LEADING_QUESTION_PATTERNS)
    if not is_leading:
        return []
    if any(marker in lowered_response for marker in AGREEMENT_MARKERS):
        return ["reframing_susceptibility_high"]
    return []


def _persona_turn_texts(previous_turns: list[InterviewTurn]) -> list[str]:
    return [turn.content.lower() for turn in previous_turns if turn.role == "persona"]


def _sentiment_kind(text: str) -> str | None:
    has_positive = any(pattern in text for pattern in _SENTIMENT_POSITIVE)
    has_negative = any(pattern in text for pattern in _SENTIMENT_NEGATIVE)
    if has_positive and not has_negative:
        return "positive"
    if has_negative and not has_positive:
        return "negative"
    return None


def _extract_brand_positions(text: str) -> dict[str, str]:
    positions: dict[str, str] = {}
    for brand in _BRANDS:
        use_pattern = re.compile(
            rf"\b(i|we)\s+(use|used|buy|bought|take|have)\s+{re.escape(brand)}\b",
            flags=re.IGNORECASE,
        )
        no_use_pattern = re.compile(
            rf"\b(i|we)\s+(have\s+)?(never used|don't use|do not use|haven't used|never bought|never brought|don't buy|do not buy)\s+{re.escape(brand)}\b",
            flags=re.IGNORECASE,
        )
        if use_pattern.search(text):
            positions[brand] = "uses"
        if no_use_pattern.search(text):
            positions[brand] = "does_not_use"
    return positions


def check_cross_turn_consistency(
    current_response: str,
    previous_turns: list[InterviewTurn],
    persona: Persona,
) -> list[str]:
    """Detect contradictions between current response and prior turns."""

    if not previous_turns:
        return []

    current = _normalize(current_response)
    prior_persona_turns = _persona_turn_texts(previous_turns)
    if not prior_persona_turns:
        return []

    warnings: list[str] = []
    current_sentiment = _sentiment_kind(current)
    prior_sentiments = {_sentiment_kind(text) for text in prior_persona_turns}
    if (
        (current_sentiment == "positive" and "negative" in prior_sentiments)
        or (current_sentiment == "negative" and "positive" in prior_sentiments)
    ):
        warnings.append("sentiment_flip_detected")

    current_brand_positions = _extract_brand_positions(current)
    for prior in prior_persona_turns:
        prior_brand_positions = _extract_brand_positions(prior)
        for brand, current_position in current_brand_positions.items():
            prior_position = prior_brand_positions.get(brand)
            if prior_position and prior_position != current_position:
                warnings.append("brand_reference_contradiction")
                break
        if "brand_reference_contradiction" in warnings:
            break

    low_income = float(persona.demographics.household_income_lpa) < 8.0
    if (
        low_income
        and any(reference in current for reference in SEC_PREMIUM_REFERENCES)
        and any(marker in prior for marker in SEC_BUDGET_MARKERS for prior in prior_persona_turns)
    ):
        warnings.append("income_lifestyle_inconsistency")

    return warnings


def run_all_guardrails(
    response: str,
    question: str,
    persona: Persona,
    decision_result: dict[str, Any],
    previous_turns: list[InterviewTurn] | None = None,
) -> list[str]:
    """Run all guardrail checks and return aggregated warnings."""

    del decision_result
    warnings: list[str] = []
    warnings.extend(check_scope_violation(response))
    warnings.extend(check_sec_coherence(response, persona))
    warnings.extend(check_reframing_susceptibility(response, question))
    if previous_turns:
        warnings.extend(check_cross_turn_consistency(response, previous_turns, persona))
    return warnings
