"""
Cognitive agent wrapper for personas during simulation.

Wraps a Persona with perception, memory update, and decision-making capabilities.
See ARCHITECTURE.md §7 for the agent architecture.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from src.agents.memory import MemoryManager
from src.agents.perception_result import PerceptionResult

from .decision_result import DecisionResult

if TYPE_CHECKING:
    from src.agents.reflection import ReflectionInsight
    from src.taxonomy.schema import Persona

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

DECISION_PROMPT = """\
You are simulating the decision-making of a specific Indian parent evaluating a child nutrition product.

=== PERSONA: {name} ===
Decision style:   {decision_style}
Trust anchor:     {trust_anchor}
Risk appetite:    {risk_appetite}
Primary values:   {primary_value_orientation}
Coping mechanism: {coping_mechanism}
Budget:           Rs{budget_inr}/month for child nutrition
Budget ceiling:   {price_sensitivity} price sensitivity

=== CORE MEMORY (who they are) ===
{core_memory_summary}

=== RECENT MEMORIES (most relevant to this decision) ===
{retrieved_memories}

=== SCENARIO ===
{scenario_description}

=== YOUR TASK ===
Decide what this persona does in this scenario. Think step by step:

STEP 1 - INITIAL REACTION: What is their gut feeling? (1-2 sentences)
STEP 2 - INFORMATION PROCESSING: What information do they focus on, given their attributes?
STEP 3 - CONSTRAINT CHECK: What hard limits apply? (budget, non-negotiables, trust requirements)
STEP 4 - SOCIAL SIGNAL CHECK: What would people in their trust network say about this?
STEP 5 - FINAL DECISION: What do they actually do?

