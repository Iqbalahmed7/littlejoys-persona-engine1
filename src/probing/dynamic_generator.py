"""Dynamic hypothesis-tree generator.

Uses Claude Sonnet to generate a full ProblemTreeDefinition for any
custom business problem supplied as free-form text.

Usage::

    from src.probing.dynamic_generator import generate_hypothesis_tree

    tree = generate_hypothesis_tree(
        "Why are parents not repurchasing our magnesium gummies after the first order?",
        scenario_id="custom_repurchase_study",
        n_hypotheses=5,
    )
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from src.probing.models import (
    Hypothesis,
    Probe,
    ProbeType,
    ProblemStatement,
    ProblemTreeDefinition,
)
from src.probing.predefined_trees import generate_fallback_probes_for_custom_hypotheses

# ---------------------------------------------------------------------------
# Allowed indicator attributes (flat-dict keys from the persona taxonomy)
# ---------------------------------------------------------------------------
_VALID_INDICATOR_ATTRIBUTES: frozenset[str] = frozenset(
    [
        "health_anxiety",
        "information_need",
        "social_proof_bias",
        "budget_consciousness",
        "brand_loyalty_tendency",
        "price_reference_point",
        "ad_receptivity",
        "research_before_purchase",
        "risk_tolerance",
        "deal_seeking_intensity",
        "child_taste_veto",
        "subscription_comfort",
        "indie_brand_openness",
        "food_first_belief",
    ]
)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are an expert consumer-insights researcher specialising in Indian FMCG and \
child-nutrition categories. You generate rigorous, behaviourally-grounded \
hypothesis trees for business problems faced by brands in the Indian market.

Your output must be valid JSON — no markdown prose, no explanation outside the \
JSON block.
"""

