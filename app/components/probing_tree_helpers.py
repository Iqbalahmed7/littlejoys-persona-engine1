"""Presentation helpers for the Probing Tree Streamlit page (PRD-014b)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.constants import DASHBOARD_DEFAULT_POPULATION_PATH
from src.generation.population import Population
from src.probing.models import Probe, ProbeResult, ProbeType
from src.utils.display import display_name


def _target_outcome_phrase(outcome: str | None) -> str:
    if not outcome:
        return ""
    ol = outcome.strip().lower()
    if ol == "adopt":
        return "would-buy"
    if ol == "reject":
        return "wouldn't-buy"
    return outcome.replace("_", " ")


def _format_mod_value(value: Any) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, float) and 0.0 <= value <= 1.0:
        return f"{value:.0%}"
    return str(value)


def probe_icon(probe_type: ProbeType) -> str:
    """Return emoji icon for probe type."""

    return {
        ProbeType.INTERVIEW: "🎤",
        ProbeType.SIMULATION: "🔬",
        ProbeType.ATTRIBUTE: "📊",
    }.get(probe_type, "❓")


def probe_label(probe: Probe) -> str:
    """One-line description of what this probe does."""

    if probe.probe_type == ProbeType.INTERVIEW:
        q = probe.question_template or ""
        phrase = _target_outcome_phrase(probe.target_outcome)
        suffix = f" (focus: {phrase} personas only)" if phrase else ""
        return f'"{q}"{suffix}'
    if probe.probe_type == ProbeType.SIMULATION:
        mods = probe.scenario_modifications or {}
        changes = ", ".join(
            f"{display_name(str(k).split('.')[-1])} → {_format_mod_value(v)}"
            for k, v in mods.items()
        )
        return f"Simulate: {changes}" if changes else f"Simulate ({probe.id})"
    if probe.probe_type == ProbeType.ATTRIBUTE:
        attrs = ", ".join(display_name(a) for a in probe.analysis_attributes[:3])
        return f"Analyse: {attrs} by purchase intent"
    return probe.id


def verdict_status_display(status: str) -> str:
    """User-facing verdict label (no raw snake_case)."""

    return status.replace("_", " ").title()


def render_interview_detail(result: ProbeResult) -> None:
    """Show response clusters with representative quotes."""

    for cluster in result.response_clusters:
        pct = f"{cluster.percentage:.0%}"
        st.markdown(f"**{cluster.theme.replace('_', ' ').title()}** — {pct} of responses")
        st.caption(cluster.description)
        if cluster.representative_quotes:
            for quote in cluster.representative_quotes[:3]:
                st.markdown(f"> _{quote[:300]}_")
        if cluster.dominant_attributes:
            attrs = ", ".join(
                f"{display_name(k)}: {v:.2f}"
                for k, v in list(cluster.dominant_attributes.items())[:5]
            )
            st.caption(f"Dominant attributes: {attrs}")


def render_simulation_detail(result: ProbeResult) -> None:
    """Show baseline vs modified metric with lift."""

    col_base, col_mod, col_lift = st.columns(3)
    col_base.metric(
        "Baseline",
        f"{result.baseline_metric:.0%}" if result.baseline_metric is not None else "—",
    )
    col_mod.metric(
        "Modified",
        f"{result.modified_metric:.0%}" if result.modified_metric is not None else "—",
    )
    col_lift.metric(
        "Lift",
        f"{result.lift:+.1%}" if result.lift is not None else "—",
        delta=f"{result.lift:+.1%}" if result.lift is not None else None,
    )


def render_attribute_detail(result: ProbeResult) -> None:
    """Show attribute splits as a comparison table."""

    rows = []
    for split in result.attribute_splits:
        rows.append(
            {
                "Attribute": display_name(split.attribute),
                "Would-buy mean": f"{split.adopter_mean:.2f}",
                "Wouldn't-buy mean": f"{split.rejector_mean:.2f}",
                "Effect size": f"{split.effect_size:+.2f}",
                "Significant": "Yes" if split.significant else "No",
            }
        )
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def load_population_for_probing() -> Population | None:
    """Load population from session state or default disk path."""

    if "population" in st.session_state:
        return st.session_state["population"]
    pop_path = Path(DASHBOARD_DEFAULT_POPULATION_PATH)
    if pop_path.exists():
        pop = Population.load(pop_path)
        st.session_state["population"] = pop
        return pop
    return None
