# Sprint 25 — Codex (S5-02)
**Engineer:** Codex (GPT-5.3)
**Theme:** Contradiction Detection Across Hypotheses

---

## Context

Phase 2 currently presents each hypothesis independently. When two hypotheses produce conflicting evidence (e.g. H1 says "price is the barrier" but H3 simulation shows price changes have no lift), the user has no signal to reconcile them. This sprint adds a contradiction detection layer that surfaces cross-hypothesis conflicts as warnings in Phase 2 and Phase 3.

---

## Task A — Contradiction Detection Logic

**New file:** `src/analysis/contradiction_detector.py`

Write a function:

```python
def detect_contradictions(
    hypotheses: list[Hypothesis],
    verdicts: dict[str, Verdict],
    probes: list[Probe],
) -> list[ContradictionWarning]:
```

A `ContradictionWarning` is a simple dataclass:
```python
@dataclass
class ContradictionWarning:
    hypothesis_a_id: str
    hypothesis_b_id: str
    contradiction_type: str  # "confidence_conflict" | "mechanism_overlap" | "simulation_divergence"
    description: str
    severity: str  # "high" | "medium" | "low"
```

**Detection rules:**

1. **Confidence conflict**: One hypothesis is `confirmed` (≥70%) and another covers the same signal domain at `rejected` (<30%). Flag as `high` severity.

2. **Mechanism overlap**: Two hypotheses have the same dominant interview theme (e.g. both dominated by "Forgetfulness") but different verdicts. Flag as `medium` severity with description "Both H{a} and H{b} share the '{theme}' theme but reached different conclusions — investigate shared drivers."

3. **Simulation divergence**: One hypothesis's simulation probe shows positive lift (>+2pp) but the overall hypothesis is `inconclusive` or `rejected`. Flag as `low` severity with description "Simulation suggests an effect for H{x} that the interview evidence does not support — consider a deeper counterfactual test."

---

## Task B — Surface in Phase 2 UI

**File:** `app/pages/3_decompose.py`

After the "Investigation Results" section and before "Dominant Narrative", add a new section:

```
## ⚡ Cross-Hypothesis Conflicts
```

Only show if `detect_contradictions()` returns at least one warning.

For each warning, render a styled callout:
- 🔴 High severity: red left border
- 🟡 Medium severity: yellow left border
- ⚪ Low severity: grey left border

Each callout shows:
- Which two hypotheses conflict (H1 vs H3 etc.)
- `contradiction_type` as a badge
- `description` text

If no contradictions detected: show `st.success("No cross-hypothesis conflicts detected.")` in a small caption.

---

## Task C — Surface in Phase 3

**File:** `app/pages/4_finding.py`

In the "Evidence Chain" section, after rendering individual hypothesis verdicts, add a compact `st.warning()` for any `high` severity contradictions:

```
⚡ Conflict detected: H1 and H3 share evidence but diverge in confidence.
   Review both branches before finalising the core finding.
```

Only show for `high` severity. No UI changes for medium/low in Phase 3.

---

## Acceptance Criteria

- [ ] `detect_contradictions()` correctly identifies all 3 rule types
- [ ] Phase 2 shows contradiction warnings section (or success if none)
- [ ] Phase 3 shows high-severity warnings inline in evidence chain
- [ ] Function is unit-tested in `tests/unit/test_contradiction_detector.py` (at least 3 tests)
- [ ] All existing tests pass
