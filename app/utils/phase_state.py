"""Phase completion state management and sidebar gating."""

from __future__ import annotations

import streamlit as st

# Keys in st.session_state that mark each phase complete
_PHASE_KEYS: dict[int, str] = {
    0: "",  # always unlocked
    1: "baseline_cohorts",  # set after baseline simulation completes
    2: "probe_results",  # set after at least one probe chain completes
    3: "core_finding",  # set after Core Finding is generated
    4: "intervention_results",  # set after intervention simulations complete
}

_PHASE_LABELS: dict[int, str] = {
    0: "Explore Population",
    1: "Problem & Simulation",
    2: "Decomposition & Probing",
    3: "Core Finding",
    4: "Interventions",
}

_PHASE_PREREQS: dict[int, str] = {
    1: "Load a population first.",
    2: "Run the baseline simulation in Phase 1 first.",
    3: "Run the investigation in Phase 2 first.",
    4: "Generate the Core Finding in Phase 3 first.",
}


def phase_complete(phase: int) -> bool:
    """Return True if the given phase's prerequisite is satisfied."""
    if phase == 0:
        return True
    if phase == 1:
        return "population" in st.session_state
    key = _PHASE_KEYS.get(phase, "")
    return bool(key and key in st.session_state)


def mark_phase_complete(phase: int) -> None:
    """Mark a phase as complete by writing its sentinel key."""
    # Phase 1 is marked by writing baseline_cohorts (done in the simulation page)
    # Other phases write their own keys; this is a no-op marker for clarity.
    pass


def render_phase_sidebar() -> None:
    """Render the phase navigation sidebar with lock/unlock status icons."""
    st.sidebar.markdown("### Navigation")
    icons = {True: "🟢", False: "🔒"}
    for phase, label in _PHASE_LABELS.items():
        unlocked = phase_complete(phase)
        icon = icons[unlocked]
        prereq = _PHASE_PREREQS.get(phase, "")
        st.sidebar.caption(f"{icon} {phase} — {label}")
        if not unlocked and prereq:
            st.sidebar.caption(f"   ↳ _{prereq}_")

    st.sidebar.divider()
    st.sidebar.page_link(
        "pages/9_compare.py",
        label="⚖️ Compare Scenarios",
        icon="⚖️",
    )
