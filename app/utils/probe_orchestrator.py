"""Sequential Probe Orchestrator — runs probes per hypothesis in order with early exit."""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from src.probing.engine import ProbingTreeEngine
from src.probing.models import (
    Hypothesis,
    Probe,
    ProbeResult,
    ProbeType,
    ProblemStatement,
)

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ProbeChainResult:
    """Result of running all probes for one hypothesis sequentially."""

    hypothesis_id: str
    hypothesis_title: str
    probes_run: list[ProbeResult]
    final_verdict: str  # "confirmed" | "partially_confirmed" | "rejected" | "insufficient"
    stopped_early: bool
    narrative: str  # system-voice style narration of what was found


@dataclass
class OrchestrationResult:
    """Full result of the sequential probing run across all hypotheses."""

    problem_id: str
    chain_results: list[ProbeChainResult]
    synthesis_narrative: str  # cross-hypothesis pattern text
    core_finding_draft: str  # one-sentence finding for Phase 3


# ---------------------------------------------------------------------------
# Narrative helpers
# ---------------------------------------------------------------------------


def _effect_label(effect_size: float) -> str:
    """Convert Cohen's d-style effect size to a plain-language label."""
    abs_d = abs(effect_size)
    if abs_d >= 0.8:
        return "strong"
    if abs_d >= 0.5:
        return "moderate"
    if abs_d >= 0.3:
        return "weak-to-moderate"
    return "weak"


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.70:
        return "strong"
    if confidence >= 0.45:
        return "moderate"
    return "weak"


def _format_interview_detail(result: ProbeResult) -> str:
    """Produce a concise string describing interview cluster results."""
    clusters = result.response_clusters
    if not clusters:
        return f"{result.sample_size} interviews yielded no clear theme"

    dominant = clusters[0]
    count = dominant.persona_count
    total = result.sample_size
    detail = f"{count} of {total} interviews — {dominant.description.lower()}"

    if len(clusters) > 1:
        secondary = clusters[1]
        detail += (
            f"; {secondary.persona_count} cite {secondary.description.lower()}"
        )
    return detail


def _format_attribute_detail(result: ProbeResult) -> str:
    """Produce a concise string describing attribute split results."""
    splits = result.attribute_splits
    if not splits:
        return "no meaningful attribute separation found"

    top = splits[0]
    direction = "higher among adopters" if top.adopter_mean >= top.rejector_mean else "higher among rejectors"
    label = top.attribute.replace("_", " ")
    return (
        f"{label} {direction} "
        f"({top.adopter_mean:.2f} vs {top.rejector_mean:.2f}, d={top.effect_size:.2f})"
    )


def _format_simulation_detail(result: ProbeResult) -> str:
    """Produce a concise string describing simulation/counterfactual results."""
    if result.lift is not None and result.baseline_metric is not None and result.modified_metric is not None:
        return (
            f"counterfactual moved metric from {result.baseline_metric:.0%} "
            f"to {result.modified_metric:.0%} (lift {result.lift:+.1%})"
        )
    return result.evidence_summary


def _describe_probe_result(result: ProbeResult, probe_type: ProbeType | None) -> str:
    """Return a short descriptive phrase for one probe result, keyed by type."""
    if probe_type == ProbeType.INTERVIEW:
        return _format_interview_detail(result)
    if probe_type == ProbeType.SIMULATION:
        return _format_simulation_detail(result)
    if probe_type == ProbeType.ATTRIBUTE:
        return _format_attribute_detail(result)
    # Fallback
    return result.evidence_summary