Return valid JSON:
{{
  "decision": "buy | trial | reject | defer | research_more",
  "confidence": <float 0.0-1.0>,
  "reasoning_trace": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ...",
    "Step 4: ...",
    "Step 5: ..."
  ],
  "key_drivers": ["driver1", "driver2"],
  "objections": ["objection1"],
  "willingness_to_pay_inr": <int or null>,
  "follow_up_action": "short description of what they do next"
}}
"""


class CognitiveAgent:
    """
    Agent wrapper that gives a Persona the ability to perceive, remember, and decide.

    The agent processes stimuli through its persona's psychological lens,
    updates memory based on experiences, and makes purchase decisions.
    """

    def __init__(self, persona: Persona) -> None:
        self.persona = persona
        self.memory = MemoryManager(persona)  # Cursor implements MemoryManager
        self._client = None  # lazy init — no API call at construction time

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
            name=getattr(self.persona, "display_name", None) or self.persona.id,
            age=demo.parent_age,
            health_anxiety=psych.health_anxiety,
            information_need=psych.information_need,
            social_proof_bias=psych.social_proof_bias,
            best_for_my_child=self.persona.values.best_for_my_child_intensity,
            supplement_necessity=self.persona.values.supplement_necessity_belief,
            decision_style=derived.decision_style if derived is not None else "analytical",
            trust_anchor=derived.trust_anchor if derived is not None else "self",
            stimulus_description=stimulus_description,
        )

        result_raw = self._llm_call(prompt)

        try:
            parsed = json.loads(result_raw)
        except json.JSONDecodeError:
            start = result_raw.find("{")
            end = result_raw.rfind("}") + 1
            parsed = json.loads(result_raw[start:end]) if start >= 0 and end > start else {}

        importance_raw = int(parsed.get("importance", 5))
        importance_raw = max(1, min(10, importance_raw))
        importance_norm = round((importance_raw - 1) / 9.0, 4)  # 1-10 → 0.0-1.0
        emotional_valence = float(parsed.get("emotional_valence", 0.0))
        emotional_valence = max(-1.0, min(1.0, emotional_valence))
        dominant_attrs = parsed.get("dominant_attributes", [])
        if not isinstance(dominant_attrs, list):
            dominant_attrs = []
        dominant_attrs = [str(a) for a in dominant_attrs if str(a).strip()]
        interpretation = str(parsed.get("interpretation", ""))

        self.memory.add_episodic(
            {
                "event_type": "stimulus",
                "content": (
                    f"[{stimulus.get('type', 'stimulus')} from {stimulus.get('source', '?')}] "
                    f"{stimulus.get('content', '')}"
                ),
                "emotional_valence": emotional_valence,
                "salience": importance_norm,
                "simulation_tick": stimulus.get("simulation_tick", 0),
            }
        )

        brand = stimulus.get("brand")
        if brand:
            self.memory.update_brand_memory(
                str(brand),
                {
                    "channel": stimulus.get("type", "ad"),
                    "sentiment": emotional_valence,
                    "content": str(stimulus.get("content", ""))[:200],
                    "trust_delta": 0.0,
                },
            )

        return PerceptionResult(
            importance=importance_norm,
            emotional_valence=emotional_valence,
            reflection_trigger_candidate=importance_raw >= 7,
            interpretation=interpretation,
            dominant_attributes=dominant_attrs,
            memory_written=True,
        )

    def update_memory(self, event: dict) -> None:
        """
        Directly write an event to episodic memory.
        Use this for non-stimulus events (decisions, reflections, purchases).

        Args: same dict schema as memory.add_episodic()
        """
        self.memory.add_episodic(event)

    def reflect(self, n_insights: int = 2) -> list[ReflectionInsight]:
        """
        Trigger a reflection pass over this persona's recent episodic memory.

        Should be called after a sequence of perceive() calls — typically when
        the cumulative importance of recent stimuli crosses a threshold. The
        caller (scenario runner) is responsible for tracking cumulative salience
        and deciding when to call this.

        Args:
            n_insights: Number of insights to generate (1-3, default 2).

        Returns:
            List of ReflectionInsight objects. Each insight is also appended
            to persona.episodic_memory automatically by ReflectionEngine.

        Side effects:
            Appends n_insights new MemoryEntry objects (event_type="reflection")
            to persona.episodic_memory via ReflectionEngine.
        """
        from src.agents.reflection import ReflectionEngine

        engine = ReflectionEngine()
        return engine.reflect(
            persona=self.persona,
            llm_call_fn=lambda prompt: self._llm_call(prompt, model="claude-sonnet-4-5"),
            n_insights=n_insights,
        )

    def decide(self, scenario: dict) -> DecisionResult:
        """
        Simulate this persona making a decision in a given scenario.

        Args:
            scenario: dict with keys:
                description     (str)  — what's happening
                product         (str, optional) — product name
                price_inr       (int, optional) — price of product
                channel         (str, optional) — where the scenario occurs
                simulation_tick (int, optional) — current sim time

        Returns:
            DecisionResult with decision, confidence, 5-step reasoning trace.

        Side effects:
            - Retrieves top-10 relevant memories via memory.retrieve()
            - Writes the decision outcome to episodic memory
        """
        tick = scenario.get("simulation_tick", 0)

        # Retrieve relevant memories
        query = f"{scenario.get('description', '')} {scenario.get('product', '')}"
        retrieved = self.memory.retrieve(query, top_k=10, simulation_tick=tick)

        core_memory_summary = self._build_core_memory_summary()
        retrieved_memories_text = self._format_retrieved_memories(retrieved)

        derived = self.persona.parent_traits
        budget = self.persona.budget_profile

        # Some unit tests use minimal Persona fixtures that omit derived traits
        # and budget profiles. The prompt must still be constructible.
        decision_style = derived.decision_style if derived is not None else "unknown"
        trust_anchor = derived.trust_anchor if derived is not None else "unknown"
        risk_appetite = derived.risk_appetite if derived is not None else "unknown"
        primary_value_orientation = (
            derived.primary_value_orientation if derived is not None else "unknown"
        )
        coping_mechanism = derived.coping_mechanism if derived is not None else "unknown"

        budget_inr = budget.discretionary_child_nutrition_budget_inr if budget is not None else 0
        price_sensitivity = budget.price_sensitivity if budget is not None else "unknown"

        prompt = DECISION_PROMPT.format(
            name=self.persona.display_name or self.persona.id,
            decision_style=decision_style,
            trust_anchor=trust_anchor,
            risk_appetite=risk_appetite,
            primary_value_orientation=primary_value_orientation,
            coping_mechanism=coping_mechanism,
            budget_inr=budget_inr,
            price_sensitivity=price_sensitivity,
            core_memory_summary=core_memory_summary,
            retrieved_memories=retrieved_memories_text,
            scenario_description=scenario.get("description", ""),
        )

        raw = self._llm_call(prompt, model="claude-sonnet-4-5", max_tokens=2048)

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            parsed = json.loads(raw[start:end]) if start >= 0 else {}

        result = DecisionResult(
            decision=parsed.get("decision", "defer"),
            confidence=float(parsed.get("confidence", 0.5)),
            reasoning_trace=parsed.get("reasoning_trace", []),
            key_drivers=parsed.get("key_drivers", []),
            objections=parsed.get("objections", []),
            willingness_to_pay_inr=parsed.get("willingness_to_pay_inr"),
            follow_up_action=parsed.get("follow_up_action", ""),
            persona_id=self.persona.display_name or self.persona.id,
        )

        # Write decision to memory
        valence = 0.3 if result.decision == "buy" else -0.2 if result.decision == "reject" else 0.0
        self.memory.add_episodic(
            {
                "event_type": "decision",
                "content": f"Decided to {result.decision} in scenario: {scenario.get('description', '')[:100]}. Confidence: {result.confidence:.2f}",
                "emotional_valence": valence,
                "salience": 0.75,
                "simulation_tick": tick,
            }
        )

        return result

    def _get_client(self):
        # Always create a fresh client — httpx 0.28+ transport state is not
        # thread-safe when an instance is reused across ThreadPoolExecutor workers.
        try:
            import anthropic
            import httpx
        except ImportError as exc:
            raise RuntimeError("anthropic package required: pip install anthropic") from exc

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise anthropic.AuthenticationError(
                "ANTHROPIC_API_KEY is missing",
                response=httpx.Response(status_code=401),
                body={"error": "missing_api_key"},
            )
        return anthropic.Anthropic(api_key=api_key)

    def _llm_call(self, prompt: str, model: str = "claude-haiku-4-5", max_tokens: int = 512) -> str:
        client = self._get_client()
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        content: Any = msg.content[0]
        return str(getattr(content, "text", ""))

    def _build_core_memory_summary(self) -> str:
        """Extract a condensed summary from narrative and first-person summary."""
        summary_parts = []
        if hasattr(self.persona, "first_person_summary") and self.persona.first_person_summary:
            summary_parts.append(self.persona.first_person_summary)
        if hasattr(self.persona, "narrative") and self.persona.narrative:
            summary_parts.append(self.persona.narrative[:300] + "...")
        return "\n".join(summary_parts) if summary_parts else "No core memory available."

    def _format_retrieved_memories(self, memories: list) -> str:
        if not memories:
            return "No relevant memories found."
        lines = []
        for i, mem in enumerate(memories, 1):
            valence_label = (
                "+" if mem.emotional_valence > 0.1 else "-" if mem.emotional_valence < -0.1 else "~"
            )
            lines.append(f"{i}. [{mem.event_type}|valence:{valence_label}] {mem.content[:120]}")
        return "\n".join(lines)
