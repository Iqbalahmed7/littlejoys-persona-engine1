# Sprint 31 — CURSOR Brief: JourneyConfig + JourneyBuilder

## Context
The multi-tick simulation engine (TickEngine) currently has JOURNEY_A and JOURNEY_B hardcoded
as Python dicts inside `src/simulation/tick_engine.py`. This sprint extracts them into
configurable Pydantic models so the Streamlit UI can build, tweak, and run custom journeys
without editing Python.

## Working directory
`/Users/admin/Documents/Simulatte Projects/1. LittleJoys`

## Task 1 — Create `src/simulation/journey_config.py`

Define three Pydantic models:

```python
class StimulusConfig(BaseModel):
    id: str
    tick: int
    type: str          # "ad", "wom", "price_change", "social_event", "product"
    source: str        # "instagram", "whatsapp_friend", "pediatrician", etc.
    content: str
    brand: str = ""

class DecisionScenarioConfig(BaseModel):
    tick: int
    description: str
    product: str
    price_inr: float
    channel: str       # "bigbasket", "firstcry_online", "d2c", etc.

class JourneyConfig(BaseModel):
    journey_id: str
    total_ticks: int
    primary_brand: str
    stimuli: list[StimulusConfig]
    decisions: list[DecisionScenarioConfig]

    def to_journey_spec(self) -> "JourneySpec":
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

    def with_price(self, price_inr: float) -> "JourneyConfig":
        """Return a copy with all decision prices updated."""
        new_decisions = [d.model_copy(update={"price_inr": price_inr}) for d in self.decisions]
        return self.model_copy(update={"decisions": new_decisions})

    def with_channel(self, channel: str) -> "JourneyConfig":
        """Return a copy with all decision channels updated."""
        new_decisions = [d.model_copy(update={"channel": channel}) for d in self.decisions]
        return self.model_copy(update={"decisions": new_decisions})
```

## Task 2 — Create `src/simulation/journey_presets.py`

Migrate the hardcoded schedules from `tick_engine.py` (`_journey_a_schedule()` and
`_journey_b_schedule()`) into `JourneyConfig` instances.

