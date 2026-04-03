# Sprint 28 — Brief: CODEX

**Role:** Backend algorithms
**Model:** GPT-5.3
**Assignment:** Implement `perceive()` + `update_memory()` on `CognitiveAgent`. Build `PerceptionResult`.
**Est. duration:** 4-5 hours

---

## Files to Create / Modify

| Action | File |
|---|---|
| MODIFY (`perceive` + `update_memory` stubs only) | `src/agents/agent.py` |
| CREATE | `src/agents/perception_result.py` |

## Do NOT Touch

- `src/agents/memory.py` — owned by Cursor
- `src/agents/perception.py` — do not refactor this file
- `src/taxonomy/schema.py` — read-only
- The `decide()` method in `agent.py` — leave it as `NotImplementedError` (Goose owns it)

---

## Coordination Note

`MemoryManager` is being written in parallel by Cursor.
Your `perceive()` calls `self.memory.add_episodic()` and `self.memory.update_brand_memory()`.
Do NOT implement these methods yourself — just call them.
In `__init__`, write: `self.memory = MemoryManager(persona)` — it will resolve when Cursor lands.

---

## File 1: `src/agents/perception_result.py` (NEW)

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from src.taxonomy.schema import UnitInterval, SignedUnitInterval

class PerceptionResult(BaseModel):
    """Structured output of CognitiveAgent.perceive()."""

    model_config = {"extra": "forbid"}

    # Raw importance score 1-10 from LLM, normalised to 0.0-1.0
    importance: UnitInterval = 0.5

    # Emotional valence of this stimulus for this persona, -1 to 1
    emotional_valence: SignedUnitInterval = 0.0

    # Whether this stimulus is salient enough to trigger a reflection check
    reflection_trigger_candidate: bool = False

    # Brief explanation of how this persona interpreted the stimulus
    interpretation: str = ""

    # Which psychological attributes most shaped the perception
    dominant_attributes: list[str] = Field(default_factory=list)

    # Was memory written?
    memory_written: bool = False
```

---

## File 2: `src/agents/agent.py` — Modify Stubs Only

Replace `perceive()` and `update_memory()` stubs. Leave `decide()` as `NotImplementedError`.

### Prompt constant (add at module level)

```python
IMPORTANCE_SCORING_PROMPT = """\
You are scoring how important a stimulus is to a specific person.

PERSONA PROFILE (condensed):
- Name: {name}, Age: {age}
- Health anxiety: {health_anxiety:.2f}/1.0
- Information need: {information_need:.2f}/1.0
- Social proof bias: {social_proof_bias:.2f}/1.0
- Best-for-my-child intensity: {best_for_my_child:.2f}/1.0
- Supplement necessity belief: {supplement_necessity:.2f}/1.0
- Dominant decision style: {decision_style}
- Trust anchor: {trust_anchor}

STIMULUS:
{stimulus_description}

TASK:
Score this stimulus on two dimensions:

1. IMPORTANCE (1-10): How much would this persona pay attention to and remember this?
   1-3 = barely notices (irrelevant to their life)
   4-6 = mildly interesting but forgettable
   7-8 = noticeably relevant, will remember
   9-10 = highly salient, may change behaviour

2. EMOTIONAL_VALENCE (-1.0 to 1.0): What emotional response does this trigger?
   -1.0 = strong negative (fear, anger, disgust)
   0.0  = neutral
   +1.0 = strong positive (joy, relief, desire)

3. DOMINANT_ATTRIBUTES: List 2-3 persona attributes most activated by this stimulus.
   Choose from: health_anxiety, information_need, social_proof_bias, authority_bias,
   guilt_sensitivity, best_for_my_child_intensity, supplement_necessity_belief,
   loss_aversion, status_quo_bias, risk_tolerance

4. INTERPRETATION: One sentence describing how this persona interprets the stimulus.

Return ONLY valid JSON:
{{
  "importance": <int 1-10>,
  "emotional_valence": <float -1.0 to 1.0>,
  "dominant_attributes": ["attr1", "attr2"],
  "interpretation": "..."
}}
"""
```

### Updated `__init__`

```python
def __init__(self, persona: Persona) -> None:
    self.persona = persona
    self.memory = MemoryManager(persona)  # Cursor implements MemoryManager
    self._client = None  # lazy init — no API call at construction time
