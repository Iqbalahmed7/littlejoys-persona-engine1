"""
Open-ended question engine for the LittleJoys Persona Intelligence Platform.

Converts a natural language business question into one of two query modes:

  POPULATION_STAT   — answered instantly from persona attributes (no simulation needed).
                      Example: "What % of Tier 2 moms trust doctors over influencers?"

  SCENARIO_PROPOSAL — generates a proposed JourneyConfig the user can review and run.
                      Example: "What if we added a free-sample drop to the 7-14 campaign?"

Architecture
------------
1. LLM parses the question → structured ParsedQuery (via Claude API, sync)
2. For POPULATION_STAT:
   - Filter the 200 personas by demographic criteria
   - Compute attribute distributions on the filtered set
   - LLM synthesises a plain-English answer from the stats
3. For SCENARIO_PROPOSAL:
   - Return the proposed journey config + population filter for the UI to present
   - User clicks "Run Simulation" to actually execute it
"""

from __future__ import annotations

import json
import os
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class QueryMode(str, Enum):
    POPULATION_STAT = "population_stat"
    SCENARIO_PROPOSAL = "scenario_proposal"


@dataclass
class PersonaFilter:
    """Demographic + psychographic filter applied before analysis."""

    city_tier: str | None = None          # "Tier1" | "Tier2" | "Tier3"
    child_age_min: int | None = None
    child_age_max: int | None = None
    price_sensitivity: str | None = None  # "low" | "medium" | "high"
    trust_anchor: str | None = None       # "self" | "peer" | "authority" | "family"
    decision_style: str | None = None     # "analytical" | "emotional" | "habitual" | "social"
    family_structure: str | None = None   # "nuclear" | "joint" | "single_parent"

    def description(self) -> str:
        """Human-readable filter description."""
        parts: list[str] = []
        if self.city_tier:
            parts.append(self.city_tier)
        if self.child_age_min is not None or self.child_age_max is not None:
            lo = self.child_age_min or 0
            hi = self.child_age_max or 18
            parts.append(f"children aged {lo}–{hi}")
        if self.price_sensitivity:
            parts.append(f"{self.price_sensitivity} price sensitivity")
        if self.trust_anchor:
            parts.append(f"{self.trust_anchor}-trust anchor")
        if self.decision_style:
            parts.append(f"{self.decision_style} decision style")
        if self.family_structure:
            parts.append(f"{self.family_structure} families")
        return ", ".join(parts) if parts else "all 200 personas"


@dataclass
class AttributeStat:
    attribute_path: str
    label: str
    count: int
    # For numeric attributes (0-1 floats)
    mean: float | None = None
    median: float | None = None
    high_pct: float | None = None   # % of personas with value > 0.7
    low_pct: float | None = None    # % of personas with value < 0.3
    # For categorical attributes
    distribution: dict[str, int] = field(default_factory=dict)


@dataclass
class AnsweredQuestion:
    mode: QueryMode
    raw_question: str
    interpretation: str          # LLM's restatement of the question
    persona_filter: PersonaFilter
    filtered_count: int          # how many personas matched the filter

    # POPULATION_STAT fields
    attribute_stats: list[AttributeStat] = field(default_factory=list)
    narrative_answer: str = ""   # LLM-synthesised plain-English answer

    # SCENARIO_PROPOSAL fields
    hypothesis: str = ""
    base_journey: str = ""       # "A" | "B" | "C"
    intervention_description: str = ""
    proposed_stimuli_changes: list[dict] = field(default_factory=list)
    proposed_price_change: int | None = None
    can_run: bool = False        # True once the user has accepted the proposal

    error: str = ""


# ---------------------------------------------------------------------------
# LLM prompt + parsing
# ---------------------------------------------------------------------------

