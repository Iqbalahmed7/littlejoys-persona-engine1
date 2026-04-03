"""Sprint 33A — structured report builder.

Converts probe results and tree synthesis into a ReportData dataclass
that can be serialised to JSON or rendered as a PDF.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from src.probing.models import (
    Hypothesis,
    HypothesisVerdict,
    Probe,
    ProbeResult,
    ProblemStatement,
    TreeSynthesis,
)


# ── Output dataclasses ────────────────────────────────────────────────────────

@dataclass
class ReportSection:
    title: str
    body: str  # markdown-style plain text


@dataclass
class HypothesisReport:
    id: str
    title: str
    confidence: float        # 0.0–1.0
    status: str              # "confirmed" / "inconclusive" / "rejected"
    evidence_summary: str
    key_quotes: list[str]    # top 3 verbatim from interview probes
    attribute_splits: list[dict]  # [{"attribute": str, "adopter": float, "rejector": float}]
    recommended_action: str  # one concrete action this hypothesis implies


@dataclass
class ReportData:
    problem_title: str
    problem_context: str
    generated_at: str        # ISO timestamp
    total_personas: int
    hypotheses: list[HypothesisReport]
    top_findings: list[str]  # 3–5 bullet-point findings
    recommended_interventions: list[dict]  # 3–5 interventions
    overall_confidence: float
    raw_synthesis: dict      # full synthesis.model_dump() for JSON export


# ── Intervention mapping ──────────────────────────────────────────────────────

_INTERVENTION_TEMPLATES: list[dict] = [
    {
        "title": "Awareness campaign via paediatrician network",
        "type": "awareness",
        "expected_lift_pct": 15,
        "keywords": ["aware", "know", "famil"],
        "rationale": (
            "A significant share of non-adopters lack basic awareness of the product. "
            "Reaching parents through trusted paediatricians at the point of prescription "
            "shortens the awareness-to-trial gap."
        ),
        "intervention_type": "awareness",
        "config": {"channel": "paediatrician_network", "format": "in-clinic_leaflet"},
    },
    {
        "title": "Introductory price trial at Rs 449",
        "type": "pricing",
        "expected_lift_pct": 12,
        "keywords": ["price", "cost", "afford", "expensive", "cheap"],
        "rationale": (
            "Price sensitivity is a primary barrier at reorder. A limited-time trial "
            "price reduces the perceived financial risk and drives first repeat purchase."
        ),
        "intervention_type": "pricing",
        "config": {"sku": "trial_pack_30day", "price_inr": 449, "duration_days": 30},
    },
    {
        "title": "Doctor-led sampling in hospital pharmacies",
        "type": "channel",
        "expected_lift_pct": 18,
        "keywords": ["trust", "doctor", "recommend", "credib", "safe"],
        "rationale": (
            "Trust deficits are overcome most efficiently at the point of clinical "
            "recommendation. Hospital pharmacy sampling converts skeptical parents via "
            "an already-trusted authority."
        ),
        "intervention_type": "channel",
        "config": {"channel": "hospital_pharmacy", "mechanic": "doctor_sample"},
    },
    {
        "title": "Free trial sachet campaign",
        "type": "sampling",
        "expected_lift_pct": 22,
        "keywords": ["taste", "format", "flavour", "texture", "mix", "sachet"],
        "rationale": (
            "Taste and format hesitation is resolved fastest through zero-risk trial. "
            "A free sachet distributed at pediatric checkups or via e-commerce inserts "
            "removes the sensory uncertainty barrier."
        ),
        "intervention_type": "sampling",
        "config": {"pack_size_g": 30, "channels": ["ecommerce_insert", "clinic"]},
    },
    {
        "title": "30-day reorder reminder + loyalty reward",
        "type": "retention",
        "expected_lift_pct": 14,
        "keywords": ["lapse", "forget", "reorder", "repeat", "retain", "loyalty"],
        "rationale": (
            "Lapsed buyers often intend to reorder but fall out of habit. A timely "
            "push notification at day 28 paired with a loyalty reward increases "
            "the probability of a second purchase."
        ),
        "intervention_type": "retention",
        "config": {"trigger_day": 28, "reward_type": "discount_10pct"},
    },
]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _derive_status(confidence: float) -> str:
    if confidence >= 0.65:
        return "confirmed"
    if confidence >= 0.40:
        return "inconclusive"
    return "rejected"


def _derive_recommended_action(title: str, confidence: float) -> str:
    if confidence > 0.6:
        return f"Prioritise addressing: {title}"
    if confidence >= 0.4:
        return f"Further investigate: {title}"
    return f"Deprioritise: {title}"


def _extract_key_quotes(
    hypothesis_id: str,
    probes: list[Probe],
    probe_results: dict[str, ProbeResult],
    top_n: int = 3,
) -> list[str]:
    """Collect verbatim interview quotes for a hypothesis, ranked by length."""
    quotes: list[tuple[int, str]] = []
    for probe in probes:
        if probe.hypothesis_id != hypothesis_id:
            continue
        result = probe_results.get(probe.id)
        if result is None:
            continue
        for resp in result.interview_responses:
            content = (resp.content or "").strip()
            if content:
                quotes.append((len(content), content))
    quotes.sort(key=lambda x: x[0], reverse=True)
    return [q for _, q in quotes[:top_n]]


def _extract_attribute_splits(
    hypothesis_id: str,
    probes: list[Probe],
    probe_results: dict[str, ProbeResult],
    top_n: int = 3,
) -> list[dict]:
    """Return top-N attribute splits by effect size."""
    splits: list[tuple[float, dict]] = []
    for probe in probes:
        if probe.hypothesis_id != hypothesis_id:
            continue
        result = probe_results.get(probe.id)
        if result is None:
            continue
        for split in result.attribute_splits:
            splits.append((
                abs(split.effect_size),
                {
                    "attribute": split.attribute,
                    "adopter": round(split.adopter_mean, 3),
                    "rejector": round(split.rejector_mean, 3),
                    "effect_size": round(split.effect_size, 3),
                },
            ))
    splits.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in splits[:top_n]]


def _build_hypothesis_reports(
    hypotheses: list[Hypothesis],
    probes: list[Probe],
    probe_results: dict[str, ProbeResult],
    synthesis: TreeSynthesis,
) -> list[HypothesisReport]:
    confidence_map: dict[str, float] = dict(synthesis.confidence_ranking)

    reports: list[HypothesisReport] = []
    for hyp in hypotheses:
        confidence = confidence_map.get(hyp.id, hyp.confidence_prior)

        # Gather evidence summary from probe results
        evidence_parts: list[str] = []
        for probe in probes:
            if probe.hypothesis_id != hyp.id:
                continue
            result = probe_results.get(probe.id)
            if result and result.evidence_summary:
                evidence_parts.append(result.evidence_summary)
        evidence_summary = (
            " ".join(evidence_parts)
            if evidence_parts
            else f"No detailed evidence captured for hypothesis '{hyp.title}'."
        )

        status = _derive_status(confidence)
        quotes = _extract_key_quotes(hyp.id, probes, probe_results)
        attr_splits = _extract_attribute_splits(hyp.id, probes, probe_results)
        action = _derive_recommended_action(hyp.title, confidence)

        reports.append(HypothesisReport(
            id=hyp.id,
            title=hyp.title,
            confidence=round(confidence, 3),
            status=status,
            evidence_summary=evidence_summary,
            key_quotes=quotes,
            attribute_splits=attr_splits,
            recommended_action=action,
        ))

    # If no hypotheses objects were provided but synthesis has ranking, build
    # minimal placeholders so we still produce a useful report.
    if not reports and synthesis.confidence_ranking:
        for h_id, conf in synthesis.confidence_ranking:
            reports.append(HypothesisReport(
                id=h_id,
                title=h_id.replace("_", " ").title(),
                confidence=round(conf, 3),
                status=_derive_status(conf),
                evidence_summary="",
                key_quotes=[],
                attribute_splits=[],
                recommended_action=_derive_recommended_action(h_id, conf),
            ))

    return reports


def _build_top_findings(
    hypothesis_reports: list[HypothesisReport],
    synthesis: TreeSynthesis,
) -> list[str]:
    """Produce 3–5 bullet findings from synthesis narrative or confirmed hypotheses."""
    # If synthesis has a narrative, split on sentences into bullets
    narrative = (synthesis.synthesis_narrative or "").strip()
    if narrative:
        # Split on ". " boundaries
        sentences = [s.strip() for s in narrative.replace(". ", ".|").split("|") if s.strip()]
        findings = [s if s.endswith(".") else s + "." for s in sentences[:5]]
        if len(findings) >= 3:
            return findings

    # Fallback: derive from top 3 confirmed hypotheses
    confirmed = [h for h in hypothesis_reports if h.status == "confirmed"]
    if not confirmed:
        confirmed = sorted(hypothesis_reports, key=lambda h: h.confidence, reverse=True)
    findings = []
    for h in confirmed[:5]:
        pct = int(h.confidence * 100)
        findings.append(
            f"{h.title} (confidence {pct}%): {h.evidence_summary[:200].rstrip('.')}."
        )
    if not findings:
        findings = ["Insufficient probe data to generate top findings."]
    return findings[:5]


def _build_interventions(
    hypothesis_reports: list[HypothesisReport],
    synthesis: TreeSynthesis,
) -> list[dict]:
    """Map confirmed hypotheses to intervention templates, return top 3–5 by lift."""
    confirmed = [h for h in hypothesis_reports if h.status in ("confirmed", "inconclusive")]
    selected: dict[str, dict] = {}  # keyed by intervention title to avoid duplicates

    for h in confirmed:
        title_lower = h.title.lower()
        for template in _INTERVENTION_TEMPLATES:
            if any(kw in title_lower for kw in template["keywords"]):
                entry = {
                    "title": template["title"],
                    "rationale": template["rationale"],
                    "expected_lift_pct": template["expected_lift_pct"],
                    "intervention_type": template["intervention_type"],
                    "config": template["config"],
                    "hypothesis_id": h.id,
                }
                key = template["title"]
                if key not in selected:
                    selected[key] = entry

    result = sorted(selected.values(), key=lambda x: x["expected_lift_pct"], reverse=True)

    # If nothing matched, fall back to top-3 by lift across all templates
    if not result:
        result = sorted(
            [
                {
                    "title": t["title"],
                    "rationale": t["rationale"],
                    "expected_lift_pct": t["expected_lift_pct"],
                    "intervention_type": t["intervention_type"],
                    "config": t["config"],
                    "hypothesis_id": "",
                }
                for t in _INTERVENTION_TEMPLATES
            ],
            key=lambda x: x["expected_lift_pct"],
            reverse=True,
        )[:3]

    return result[:5]


# ── Public API ────────────────────────────────────────────────────────────────

def build_report(
    problem: ProblemStatement,
    hypotheses: list[Hypothesis],
    probes: list[Probe],
    probe_results: dict[str, ProbeResult],
    synthesis: TreeSynthesis,
) -> ReportData:
    """Build a structured ReportData from probe results and tree synthesis."""

    hypothesis_reports = _build_hypothesis_reports(
        hypotheses, probes, probe_results, synthesis
    )

    top_findings = _build_top_findings(hypothesis_reports, synthesis)
    interventions = _build_interventions(hypothesis_reports, synthesis)

    # overall_confidence: prefer synthesis field, fall back to mean of hypothesis confs
    if synthesis.overall_confidence and synthesis.overall_confidence > 0.0:
        overall_conf = round(synthesis.overall_confidence, 3)
    elif hypothesis_reports:
        overall_conf = round(mean(h.confidence for h in hypothesis_reports), 3)
    else:
        overall_conf = 0.0

    # Total personas: sum sample sizes across all probe results, or 0
    total_personas: int = 0
    seen_probes: set[str] = set()
    for probe in probes:
        result = probe_results.get(probe.id)
        if result and probe.id not in seen_probes:
            total_personas = max(total_personas, result.population_size or result.sample_size)
            seen_probes.add(probe.id)

    return ReportData(
        problem_title=problem.title,
        problem_context=problem.context,
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
        total_personas=total_personas,
        hypotheses=hypothesis_reports,
        top_findings=top_findings,
        recommended_interventions=interventions,
        overall_confidence=overall_conf,
        raw_synthesis=synthesis.model_dump(),
    )


def report_to_json(report_data: ReportData) -> str:
    """Serialise a ReportData to a JSON string."""
    return json.dumps(asdict(report_data), indent=2, ensure_ascii=False)