_USER_PROMPT_TEMPLATE = """\
Generate a complete probing-tree for the following business problem:

PROBLEM:
{problem_text}

OUTPUT REQUIREMENTS
===================

Return a single JSON object with exactly this structure (fill all fields):

{{
  "problem_id": "<snake_case id derived from the first 8 words of the problem>",
  "problem_title": "<clear title, max 80 chars>",
  "problem_context": "<2-3 sentence business context>",
  "success_metric": "<one snake_case word e.g. repeat_rate, adoption_rate, conversion_rate>",
  "hypotheses": [
    {{
      "id": "h1_<snake_case>",
      "title": "<clear business-language title, max 80 chars>",
      "rationale": "<2-3 sentences grounded in consumer psychology>",
      "confidence_prior": <float 0.0-1.0, how likely this is a real driver>,
      "real_world_analogy": "<cite a REAL Indian FMCG brand example — Horlicks, Dabur Chyawanprash, PediaSure, Complan, Mamaearth, Emami, Himalaya, Bournvita, Nestle Milo, Amrutanjan, etc.>",
      "why_level": 1,
      "parent_hypothesis_id": null,
      "cohort_filter": {{"outcome": "lapsed"}},
      "indicator_attributes": ["<3-5 from the allowed list below>"],
      "edge_case": false,
      "sub_hypotheses": [
        {{
          "id": "h1a_<snake_case>",
          "title": "<more specific title>",
          "rationale": "<2-3 sentences>",
          "confidence_prior": <0.05-0.15 lower than parent>,
          "real_world_analogy": "<REAL Indian FMCG example>",
          "why_level": 2,
          "parent_hypothesis_id": "h1_<snake_case>",
          "cohort_filter": {{"trust_anchor": "doctor"}},
          "indicator_attributes": ["<1-3 from allowed list>"],
          "edge_case": false
        }}
      ]
    }}
  ],
  "probes": [
    {{
      "hypothesis_id": "h1_<snake_case>",
      "probe_type": "interview",
      "question": "<open-ended interview question for this hypothesis>"
    }},
    {{
      "hypothesis_id": "h1_<snake_case>",
      "probe_type": "attribute",
      "attributes": ["<attr1>", "<attr2>"],
      "split_by": "outcome"
    }}
  ]
}}

RULES
-----
1. Generate exactly {n_hypotheses} top-level hypotheses (why_level=1).
2. Each top-level hypothesis must have {max_why_depth} sub-hypotheses (why_level=2).
   If max_why_depth is 1, omit sub_hypotheses entirely or set to [].
3. Exactly 1 of the {n_hypotheses} hypotheses must have "edge_case": true \
(low-probability but high-importance driver).
4. Generate 2 probes per top-level hypothesis: 1 interview + 1 attribute.
5. Sub-hypotheses do NOT need probes.
6. confidence_prior for sub-hypotheses must be 0.05-0.15 lower than the parent.
7. indicator_attributes MUST only contain values from this allowed list:
   {allowed_attributes}
8. real_world_analogy MUST cite a real, named Indian FMCG brand — do not invent brands.
9. cohort_filter should be a small dict like {{"outcome":"lapsed"}} or \
{{"trust_anchor":"doctor"}} — use relevant persona attributes as keys.
10. problem_id must be a valid Python identifier using only lowercase letters, \
digits, and underscores, max 60 chars.

Generate the JSON now.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_dynamic_generator_available() -> bool:
    """Return True if ANTHROPIC_API_KEY is set in the environment."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def generate_hypothesis_tree(
    problem_text: str,
    scenario_id: str = "custom",
    n_hypotheses: int = 5,
    max_why_depth: int = 2,
    model: str = "claude-sonnet-4-5",
) -> ProblemTreeDefinition:
    """Generate a full ProblemTreeDefinition for any business problem.

    Calls Claude Sonnet with a structured prompt, parses the JSON response,
    and returns a :class:`ProblemTreeDefinition` containing
    :class:`ProblemStatement`, :class:`Hypothesis`, and :class:`Probe` objects.

    Args:
        problem_text: Free-form description of the business problem to investigate.
        scenario_id: Scenario identifier to embed in :class:`ProblemStatement`.
            Defaults to ``"custom"``.
        n_hypotheses: Number of top-level hypotheses to generate (default 5).
        max_why_depth: Depth of sub-hypotheses tree.  1 = top-level only,
            2 = one level of sub-hypotheses (default 2).
        model: Anthropic model to use.  Defaults to ``"claude-sonnet-4-5"``.

    Returns:
        A fully populated :class:`ProblemTreeDefinition`.

    Raises:
        RuntimeError: If the Anthropic API call fails or the response cannot
            be parsed.
    """
    # --- build prompt ---
    allowed_str = ", ".join(sorted(_VALID_INDICATOR_ATTRIBUTES))
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        problem_text=problem_text.strip(),
        n_hypotheses=n_hypotheses,
        max_why_depth=max_why_depth,
        allowed_attributes=allowed_str,
    )

    # --- call Claude ---
    raw_response = _call_claude(user_prompt, model=model)

    # --- parse JSON ---
    payload = _parse_json(raw_response)

    # --- derive problem_id ---
    derived_problem_id = _derive_problem_id(problem_text, payload)

    # --- build ProblemStatement ---
    problem = ProblemStatement(
        id=derived_problem_id,
        title=str(payload.get("problem_title", problem_text[:80])),
        scenario_id=scenario_id,
        context=str(payload.get("problem_context", "")),
        success_metric=str(payload.get("success_metric", "adoption_rate")),
    )

    # --- flatten hypotheses (top-level + sub-hypotheses) ---
    raw_hypotheses: list[dict[str, Any]] = payload.get("hypotheses", [])
    flat_hypotheses = _flatten_hypotheses(raw_hypotheses, derived_problem_id)
    hypotheses = [_build_hypothesis(h, derived_problem_id, idx) for idx, h in enumerate(flat_hypotheses)]

    # --- build probes from LLM response ---
    raw_probes: list[dict[str, Any]] = payload.get("probes", [])
    probes = _build_probes(raw_probes, hypotheses)

    # --- append fallback probes for any custom hypotheses not yet covered ---
    probes = generate_fallback_probes_for_custom_hypotheses(hypotheses, probes)

    return ProblemTreeDefinition(problem=problem, hypotheses=hypotheses, probes=probes)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _call_claude(user_prompt: str, model: str) -> str:
    """Make a single synchronous call to the Anthropic Messages API.

    Creates a fresh client per call (httpx transport safety).

    Raises:
        RuntimeError: On any API error.
    """
    try:
        import anthropic  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "anthropic package is required: pip install anthropic"
        ) from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
            model=model,
            max_tokens=8192,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:
        raise RuntimeError(
            f"Claude API call failed: {exc}"
        ) from exc

    content_block: Any = message.content[0]
    return str(getattr(content_block, "text", ""))


def _parse_json(raw: str) -> dict[str, Any]:
    """Extract and parse JSON from a raw Claude response.

    Handles:
    - Plain JSON
    - JSON wrapped in markdown fences (```json … ```)
    - Partial JSON (falls back to extracting between first ``{`` and last ``}``)

    Raises:
        RuntimeError: If no valid JSON can be extracted.
    """
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: extract substring between first { and last }
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(cleaned[start:end])
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Could not parse JSON from Claude response. "
                f"First 400 chars: {cleaned[:400]!r}"
            ) from exc

    raise RuntimeError(
        f"No JSON object found in Claude response. "
        f"First 400 chars: {raw[:400]!r}"
    )


def _derive_problem_id(problem_text: str, payload: dict[str, Any]) -> str:
    """Derive a safe ``problem_id`` string.

    Uses Claude's ``problem_id`` field if provided and valid, otherwise
    slugifies the first 8 words of ``problem_text``.
    """
    llm_id = str(payload.get("problem_id", "")).strip()
    if llm_id and re.match(r"^[a-z][a-z0-9_]{0,59}$", llm_id):
        return llm_id

    words = re.split(r"\W+", problem_text.lower())
    words = [w for w in words if w][:8]
    slug = "_".join(words)
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:60] or "custom_problem"


