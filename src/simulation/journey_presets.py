from __future__ import annotations

from src.simulation.journey_config import DecisionScenarioConfig, JourneyConfig, StimulusConfig

PRESET_JOURNEY_A = JourneyConfig(
    journey_id="A",
    total_ticks=61,
    primary_brand="littlejoys",
    stimuli=[
        StimulusConfig(
            id="A-S01",
            tick=1,
            type="ad",
            source="instagram",
            content=(
                "Sponsored reel: LittleJoys Nutrimix launch — complete drink mix for "
                "pickier eaters, emphasising iron and growth."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="A-S05",
            tick=5,
            type="wom",
            source="whatsapp_friend",
            content=(
                "Close friend says her child likes LittleJoys Nutrimix and she "
                "saw improvement in appetite."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="A-S08",
            tick=8,
            type="price_change",
            source="bigbasket",
            content=(
                "Price drop alert: LittleJoys Nutrimix 500g now Rs 649 (was Rs 799) on BigBasket."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="A-S12",
            tick=12,
            type="social_event",
            source="pediatrician",
            content=(
                "At routine visit, Ped mentions low iron is common; suggests considering "
                "a paediatric drink mix like Nutrimix category."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="A-S15",
            tick=15,
            type="social_event",
            source="school_whatsapp",
            content=(
                "Parents debate Horlicks vs 'cleaner' options — someone links LittleJoys "
                "as a newer alternative."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="A-S23",
            tick=23,
            type="product",
            source="home",
            content=(
                "First week using Nutrimix: child takes it on most mornings without fuss. "
                "Mixes well with milk. One refusal mid-week but generally cooperative."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="A-S28",
            tick=28,
            type="social_event",
            source="parent_observation",
            content=(
                "Four weeks in. Child acceptance is mixed — takes it about 5 out of 7 "
                "days without complaint, but asks for plain milk the other two. "
                "No visible change in appetite or energy yet. Can't tell if it's working."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="A-S32",
            tick=32,
            type="ad",
            source="instagram",
            content="Retargeting ad for Horlicks Growth Plus — familiar jingle, strong brand.",
            brand="horlicks",
        ),
        StimulusConfig(
            id="A-S36",
            tick=36,
            type="wom",
            source="school_mom_mixed",
            content=(
                "School mom who also started Nutrimix says her child is 'okay with it' — "
                "takes it most days, no strong complaints, but she hasn't noticed any "
                "clear improvement either. She's on the fence about reordering: "
                "'I'll probably try one more pack and see.'"
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="A-S38",
            tick=38,
            type="social_event",
            source="internal",
            content=(
                "Nutrimix pack is running low — about a week left. "
                "No discount visible on BigBasket right now."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="A-S48",
            tick=48,
            type="price_change",
            source="bigbasket",
            content=(
                "Browsing BigBasket: LittleJoys Nutrimix Rs 649, no discount. "
                "Horlicks Growth Plus 500g is Rs 449 on the same page. "
                "Bournvita 500g is Rs 389."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="A-S55",
            tick=55,
            type="social_event",
            source="parent_observation",
            content=(
                "Five weeks done. Child has taken Nutrimix on most days — "
                "roughly 5 out of 7. No dramatic improvement visible, but no "
                "rejection pattern either. Pediatrician's iron concern is still "
                "in the back of mind. Not sure if the product is 'working' "
                "but the child hasn't refused it consistently."
            ),
            brand="littlejoys",
        ),
    ],
    decisions=[
        DecisionScenarioConfig(
            tick=20,
            product="LittleJoys Nutrimix 500g",
            price_inr=649,
            channel="bigbasket",
            description=(
                "You see LittleJoys Nutrimix available on BigBasket. Rs 649 for 500g. "
                "You have seen ads, heard from a friend, and your pediatrician mentioned it. "
                "Do you buy?"
            ),
        ),
        DecisionScenarioConfig(
            tick=60,
            product="LittleJoys Nutrimix 500g",
            price_inr=649,
            channel="bigbasket",
            description=(
                "Your LittleJoys Nutrimix pack is nearly finished. You're on BigBasket — "
                "it's Rs 649, no discount this time. Do you reorder?"
            ),
        ),
    ],
)

PRESET_JOURNEY_B = JourneyConfig(
    journey_id="B",
    total_ticks=61,
    primary_brand="littlejoys",
    stimuli=[
        StimulusConfig(
            id="B-S02",
            tick=2,
            type="ad",
            source="instagram_reel",
            content="Reel about child sleep issues and whether magnesium deficiency could play a role.",
        ),
        StimulusConfig(
            id="B-S07",
            tick=7,
            type="social_event",
            source="pediatrician",
            content=(
                "Pediatrician mentions poor sleep can sometimes relate to magnesium intake "
                "in picky eaters."
            ),
        ),
        StimulusConfig(
            id="B-S10",
            tick=10,
            type="social_event",
            source="whatsapp_forward",
            content="Forwarded article on magnesium for growing kids — skimmed on the way to work.",
        ),
        StimulusConfig(
            id="B-S18",
            tick=18,
            type="social_event",
            source="google_search",
            content="Search: 'magnesium for kids India' — scan top results and parent forums.",
        ),
        StimulusConfig(
            id="B-S22",
            tick=22,
            type="ad",
            source="instagram",
            content=(
                "Ad: LittleJoys Magnesium Gummies — 30-day pack, Rs 499, kid-friendly format."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="B-S27",
            tick=27,
            type="ad",
            source="instagram_influencer",
            content=(
                "Mom influencer shows her child taking magnesium gummies; claims sleep improved "
                "in two weeks."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="B-S32",
            tick=32,
            type="social_event",
            source="pediatrician_followup",
            content=(
                "Follow-up: pediatrician says magnesium supplementation is generally fine if "
                "product is reputable and dosing is age-appropriate."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="B-S38",
            tick=38,
            type="product",
            source="home",
            content="First days of gummies: child likes the taste; no stomach issues.",
            brand="littlejoys",
        ),
        StimulusConfig(
            id="B-S42",
            tick=42,
            type="social_event",
            source="parent_observation",
            content=(
                "About two weeks into the 30-day pack. Child takes the gummy each evening "
                "without resistance. No particular changes observed yet."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="B-S50",
            tick=50,
            type="ad",
            source="instagram",
            content=(
                "Retargeting ad: LittleJoys Magnesium Gummies — 'Most parents reorder. "
                "See why.' No discount shown."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="B-S55",
            tick=55,
            type="social_event",
            source="internal",
            content=(
                "30-day pack of LittleJoys Magnesium Gummies is running low — about 5 days "
                "remaining. No active discount visible on FirstCry."
            ),
            brand="littlejoys",
        ),
    ],
    decisions=[
        DecisionScenarioConfig(
            tick=35,
            product="LittleJoys Magnesium Gummies 30-day pack",
            price_inr=499,
            channel="firstcry_online",
            description=(
                "You've been reading about magnesium for kids. Your pediatrician mentioned it. "
                "You see LittleJoys Magnesium Gummies — Rs 499 for a 30-day supply, gummy format "
                "your child will actually eat. Do you try it?"
            ),
        ),
        DecisionScenarioConfig(
            tick=60,
            product="LittleJoys Magnesium Gummies 30-day pack",
            price_inr=499,
            channel="firstcry_online",
            description=(
                "Your 30-day pack of LittleJoys Magnesium Gummies is nearly finished. "
                "Rs 499 to reorder. Do you continue with another pack?"
            ),
        ),
    ],
)


PRESET_JOURNEY_C = JourneyConfig(
    journey_id="C",
    total_ticks=61,
    primary_brand="littlejoys",
    stimuli=[
        StimulusConfig(
            id="C-S02",
            tick=2,
            type="ad",
            source="youtube_preroll",
            content=(
                "YouTube pre-roll: LittleJoys Nutrimix for school-age kids — "
                "daily energy, focus, and growth support for active children aged 7-14."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="C-S07",
            tick=7,
            type="social_event",
            source="school_whatsapp",
            content=(
                "School parent WhatsApp group: a parent mentions her 9-year-old "
                "comes home exhausted and irritable — others suggest checking iron and B12 levels."
            ),
        ),
        StimulusConfig(
            id="C-S12",
            tick=12,
            type="ad",
            source="instagram_influencer",
            content=(
                "Mom influencer's 'school morning routine' reel — her 10-year-old "
                "has Nutrimix in milk before leaving for school; credits it for better concentration."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="C-S17",
            tick=17,
            type="social_event",
            source="pediatrician",
            content=(
                "Annual checkup: pediatrician notes that school-age children often "
                "develop iron and B12 gaps as diet gets pickier; suggests a daily drink mix "
                "if the child isn't eating a varied diet."
            ),
        ),
        StimulusConfig(
            id="C-S22",
            tick=22,
            type="price_change",
            source="bigbasket",
            content=(
                "BigBasket comparison page: Nutrimix 500g at Rs 649, Bournvita 500g at Rs 399, "
                "Horlicks Growth Plus 500g at Rs 499. Nutrimix has more specific micronutrient info."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="C-S27",
            tick=27,
            type="wom",
            source="school_parent",
            content=(
                "Parent at school pickup says her 8-year-old switched from Bournvita to Nutrimix "
                "two months ago — less sugar, and the child actually finishes the glass now."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="C-S35",
            tick=35,
            type="product",
            source="home",
            content=(
                "First week: child accepts the taste without complaints; mixes cleanly into milk "
                "with no lumps. School bag packed and out of the door on time."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="C-S42",
            tick=42,
            type="social_event",
            source="parent_observation",
            content=(
                "Four weeks in: child takes Nutrimix in milk each morning without complaints. "
                "Routine is established. No specific changes clearly attributable to the product."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="C-S48",
            tick=48,
            type="ad",
            source="instagram",
            content=(
                "Retargeting ad: Bournvita 'Junior Champion' campaign — legacy imagery, "
                "sports trophy imagery, strong brand recall."
            ),
            brand="bournvita",
        ),
        StimulusConfig(
            id="C-S55",
            tick=55,
            type="social_event",
            source="internal",
            content=(
                "Nutrimix pack is running low. Child asks if there is more 'the brown milk drink'. "
                "Replenishment needed this week."
            ),
            brand="littlejoys",
        ),
    ],
    decisions=[
        DecisionScenarioConfig(
            tick=28,
            product="LittleJoys Nutrimix 500g",
            price_inr=649,
            channel="bigbasket",
            description=(
                "You've seen Nutrimix in ads, heard about it from a school parent, "
                "and your pediatrician mentioned a daily drink mix for school-age kids. "
                "Rs 649 on BigBasket — costlier than Bournvita but more specific. "
                "Do you try it for your child?"
            ),
        ),
        DecisionScenarioConfig(
            tick=60,
            product="LittleJoys Nutrimix 500g",
            price_inr=649,
            channel="bigbasket",
            description=(
                "Your Nutrimix pack is nearly finished. "
                "Rs 649 to reorder — no discount this time. "
                "Bournvita is Rs 250 cheaper on the same shelf. Do you stick with Nutrimix?"
            ),
        ),
    ],
)


def list_presets() -> dict[str, JourneyConfig]:
    return {"A": PRESET_JOURNEY_A, "B": PRESET_JOURNEY_B, "C": PRESET_JOURNEY_C}
