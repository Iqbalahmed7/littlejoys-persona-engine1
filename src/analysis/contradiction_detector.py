"""Cross-hypothesis contradiction detection utilities."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING

from src.probing.models import ProbeType

if TYPE_CHECKING:
    from src.probing.models import Hypothesis, HypothesisVerdict, Probe

    Verdict = HypothesisVerdict


@dataclass
class ContradictionWarning:
    hypothesis_a_id: str
    hypothesis_b_id: str
    contradiction_type: str
    description: str
    severity: str


def _probe_type_value(raw: object) -> str:
    if isinstance(raw, ProbeType):
        return raw.value
    return str(raw).split(".")[-1].lower()


def _status(raw: object) -> str:
    return str(raw or "").lower()


def _dominant_theme_by_hypothesis(probes: list[Probe]) -> dict[str, str]:
    themes: dict[str, str] = {}
    for probe in probes:
        if _probe_type_value(getattr(probe, "probe_type", "")) != ProbeType.INTERVIEW.value:
            continue
        result = getattr(probe, "result", None)
        if result is None:
            continue
        clusters = getattr(result, "response_clusters", None) or []
        if not clusters:
            continue
        dominant = max(
            clusters,
            key=lambda c: (
                int(getattr(c, "persona_count", 0) or 0),
                float(getattr(c, "percentage", 0.0) or 0.0),
            ),
        )
        theme = str(getattr(dominant, "theme", "")).strip()
        if theme:
            themes[probe.hypothesis_id] = theme
    return themes


def detect_contradictions(
    hypotheses: list[Hypothesis],
    verdicts: dict[str, Verdict],
    probes: list[Probe],
) -> list[ContradictionWarning]:
    warnings: list[ContradictionWarning] = []
    hyp_by_id = {h.id: h for h in hypotheses}
    probe_by_hypothesis: dict[str, list[Probe]] = {}
    for probe in probes:
        probe_by_hypothesis.setdefault(probe.hypothesis_id, []).append(probe)

    # 1) Confidence conflict
    for a_id, b_id in combinations(verdicts.keys(), 2):
        a_verdict = verdicts[a_id]
        b_verdict = verdicts[b_id]
        a_status = _status(getattr(a_verdict, "status", ""))
        b_status = _status(getattr(b_verdict, "status", ""))
        a_conf = float(getattr(a_verdict, "confidence", 0.0) or 0.0)
        b_conf = float(getattr(b_verdict, "confidence", 0.0) or 0.0)

        h_a = hyp_by_id.get(a_id)
        h_b = hyp_by_id.get(b_id)
        if h_a is None or h_b is None:
            continue

        overlap = set(h_a.indicator_attributes).intersection(set(h_b.indicator_attributes))
        if not overlap:
            continue

        a_confirmed_b_rejected = a_status == "confirmed" and a_conf >= 0.70 and b_status == "rejected" and b_conf < 0.30
        b_confirmed_a_rejected = b_status == "confirmed" and b_conf >= 0.70 and a_status == "rejected" and a_conf < 0.30
        if a_confirmed_b_rejected or b_confirmed_a_rejected:
            overlap_label = ", ".join(sorted(overlap))
            warnings.append(
                ContradictionWarning(
                    hypothesis_a_id=a_id,
                    hypothesis_b_id=b_id,
                    contradiction_type="confidence_conflict",
                    description=(
                        f"Hypotheses {a_id} and {b_id} overlap on '{overlap_label}' but reached "
                        "opposite confidence outcomes (confirmed vs rejected)."
                    ),
                    severity="high",
                )
            )

    # 2) Mechanism overlap
    dominant_theme = _dominant_theme_by_hypothesis(probes)
    for a_id, b_id in combinations(verdicts.keys(), 2):
        theme_a = dominant_theme.get(a_id)
        theme_b = dominant_theme.get(b_id)
        if not theme_a or not theme_b:
            continue
        if theme_a.lower() != theme_b.lower():
            continue
        a_status = _status(getattr(verdicts[a_id], "status", ""))
        b_status = _status(getattr(verdicts[b_id], "status", ""))
        if a_status == b_status:
            continue
        warnings.append(
            ContradictionWarning(
                hypothesis_a_id=a_id,
                hypothesis_b_id=b_id,
                contradiction_type="mechanism_overlap",
                description=(
                    f"Both {a_id} and {b_id} share the '{theme_a}' theme but reached different "
                    "conclusions — investigate shared drivers."
                ),
                severity="medium",
            )
        )

    # 3) Simulation divergence
    for hyp_id, verdict in verdicts.items():
        status = _status(getattr(verdict, "status", ""))
        if status not in {"inconclusive", "rejected"}:
            continue
        hyp_probes = probe_by_hypothesis.get(hyp_id, [])
        for probe in hyp_probes:
            if _probe_type_value(getattr(probe, "probe_type", "")) != ProbeType.SIMULATION.value:
                continue
            result = getattr(probe, "result", None)
            if result is None:
                continue
            lift = getattr(result, "lift", None)
            if lift is None or float(lift) <= 0.02:
                continue
            warnings.append(
                ContradictionWarning(
                    hypothesis_a_id=hyp_id,
                    hypothesis_b_id=hyp_id,
                    contradiction_type="simulation_divergence",
                    description=(
                        f"Simulation suggests an effect for {hyp_id} that the interview evidence does not "
                        "support — consider a deeper counterfactual test."
                    ),
                    severity="low",
                )
            )
            break

    severity_order = {"high": 0, "medium": 1, "low": 2}
    warnings.sort(
        key=lambda w: (
            severity_order.get(w.severity, 3),
            w.hypothesis_a_id,
            w.hypothesis_b_id,
            w.contradiction_type,
        )
    )
    return warnings
