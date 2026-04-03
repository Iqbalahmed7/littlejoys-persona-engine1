# Sprint 29 — Brief: CURSOR

**Role:** Architecture lead / complex implementation
**Model:** Auto
**Assignment:** (1) `ReflectionEngine` class — the Generative Agents reflection mechanism
              (2) Tier 1 generator post-sample constraint enforcement
**Est. duration:** 5-6 hours

---

## Files to Create / Modify

| Action | File |
|---|---|
| CREATE | `src/agents/reflection.py` |
| MODIFY | `src/generation/tier1_generator.py` (add post-sample enforcement only) |

## Do NOT Touch
- `src/agents/agent.py` — Codex adds `reflect()` using your `ReflectionEngine`
- `src/taxonomy/schema.py` — read-only
- Any test file

---

## Verified Field Names (use exactly these)

```python
persona.id                          # unique ID string
persona.display_name                # human name, may be None — use persona.id as fallback
persona.demographics.parent_age
persona.demographics.family_structure   # "nuclear" | "joint" | "single_parent"
persona.psychology.health_anxiety
persona.parent_traits               # may be None — always null-check
persona.parent_traits.decision_style    # only access after null-check
persona.episodic_memory             # list[MemoryEntry]
```

---

## Part 1: `src/agents/reflection.py`

### Design (from Generative Agents, adapted)

```
Trigger:    cumulative_salience_since_last_reflection > REFLECTION_THRESHOLD (5.0)
Input:      Top-20 most recent MemoryEntry objects (by position, not score)
LLM task:   "Given these observations about {persona}, what are the 2-3 most
             important insights you can infer?"
Output:     2-3 ReflectionInsight objects, each stored back as a MemoryEntry
             with event_type="reflection", salience=0.85, source_ids=[...]
```

### `ReflectionInsight` dataclass

```python
from __future__ import annotations
from dataclasses import dataclass, field
from src.taxonomy.schema import MemoryEntry

@dataclass
class ReflectionInsight:
    """A higher-order insight generated from a set of episodic memories."""
    insight: str                    # the insight text
    confidence: float               # 0.0-1.0 — how strongly the LLM believes this
    source_indices: list[int]       # indices into episodic_memory that generated this
    emotional_valence: float = 0.0  # -1.0 to 1.0

    def to_memory_entry(self, timestamp: str) -> MemoryEntry:
        """Convert to a MemoryEntry for storage in persona.episodic_memory."""
        from src.taxonomy.schema import MemoryEntry
        sources = ", ".join(f"[mem#{i}]" for i in self.source_indices)
        return MemoryEntry(
            timestamp=timestamp,
            event_type="reflection",
            content=f"[REFLECTION] {self.insight} (sources: {sources})",
            emotional_valence=self.emotional_valence,
            salience=0.85,
        )
```

### `ReflectionEngine` class