def _generate_hypothesis_narrative(
    h: Hypothesis,
    probes_run: list[ProbeResult],
    verdict: str,
    probes_ref: list[Probe] | None = None,
) -> str:
    """
    Generate a realistic reasoning narrative for one hypothesis chain.

    Uses actual numbers from ProbeResult fields — confidence, effect sizes,
    cluster counts, lift — to produce analyst-voice text rather than boilerplate.
    """
    if not probes_run:
        return f"{h.title}: no probes executed — insufficient data to assess."

    # Build a type lookup so we can call the right formatter per result
    type_by_probe_id: dict[str, ProbeType] = {}
    if probes_ref:
        for p in probes_ref:
            type_by_probe_id[p.id] = p.probe_type

    # Overall confidence is the mean across run probes
    confidences = [r.confidence for r in probes_run]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    peak_conf = max(confidences) if confidences else 0.0

    conf_label = _confidence_label(avg_conf)
    verdict_text = verdict.replace("_", " ")

    # Lead sentence: signal strength + confidence
    narrative_parts: list[str] = []

    # Pull effect size from first attribute probe if available
    effect_str = ""
    for r in probes_run:
        if r.attribute_splits:
            top_split = r.attribute_splits[0]
            d = top_split.effect_size
            effect_str = f" (d={d:.2f})"
            break
    # If no attribute probe, use peak confidence as the effect proxy
    if not effect_str:
        effect_str = f" (confidence peak {peak_conf:.0%})"

    narrative_parts.append(
        f"{h.title} shows {conf_label} signal{effect_str}."
    )

    # Evidence sentences — one per probe
    for idx, result in enumerate(probes_run):
        probe_type = type_by_probe_id.get(result.probe_id)
        detail = _describe_probe_result(result, probe_type)
        if probe_type == ProbeType.INTERVIEW:
            narrative_parts.append(f"Interviews: {detail}.")
        elif probe_type == ProbeType.SIMULATION:
            narrative_parts.append(f"Counterfactual: {detail}.")
        elif probe_type == ProbeType.ATTRIBUTE:
            narrative_parts.append(f"Attribute split: {detail}.")
        else:
            narrative_parts.append(f"Probe {idx + 1}: {detail}.")

    # Closing verdict sentence
    if verdict == "confirmed":
        narrative_parts.append(
            f"Confirmed as a primary driver at {avg_conf:.0%} avg confidence."
        )
    elif verdict == "partially_confirmed":
        narrative_parts.append(
            f"Partially confirmed ({avg_conf:.0%} avg confidence) — likely a contributing "
            "factor rather than root cause."
        )
    elif verdict == "rejected":
        narrative_parts.append(
            f"Signal too weak ({avg_conf:.0%} avg confidence). "
            "Not a primary driver — possible moderator or context-dependent effect."
        )
    else:  # insufficient
        narrative_parts.append(
            "Insufficient data — probing did not complete. Verdict deferred."
        )

    return " ".join(narrative_parts)


def _build_synthesis_narrative(
    chain_results: list[ProbeChainResult],
    hypotheses: list[Hypothesis],
) -> str:
    """
    Build a cross-hypothesis synthesis narrative.

    Identifies confirmed hypotheses, looks for shared indicator attributes,
    and flags any hypotheses that were rejected early vs. those that partially confirmed.
    """
    if not chain_results:
        return "No hypotheses were probed — no synthesis available."

    confirmed = [c for c in chain_results if c.final_verdict == "confirmed"]
    partial = [c for c in chain_results if c.final_verdict == "partially_confirmed"]
    rejected = [c for c in chain_results if c.final_verdict in ("rejected", "insufficient")]
    early_stopped = [c for c in chain_results if c.stopped_early]

    h_by_id = {h.id: h for h in hypotheses}

    parts: list[str] = []

    if confirmed:
        titles = ", ".join(c.hypothesis_title for c in confirmed)
        parts.append(f"Confirmed hypotheses: {titles}.")

    if partial:
        titles = ", ".join(c.hypothesis_title for c in partial)
        parts.append(f"Partial confirmation: {titles} — worth monitoring but not primary drivers.")

    if early_stopped:
        count = len(early_stopped)
        parts.append(
            f"{count} hypothesis{'es' if count > 1 else ''} exited early on weak L1 signal "
            "and were not pursued further."
        )
    elif rejected:
        titles = ", ".join(c.hypothesis_title for c in rejected)
        parts.append(f"Rejected: {titles}.")

    # Shared indicator attributes between confirmed/partial hypotheses
    signal_hyps = confirmed + partial
    if len(signal_hyps) > 1:
        shared_attrs: dict[str, list[str]] = {}
        for chain in signal_hyps:
            h = h_by_id.get(chain.hypothesis_id)
            if h:
                for attr in h.indicator_attributes:
                    shared_attrs.setdefault(attr, []).append(h.id)
        overlapping = [attr for attr, ids in shared_attrs.items() if len(ids) > 1]
        if overlapping:
            attr_str = ", ".join(a.replace("_", " ") for a in overlapping[:3])
            parts.append(
                f"Common signal attributes across confirmed branches: {attr_str} — "
                "these dimensions appear structural and warrant deeper segmentation."
            )

    if not parts:
        return "No confirmed or partially confirmed hypotheses found. Consider expanding the probe set."

    return " ".join(parts)