_PARSE_SYSTEM = """You are a consumer research analyst for LittleJoys, an Indian children's nutrition brand.
You have access to 200 synthetic Indian parent personas.

PERSONA SCHEMA (key attribute paths):
  demographics.city_tier         — "Tier1" | "Tier2" | "Tier3"
  demographics.parent_age        — integer (25–45)
  demographics.child_ages        — list of ints (0–18)
  demographics.oldest_child_age  — int
  demographics.youngest_child_age — int
  demographics.family_structure  — "nuclear" | "joint" | "single_parent"
  parent_traits.decision_style   — "analytical" | "emotional" | "habitual" | "social"
  parent_traits.trust_anchor     — "self" | "peer" | "authority" | "family"
  parent_traits.risk_appetite    — "low" | "medium" | "high"
  budget_profile.price_sensitivity — "low" | "medium" | "high"
  psychology.social_proof_bias   — float 0–1
  psychology.authority_bias      — float 0–1
  psychology.risk_tolerance      — float 0–1
  psychology.health_anxiety      — float 0–1 (inferred from health section)
  values.supplement_necessity_belief — float 0–1
  values.food_first_belief       — float 0–1
  values.indie_brand_openness    — float 0–1
  values.brand_loyalty_tendency  — float 0–1
  health.child_nutrition_concerns — list of strings
  health.pediatrician_visit_frequency — string
  media.primary_social_platform  — string
  media.influencer_trust         — float 0–1 (from psychology section)

PRODUCTS:
  Nutrimix — flagship nutritional drink, strong in 2-6 age group, trying to expand to 7-14
  Magnesium Gummies — low awareness, sleep/focus benefit, gummy format
  ProteinMix — new, lower priority

JOURNEYS:
  A — Nutrimix Repeat Purchase (60 days, standard 2-6 audience)
  B — Magnesium Gummies awareness + trial (45 days)
  C — Nutrimix 7-14 Expansion (60 days, school-age audience)

Given a business question, return ONLY valid JSON (no markdown fences):
{
  "mode": "population_stat" | "scenario_proposal",
  "interpretation": "<one sentence: what you understand the question to be asking>",
  "filter": {
    "city_tier": "Tier1" | "Tier2" | "Tier3" | null,
    "child_age_min": <int> | null,
    "child_age_max": <int> | null,
    "price_sensitivity": "low" | "medium" | "high" | null,
    "trust_anchor": "self" | "peer" | "authority" | "family" | null,
    "decision_style": "analytical" | "emotional" | "habitual" | "social" | null,
    "family_structure": "nuclear" | "joint" | "single_parent" | null
  },
  "attributes_to_analyse": ["dot.notation.path", ...],   // for population_stat
  "hypothesis": "<what you expect to find or what should happen>",
  "base_journey": "A" | "B" | "C" | null,               // for scenario_proposal
  "intervention": "<plain language description of the proposed change>"  // for scenario_proposal
}"""

_SYNTHESIS_SYSTEM = """You are a consumer insight analyst for LittleJoys, an Indian children's nutrition brand.
You have just run a statistical probe on a population of 200 synthetic Indian parent personas.
Write a concise, business-ready answer (3–5 sentences) that:
- Directly answers the question in plain English
- Cites the most striking numbers (rounded to nearest %)
- Names the key persona segments driving the pattern
- Ends with one concrete recommendation for LittleJoys

Do NOT use bullet points. Write in flowing prose. Do NOT mention "synthetic personas" or "simulated data".
Write as if you are presenting findings from real consumer research."""


def _call_claude(system: str, user_prompt: str, api_key: str) -> str:
    """Synchronous Claude API call. Returns the response text."""
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return msg.content[0].text.strip()


# ---------------------------------------------------------------------------
# Persona filtering
# ---------------------------------------------------------------------------