def _flatten_hypotheses(
    raw: list[dict[str, Any]],
    problem_id: str,
) -> list[dict[str, Any]]:
    """Flatten nested sub-hypotheses into a single list.

    Claude may return ``sub_hypotheses`` inline inside each top-level
    hypothesis dict.  This function extracts them and appends them to the
    flat list, ensuring ``parent_hypothesis_id`` is set correctly.
    """
    flat: list[dict[str, Any]] = []
    for item in raw:
        sub = item.pop("sub_hypotheses", None) or []
        flat.append(item)
        for sub_item in sub:
            # Ensure parent linkage
            if not sub_item.get("parent_hypothesis_id"):
                sub_item["parent_hypothesis_id"] = item.get("id")
            flat.append(sub_item)
    return flat


def _build_hypothesis(raw: dict[str, Any], problem_id: str, order: int) -> Hypothesis:
    """Build a :class:`Hypothesis` from a raw dict, filling defaults for missing fields.

    Uses ``getattr``-style dict.get() patterns so that fields introduced in
    Sprint 1a are tolerated even if the :class:`Hypothesis` model has not
    yet been updated.
    """
    h_id = str(raw.get("id") or f"h{order + 1}_generated")
    title = str(raw.get("title") or "Untitled hypothesis")[:80]
    rationale = str(raw.get("rationale") or "")
    indicator_attributes = _clean_indicator_attributes(raw.get("indicator_attributes") or [])
    is_custom = True  # dynamically generated hypotheses are always custom

    # Base Hypothesis kwargs (always present in model)
    kwargs: dict[str, Any] = dict(
        id=h_id,
        problem_id=problem_id,
        title=title,
        rationale=rationale,
        indicator_attributes=indicator_attributes,
        is_custom=is_custom,
        order=order,
    )

    # Sprint-1a extended fields — set via dict only; tolerate absent model fields
    # by passing them as kwargs and letting Pydantic ignore extras if configured.
    # Since the current model uses extra="forbid", we guard each field with
    # hasattr on the Hypothesis class.
    extended_fields: dict[str, Any] = {
        "confidence_prior": float(raw.get("confidence_prior") or 0.5),
        "real_world_analogy": str(raw.get("real_world_analogy") or ""),
        "why_level": int(raw.get("why_level") or 1),
        "parent_hypothesis_id": raw.get("parent_hypothesis_id") or None,
        "cohort_filter": raw.get("cohort_filter") or {},
        "edge_case": bool(raw.get("edge_case") or False),
    }
    for field_name, field_value in extended_fields.items():
        if field_name in Hypothesis.model_fields:
            kwargs[field_name] = field_value

    return Hypothesis(**kwargs)


def _clean_indicator_attributes(raw_attrs: list[Any]) -> list[str]:
    """Return only attributes that exist in the allowed set."""
    cleaned: list[str] = []
    for attr in raw_attrs:
        attr_str = str(attr).strip()
        if attr_str in _VALID_INDICATOR_ATTRIBUTES:
            cleaned.append(attr_str)
    return cleaned


def _build_probes(
    raw_probes: list[dict[str, Any]],
    hypotheses: list[Hypothesis],
) -> list[Probe]:
    """Build :class:`Probe` objects from the LLM probe list.

    Tracks ``order`` per hypothesis independently (1-indexed).
    Skips probes whose ``hypothesis_id`` does not match a known hypothesis.
    """
    known_ids: set[str] = {h.id for h in hypotheses}
    order_counter: dict[str, int] = {}
    probes: list[Probe] = []
    seen_probe_ids: set[str] = set()

    for raw in raw_probes:
        hyp_id = str(raw.get("hypothesis_id") or "")
        if hyp_id not in known_ids:
            continue

        probe_type_raw = str(raw.get("probe_type") or "interview").lower()
        order_counter[hyp_id] = order_counter.get(hyp_id, 0) + 1
        order = order_counter[hyp_id]

        if probe_type_raw == "interview":
            probe_id = f"{hyp_id}_dyn_interview_{order}"
            if probe_id in seen_probe_ids:
                continue
            probe = Probe(
                id=probe_id,
                hypothesis_id=hyp_id,
                probe_type=ProbeType.INTERVIEW,
                question_template=str(raw.get("question") or ""),
                order=order,
            )
        elif probe_type_raw == "attribute":
            probe_id = f"{hyp_id}_dyn_attribute_{order}"
            if probe_id in seen_probe_ids:
                continue
            attrs = _clean_indicator_attributes(raw.get("attributes") or [])
            split_by = str(raw.get("split_by") or "outcome")
            probe = Probe(
                id=probe_id,
                hypothesis_id=hyp_id,
                probe_type=ProbeType.ATTRIBUTE,
                analysis_attributes=attrs,
                split_by=split_by,
                order=order,
            )
        else:
            # Unknown probe type — skip
            continue

        probes.append(probe)
        seen_probe_ids.add(probe_id)

    return probes
