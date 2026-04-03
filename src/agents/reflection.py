from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.taxonomy.schema import MemoryEntry, Persona


REFLECTION_THRESHOLD = 5.0
REFLECTION_WINDOW = 20
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


@dataclass
class ReflectionInsight:
    """A higher-order insight generated from a set of episodic memories."""

    insight: str
    confidence: float
    source_indices: list[int] = field(default_factory=list)
    emotional_valence: float = 0.0

    def to_memory_entry(self, timestamp: str) -> "MemoryEntry":
        """Convert this insight to a MemoryEntry for episodic storage."""
        from src.taxonomy.schema import MemoryEntry

        sources = ", ".join(f"[mem#{i}]" for i in self.source_indices)
        source_suffix = f" (sources: {sources})" if sources else ""
        return MemoryEntry(
            timestamp=timestamp,
            event_type="reflection",
            content=f"[REFLECTION] {self.insight}{source_suffix}",
            emotional_valence=max(-1.0, min(1.0, float(self.emotional_valence))),
            salience=0.85,
        )


class ReflectionEngine:
    """
    Generates higher-order insights from a persona's episodic memory.

    Trigger model:
      - Reflection is due when cumulative salience reaches threshold.
      - Reflection input is the most recent `window` memories.
      - LLM output is parsed into 1..max_insights ReflectionInsight objects.
      - Parsed insights are appended back as reflection MemoryEntry records.
    """

    def __init__(
        self,
        threshold: float = REFLECTION_THRESHOLD,
        window: int = REFLECTION_WINDOW,
        max_insights: int = MAX_INSIGHTS,
    ) -> None:
        self.threshold = threshold
        self.window = window
        self.max_insights = max_insights

    def should_reflect(self, cumulative_salience: float) -> bool:
        """Return True when cumulative salience crosses the trigger threshold."""
        return cumulative_salience >= self.threshold

    def reflect(
        self,
        persona: "Persona",
        llm_call_fn: Callable[[str], str],
        n_insights: int = 2,
    ) -> list[ReflectionInsight]:
        """Generate and persist reflection insights from recent episodic memory."""
        if not persona.episodic_memory:
            return []

        requested = max(1, min(int(n_insights), self.max_insights))
        recent = persona.episodic_memory[-self.window :]
        memory_text = self._format_memories(recent)

        decision_style = "unknown"
        trust_anchor = "unknown"
        if persona.parent_traits is not None:
            decision_style = str(persona.parent_traits.decision_style)
            trust_anchor = str(persona.parent_traits.trust_anchor)

        prompt = REFLECTION_PROMPT.format(
            persona_id=persona.id,
            age=persona.demographics.parent_age,
            decision_style=decision_style,
            trust_anchor=trust_anchor,
            memory_text=memory_text,
            n_insights=requested,
        )
        raw = llm_call_fn(prompt)
        insights = self._parse_insights(raw)
        insights = insights[:requested]

        now = datetime.now(timezone.utc).isoformat()
        for insight in insights:
            persona.episodic_memory.append(insight.to_memory_entry(now))
        return insights

    def _format_memories(self, memories: list["MemoryEntry"]) -> str:
        lines: list[str] = []
        for i, mem in enumerate(reversed(memories)):
            valence = f"{mem.emotional_valence:+.1f}"
            lines.append(
                f"[{i}] [{mem.event_type}|val:{valence}|sal:{mem.salience:.1f}] {mem.content[:120]}"
            )
        return "\n".join(lines)

    def _parse_insights(self, raw: str) -> list[ReflectionInsight]:
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            parsed = json.loads(raw[start:end])
        except (json.JSONDecodeError, ValueError):
            return []

        insights: list[ReflectionInsight] = []
        for item in parsed.get("insights", []):
            try:
                source_indices = item.get("source_indices", [])
                if not isinstance(source_indices, list):
                    source_indices = []
                cast_source_indices = [int(idx) for idx in source_indices if isinstance(idx, int)]
                insights.append(
                    ReflectionInsight(
                        insight=str(item["insight"]),
                        confidence=max(0.0, min(1.0, float(item.get("confidence", 0.7)))),
                        source_indices=cast_source_indices,
                        emotional_valence=max(-1.0, min(1.0, float(item.get("emotional_valence", 0.0)))),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return insights