def _build_core_finding(
    chain_results: list[ProbeChainResult],
    problem: ProblemStatement,
) -> str:
    """Produce a single-sentence core finding for Phase 3 consumption."""
    confirmed = [c for c in chain_results if c.final_verdict == "confirmed"]
    partial = [c for c in chain_results if c.final_verdict == "partially_confirmed"]

    top_results = confirmed or partial
    if not top_results:
        return (
            f"Probing for '{problem.title}' found no strong primary driver; "
            "all hypotheses returned weak or insufficient signal."
        )

    if len(top_results) == 1:
        c = top_results[0]
        verdict_word = "primary driver" if c.final_verdict == "confirmed" else "contributing factor"
        return (
            f"The {verdict_word} behind '{problem.title}' is {c.hypothesis_title.lower()}, "
            f"supported by {len(c.probes_run)} probe{'s' if len(c.probes_run) != 1 else ''}."
        )

    # Multiple confirmed — pick the one with the highest average probe confidence
    def _avg_conf(chain: ProbeChainResult) -> float:
        if not chain.probes_run:
            return 0.0
        return sum(r.confidence for r in chain.probes_run) / len(chain.probes_run)

    top = max(top_results, key=_avg_conf)
    others = [c.hypothesis_title.lower() for c in top_results if c.hypothesis_id != top.hypothesis_id]
    others_str = f" with supporting signals from {', '.join(others)}" if others else ""
    return (
        f"The dominant driver of '{problem.title}' is {top.hypothesis_title.lower()}"
        f"{others_str}."
    )


# ---------------------------------------------------------------------------
# Main orchestration function
# ---------------------------------------------------------------------------