def _matches_filter(persona: dict, f: PersonaFilter) -> bool:
    d = persona.get("demographics", {})
    pt = persona.get("parent_traits", {}) or {}
    bp = persona.get("budget_profile", {}) or {}

    if f.city_tier and d.get("city_tier") != f.city_tier:
        return False

    child_ages: list[int] = d.get("child_ages") or []
    if f.child_age_min is not None or f.child_age_max is not None:
        lo = f.child_age_min if f.child_age_min is not None else 0
        hi = f.child_age_max if f.child_age_max is not None else 99
        if not any(lo <= a <= hi for a in child_ages):
            return False

    if f.price_sensitivity and bp.get("price_sensitivity") != f.price_sensitivity:
        return False
    if f.trust_anchor and pt.get("trust_anchor") != f.trust_anchor:
        return False
    if f.decision_style and pt.get("decision_style") != f.decision_style:
        return False
    if f.family_structure and d.get("family_structure") != f.family_structure:
        return False

    return True


def _resolve_attribute(persona: dict, path: str) -> Any:
    """Walk a dot-separated path through the persona dict."""
    parts = path.split(".")
    node: Any = persona
    for part in parts:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


# ---------------------------------------------------------------------------
# Attribute statistics
# ---------------------------------------------------------------------------

_ATTRIBUTE_LABELS: dict[str, str] = {
    "psychology.social_proof_bias": "Social Proof Bias",
    "psychology.authority_bias": "Authority Bias",
    "psychology.risk_tolerance": "Risk Tolerance",
    "psychology.information_need": "Information Need",
    "psychology.loss_aversion": "Loss Aversion",
    "values.supplement_necessity_belief": "Supplement Necessity Belief",
    "values.food_first_belief": "Food-First Belief",
    "values.indie_brand_openness": "Indie Brand Openness",
    "values.brand_loyalty_tendency": "Brand Loyalty",
    "parent_traits.decision_style": "Decision Style",
    "parent_traits.trust_anchor": "Trust Anchor",
    "parent_traits.risk_appetite": "Risk Appetite",
    "budget_profile.price_sensitivity": "Price Sensitivity",
    "demographics.city_tier": "City Tier",
    "demographics.family_structure": "Family Structure",
}