```python
from src.simulation.journey_config import JourneyConfig, StimulusConfig, DecisionScenarioConfig

PRESET_JOURNEY_A = JourneyConfig(
    journey_id="A",
    total_ticks=61,
    primary_brand="littlejoys",
    stimuli=[
        StimulusConfig(id="A-S01", tick=1, type="ad", source="instagram",
            content="Sponsored reel: LittleJoys Nutrimix launch — complete drink mix for "
                    "pickier eaters, emphasising iron and growth.", brand="littlejoys"),
        StimulusConfig(id="A-S05", tick=5, type="wom", source="whatsapp_friend",
            content="Close friend says her child likes LittleJoys Nutrimix and she "
                    "saw improvement in appetite.", brand="littlejoys"),
        StimulusConfig(id="A-S08", tick=8, type="price_change", source="bigbasket",
            content="Price drop alert: LittleJoys Nutrimix 500g now Rs 649 (was Rs 799) on BigBasket.",
            brand="littlejoys"),
        StimulusConfig(id="A-S12", tick=12, type="social_event", source="pediatrician",
            content="At routine visit, Ped mentions low iron is common; suggests considering "
                    "a paediatric drink mix like Nutrimix category.", brand="littlejoys"),
        StimulusConfig(id="A-S15", tick=15, type="social_event", source="school_whatsapp",
            content="Parents debate Horlicks vs 'cleaner' options — someone links LittleJoys "
                    "as a newer alternative.", brand="littlejoys"),
        StimulusConfig(id="A-S23", tick=23, type="product", source="home",
            content="First week using Nutrimix: child accepts the taste; mixes easily with milk.",
            brand="littlejoys"),
        StimulusConfig(id="A-S28", tick=28, type="social_event", source="parent_observation",
            content="Parent notices child seems a bit more energetic in the mornings "
                    "after two weeks of daily use.", brand="littlejoys"),
        StimulusConfig(id="A-S32", tick=32, type="ad", source="instagram",
            content="Retargeting ad for Horlicks Growth Plus — familiar jingle, strong brand.",
            brand="horlicks"),
        StimulusConfig(id="A-S38", tick=38, type="social_event", source="internal",
            content="Noticing the LittleJoys Nutrimix pack is running low; due for replenishment "
                    "this week.", brand="littlejoys"),
        StimulusConfig(id="A-S42", tick=42, type="wom", source="school_mom",
            content="Another mom at pickup asks how Nutrimix is going — you've been honest "
                    "that it's working okay.", brand="littlejoys"),
        StimulusConfig(id="A-S48", tick=48, type="price_change", source="bigbasket",
            content="Check BigBasket: LittleJoys Nutrimix still Rs 649; no active discount "
                    "this week.", brand="littlejoys"),
        StimulusConfig(id="A-S55", tick=55, type="social_event", source="pharmacy",
            content="Pharmacist casually suggests Complan as a 'safe default' if you're "
                    "unsure about newer brands.", brand="complan"),
    ],
    decisions=[
        DecisionScenarioConfig(tick=20, product="LittleJoys Nutrimix 500g", price_inr=649,
            channel="bigbasket",
            description="You see LittleJoys Nutrimix available on BigBasket. Rs 649 for 500g. "
                        "You have seen ads, heard from a friend, and your pediatrician mentioned it. "
                        "Do you buy?"),
        DecisionScenarioConfig(tick=60, product="LittleJoys Nutrimix 500g", price_inr=649,
            channel="bigbasket",
            description="Your LittleJoys Nutrimix pack is nearly finished. Your child has been "
                        "having it for 5 weeks. You're on BigBasket — it's Rs 649, no discount "
                        "this time. Do you reorder?"),
    ],
)

PRESET_JOURNEY_B = JourneyConfig(
    journey_id="B",
    total_ticks=46,
    primary_brand="littlejoys",
    stimuli=[
        StimulusConfig(id="B-S02", tick=2, type="ad", source="instagram_reel",
            content="Reel about child sleep issues and whether magnesium deficiency could play a role."),
        StimulusConfig(id="B-S07", tick=7, type="social_event", source="pediatrician",
            content="Pediatrician mentions poor sleep can sometimes relate to magnesium intake "
                    "in picky eaters."),
        StimulusConfig(id="B-S10", tick=10, type="social_event", source="whatsapp_forward",
            content="Forwarded article on magnesium for growing kids — skimmed on the way to work."),
        StimulusConfig(id="B-S18", tick=18, type="social_event", source="google_search",
            content="Search: 'magnesium for kids India' — scan top results and parent forums."),
        StimulusConfig(id="B-S22", tick=22, type="ad", source="instagram",
            content="Ad: LittleJoys Magnesium Gummies — 30-day pack, Rs 499, kid-friendly format.",
            brand="littlejoys"),
        StimulusConfig(id="B-S27", tick=27, type="ad", source="instagram_influencer",
            content="Mom influencer shows her child taking magnesium gummies; claims sleep improved "
                    "in two weeks.", brand="littlejoys"),
        StimulusConfig(id="B-S32", tick=32, type="social_event", source="pediatrician_followup",
            content="Follow-up: pediatrician says magnesium supplementation is generally fine if "
                    "product is reputable and dosing is age-appropriate.", brand="littlejoys"),
        StimulusConfig(id="B-S38", tick=38, type="product", source="home",
            content="First days of gummies: child likes the taste; no stomach issues.",
            brand="littlejoys"),
        StimulusConfig(id="B-S42", tick=42, type="social_event", source="parent_observation",
            content="After ~10 days, parent believes sleep has improved slightly — not sure if placebo.",
            brand="littlejoys"),
    ],
    decisions=[
        DecisionScenarioConfig(tick=35, product="LittleJoys Magnesium Gummies 30-day pack",
            price_inr=499, channel="firstcry_online",
            description="You've been reading about magnesium for kids. Your pediatrician mentioned it. "
                        "You see LittleJoys Magnesium Gummies — Rs 499 for a 30-day supply, gummy format "
                        "your child will actually eat. Do you try it?"),
        DecisionScenarioConfig(tick=45, product="LittleJoys Magnesium Gummies 30-day pack",
            price_inr=499, channel="firstcry_online",
            description="You've been giving your child LittleJoys Magnesium Gummies for 10 days. "
                        "You've noticed some improvement in sleep. The pack will run out in 5 days. "
                        "Rs 499 to reorder. Do you continue?"),
    ],
)

def list_presets() -> dict[str, JourneyConfig]:
    return {"A": PRESET_JOURNEY_A, "B": PRESET_JOURNEY_B}
```

## Task 3 — Update `src/simulation/tick_engine.py`

Replace the bottom of `tick_engine.py` (the `_journey_a_schedule`, `_journey_b_schedule` functions
and the `JOURNEY_A`, `JOURNEY_B` module-level constants) with:

```python
from src.simulation.journey_presets import PRESET_JOURNEY_A, PRESET_JOURNEY_B

JOURNEY_A = PRESET_JOURNEY_A.to_journey_spec()
JOURNEY_B = PRESET_JOURNEY_B.to_journey_spec()
```

Keep all existing `TickEngine`, `TickSnapshot`, `TickJourneyLog`, `JourneySpec` classes unchanged.

## Verification
```bash
python3 -c "
from src.simulation.journey_config import JourneyConfig
from src.simulation.journey_presets import PRESET_JOURNEY_A, PRESET_JOURNEY_B, list_presets
from src.simulation.tick_engine import JOURNEY_A, JOURNEY_B

# Round-trip check
spec_a = PRESET_JOURNEY_A.to_journey_spec()
assert spec_a.total_ticks == 61
assert spec_a.stimuli_at(1)[0]['source'] == 'instagram'
assert spec_a.decision_at(20)['price_inr'] == 649

# with_price mutator
cheaper = PRESET_JOURNEY_A.with_price(549)
assert cheaper.decisions[0].price_inr == 549
assert PRESET_JOURNEY_A.decisions[0].price_inr == 649  # original unchanged

# JOURNEY_A still works
assert JOURNEY_A.total_ticks == 61
print('All checks passed')
"
```

All existing tests must still pass: `python3 -m pytest tests/test_tick_engine.py -q`
