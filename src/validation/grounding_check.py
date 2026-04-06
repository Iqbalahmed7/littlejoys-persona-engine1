"""src/validation/grounding_check.py — G12 Simulation Grounding Check.

Automatically runs after every batch simulation in batch_runner.py.

Detects three contamination types in simulation outputs:

  T1 — Injected Product Facts
       Numbers/claims in the product frame (journey stimuli) that cannot be
       traced to a real source document — e.g. invented prices or stats.

  T2 — Impossible Persona Attributes
       Persona prior exposure or decision reasoning that references a channel,
       retailer, or touchpoint that doesn't exist for LittleJoys — e.g. a
       persona claiming to have bought Nutrimix at a store that doesn't stock it.

  T3 — Quote Leakage
       Specific numbers (prices, dosages, percentages) in a persona's verbatim
       reasoning trace that were never established in the journey stimuli fed to
       the simulation.

Usage (automatic — called by batch_runner.run_batch):
    Results are embedded in BatchResult.grounding_report and printed to stdout.

Manual usage:
    from src.validation.grounding_check import run_grounding_check, LITTLEJOYS_MARKET_FACTS
    report = run_grounding_check(product_frame, LITTLEJOYS_MARKET_FACTS, persona_outputs)
    print(report.summary())
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# LittleJoys market facts — single source of truth for T2 validation
# ---------------------------------------------------------------------------

LITTLEJOYS_MARKET_FACTS: dict = {
    "client": "LittleJoys",
    "brand": "LittleJoys",
    "product": "Nutrimix",
    "distribution": {
        "model": "Online + pharmacy",
        "channels": [
            "Amazon.in",
            "BigBasket",
            "Flipkart",
            "1mg",
            "Netmeds",
            "own website",
        ],
        "offline_retail": False,
        "forbidden_touchpoints": [
            # No confirmed general offline retail presence
            "D-Mart",
            "Big Bazaar",
            "Reliance Fresh",
            "Reliance Smart",
            "More Supermarket",
            "Spencer's",
            "kirana store",
            "local grocery",
            "general store",
            "supermarket shelf",
            "pharmacy shelf",   # sold at pharmacies online, not confirmed walk-in
        ],
        "notes": (
            "LittleJoys Nutrimix is sold online (Amazon, BigBasket, Flipkart) "
            "and via pharmacy e-commerce (1mg, Netmeds). No confirmed general "
            "offline supermarket or kirana presence."
        ),
    },
    "brand_facts": {
        "category": "Child nutrition supplement drink mix",
        "target_age_child": "2-12 years",
        "target_buyer": "Indian mothers",
        "verified_claims": {
            "nutrimix_500g_price_inr": 649,
            "nutrimix_original_price_inr": 799,
            "pediatrician_influence_pct": 42,
            "median_wtp_inr": 649,
            "primary_purchase_driver": "Pediatrician recommendation",
        },
        "unverified_claims_to_flag": [
            # Numbers that should NOT appear in persona quotes unless in stimuli
            "Rs 399",
            "Rs 449",
            "Rs 499",
            "Rs 549",
            "Rs 699",
            "Rs 749",
            "Rs 849",
            "Rs 899",
            "Rs 999",
        ],
    },
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class GroundingIssue:
    """A single contamination finding.

    Attributes
    ----------
    issue_type : "T1" | "T2" | "T3"
    severity   : "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    persona_id : persona that surfaced this issue, or None for product-frame issues
    location   : human-readable description of where the issue was found
    contaminated_text : exact snippet that triggered the flag
    reason     : why this text is problematic
    suggested_fix : actionable remediation guidance
    """

    issue_type: str
    severity: str
    persona_id: Optional[str]
    location: str
    contaminated_text: str
    reason: str
    suggested_fix: str


@dataclass
class GroundingReport:
    """Aggregated result of a full G12 run.

    Attributes
    ----------
    passed      : True when zero CRITICAL or HIGH issues exist
    issues      : all issues, sorted by severity
    clean_count : number of personas (+ product frame if clean) with zero issues
    journey_id  : journey that was checked
    """

    passed: bool
    issues: list[GroundingIssue]
    clean_count: int
    journey_id: str = ""

    def summary(self) -> str:
        """Return a formatted multi-line summary suitable for stdout."""
        lines: list[str] = []
        lines.append(f"=== G12 Simulation Grounding Check — Journey {self.journey_id} ===")
        lines.append("")

        result_label = "PASS" if self.passed else "FAIL"
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in self.issues:
            sev = issue.severity.upper()
            if sev in counts:
                counts[sev] += 1

        sev_str = "  ".join(f"{v} {k}" for k, v in counts.items())
        lines.append(f"  Result : {result_label}  ({sev_str})")
        lines.append(f"  Issues : {len(self.issues)} total")
        lines.append(f"  Clean  : {self.clean_count} elements passed with no issues")

        if self.issues:
            lines.append("")
            for issue in self.issues:
                pid_str = f"persona:{issue.persona_id}" if issue.persona_id else "product_frame"
                lines.append(
                    f"  {issue.issue_type}  {issue.severity:<8}  {pid_str}  {issue.location}"
                )
                snippet = issue.contaminated_text[:120].replace("\n", " ")
                lines.append(f'      "{snippet}"')
                lines.append(f"      Reason: {issue.reason}")
                lines.append(f"      Fix: {issue.suggested_fix}")
                lines.append("")

        if self.passed:
            lines.append(
                f"  [G12] PASS — LittleJoys simulation output is clean. "
                f"Safe to build reports."
            )
        else:
            lines.append(
                "  [G12] FAIL — fix contamination issues before building reports."
            )

        return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

_RE_RUPEE = re.compile(r"(?:₹|Rs\.?\s*)\s*[\d,]+(?:\.\d+)?")
_RE_PERCENTAGE = re.compile(r"\b\d+(?:\.\d+)?\s*%")
_RE_DURATION = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b",
    re.IGNORECASE,
)
_RE_SUPERLATIVE = re.compile(
    r"\b(fastest|best|only|first|number\s*one|#1|top)\b", re.IGNORECASE
)
_RE_ANY_NUMBER = re.compile(r"\b\d+(?:[.,]\d+)?\b")


def _extract_numbers(text: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for pattern in (_RE_RUPEE, _RE_PERCENTAGE, _RE_DURATION):
        for m in pattern.finditer(text):
            t = m.group()
            if t not in seen:
                tokens.append(t)
                seen.add(t)
    for m in _RE_ANY_NUMBER.finditer(text):
        raw = m.group()
        already = any(raw in tok for tok in tokens)
        if not already and raw not in seen:
            tokens.append(raw)
            seen.add(raw)
    return tokens


def _token_in_text(token: str, text: str) -> bool:
    clean = re.sub(r"[₹Rs.\s★,]", "", token)
    if not clean:
        return False
    return bool(re.search(re.escape(clean), re.sub(r"[₹Rs.\s★,]", "", text)))


def _snippet(text: str, keyword: str, radius: int = 80) -> str:
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return text[:160]
    start = max(0, idx - radius)
    end = min(len(text), idx + len(keyword) + radius)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet += "..."
    return snippet


# ---------------------------------------------------------------------------
# T1 — Injected Product Facts (scan journey stimuli / product frame)
# ---------------------------------------------------------------------------


def _check_t1(product_frame: str, source_documents: list[str]) -> list[GroundingIssue]:
    issues: list[GroundingIssue] = []
    all_sources = "\n".join(source_documents)

    for m in _RE_RUPEE.finditer(product_frame):
        token = m.group()
        if not _token_in_text(token, all_sources):
            issues.append(GroundingIssue(
                issue_type="T1",
                severity="HIGH",
                persona_id=None,
                location="product_frame (price claim)",
                contaminated_text=token,
                reason=(
                    f"Price '{token}' appears in journey stimuli but cannot be "
                    "traced to any source document."
                ),
                suggested_fix=(
                    "Add an explicit source reference for this price, or remove it "
                    "from the journey stimulus."
                ),
            ))

    for m in _RE_PERCENTAGE.finditer(product_frame):
        token = m.group()
        if not _token_in_text(token, all_sources):
            issues.append(GroundingIssue(
                issue_type="T1",
                severity="MEDIUM",
                persona_id=None,
                location="product_frame (percentage claim)",
                contaminated_text=token,
                reason=(
                    f"Percentage '{token}' in journey stimuli has no source document."
                ),
                suggested_fix="Cite the source of this percentage or remove it.",
            ))

    for m in _RE_SUPERLATIVE.finditer(product_frame):
        token = m.group()
        start = max(0, m.start() - 50)
        end = min(len(product_frame), m.end() + 50)
        context = product_frame[start:end].strip()
        has_cite = bool(re.search(
            r"\(source|according to|per |cited|verified|study", context, re.IGNORECASE
        ))
        if not has_cite and not _token_in_text(token, all_sources):
            issues.append(GroundingIssue(
                issue_type="T1",
                severity="MEDIUM",
                persona_id=None,
                location="product_frame (unsourced superlative)",
                contaminated_text=context,
                reason=(
                    f"Superlative '{token}' in journey stimuli has no citation."
                ),
                suggested_fix=(
                    "Add a source reference or soften to a relative claim."
                ),
            ))

    return issues


# ---------------------------------------------------------------------------
# T2 — Impossible Persona Attributes
# ---------------------------------------------------------------------------

_PERSONA_TEXT_FIELDS = (
    "prior_exposure", "backstory", "narrative",
    "first_person_summary", "channel_usage", "discovery_path",
)


def _check_t2(persona_outputs: list[dict], market_facts: dict) -> list[GroundingIssue]:
    issues: list[GroundingIssue] = []
    distribution = market_facts.get("distribution", {})
    forbidden: list[str] = distribution.get("forbidden_touchpoints", [])
    distribution_model: str = distribution.get("model", "")

    for persona in persona_outputs:
        persona_id: Optional[str] = (
            persona.get("persona_id") or persona.get("id") or persona.get("name")
        )

        # Collect all text to scan
        scan_texts: list[tuple[str, str]] = []
        for field_name in _PERSONA_TEXT_FIELDS:
            value = persona.get(field_name)
            if isinstance(value, str) and value.strip():
                scan_texts.append((f"{field_name} field", value))

        for idx, q in enumerate(_extract_persona_quotes(persona)):
            scan_texts.append((f"reasoning/quote #{idx + 1}", q))

        for location_label, text in scan_texts:
            for touchpoint in forbidden:
                if touchpoint.lower() in text.lower():
                    issues.append(GroundingIssue(
                        issue_type="T2",
                        severity="CRITICAL",
                        persona_id=persona_id,
                        location=location_label,
                        contaminated_text=_snippet(text, touchpoint),
                        reason=(
                            f"Forbidden touchpoint '{touchpoint}' found. "
                            f"LittleJoys distribution model is '{distribution_model}'. "
                            "This retail channel is not a confirmed LittleJoys stockist."
                        ),
                        suggested_fix=(
                            f"Remove reference to '{touchpoint}'. Replace with an "
                            "online channel (BigBasket, Amazon, 1mg) or a general "
                            "'online purchase' reference."
                        ),
                    ))

    return issues


# ---------------------------------------------------------------------------
# T3 — Quote Leakage
# ---------------------------------------------------------------------------


def _check_t3(product_frame: str, persona_outputs: list[dict]) -> list[GroundingIssue]:
    issues: list[GroundingIssue] = []

    for persona in persona_outputs:
        persona_id: Optional[str] = (
            persona.get("persona_id") or persona.get("id") or persona.get("name")
        )

        for idx, quote in enumerate(_extract_persona_quotes(persona)):
            location = f"reasoning/quote #{idx + 1}"
            for num_token in _extract_numbers(quote):
                if not _token_in_text(num_token, product_frame):
                    issues.append(GroundingIssue(
                        issue_type="T3",
                        severity="HIGH",
                        persona_id=persona_id,
                        location=location,
                        contaminated_text=quote[:200],
                        reason=(
                            f"Number '{num_token}' appears in persona reasoning but "
                            "was not established in the journey stimuli fed to the simulation."
                        ),
                        suggested_fix=(
                            "Remove the specific number from the reasoning output, or "
                            "add it to the journey stimulus before running the simulation."
                        ),
                    ))

    return issues


# ---------------------------------------------------------------------------
# Quote / reasoning extraction from LittleJoys decision result structure
# ---------------------------------------------------------------------------


def _extract_persona_quotes(persona: dict) -> list[str]:
    """Extract all verbatim text from a LittleJoys persona simulation result dict."""
    quotes: list[str] = []

    # Direct quote/reasoning fields
    for key in ("reasoning_trace", "reasoning", "response", "follow_up_action",
                 "quotes", "verbatim", "key_drivers", "objections"):
        value = persona.get(key)
        if isinstance(value, str) and value.strip():
            quotes.append(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    quotes.append(item)

    # Decision result nested dict (from TickJourneyLog structure)
    for dec_key in ("final_decision", "first_decision", "second_decision"):
        dec = persona.get(dec_key)
        if isinstance(dec, dict):
            for sub in ("reasoning_trace", "reasoning", "follow_up_action",
                        "key_drivers", "objections"):
                val = dec.get(sub)
                if isinstance(val, str) and val.strip():
                    quotes.append(val)
                elif isinstance(val, list):
                    for item in val:
                        if isinstance(item, str) and item.strip():
                            quotes.append(item)

    # Snapshots (TickSnapshot list)
    for snap in persona.get("snapshots", []):
        if not isinstance(snap, dict):
            continue
        dr = snap.get("decision_result")
        if isinstance(dr, dict):
            for sub in ("reasoning_trace", "reasoning", "follow_up_action",
                        "key_drivers", "objections"):
                val = dr.get(sub)
                if isinstance(val, str) and val.strip():
                    quotes.append(val)
                elif isinstance(val, list):
                    for item in val:
                        if isinstance(item, str) and item.strip():
                            quotes.append(item)
        # Also scan perception interpretations
        for perc in snap.get("perceptions", []) if isinstance(snap.get("perceptions"), list) else []:
            if isinstance(perc, dict):
                interp = perc.get("interpretation")
                if isinstance(interp, str) and interp.strip():
                    quotes.append(interp)

    return [q for q in quotes if q.strip()]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_grounding_check(
    product_frame: str,
    market_facts: dict,
    persona_outputs: list[dict],
    source_documents: list[str] | None = None,
    journey_id: str = "",
) -> GroundingReport:
    """Run T1, T2, T3 grounding checks and return a GroundingReport.

    Args:
        product_frame:
            Concatenated text of all journey stimuli — the product brief
            fed to the simulation. T1 and T3 checks reference this.
        market_facts:
            Market facts dict. Use LITTLEJOYS_MARKET_FACTS or pass a custom
            dict with the same structure.
        persona_outputs:
            List of persona result dicts from BatchResult.logs.
        source_documents:
            Optional list of source doc strings. If provided, T1 checks
            verify product_frame claims are traceable to these docs.
        journey_id:
            Journey identifier for display purposes (e.g. "A", "B", "C").

    Returns:
        GroundingReport. .passed is True only when zero CRITICAL or HIGH issues.
    """
    if source_documents is None:
        source_documents = []

    all_issues: list[GroundingIssue] = []
    all_issues.extend(_check_t1(product_frame, source_documents))
    all_issues.extend(_check_t2(persona_outputs, market_facts))
    all_issues.extend(_check_t3(product_frame, persona_outputs))

    _sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_issues.sort(
        key=lambda i: (_sev_order.get(i.severity, 9), i.issue_type, i.persona_id or "")
    )

    blocking = [i for i in all_issues if i.severity in ("CRITICAL", "HIGH")]
    passed = len(blocking) == 0

    personas_with_issues = {i.persona_id for i in all_issues if i.persona_id}
    clean_personas = len(persona_outputs) - len(personas_with_issues)
    product_frame_clean = 1 if not [i for i in all_issues if i.persona_id is None] else 0
    clean_count = clean_personas + product_frame_clean

    return GroundingReport(
        passed=passed,
        issues=all_issues,
        clean_count=clean_count,
        journey_id=journey_id,
    )


def build_product_frame_from_journey(journey_config) -> str:
    """Build a product frame string from a JourneyConfig object.

    Concatenates all stimulus content strings so T1/T3 checks have the
    full text of what personas were exposed to.
    """
    parts: list[str] = []
    for stimulus in getattr(journey_config, "stimuli", []):
        content = getattr(stimulus, "content", None)
        if content:
            parts.append(str(content))
    decision = getattr(journey_config, "decisions", None) or []
    for dec in decision:
        desc = getattr(dec, "description", None)
        if desc:
            parts.append(str(desc))
        product = getattr(dec, "product", None)
        if product:
            parts.append(str(product))
    return " ".join(parts)
