from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


@dataclass
class TickSnapshot:
    """State of persona at a single simulation tick."""

    tick: int
    brand_trust: dict[str, float]
    memories_count: int
    cumulative_salience: float
    reflected: bool
    perception_results: list[dict]
    decision_result: dict | None


@dataclass
class TickJourneyLog:
    """Complete record of a persona's multi-tick journey."""

    persona_id: str
    display_name: str
    journey_id: str
    total_ticks: int
    snapshots: list[TickSnapshot]
    final_decision: dict | None
    reordered: bool
    error: str | None

    def to_dict(self) -> dict:
        """Serialise to JSON-compatible dict."""
        return {
            "persona_id": self.persona_id,
            "display_name": self.display_name,
            "journey_id": self.journey_id,
            "total_ticks": self.total_ticks,
            "snapshots": [
                {
                    "tick": s.tick,
                    "brand_trust": dict(s.brand_trust),
                    "memories_count": s.memories_count,
                    "cumulative_salience": s.cumulative_salience,
                    "reflected": s.reflected,
                    "perception_results": list(s.perception_results),
                    "decision_result": s.decision_result,
                }
                for s in self.snapshots
            ],
            "final_decision": self.final_decision,
            "reordered": self.reordered,
            "error": self.error,
        }


@dataclass
class JourneySpec:
    """Defines a simulation journey: which stimuli fire at which ticks."""

    journey_id: str
    total_ticks: int
    primary_brand: str
    _stimuli_schedule: dict[int, list[dict]] = field(repr=False)
    _decision_schedule: dict[int, dict] = field(repr=False)

    def stimuli_at(self, tick: int) -> list[dict]:
        return list(self._stimuli_schedule.get(tick, []))

    def decision_at(self, tick: int) -> dict | None:
        return self._decision_schedule.get(tick)


class TickEngine:
    """
    Runs a persona through a multi-tick simulation journey.

    A journey is a schedule of stimuli and decision scenarios mapped to
    specific simulation ticks. The engine advances tick by tick, fires
    the appropriate perceive/decide calls, tracks memory accumulation,
    triggers reflection when cumulative salience crosses threshold, and
    records brand trust snapshots at every tick.
    """

    REFLECTION_THRESHOLD = 5.0

    def __init__(self) -> None:
        pass

    def run(
        self,
        persona: Persona,
        journey: JourneySpec,
    ) -> TickJourneyLog:
        """Run a complete journey for one persona."""
        from src.agents.agent import CognitiveAgent

        agent = CognitiveAgent(persona)
        cumulative_salience = 0.0
        snapshots: list[TickSnapshot] = []
        final_decision: dict | None = None
        error: str | None = None

        try:
            for tick in range(journey.total_ticks):
                tick_perceptions: list[dict] = []
                tick_decision: dict | None = None
                reflected = False

                for stimulus in journey.stimuli_at(tick):
                    try:
                        payload = {**stimulus, "simulation_tick": tick}
                        pr = agent.perceive(payload)
                        cumulative_salience += float(pr.importance)
                        tick_perceptions.append(
                            {
                                "stimulus_id": stimulus.get("id", f"S-{tick}"),
                                "importance": float(pr.importance),
                                "emotional_valence": float(pr.emotional_valence),
                                "reflection_trigger": pr.reflection_trigger_candidate,
                            }
                        )
                    except Exception as e:  # noqa: BLE001 — surface per-stimulus errors in log
                        tick_perceptions.append(
                            {
                                "stimulus_id": stimulus.get("id", f"S-{tick}"),
                                "error": str(e),
                            }
                        )

                if cumulative_salience >= self.REFLECTION_THRESHOLD:
                    try:
                        agent.reflect(n_insights=2)
                        reflected = True
                        cumulative_salience = 0.0
                    except Exception:
                        pass

                scenario = journey.decision_at(tick)
                if scenario is not None:
                    try:
                        scen = {**scenario, "simulation_tick": scenario.get("simulation_tick", tick)}
                        dr = agent.decide(scen)
                        tick_decision = dr.to_dict()
                        final_decision = tick_decision

                        if dr.decision in ("buy", "trial"):
                            brand = journey.primary_brand
                            if brand in persona.brand_memories:
                                persona.brand_memories[brand].purchase_count += 1
                    except Exception as e:  # noqa: BLE001
                        tick_decision = {"error": str(e)}

                brand_trust = {
                    b: round(float(bm.trust_level), 4) for b, bm in persona.brand_memories.items()
                }

                snapshots.append(
                    TickSnapshot(
                        tick=tick,
                        brand_trust=brand_trust,
                        memories_count=len(persona.episodic_memory),
                        cumulative_salience=round(cumulative_salience, 4),
                        reflected=reflected,
                        perception_results=tick_perceptions,
                        decision_result=tick_decision,
                    )
                )

        except Exception as e:  # noqa: BLE001
            error = str(e)

        reordered = False
        brand = journey.primary_brand
        if brand in persona.brand_memories:
            reordered = persona.brand_memories[brand].purchase_count > 1

        return TickJourneyLog(
            persona_id=persona.id,
            display_name=persona.display_name or persona.id,
            journey_id=journey.journey_id,
            total_ticks=journey.total_ticks,
            snapshots=snapshots,
            final_decision=final_decision,
            reordered=reordered,
            error=error,
        )


from src.simulation.journey_presets import PRESET_JOURNEY_A, PRESET_JOURNEY_B

JOURNEY_A = PRESET_JOURNEY_A.to_journey_spec()
JOURNEY_B = PRESET_JOURNEY_B.to_journey_spec()
