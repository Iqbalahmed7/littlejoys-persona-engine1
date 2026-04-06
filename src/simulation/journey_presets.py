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
            content=(
                "Short reel in the feed: a parent talking about her child's restless nights "
                "and whether it could be a nutrition issue. The video is not branded — just "
                "a parent sharing. Mentions magnesium in passing as something she is looking into."
            ),
        ),
        StimulusConfig(
            id="B-S07",
            tick=7,
            type="social_event",
            source="pediatrician",
            content=(
                "Routine checkup. You mention the sleep issues. Pediatrician says: "
                "'Most kids this age have some sleep variability — it's usually routine and "
                "screen time, not nutrition. If you want to try a supplement, that's fine, "
                "but manage your expectations. Magnesium deficiency is rare in kids who eat "
                "any variety at all. I wouldn't call it a first line recommendation.'"
            ),
        ),
        StimulusConfig(
            id="B-S10",
            tick=10,
            type="social_event",
            source="whatsapp_forward",
            content=(
                "Forwarded article: 'Can magnesium help kids sleep better?' "
                "Skimmed it on the way to work. Claims are mixed — some studies suggest benefit, "
                "others say evidence is limited for children without diagnosed deficiency. "
                "The article is not India-specific."
            ),
        ),
        StimulusConfig(
            id="B-S18",
            tick=18,
            type="social_event",
            source="google_search",
            content=(
                "Search: 'magnesium gummies for kids India sleep.' Top results are mostly "
                "brand pages and blogs. One Quora thread has parents saying results were "
                "unclear. One doctor's blog says magnesium supplementation is generally "
                "safe but rarely the root cause of sleep problems in otherwise healthy kids."
            ),
        ),
        StimulusConfig(
            id="B-S22",
            tick=22,
            type="ad",
            source="instagram",
            content=(
                "Instagram ad: LittleJoys Magnesium Gummies — '30-day pack, Rs 499, "
                "gummy format kids actually like.' Clean packaging, no strong health claims "
                "beyond 'supports restful sleep.' Tagged as sponsored."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="B-S27",
            tick=27,
            type="ad",
            source="instagram_influencer",
            content=(
                "Paid partnership post: a mom influencer shows her child taking a gummy "
                "before bed and says sleep has been 'so much better lately.' Post includes "
                "#ad and #gifted tags. Comments are split — some parents say it worked for "
                "them, several others ask 'how much of this is the product vs the bedtime "
                "routine you also started?' No clinical backing cited."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="B-S30",
            tick=30,
            type="wom",
            source="close_parent_friend",
            content=(
                "A close friend with a same-age child mentions she tried magnesium gummies "
                "a few months ago. 'Honestly, I couldn't tell if they helped. Maybe 10% better "
                "the first month, but I also started a stricter bedtime routine at the same time. "
                "Didn't reorder because at Rs 500 a month I need to see something clear. "
                "Too much guesswork for me.'"
            ),
        ),
        StimulusConfig(
            id="B-S38",
            tick=38,
            type="product",
            source="home",
            content=(
                "First week of gummies: child takes one each evening without resistance — "
                "likes the taste. No stomach issues or complaints. But sleep is about the same "
                "as before. It's only been a week."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="B-S42",
            tick=42,
            type="social_event",
            source="parent_observation",
            content=(
                "Two weeks into the trial. Sleep is variable — a few better nights, "
                "a few difficult ones. No consistent pattern. Hard to say if anything has changed. "
                "You've also been more disciplined about lights-out time this week, which could "
                "be the factor."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="B-S45",
            tick=45,
            type="social_event",
            source="parent_observation",
            content=(
                "Three weeks in. You check your notes from before the trial. Sleep is roughly "
                "the same — still 2 to 3 difficult nights per week. The better nights correlate "
                "more with earlier dinner and no screens than with the gummy timing. "
                "The gummy doesn't seem to be the deciding factor."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="B-S50",
            tick=50,
            type="wom",
            source="school_parent_group",
            content=(
                "School parent group conversation: one mom says she tried magnesium gummies "
                "for two months. 'Didn't see a clear difference. My doctor told me most kids "
                "don't have an actual deficiency — it's usually routine and screen discipline. "
                "I stopped after two packs. Switched to just a basic multivitamin.' "
                "One other parent agrees; a third says it worked for her but she also changed "
                "three things at once so she can't be sure."
            ),
        ),
        StimulusConfig(
            id="B-S53",
            tick=53,
            type="price_change",
            source="firstcry",
            content=(
                "Browsing FirstCry ahead of pack finishing: LittleJoys Magnesium Gummies "
                "Rs 499, no discount. Himalaya Qukes Kids Multivitamin (includes magnesium) "
                "Rs 340. Baidyanath Calcium + Magnesium syrup Rs 280. "
                "The price difference is real for an uncertain benefit."
            ),
        ),
        StimulusConfig(
            id="B-S55",
            tick=55,
            type="social_event",
            source="internal",
            content=(
                "Pack has about 5 days left. No active discount on FirstCry. "
                "Child takes the gummy when you offer it but doesn't ask for it independently. "
                "Sleep this week: two decent nights, two rough ones. Same as week one."
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
                "Your child has sleep issues. You've read about magnesium — results are mixed. "
                "Your pediatrician said it's fine to try but wasn't enthusiastic; sleep issues "
                "are usually about routine, not nutrition. A close friend tried it and couldn't "
                "tell if it helped. You see LittleJoys Magnesium Gummies at Rs 499 for 30 days. "
                "Do you commit Rs 499 to trial a product with uncertain efficacy?"
            ),
        ),
        DecisionScenarioConfig(
            tick=60,
            product="LittleJoys Magnesium Gummies 30-day pack",
            price_inr=499,
            channel="firstcry_online",
            description=(
                "30-day pack is nearly finished. Sleep has been variable throughout — "
                "some better nights, some not. You can't isolate whether the gummy, "
                "the stricter bedtime routine, or just a phase is responsible. "
                "No clear 'yes this is working' signal. Rs 499 to reorder. "
                "Himalaya makes a similar product for Rs 340; Baidyanath for Rs 280. "
                "Do you continue with LittleJoys, switch to a cheaper alternative, or stop?"
            ),
        ),
    ],
)


PRESET_JOURNEY_C = JourneyConfig(
    journey_id="C",
    total_ticks=61,
    primary_brand="littlejoys",
    stimuli=[
        # ── PRE-TRIAL: AWARENESS & COMPETITIVE PULL (ticks 2–27) ──────────────
        StimulusConfig(
            id="C-S02",
            tick=2,
            type="ad",
            source="youtube_preroll",
            content=(
                "YouTube pre-roll on a parenting channel: LittleJoys Nutrimix for school-age kids — "
                "iron, B12, calcium and zinc formulated for children aged 7-14. "
                "Tagline: 'Give their growth the right building blocks.'"
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="C-S05",
            tick=5,
            type="ad",
            source="bournvita_youtube_kids",
            content=(
                "Child watches YouTube on the family tablet. A Bournvita 'Junior Champions' ad plays "
                "before a cricket highlights video — a young boy scores a match-winning boundary, "
                "then shows his Bournvita mug. Child mentions at dinner: "
                "'Papa, Bournvita is what champions drink. Arjun from my class has it every day.'"
            ),
            brand="bournvita",
        ),
        StimulusConfig(
            id="C-S07",
            tick=7,
            type="social_event",
            source="school_whatsapp",
            content=(
                "School parent WhatsApp group: a parent mentions her 9-year-old "
                "comes home exhausted and irritable after school — "
                "others suggest iron and B12 checks; one parent says 'we noticed the same, "
                "pediatrician said it was just exam stress and less outdoor time'."
            ),
        ),
        StimulusConfig(
            id="C-S12",
            tick=12,
            type="ad",
            source="instagram_influencer",
            content=(
                "Mom influencer's 'school morning routine' reel — her 10-year-old "
                "has Nutrimix in milk before leaving for school. Top comment (317 likes): "
                "'My son refused it after day 3 — did yours ever reject it? 😅' "
                "Influencer replies: 'It took 2 weeks, keep going!' Reply below: "
                "'Tried for 3 weeks, no difference. Went back to Bournvita.'"
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="C-S17",
            tick=17,
            type="social_event",
            source="pediatrician",
            content=(
                "Annual checkup: pediatrician notes that school-age children (7-14) often "
                "develop iron and B12 gaps as diet becomes pickier and screen time rises. "
                "'A daily drink-mix makes sense IF your child is a picky eater — "
                "choose one with lower added sugar. Bournvita has about 14g sugar per serving; "
                "check the label on whatever you buy.'"
            ),
        ),
        StimulusConfig(
            id="C-S21",
            tick=21,
            type="wom",
            source="school_pickup_parent",
            content=(
                "Parent at school pickup (child aged 11): 'We tried Nutrimix for 6 weeks. "
                "My son hated the taste after week 2 — kept asking for Horlicks instead. "
                "We eventually gave up. He prefers the chocolate flavour and honestly, "
                "I couldn't tell if Nutrimix was doing anything different.'"
            ),
        ),
        StimulusConfig(
            id="C-S22",
            tick=22,
            type="price_change",
            source="bigbasket",
            content=(
                "BigBasket search results for 'health drink for kids': "
                "Nutrimix 500g Rs 649 | Bournvita 500g Rs 399 (on sale Rs 349 this week) | "
                "Horlicks Growth+ 500g Rs 449 | Complan NutriGro 500g Rs 479. "
                "Nutrimix shows detailed micronutrient breakdown. Others have better ratings volume."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="C-S27",
            tick=27,
            type="wom",
            source="school_parent",
            content=(
                "Parent at school pickup (child aged 8): 'Switched from Bournvita to Nutrimix "
                "two months ago — less added sugar and my daughter actually finishes the glass now. "
                "Haven't noticed a dramatic change but I feel better about what she's having.'"
            ),
            brand="littlejoys",
        ),
        # ── POST-TRIAL: USAGE, EFFICACY & COMPETITIVE THREAT (ticks 30–55) ───
        StimulusConfig(
            id="C-S30",
            tick=30,
            type="social_event",
            source="child_peer_pressure",
            content=(
                "Child comes home from school: 'Mamma, all my friends have Bournvita in their tiffin. "
                "Priya has it with a straw and it smells like chocolate. "
                "Why do I have to have the boring one? Can we please get the cricket one?'"
            ),
        ),
        StimulusConfig(
            id="C-S35",
            tick=35,
            type="product",
            source="home",
            content=(
                "First week of use: child takes Nutrimix reluctantly — "
                "says it 'tastes okay but not as nice as Bournvita'. "
                "Mixes cleanly into milk, no lumps. "
                "Morning routine is slightly smoother. Child does not ask for it independently."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="C-S42",
            tick=42,
            type="social_event",
            source="parent_observation",
            content=(
                "Four weeks in: child takes Nutrimix each morning without active protest. "
                "Energy and focus look roughly the same as before — hard to isolate. "
                "School report came back decent but tuition classes also started this month. "
                "No specific improvement clearly attributable to the product."
            ),
            brand="littlejoys",
        ),
        StimulusConfig(
            id="C-S46",
            tick=46,
            type="ad",
            source="bournvita_retargeting_flipkart",
            content=(
                "Bournvita retargeting ad on Flipkart + YouTube: 'Doodh Mein Daalo — "
                "the taste children love, the strength mothers trust.' "
                "Cricket World Cup co-branded imagery. Flipkart sale: Rs 349 for 500g (limited time). "
                "Child sees ad on tablet and says: 'That's the one Arjun drinks!'"
            ),
            brand="bournvita",
        ),
        StimulusConfig(
            id="C-S50",
            tick=50,
            type="wom",
            source="parent_whatsapp_group",
            content=(
                "School parent WhatsApp group — mixed thread: "
                "'Nutrimix has a better iron profile.' "
                "'But mine refused it after a month.' "
                "'We're happy with Horlicks, it has DHA now.' "
                "'Bournvita has too much sugar, I checked — 14g per serving!' "
                "'Horlicks is also 11g.' "
                "No consensus — everyone doing something different."
            ),
        ),
        StimulusConfig(
            id="C-S55",
            tick=55,
            type="social_event",
            source="home_reorder_moment",
            content=(
                "Nutrimix pack is running low — needs to be reordered this week. "
                "Child has been taking it for 30 days without strong objection, "
                "but still asks occasionally: 'Can we try the cricket Bournvita one instead?' "
                "Bournvita is currently Rs 349 on sale. No clear performance change to point to."
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
                "Your pediatrician flagged potential iron/B12 gaps for school-age children. "
                "You've seen Nutrimix ads, read mixed WOM (one parent loves it, one quit after 6 weeks), "
                "and your child has been asking for Bournvita because 'champions drink it'. "
                "Nutrimix: Rs 649 with better micronutrient label but lower brand recognition. "
                "Bournvita: Rs 399 (Rs 349 on sale), more sugar, but the child wants it. "
                "Do you trial Nutrimix for your older child, or stick with the familiar brands?"
            ),
        ),
        DecisionScenarioConfig(
            tick=60,
            product="LittleJoys Nutrimix 500g",
            price_inr=649,
            channel="bigbasket",
            description=(
                "30 days complete. No dramatic change in energy or focus — hard to isolate from tuition. "
                "Child takes it without protest but still asks for Bournvita occasionally. "
                "Pack is nearly finished. Rs 649 to reorder Nutrimix — Bournvita currently Rs 349 on sale "
                "(Rs 300 cheaper). School peers are mostly on Bournvita or Horlicks. "
                "Do you stick with Nutrimix or switch to Bournvita at the lower price?"
            ),
        ),
    ],
)


def list_presets() -> dict[str, JourneyConfig]:
    return {"A": PRESET_JOURNEY_A, "B": PRESET_JOURNEY_B, "C": PRESET_JOURNEY_C}