def run_sequential_probing(
    engine: ProbingTreeEngine,
    problem: ProblemStatement,
    hypotheses: list[Hypothesis],  # only enabled ones
    probes: list[Probe],
    *,
    early_exit_threshold: float = 0.3,
    streamlit_status: bool = True,
) -> OrchestrationResult:
    """
    Run probes sequentially per hypothesis (L1 → L2 → L3) with early exit on weak signal.

    Parameters
    ----------
    engine:
        A fully initialised ProbingTreeEngine with population and scenario loaded.
    problem:
        The ProblemStatement being investigated.
    hypotheses:
        List of *enabled* Hypothesis objects, ordered as desired.
    probes:
        All Probe objects for this problem (the function filters by hypothesis_id internally).
    early_exit_threshold:
        If the L1 probe's confidence is below this value the remaining probes for that
        hypothesis are skipped and the hypothesis is marked rejected.
    streamlit_status:
        When True the function emits ``st.write`` progress messages so a running
        Streamlit session can show live status updates.

    Returns
    -------
    OrchestrationResult
        Contains per-hypothesis chain results, a cross-hypothesis synthesis narrative,
        and a single-sentence core finding ready for Phase 3.
    """
    # Conditional import — only pulled in when actually running inside Streamlit
    if streamlit_status:
        try:
            import streamlit as st  # noqa: PLC0415
            _st_write = st.write
        except ImportError:
            streamlit_status = False
            _st_write = None  # type: ignore[assignment]
    else:
        _st_write = None  # type: ignore[assignment]

    # Group probes by hypothesis_id, sorted by probe.order (then id for stability)
    probes_by_hyp: dict[str, list[Probe]] = {}
    for probe in probes:
        probes_by_hyp.setdefault(probe.hypothesis_id, []).append(probe)
    for hyp_id in probes_by_hyp:
        probes_by_hyp[hyp_id].sort(key=lambda p: (p.order, p.id))

    # Sort hypotheses by order (then id for stability)
    ordered_hypotheses = sorted(hypotheses, key=lambda h: (h.order, h.id))

    chain_results: list[ProbeChainResult] = []

    for hypothesis in ordered_hypotheses:
        log.info("orchestrator_hypothesis_start", hypothesis_id=hypothesis.id)

        if streamlit_status and _st_write is not None:
            _st_write(f"Investigating: {hypothesis.title}...")

        hyp_probes = probes_by_hyp.get(hypothesis.id, [])
        if not hyp_probes:
            log.warning("orchestrator_no_probes", hypothesis_id=hypothesis.id)
            chain_results.append(
                ProbeChainResult(
                    hypothesis_id=hypothesis.id,
                    hypothesis_title=hypothesis.title,
                    probes_run=[],
                    final_verdict="insufficient",
                    stopped_early=False,
                    narrative=(
                        f"{hypothesis.title}: no probes defined — verdict deferred."
                    ),
                )
            )
            continue

        # --- L1 probe (lowest order) ---
        l1_probe = hyp_probes[0]
        remaining_probes = hyp_probes[1:]

        log.info(
            "orchestrator_probe_start",
            probe_id=l1_probe.id,
            probe_type=l1_probe.probe_type,
            level="L1",
        )
        l1_result = engine.execute_probe(l1_probe)
        probes_run: list[ProbeResult] = [l1_result]

        # Early exit on weak L1 signal
        if l1_result.confidence < early_exit_threshold:
            log.info(
                "orchestrator_early_exit",
                hypothesis_id=hypothesis.id,
                l1_confidence=l1_result.confidence,
                threshold=early_exit_threshold,
            )
            if streamlit_status and _st_write is not None:
                _st_write(
                    f"  → Weak L1 signal on '{hypothesis.title}' "
                    f"(confidence {l1_result.confidence:.0%}). Skipping L2/L3."
                )

            narrative = (
                f"Weak signal on {hypothesis.title} (confidence {l1_result.confidence:.0%}). "
                "Not pursuing further."
            )
            chain_results.append(
                ProbeChainResult(
                    hypothesis_id=hypothesis.id,
                    hypothesis_title=hypothesis.title,
                    probes_run=probes_run,
                    final_verdict="rejected",
                    stopped_early=True,
                    narrative=narrative,
                )
            )
            continue

        # --- L2 and L3 probes ---
        for probe in remaining_probes:
            log.info(
                "orchestrator_probe_start",
                probe_id=probe.id,
                probe_type=probe.probe_type,
                level=f"L{probe.order}",
            )
            if streamlit_status and _st_write is not None:
                _st_write(f"  → Running probe: {probe.id} ({probe.probe_type})...")
            result = engine.execute_probe(probe)
            probes_run.append(result)

        # --- Determine verdict from average confidence across all run probes ---
        avg_confidence = sum(r.confidence for r in probes_run) / len(probes_run)

        if avg_confidence >= 0.70:
            verdict = "confirmed"
        elif avg_confidence >= 0.45:
            verdict = "partially_confirmed"
        else:
            verdict = "rejected"

        log.info(
            "orchestrator_hypothesis_verdict",
            hypothesis_id=hypothesis.id,
            avg_confidence=avg_confidence,
            verdict=verdict,
            probes_run=len(probes_run),
        )

        narrative = _generate_hypothesis_narrative(
            h=hypothesis,
            probes_run=probes_run,
            verdict=verdict,
            probes_ref=hyp_probes,
        )

        chain_results.append(
            ProbeChainResult(
                hypothesis_id=hypothesis.id,
                hypothesis_title=hypothesis.title,
                probes_run=probes_run,
                final_verdict=verdict,
                stopped_early=False,
                narrative=narrative,
            )
        )

    # --- Cross-hypothesis synthesis ---
    synthesis_narrative = _build_synthesis_narrative(chain_results, ordered_hypotheses)
    core_finding_draft = _build_core_finding(chain_results, problem)

    log.info(
        "orchestrator_complete",
        problem_id=problem.id,
        hypotheses_run=len(chain_results),
        confirmed=sum(1 for c in chain_results if c.final_verdict == "confirmed"),
        partial=sum(1 for c in chain_results if c.final_verdict == "partially_confirmed"),
        rejected=sum(
            1 for c in chain_results if c.final_verdict in ("rejected", "insufficient")
        ),
        early_exits=sum(1 for c in chain_results if c.stopped_early),
    )

    return OrchestrationResult(
        problem_id=problem.id,
        chain_results=chain_results,
        synthesis_narrative=synthesis_narrative,
        core_finding_draft=core_finding_draft,
    )
