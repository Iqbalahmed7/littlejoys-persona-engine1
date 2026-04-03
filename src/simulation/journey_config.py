from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from src.simulation.tick_engine import JourneySpec


class StimulusConfig(BaseModel):
    """A single scheduled stimulus for TickEngine."""

    model_config = ConfigDict(extra="forbid")

    id: str
    tick: int
    type: str
    source: str
    content: str
    brand: str = ""


class DecisionScenarioConfig(BaseModel):
    """A purchase decision scenario at a specific tick."""

    model_config = ConfigDict(extra="forbid")

    tick: int
    description: str
    product: str
    price_inr: float
    channel: str


class JourneyConfig(BaseModel):
    """Declarative journey definition convertible to JourneySpec."""

    model_config = ConfigDict(extra="forbid")

    journey_id: str
    total_ticks: int
    primary_brand: str
    stimuli: list[StimulusConfig] = Field(default_factory=list)
    decisions: list[DecisionScenarioConfig] = Field(default_factory=list)

    def to_journey_spec(self) -> JourneySpec:
        """Convert to the TickEngine-native JourneySpec format."""
        from src.simulation.tick_engine import JourneySpec

        stimuli_schedule: dict[int, list[dict]] = {}
        for s in self.stimuli:
            stimuli_schedule.setdefault(s.tick, []).append(s.model_dump(exclude={"tick"}))

        decision_schedule: dict[int, dict] = {}
        for d in self.decisions:
            decision_schedule[d.tick] = d.model_dump(exclude={"tick"})

        return JourneySpec(
            journey_id=self.journey_id,
            total_ticks=self.total_ticks,
            primary_brand=self.primary_brand,
            _stimuli_schedule=stimuli_schedule,
            _decision_schedule=decision_schedule,
        )

    def with_price(self, price_inr: float) -> JourneyConfig:
        """Return a copy with all decision prices updated."""
        new_decisions = [d.model_copy(update={"price_inr": price_inr}) for d in self.decisions]
        return self.model_copy(update={"decisions": new_decisions})

    def with_channel(self, channel: str) -> JourneyConfig:
        """Return a copy with all decision channels updated."""
        new_decisions = [d.model_copy(update={"channel": channel}) for d in self.decisions]
        return self.model_copy(update={"decisions": new_decisions})
