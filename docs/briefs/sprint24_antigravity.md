# Sprint 24 Brief — Antigravity
## S4-03: Phase 3 Evidence Chain + Quote Bank

> **Engineer**: Antigravity (Gemini 3 Flash → escalate to Gemini Pro if evidence chain assembly is complex)
> **Sprint**: 24
> **Ticket**: S4-03
> **Estimated effort**: Medium
> **Reference**: LittleJoys User Flow Document v2.0, Sections 6.1, 6.2.3

---

### Context

Phase 3 (`app/pages/4_finding.py`) currently shows:
- A Core Finding box (green bordered callout)
- A synthesis narrative expander
- Phase-complete banner

The v2.0 spec requires two additions:
1. **Evidence Chain** — a structured visualization showing exactly which probes produced which conclusions, with effect sizes and lift numbers
2. **Quote Bank** — representative persona voices organized by theme, surfacing qualitative depth without requiring the user to navigate to the interviews page

Both are built from data already in `st.session_state["probe_results"]`. No new LLM calls. No new backend. Pure UI assembly.

---

### Data Available in Session State

```python
results = st.session_state["probe_results"]

synthesis   = results["synthesis"]       # TreeSynthesis object
verdicts    = results["verdicts"]        # dict[str, HypothesisVerdict] — hyp_id → verdict
probes      = results.get("probes", []) # list[Probe] — each Probe has .result (ProbeResult or None)
hypotheses  = results.get("hypotheses", [])  # list[Hypothesis]
problem     = results.get("problem")    # ProblemStatement
```

**Key model fields you'll need:**

`HypothesisVerdict`:
- `.status` — "confirmed" | "partially_confirmed" | "rejected" | "inconclusive"
- `.confidence` — float 0–1
- `.evidence_summary` — str

`Probe`:
- `.hypothesis_id` — str
- `.probe_type` — ProbeType enum (INTERVIEW | ATTRIBUTE | SIMULATION)
- `.result` — `ProbeResult | None`
- `.question_template` — str (the probe question)

`ProbeResult`:
- `.confidence` — float 0–1
- `.evidence_summary` — str
- `.interview_responses` — list (for INTERVIEW probes) — each has `.persona_name`, `.content`, `.outcome`
- `.response_clusters` — list — each has `.theme`, `.description`, `.persona_count`, `.percentage`, `.representative_quotes`

---

### Task 1: Evidence Chain Visualization

**Location**: `app/pages/4_finding.py` — after the Core Finding callout, before the synthesis narrative expander.

```python
st.divider()
st.subheader("Evidence Chain")
st.caption(
    "Each confirmed finding is grounded in a chain of evidence — "
    "statistical signals, persona interviews, and counterfactual simulations."
)
```

For each hypothesis that is confirmed or partially confirmed, render a structured card:

```python
_PROBE_TYPE_ICON = {
    "ATTRIBUTE": "📊",
    "INTERVIEW": "🎤",
    "SIMULATION": "🔬",
}
_VERDICT_COLORS = {
    "confirmed": "#2ECC71",
    "partially_confirmed": "#F39C12",
    "rejected": "#E74C3C",
    "inconclusive": "#95A5A6",
}

# Sort: confirmed first, then partially_confirmed
sorted_hyps = sorted(
    [h for h in hypotheses_r if verdicts.get(h.id)],
    key=lambda h: (
        0 if verdicts[h.id].status == "confirmed" else
        1 if verdicts[h.id].status == "partially_confirmed" else 2
    )
)

for hyp in sorted_hyps:
    verdict = verdicts.get(hyp.id)
    if not verdict or verdict.status in ("rejected", "inconclusive"):
        continue

    v_color = _VERDICT_COLORS.get(verdict.status, "#95A5A6")
    v_label = verdict.status.replace("_", " ").title()

    with st.container(border=True):
        # Hypothesis header
        col_title, col_badge = st.columns([5, 1])
        with col_title:
            st.markdown(
                f"<span style='font-weight:700; font-size:1rem;'>{hyp.title}</span>",
                unsafe_allow_html=True,
            )
        with col_badge:
            st.markdown(
                f'<span style="background:{v_color}; color:#fff; border-radius:4px; '
                f'padding:2px 8px; font-size:0.8rem;">{v_label} · {verdict.confidence:.0%}</span>',
                unsafe_allow_html=True,
            )

        # Probe evidence rows
        hyp_probes = [p for p in probes_r if p.hypothesis_id == hyp.id and p.result]
        if hyp_probes:
            for probe in sorted(hyp_probes, key=lambda p: p.order):
                r = probe.result
                ptype = probe.probe_type.value.upper() if probe.probe_type else "PROBE"
                icon = _PROBE_TYPE_ICON.get(ptype, "🔍")
                conf_bar = "█" * int(r.confidence * 10) + "░" * (10 - int(r.confidence * 10))
                st.caption(
                    f"{icon} **{ptype.title()}** — {r.confidence:.0%} confidence  "
                    f"`{conf_bar}`"
                )
                if r.evidence_summary:
                    st.caption(f"↳ {r.evidence_summary[:180]}")
        else:
            st.caption("↳ " + (verdict.evidence_summary[:200] if verdict.evidence_summary else "Evidence from synthesis."))
```

