# Sprint 12 Brief — Cursor (Claude)
## Smart Sampling Algorithm + Language Shift

### Context
We are rebuilding LittleJoys as a hybrid research engine (Option C). The funnel runs on all 200 personas (fast, quantitative). LLM interviews run on a **smart sample** of 15-20 personas selected for maximum insight value. This sprint builds the sampling algorithm and shifts all user-facing language from "purchase/adoption" to "research/response" framing.

### Task 1: Smart Sampling Algorithm
**New file:** `src/probing/smart_sample.py`

Build a deterministic sampling algorithm that selects 15-20 personas from a population after the funnel has run, targeting the most informative cross-section.

#### Models

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

SelectionReason = Literal[
    "fragile_yes",        # adopted but score barely above threshold
    "persuadable_no",     # rejected but score barely below threshold
    "underrepresented",   # strong adopter from minority segment
    "high_need_rejecter", # rejected despite high need_score — why?
    "control",            # random baseline
]

class SampledPersona(BaseModel):
    """A persona selected for deep LLM interview with reason."""
    persona_id: str
    selection_reason: SelectionReason
    reason_detail: str  # e.g. "purchase_score 0.48 vs threshold 0.50"
    funnel_scores: dict[str, float]  # need/awareness/consideration/purchase scores

class SmartSample(BaseModel):
    """Result of smart sampling from a funnel run."""
    selections: list[SampledPersona]
    population_size: int
    total_adopters: int
    total_rejecters: int
    sample_seed: int

    @property
    def persona_ids(self) -> list[str]:
        return [s.persona_id for s in self.selections]

    def personas_by_reason(self, reason: SelectionReason) -> list[SampledPersona]:
        return [s for s in self.selections if s.selection_reason == reason]
```

#### Selection Strategy

```python
def select_smart_sample(
    personas: list[Persona],
    decisions: dict[str, dict],  # persona_id -> DecisionResult.to_dict()
    thresholds: dict[str, float] | None = None,
    target_size: int = 18,
    seed: int = 42,
) -> SmartSample:
```

**Bucket allocation** (target_size=18):
1. **Fragile Yes (4):** Adopted, but `purchase_score` is within 0.10 of the purchase threshold (default 0.50). These are personas who could easily flip — most valuable for understanding what tips the balance.
2. **Persuadable No (4):** Rejected at `consideration` or `purchase` stage (late-stage), with score within 0.10 of threshold. Close to converting — interview reveals what's missing.
3. **Underrepresented Adopters (3):** Adopted, but belong to a segment (city_tier × SEC combination) that has < 20% of the overall population. Unusual adopters reveal untapped opportunities.
4. **High-Need Rejecters (4):** Rejected, but `need_score` >= 0.65. They have the problem the product solves, yet still said no — understanding why is high-value.
5. **Control (3):** Random selection from remaining personas not already sampled. Use deterministic hash-based selection (seed-based, same approach as `src/probing/sampling.py`).

**Rules:**
- No persona appears in multiple buckets
- If a bucket can't fill its allocation (e.g. only 2 fragile-yes exist), redistribute to control
- Must be fully deterministic: same inputs + seed → same output
- Sort candidates within each bucket by score proximity to threshold (most borderline first)

**Reference files:**
- `src/probing/sampling.py` — existing stratified sampling (reuse hash-sort pattern)
- `src/decision/funnel.py:67` — default thresholds: `{"need_recognition": 0.40, "awareness": 0.35, "consideration": 0.45, "purchase": 0.50}`
- `src/decision/funnel.py:76-100` — DecisionResult structure with scores

### Task 2: Language Shift
**Edit existing files** — change user-facing strings only. Do NOT rename Python variables, function names, or internal code identifiers.

#### File: `src/utils/display.py`

Update these maps:

```python
# Line ~174-176: OUTCOME_DISPLAY
OUTCOME_DISPLAY: dict[str, str] = {
    "adopt": "Would try",
    "reject": "Wouldn't try",
}

# Line ~180-183: SCATTER_PURCHASE_OUTCOME_LABELS
SCATTER_PURCHASE_OUTCOME_LABELS: dict[str, str] = {
    "adopt": "Would try",
    "reject": "Wouldn't try",
}
```

Update the FIELD_DISPLAY_NAMES map (line ~100-106):
```python
"outcome": "Response",
"need_score": "Need Score",
"awareness_score": "Awareness Score",
"consideration_score": "Consideration Score",
"purchase_score": "Openness Score",
"rejection_stage": "Drop-off Stage",
"rejection_reason": "Drop-off Reason",
```

#### File: `app/pages/1_population.py`

Search for any remaining user-facing strings containing "adopt", "purchase intent", "funnel", "buy" and update:
- "Would buy" → "Would try"
- "Wouldn't buy" → "Wouldn't try"
- "Purchase intent" → "Openness to trial"
- "Adoption Rate" → "Positive Response Rate"
- "purchase behaviour" → "response patterns"

#### File: `app/pages/3_results.py`

Same language shift for all user-facing strings. Key targets:
- "Adoption" → "Positive response"
- "Funnel" → "Decision pathway"
- Any `st.metric` labels, `st.markdown` headers, chart titles

#### File: `app/pages/2_scenario.py`

- "Run Simulation" button label → "Run Research"
- "Simulation complete" toast → "Research complete"
- Any adoption/purchase language in help text

#### File: `app/streamlit_app.py`

- "Scenarios Evaluated" metric is fine
- "Baseline configurations evaluated" toast → "Baseline scenarios evaluated"

### Deliverables
1. `src/probing/smart_sample.py` — SmartSample, SampledPersona models + `select_smart_sample()` function
2. Language shift across `display.py`, `1_population.py`, `3_results.py`, `2_scenario.py`, `streamlit_app.py`
3. All existing tests must still pass (language changes are UI-only, shouldn't break tests)

### Do NOT
- Rename Python variables, function names, class names, or file names
- Change internal code logic — only user-facing label strings
- Modify `src/decision/funnel.py` or `src/decision/calibration.py`
- Create new Streamlit pages