def _compute_stat(attribute_path: str, values: list[Any]) -> AttributeStat:
    label = _ATTRIBUTE_LABELS.get(attribute_path, attribute_path.split(".")[-1].replace("_", " ").title())
    numeric_vals = [v for v in values if isinstance(v, (int, float))]
    categorical_vals = [str(v) for v in values if isinstance(v, str)]
    n = len(values)

    stat = AttributeStat(attribute_path=attribute_path, label=label, count=n)

    if numeric_vals and len(numeric_vals) > len(categorical_vals):
        stat.mean = round(statistics.mean(numeric_vals), 3)
        stat.median = round(statistics.median(numeric_vals), 3)
        stat.high_pct = round(100 * sum(1 for v in numeric_vals if v > 0.7) / len(numeric_vals), 1)
        stat.low_pct = round(100 * sum(1 for v in numeric_vals if v < 0.3) / len(numeric_vals), 1)
    elif categorical_vals:
        freq: dict[str, int] = {}
        for v in categorical_vals:
            freq[v] = freq.get(v, 0) + 1
        stat.distribution = dict(sorted(freq.items(), key=lambda x: -x[1]))

    return stat


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def answer_question(
    question: str,
    personas: list[dict],
    api_key: str | None = None,
) -> AnsweredQuestion:
    """
    Parse a natural language business question and return an AnsweredQuestion.

    If api_key is None, attempts to read from ANTHROPIC_API_KEY env var.
    If no key is available, returns an error result.
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return AnsweredQuestion(
            mode=QueryMode.POPULATION_STAT,
            raw_question=question,
            interpretation=question,
            persona_filter=PersonaFilter(),
            filtered_count=len(personas),
            error="ANTHROPIC_API_KEY is not set. Set it to enable the question engine.",
        )

    # ── Step 1: Parse the question ──────────────────────────────────────────
    try:
        raw_json = _call_claude(_PARSE_SYSTEM, question, api_key)
        # Strip markdown fences if present
        import re
        raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json, flags=re.MULTILINE)
        raw_json = re.sub(r"\s*```$", "", raw_json, flags=re.MULTILINE)
        parsed = json.loads(raw_json.strip())
    except Exception as exc:
        return AnsweredQuestion(
            mode=QueryMode.POPULATION_STAT,
            raw_question=question,
            interpretation=question,
            persona_filter=PersonaFilter(),
            filtered_count=len(personas),
            error=f"Could not parse question: {exc}",
        )

    mode = QueryMode(parsed.get("mode", "population_stat"))
    interpretation = parsed.get("interpretation", question)
    hypothesis = parsed.get("hypothesis", "")
    raw_filter = parsed.get("filter", {}) or {}

    persona_filter = PersonaFilter(
        city_tier=raw_filter.get("city_tier"),
        child_age_min=raw_filter.get("child_age_min"),
        child_age_max=raw_filter.get("child_age_max"),
        price_sensitivity=raw_filter.get("price_sensitivity"),
        trust_anchor=raw_filter.get("trust_anchor"),
        decision_style=raw_filter.get("decision_style"),
        family_structure=raw_filter.get("family_structure"),
    )

    filtered = [p for p in personas if _matches_filter(p, persona_filter)]

    result = AnsweredQuestion(
        mode=mode,
        raw_question=question,
        interpretation=interpretation,
        persona_filter=persona_filter,
        filtered_count=len(filtered),
        hypothesis=hypothesis,
    )

    if mode == QueryMode.POPULATION_STAT:
        # ── Step 2a: Compute attribute stats ────────────────────────────────
        attrs_to_probe: list[str] = parsed.get("attributes_to_analyse", [])
        # Always add some contextual attributes
        contextual = ["parent_traits.trust_anchor", "parent_traits.decision_style",
                      "budget_profile.price_sensitivity"]
        for attr in contextual:
            if attr not in attrs_to_probe:
                attrs_to_probe.append(attr)

        stats: list[AttributeStat] = []
        for attr_path in attrs_to_probe[:8]:  # cap at 8 attributes
            values = [_resolve_attribute(p, attr_path) for p in filtered]
            values = [v for v in values if v is not None]
            if values:
                stats.append(_compute_stat(attr_path, values))
        result.attribute_stats = stats

        # ── Step 3a: Synthesise narrative answer ────────────────────────────
        if stats and filtered:
            stats_summary = _format_stats_for_synthesis(result)
            synthesis_prompt = (
                f"Question: {question}\n\n"
                f"Population analysed: {len(filtered)} parents ({persona_filter.description()})\n\n"
                f"Statistical findings:\n{stats_summary}"
            )
            try:
                result.narrative_answer = _call_claude(_SYNTHESIS_SYSTEM, synthesis_prompt, api_key)
            except Exception as exc:
                result.narrative_answer = f"(Synthesis failed: {exc})"
        elif not filtered:
            result.narrative_answer = (
                f"No personas matched the filter criteria ({persona_filter.description()}). "
                "Try broadening the filter."
            )

    else:
        # ── Step 2b: Build scenario proposal ────────────────────────────────
        result.base_journey = parsed.get("base_journey") or "A"
        result.intervention_description = parsed.get("intervention", "")
        result.can_run = True

    return result


def _format_stats_for_synthesis(result: AnsweredQuestion) -> str:
    """Format attribute stats as a readable text block for the synthesis LLM."""
    lines: list[str] = []
    for s in result.attribute_stats:
        if s.distribution:
            top_items = list(s.distribution.items())[:3]
            dist_str = ", ".join(f"{k}: {v}" for k, v in top_items)
            lines.append(f"  {s.label}: {dist_str} (n={s.count})")
        elif s.mean is not None:
            lines.append(
                f"  {s.label}: mean={s.mean:.2f}, "
                f"{s.high_pct:.0f}% high (>0.7), {s.low_pct:.0f}% low (<0.3) (n={s.count})"
            )
    return "\n".join(lines)