```

### `perceive()` implementation

```python
def perceive(self, stimulus: dict) -> PerceptionResult:
    """
    Process an external stimulus through this persona's psychological lens.

    Args:
        stimulus: dict with keys:
            type        (str)  — "ad" | "product" | "wom" | "price_change" | "social_event"
            content     (str)  — human-readable description of the stimulus
            source      (str)  — who/what generated this (e.g. "instagram_ad", "friend_priya")
            brand       (str, optional) — brand name if applicable
            simulation_tick (int, optional) — current sim time

    Returns:
        PerceptionResult with importance, emotional_valence, interpretation, etc.

    Side effects:
        - Writes a MemoryEntry to persona.episodic_memory via memory.add_episodic()
        - Updates brand_memories if stimulus["brand"] is provided
    """
    stimulus_description = (
        f"Type: {stimulus.get('type', 'unknown')}\n"
        f"Source: {stimulus.get('source', 'unknown')}\n"
        f"Content: {stimulus.get('content', '')}"
    )

    psych = self.persona.psychology
    demo = self.persona.demographics
    derived = self.persona.parent_traits

    prompt = IMPORTANCE_SCORING_PROMPT.format(
        name=demo.parent_name,
        age=demo.parent_age,
        health_anxiety=psych.health_anxiety,
        information_need=psych.information_need,
        social_proof_bias=psych.social_proof_bias,
        best_for_my_child=self.persona.values.best_for_my_child_intensity,
        supplement_necessity=self.persona.values.supplement_necessity_belief,
        decision_style=derived.decision_style,
        trust_anchor=derived.trust_anchor,
        stimulus_description=stimulus_description,
    )

    result_raw = self._llm_call(prompt)

    try:
        parsed = json.loads(result_raw)
    except json.JSONDecodeError:
        start = result_raw.find("{")
        end = result_raw.rfind("}") + 1
        parsed = json.loads(result_raw[start:end]) if start >= 0 else {}

    importance_raw = int(parsed.get("importance", 5))
    importance_norm = round((importance_raw - 1) / 9.0, 4)  # 1-10 → 0.0-1.0
    emotional_valence = float(parsed.get("emotional_valence", 0.0))
    dominant_attrs = parsed.get("dominant_attributes", [])
    interpretation = parsed.get("interpretation", "")

    self.memory.add_episodic({
        "event_type": "stimulus",
        "content": f"[{stimulus.get('type', 'stimulus')} from {stimulus.get('source', '?')}] {stimulus.get('content', '')}",
        "emotional_valence": emotional_valence,
        "salience": importance_norm,
        "simulation_tick": stimulus.get("simulation_tick", 0),
    })

    brand = stimulus.get("brand")
    if brand:
        self.memory.update_brand_memory(brand, {
            "channel": stimulus.get("type", "ad"),
            "sentiment": emotional_valence,
            "content": stimulus.get("content", "")[:200],
            "trust_delta": 0.0,
        })

    return PerceptionResult(
        importance=importance_norm,
        emotional_valence=emotional_valence,
        reflection_trigger_candidate=importance_raw >= 7,
        interpretation=interpretation,
        dominant_attributes=dominant_attrs,
        memory_written=True,
    )
```

### `update_memory()` implementation

```python
def update_memory(self, event: dict) -> None:
    """
    Directly write an event to episodic memory.
    Use this for non-stimulus events (decisions, reflections, purchases).

    Args: same dict schema as memory.add_episodic()
    """
    self.memory.add_episodic(event)
```

### Private LLM helper (add if not already present)

```python
def _get_client(self):
    if self._client is None:
        try:
            import anthropic
            self._client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY")
            )
        except ImportError:
            raise RuntimeError("anthropic package required: pip install anthropic")
    return self._client

def _llm_call(self, prompt: str, model: str = "claude-haiku-3-5") -> str:
    client = self._get_client()
    msg = client.messages.create(
        model=model,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text
```

### Required imports at top of `agent.py`

```python
import json
import os
from src.agents.memory import MemoryManager
from src.agents.perception_result import PerceptionResult
from src.taxonomy.schema import Persona
```

---

## Acceptance Criteria

- [ ] `perceive()` accepts any dict with `content` key and returns a `PerceptionResult` instance
- [ ] Importance normalized to 0.0-1.0 via `(raw - 1) / 9.0`
- [ ] `reflection_trigger_candidate=True` when raw importance >= 7
- [ ] `memory.add_episodic()` called exactly once per `perceive()` call
- [ ] Brand memory updated when `stimulus["brand"]` is present
- [ ] `update_memory()` delegates to `memory.add_episodic()` — no longer raises `NotImplementedError`
- [ ] `decide()` still raises `NotImplementedError` (Goose replaces it)
- [ ] Lazy client init — no API calls at `__init__` time
- [ ] `PerceptionResult` exported from `src/agents/__init__.py`
- [ ] If `ANTHROPIC_API_KEY` is missing, raises `anthropic.AuthenticationError` (not a silent fail)
