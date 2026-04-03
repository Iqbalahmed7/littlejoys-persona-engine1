from __future__ import annotations

from pydantic import BaseModel, Field

from src.taxonomy.schema import SignedUnitInterval, UnitInterval  # noqa: TC001


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