```python
REFLECTION_THRESHOLD = 5.0          # cumulative salience units
REFLECTION_WINDOW = 20              # look at this many recent memories
MAX_INSIGHTS = 3

REFLECTION_PROMPT = """\
You are helping build a psychological model of a specific Indian parent.
Below are their recent observations and experiences.

PERSONA CONTEXT:
- ID: {persona_id}
- Age: {age}
- Decision style: {decision_style}
- Trust anchor: {trust_anchor}

RECENT MEMORIES (most recent first):
{memory_text}

TASK:
Based ONLY on the memories above, generate {n_insights} higher-order insights
about this persona's relationship with child nutrition products.

Focus on:
- Emerging beliefs or attitudes (not just restating what happened)
- Patterns across multiple memories
- What this reveals about their decision-making triggers

Return valid JSON only:
{{
  "insights": [
    {{
      "insight": "...",
      "confidence": <float 0.0-1.0>,
      "source_indices": [<int>, ...],
      "emotional_valence": <float -1.0 to 1.0>
    }}
  ]
}}
"""

class ReflectionEngine:
    """
    Generates higher-order insights from a persona's episodic memory.

    Follows the Generative Agents reflection mechanism:
      1. Triggered when cumulative salience since last reflection > REFLECTION_THRESHOLD
      2. Looks at the N most recent memories
      3. Generates 2-3 insights via LLM
      4. Stores insights back as high-salience "reflection" MemoryEntry objects

    Usage:
        engine = ReflectionEngine()
        # Check if reflection is due:
        if engine.should_reflect(persona, cumulative_salience):
            insights = engine.reflect(persona, llm_call_fn)
        # Or call directly:
        insights = engine.reflect(persona, llm_call_fn)
    """

    def __init__(
        self,
        threshold: float = REFLECTION_THRESHOLD,
        window: int = REFLECTION_WINDOW,
        max_insights: int = MAX_INSIGHTS,
    ):
        self.threshold = threshold
        self.window = window
        self.max_insights = max_insights

    def should_reflect(self, cumulative_salience: float) -> bool:
        """True if enough salience has accumulated to trigger reflection."""
        return cumulative_salience >= self.threshold

    def reflect(
        self,
        persona: "Persona",
        llm_call_fn: Callable[[str], str],
        n_insights: int = 2,
    ) -> list[ReflectionInsight]:
        """
        Generate insights from persona's recent episodic memory.

        Args:
            persona:      The persona to reflect on.
            llm_call_fn:  Callable that takes a prompt string and returns LLM response.
                          Signature: (prompt: str) -> str
                          Pass `agent._llm_call` from CognitiveAgent.
            n_insights:   Number of insights to generate (1-3).

        Returns:
            List of ReflectionInsight objects.

        Side effects:
            Appends each insight as a MemoryEntry to persona.episodic_memory.
        """
        from datetime import datetime, timezone

        if not persona.episodic_memory:
            return []

        # Take the most recent `window` memories
        recent = persona.episodic_memory[-self.window:]

        # Format memories for the prompt
        memory_text = self._format_memories(recent)

        # Build persona context — null-safe
        age = persona.demographics.parent_age
        decision_style = (
            persona.parent_traits.decision_style
            if persona.parent_traits else "unknown"
        )
        trust_anchor = (
            persona.parent_traits.trust_anchor
            if persona.parent_traits else "unknown"
        )

        prompt = REFLECTION_PROMPT.format(
            persona_id=persona.id,
            age=age,
            decision_style=decision_style,
            trust_anchor=trust_anchor,
            memory_text=memory_text,
            n_insights=min(n_insights, self.max_insights),
        )

        raw = llm_call_fn(prompt)

        insights = self._parse_insights(raw)

        # Store each insight back into episodic memory
        now = datetime.now(timezone.utc).isoformat()
        for insight in insights:
            persona.episodic_memory.append(insight.to_memory_entry(now))

        return insights

    def _format_memories(self, memories: list["MemoryEntry"]) -> str:
        lines = []
        for i, mem in enumerate(reversed(memories)):  # most recent first
            valence = f"{mem.emotional_valence:+.1f}"
            lines.append(
                f"[{i}] [{mem.event_type}|val:{valence}|sal:{mem.salience:.1f}] "
                f"{mem.content[:120]}"
            )
        return "\n".join(lines)

    def _parse_insights(self, raw: str) -> list[ReflectionInsight]:
        import json
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            parsed = json.loads(raw[start:end])
        except (json.JSONDecodeError, ValueError):
            return []

        results = []
        for item in parsed.get("insights", []):
            try:
                results.append(ReflectionInsight(
                    insight=item["insight"],
                    confidence=float(item.get("confidence", 0.7)),
                    source_indices=item.get("source_indices", []),
                    emotional_valence=float(item.get("emotional_valence", 0.0)),
                ))
            except (KeyError, TypeError):
                continue
        return results
```

### Required imports at top of file

```python
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona, MemoryEntry
```

---

## Part 2: `src/generation/tier1_generator.py` — Post-Sample Constraint Enforcement

The existing `Tier1Generator.generate()` is a stub (`NotImplementedError`).
Do NOT implement the full copula pipeline — that is a separate sprint.

Add ONLY a `enforce_hard_constraints()` static method that can be called
on any list of persona dicts (pre-Pydantic) to fix the 4 anti-correlation violations
found in Sprint 28.

