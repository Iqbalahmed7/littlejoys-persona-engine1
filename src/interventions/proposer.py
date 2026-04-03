"""
proposer.py — Maps confirmed/inconclusive hypotheses to concrete intervention proposals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.probing.models import Hypothesis, ProblemStatement, TreeSynthesis

logger = logging.getLogger(__name__)

# ── Keyword → intervention_type mapping ───────────────────────────────────────

_KEYWORD_MAP: list[tuple[list[str], str]] = [
    (["aware", "know", "heard"], "awareness"),
    (["price", "cost", "expensive", "budget"], "pricing"),
    (["trust", "doctor", "credib"], "channel"),
    (["taste", "format", "texture", "reject"], "sampling"),
    (["reorder", "habit", "remind", "re-engage"], "retention"),
    (["channel", "availab", "find"], "distribution"),
]


def _classify_hypothesis(hyp: Hypothesis) -> str:
    """Return the best matching intervention_type for this hypothesis."""
    text = f"{hyp.title} {hyp.rationale}".lower()
    for keywords, itype in _KEYWORD_MAP:
        if any(kw in text for kw in keywords):
            return itype
    return "awareness"  # sensible default


# ── Journey-modification templates ────────────────────────────────────────────

def _build_modifications(itype: str, hyp: Hypothesis, confidence: float) -> dict[str, Any]:
    if itype == "awareness":
        return {
            "add_stimuli": [
                {
                    "tick": 5,
                    "type": "social_event",
                    "source": "pediatrician",
                    "content": (
                        "Paediatrician actively recommends LittleJoys at routine visit, "
                        "addressing the awareness gap directly."
                    ),
                }
            ],
            "marketing.pediatrician_endorsement": True,
            "marketing.awareness_budget": round(0.45 + confidence * 0.35, 2),
        }
    if itype == "pricing":
        return {
            "price_inr": 449,
            "add_stimuli": [
                {
                    "tick": 3,
                    "type": "price_change",
                    "source": "bigbasket",
                    "content": (
                        "Launch price Rs 449 (introductory offer, first 1000 customers)."
                    ),
                }
            ],
        }
    if itype == "channel":
        return {
            "add_stimuli": [
                {
                    "tick": 4,
                    "type": "social_event",
                    "source": "pediatrician",
                    "content": (
                        "Paediatrician endorses LittleJoys by name, providing clinical "
                        "credibility at the point of recommendation."
                    ),
                }
            ],
            "marketing.pediatrician_endorsement": True,
        }
    if itype == "sampling":
        return {
            "add_stimuli": [
                {
                    "tick": 2,
                    "type": "product",
                    "source": "free_sample",
                    "content": (
                        "Free trial sachet delivered to home via targeted sampling campaign."
                    ),
                }
            ],
        }
    if itype == "retention":
        return {
            "add_stimuli": [
                {
                    "tick": 38,
                    "type": "social_event",
                    "source": "app_reminder",
                    "content": (
                        "Push notification: your LittleJoys pack is running low — reorder "
                        "now for uninterrupted supply."
                    ),
                },
                {
                    "tick": 55,
                    "type": "price_change",
                    "source": "bigbasket",
                    "content": (
                        "Loyalty discount: Rs 50 off your second pack as a returning customer."
                    ),
                },
            ],
        }
    # distribution
    return {
        "add_stimuli": [
            {
                "tick": 6,
                "type": "ad",
                "source": "google_shopping",
                "content": (
                    "LittleJoys now available on Amazon, BigBasket, and FirstCry — "
                    "easy to find wherever you shop."
                ),
            }
        ],
    }


# ── Title / rationale templates ────────────────────────────────────────────────

_TITLES: dict[str, str] = {
    "awareness": "Paediatrician-led awareness campaign",
    "pricing": "Introductory price reduction to Rs 449",
    "channel": "Clinical credibility / doctor endorsement campaign",
    "sampling": "Free trial sachet home-delivery programme",
    "retention": "Loyalty re-engagement (reminder + discount)",
    "distribution": "Expanded distribution channel rollout",
}

_RATIONALE_TEMPLATES: dict[str, str] = (
    {
        "awareness": (
            "Confirmed evidence shows a significant awareness gap; many parents in the target "
            "cohort have not encountered the brand through any channel. "
            "A paediatrician-led touchpoint at routine visits converts trusted medical authority "
            "into top-of-funnel brand awareness at the highest-credibility moment."
        ),
        "pricing": (
            "Price sensitivity is a confirmed barrier; the Rs 649 price point sits above the "
            "mental reference price for new entrants in this category. "
            "An introductory Rs 449 offer lowers the trial risk and aligns with comparable "
            "SKU pricing seen in the Horlicks and Complan segments."
        ),
        "channel": (
            "Trust and clinical credibility are confirmed barriers; parents defer to paediatric "
            "advice when choosing an unfamiliar supplement brand. "
            "A structured endorsement programme creates a verified proof point that bypasses "
            "influencer scepticism."
        ),
        "sampling": (
            "Taste and format rejection before first use is a confirmed conversion blocker, "
            "especially for picky eaters. "
            "A zero-risk free sachet removes the financial barrier to trial and lets the "
            "product's sensory profile close the sale."
        ),
        "retention": (
            "Habit formation is fragile at the reorder point; lapsed buyers cite forgetting "
            "to reorder rather than dissatisfaction. "
            "Timely reminders combined with a loyalty discount remove friction at the moment "
            "when purchase intent is highest."
        ),
        "distribution": (
            "Confirmed availability gap means potential buyers encounter 'out of stock' or "
            "cannot locate the product in preferred channels. "
            "Expanding to three major platforms simultaneously removes the discovery barrier "
            "and captures cross-channel intent."
        ),
    }
)


# ── Expected lift estimates (empirical anchors) ────────────────────────────────

_BASE_LIFT: dict[str, float] = {
    "awareness": 18.0,
    "channel": 14.0,
    "sampling": 22.0,
    "pricing": 16.0,
    "retention": 12.0,
    "distribution": 10.0,
}


# ── Main function ──────────────────────────────────────────────────────────────

@dataclass
class InterventionProposal:
    id: str
    title: str
    rationale: str
    hypothesis_ids: list[str]
    intervention_type: str
    expected_lift_pct: float
    confidence: float
    journey_modifications: dict[str, Any]
    cohort_filter: dict[str, Any] = field(default_factory=dict)
    priority: int = 1


def propose_interventions(
    synthesis: TreeSynthesis,
    hypotheses: list[Hypothesis],
    problem: ProblemStatement,
) -> list[InterventionProposal]:
    """
    Map confirmed/inconclusive hypotheses to concrete intervention proposals.

    Returns up to 5 proposals sorted by expected_lift_pct descending.
    Confirmed (confidence > 0.6): full proposal.
    Inconclusive (0.4–0.6): pilot-test framing, lower confidence.
    Rejected (< 0.4): skipped.
    """
    if not synthesis.confidence_ranking:
        return []

    confidence_by_id = dict(synthesis.confidence_ranking)
    hyp_by_id = {h.id: h for h in hypotheses}

    # Collect hypotheses that appear in the ranking, sorted by confidence desc.
    # If a ranked ID doesn't match any hypothesis object (e.g. synthetic test
    # synthesis), fall back to using the hypotheses list ordered by their own
    # confidence_prior so we still produce proposals.
    ranked_from_synthesis = sorted(
        [
            (hid, conf)
            for hid, conf in confidence_by_id.items()
            if conf >= 0.4
        ],
        key=lambda x: x[1],
        reverse=True,
    )

    # Check whether any ranking IDs actually map to hypothesis objects
    any_matched = any(hid in hyp_by_id for hid, _ in ranked_from_synthesis)

    if any_matched:
        ranked = ranked_from_synthesis
    else:
        # Fallback: use the hypotheses list sorted by confidence_prior
        ranked = sorted(
            [(h.id, h.confidence_prior) for h in hypotheses if h.confidence_prior >= 0.4],
            key=lambda x: x[1],
            reverse=True,
        )

    # Deduplicate by intervention_type so we don't emit two awareness proposals
    seen_types: set[str] = set()
    proposals: list[InterventionProposal] = []

    for hid, conf in ranked:
        hyp = hyp_by_id.get(hid)
        if hyp is None:
            # Synthesised ranking entry with no matching Hypothesis object — skip
            continue

        itype = _classify_hypothesis(hyp)
        if itype in seen_types:
            continue
        seen_types.add(itype)

        is_confirmed = conf > 0.6
        base_lift = _BASE_LIFT.get(itype, 10.0)

        if is_confirmed:
            lift = round(base_lift * (0.8 + conf * 0.4), 1)
            proposal_conf = round(min(conf * 0.9, 0.95), 2)
            title = _TITLES[itype]
            rationale = _RATIONALE_TEMPLATES[itype]
            priority = 1
        else:
            # Inconclusive — pilot framing
            lift = round(base_lift * 0.5, 1)
            proposal_conf = round(conf * 0.6, 2)
            title = f"[Pilot] {_TITLES[itype]}"
            rationale = (
                f"Evidence is inconclusive (confidence {conf:.0%}); a small-scale pilot "
                f"is recommended before full rollout. "
                + _RATIONALE_TEMPLATES[itype]
            )
            priority = 2

        proposals.append(
            InterventionProposal(
                id=f"iv_{itype}_{hyp.problem_id[:8]}",
                title=title,
                rationale=rationale,
                hypothesis_ids=[hid],
                intervention_type=itype,
                expected_lift_pct=lift,
                confidence=proposal_conf,
                journey_modifications=_build_modifications(itype, hyp, conf),
                cohort_filter=dict(hyp.cohort_filter),
                priority=priority,
            )
        )

        if len(proposals) >= 5:
            break

    proposals.sort(key=lambda p: p.expected_lift_pct, reverse=True)
    return proposals