---

### Task 2: Quote Bank

**Location**: After the Evidence Chain section.

```python
st.divider()
st.subheader("Representative Voices")
st.caption(
    "Persona responses from the investigation, organized by theme. "
    "These are simulated conversations grounded in each persona's full profile and behavior trajectory."
)
```

Collect all interview probe results:

```python
from src.probing.models import ProbeType

interview_probes = [
    p for p in probes_r
    if p.probe_type == ProbeType.INTERVIEW and p.result is not None
]

all_clusters = [c for p in interview_probes for c in p.result.response_clusters]
all_responses = [r for p in interview_probes for r in p.result.interview_responses]
```

**If clusters exist**, render by theme:

```python
if all_clusters:
    # Sort by persona count (most common themes first)
    sorted_clusters = sorted(all_clusters, key=lambda c: c.persona_count, reverse=True)

    for cluster in sorted_clusters[:5]:  # Cap at 5 themes
        theme_label = cluster.theme.replace("_", " ").title()
        pct = f"{cluster.percentage:.0%}" if cluster.percentage <= 1.0 else f"{cluster.percentage:.0f}%"

        with st.expander(f"**{theme_label}** — {cluster.persona_count} personas ({pct})", expanded=False):
            st.caption(cluster.description)
            if cluster.representative_quotes:
                for quote in cluster.representative_quotes[:3]:
                    st.markdown(f"> *{quote[:280]}*")
                    st.caption("")
```

**If no clusters but individual responses exist**, show up to 6 individual quotes:

```python
elif all_responses:
    st.caption("Individual persona responses from the investigation:")
    for resp in all_responses[:6]:
        outcome_icon = "✅" if resp.outcome == "adopt" else "❌"
        with st.container(border=True):
            st.caption(f"**{resp.persona_name}** {outcome_icon}")
            st.markdown(f"> *{resp.content[:300]}*")
```

**If neither**:
```python
else:
    st.info(
        "No interview probes were run during this investigation. "
        "Interview evidence appears when the probing tree includes interview-type probes.",
        icon="ℹ️",
    )
```

---

### Task 3: "Download Finding Brief" Button

**Location**: After the Quote Bank, before the phase-complete banner.

```python
st.divider()
st.subheader("Export")

# Assemble plain-text brief
_core = getattr(synthesis, "core_finding", None) or synthesis.synthesis_narrative or ""
_evidence_lines = []
for hyp in sorted_hyps:
    verdict = verdicts.get(hyp.id)
    if verdict and verdict.status in ("confirmed", "partially_confirmed"):
        _evidence_lines.append(f"\n{hyp.title} ({verdict.status.replace('_', ' ').title()}, {verdict.confidence:.0%} confidence)")
        if verdict.evidence_summary:
            _evidence_lines.append(f"  {verdict.evidence_summary[:300]}")

_top_quotes = []
for cluster in sorted(all_clusters, key=lambda c: c.persona_count, reverse=True)[:3]:
    if cluster.representative_quotes:
        _top_quotes.append(f"\"{cluster.representative_quotes[0][:200]}\"")

brief_text = f"""CORE FINDING
{'-' * 60}
{_core}

EVIDENCE CHAIN
{'-' * 60}
{''.join(_evidence_lines) or 'See full investigation results.'}

REPRESENTATIVE VOICES
{'-' * 60}
{chr(10).join(_top_quotes) or 'No interview evidence available.'}

Generated by LittleJoys Persona Simulation Engine
Simulatte Research Pvt Ltd — {scenario_id}
"""

st.download_button(
    label="⬇️ Download Finding Brief (.txt)",
    data=brief_text,
    file_name=f"{scenario_id}_core_finding.txt",
    mime="text/plain",
)
```

Note: `scenario_id` is already available in the page from `core_finding.get("scenario_id")` or `st.session_state.get("baseline_scenario_id")`.

---

### Acceptance Criteria

- [ ] Evidence chain renders for all confirmed/partially-confirmed hypotheses
- [ ] Rejected and inconclusive hypotheses are excluded from the evidence chain
- [ ] Probe rows show the correct icon (📊 attribute, 🎤 interview, 🔬 simulation)
- [ ] Quote bank shows themes when clusters exist, individual quotes when only responses exist, info message when neither
- [ ] Download button produces a readable plain-text file with core finding + evidence + quotes
- [ ] Page doesn't crash when `probe_results` has missing or None fields — all `.get()` or `or ""` fallbacks in place
- [ ] Existing Core Finding callout, synthesis narrative expander, and phase-complete banner remain intact and unchanged

---

### Files to Modify

| File | Change |
|------|--------|
| `app/pages/4_finding.py` | Add Evidence Chain section, Quote Bank section, Download Finding Brief button |

### Files NOT to Modify

Any `src/` files. Do not modify `probing/models.py` or `probing/engine.py`.

---

### Escalation Rule

If `ProbeResult.response_clusters` or `.interview_responses` are empty even for INTERVIEW probes, check `src/probing/engine.py` to verify that interview probes populate these fields. If the fields have different names, grep `src/probing/models.py` for the correct attribute names before coding.