```python
class Tier1Generator:
    """Generates statistically grounded Tier 1 personas."""

    def generate(self, n: int, seed: int) -> list["Persona"]:
        raise NotImplementedError("Full implementation in PRD-001 / PRD-003")

    @staticmethod
    def enforce_hard_constraints(persona_dict: dict) -> dict:
        """
        Post-sample constraint enforcement for anti-correlation violations.

        Applies 4 hard caps identified in Sprint 28 constraint audit.
        Mutates persona_dict in-place and returns it.

        Rules enforced:
            R014: risk_tolerance > 0.75 → cap loss_aversion at 0.65
            R014: loss_aversion > 0.75  → cap risk_tolerance at 0.65
            R017: analysis_paralysis > 0.8 → cap decision_speed at 0.60
            R017: decision_speed > 0.8    → cap analysis_paralysis at 0.60
            R027: supplement_necessity > 0.8 → cap food_first_belief at 0.70
            R027: food_first_belief > 0.85   → cap supplement_necessity at 0.70
            R020: impulse_purchase > 0.85 → cap analysis_paralysis at 0.60
            R020: analysis_paralysis > 0.85 → cap impulse_purchase at 0.60
            R030: family_structure == "single_parent" →
                  force decision_rights.child_nutrition to "mother_final"
        """
        psych = persona_dict.get("psychology", {})
        values = persona_dict.get("values", {})
        daily = persona_dict.get("daily_routine", {})
        demo = persona_dict.get("demographics", {})

        # R014: risk_tolerance ↔ loss_aversion
        risk = psych.get("risk_tolerance", 0.5)
        loss = psych.get("loss_aversion", 0.5)
        if risk > 0.75 and loss > 0.65:
            psych["loss_aversion"] = 0.65
        if loss > 0.75 and risk > 0.65:
            psych["risk_tolerance"] = 0.65

        # R017: analysis_paralysis ↔ decision_speed
        paralysis = psych.get("analysis_paralysis_tendency", 0.5)
        speed = psych.get("decision_speed", 0.5)
        if paralysis > 0.8 and speed > 0.60:
            psych["decision_speed"] = 0.60
        if speed > 0.8 and paralysis > 0.60:
            psych["analysis_paralysis_tendency"] = 0.60

        # R027: supplement_necessity ↔ food_first_belief
        necessity = values.get("supplement_necessity_belief", 0.5)
        food_first = values.get("food_first_belief", 0.5)
        if necessity > 0.8 and food_first > 0.70:
            values["food_first_belief"] = 0.70
        if food_first > 0.85 and necessity > 0.70:
            values["supplement_necessity_belief"] = 0.70

        # R020: impulse_purchase ↔ analysis_paralysis
        impulse = daily.get("impulse_purchase_tendency", 0.5)
        if impulse > 0.85 and paralysis > 0.60:
            psych["analysis_paralysis_tendency"] = 0.60
        if paralysis > 0.85 and impulse > 0.60:
            daily["impulse_purchase_tendency"] = 0.60

        # R030: single_parent → force mother_final decision rights
        if demo.get("family_structure") == "single_parent":
            rights = persona_dict.setdefault("decision_rights", {})
            if rights.get("child_nutrition") in ("father_final", "joint"):
                rights["child_nutrition"] = "mother_final"
            if rights.get("supplements") == "joint":
                rights["supplements"] = "mother_final"

        # Write back
        persona_dict["psychology"] = psych
        persona_dict["values"] = values
        persona_dict["daily_routine"] = daily
        return persona_dict
```

---

## Acceptance Criteria

**`reflection.py`:**
- [ ] `ReflectionEngine()` instantiates without error
- [ ] `should_reflect(4.9)` returns `False`, `should_reflect(5.0)` returns `True`
- [ ] `reflect()` appends exactly `n_insights` new `MemoryEntry` objects with `event_type="reflection"` to `persona.episodic_memory`
- [ ] Each stored reflection entry has `salience=0.85`
- [ ] `reflect()` on empty `episodic_memory` returns `[]` without error
- [ ] `_parse_insights()` returns `[]` on malformed JSON without raising
- [ ] `ReflectionInsight.to_memory_entry()` produces valid `MemoryEntry`
- [ ] `ReflectionEngine` exported from `src/agents/__init__.py` (OpenCode adds this)

**`tier1_generator.py`:**
- [ ] `enforce_hard_constraints()` is a `@staticmethod`
- [ ] After calling it, no persona dict violates R014, R017, R027, R020, R030
- [ ] Does NOT raise if a key is missing (uses `.get()` with defaults)
- [ ] Original `generate()` stub preserved — do not remove it
