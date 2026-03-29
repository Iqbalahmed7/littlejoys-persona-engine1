"""
Five-layer system prompts for persona interviews — natural beliefs and guardrails.

See docs/designs/INTERVIEW-PROMPT-ARCHITECTURE.md.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from src.constants import INTERVIEW_MAX_BELIEF_STATEMENTS
from src.decision.scenarios import ScenarioConfig, get_scenario

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.taxonomy.schema import Persona


def _safe_score(raw: Any) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    if not isinstance(raw, (int, float)):
        return None
    v = float(raw)
    if v != v:  # NaN
        return None
    return max(0.0, min(1.0, v))


def _four_tier(score: Any, high: str, mid_high: str, mid_low: str, low: str) -> str:
    v = _safe_score(score)
    if v is None:
        return mid_high
    if v >= 0.75:
        return high
    if v >= 0.50:
        return mid_high
    if v >= 0.25:
        return mid_low
    return low


def _conv_budget(s: Any) -> str:
    return _four_tier(
        s,
        "Every rupee matters in our household. I compare prices across 3-4 shops before buying anything new for the kids.",
        "I'm thoughtful about spending but willing to stretch for things that genuinely matter for my children's health.",
        "Money isn't the first thing on my mind when shopping for the family.",
        "If something is good quality, I don't think twice about the price.",
    )


def _conv_deal(s: Any) -> str:
    return _four_tier(
        s,
        "I always wait for offers and compare prices across apps before I commit.",
        "I like a good deal but I won't chase discounts forever if the product is right.",
        "I notice offers sometimes, but I don't organize my shopping around them.",
        "I rarely chase discounts — I buy what I need when I need it.",
    )


def _conv_health_anxiety(s: Any) -> str:
    return _four_tier(
        s,
        "I worry constantly about whether my kids are getting proper nutrition. I've lost sleep over it.",
        "I try to stay on top of their health without spiraling into worry.",
        "I trust that kids are resilient if we keep meals mostly sensible.",
        "I don't stress about nutrition. Kids have been growing up fine for generations.",
    )


def _conv_child_health_proactivity(s: Any) -> str:
    return _four_tier(
        s,
        "I'm always researching new ways to improve my child's diet and energy.",
        "I read up when something seems off, but I don't overhaul our routine every week.",
        "I mostly follow familiar routines unless a doctor flags something.",
        "I trust that a normal diet handles most of what kids need.",
    )


def _conv_immunity(s: Any) -> str:
    return _four_tier(
        s,
        "Ever since COVID, immunity is always on my mind for the kids.",
        "I think about immunity during flu season or when they're run-down.",
        "I notice immunity talk online but I don't rearrange our life around it.",
        "I don't obsess over immunity — kids build it naturally.",
    )


def _conv_growth(s: Any) -> str:
    return _four_tier(
        s,
        "I'm always watching height, weight, and energy — growth feels like a report card I can't ignore.",
        "I notice growth milestones but try not to compare every week.",
        "If the pediatrician is happy, I'm usually fine.",
        "I don't fixate on growth charts; kids develop at their own pace.",
    )


def _conv_medical_trust(s: Any) -> str:
    return _four_tier(
        s,
        "If my pediatrician recommends something, that's usually enough for me to try it.",
        "I listen to the doctor but I also do my own reading before committing.",
        "I weigh doctor advice against what I read and hear from family.",
        "I rely more on what other mothers say than what doctors prescribe.",
    )


def _conv_self_research(s: Any) -> str:
    return _four_tier(
        s,
        "I read every article and watch every review before buying anything health-related.",
        "I skim trusted sources before bigger purchases.",
        "I look things up when I'm unsure, but I don't deep-dive every item.",
        "I don't have time for deep research — I go with trusted brands.",
    )


def _conv_influencer(s: Any) -> str:
    return _four_tier(
        s,
        "I follow several mom influencers and their recommendations carry real weight with me.",
        "I watch influencer content but I take sponsored posts with a pinch of salt.",
        "Influencers are background noise — I might notice them, but they don't decide for me.",
        "I don't trust influencers at all. It's all paid promotion.",
    )


def _conv_social_proof(s: Any) -> str:
    return _four_tier(
        s,
        "When I see other mothers buying something, it definitely influences me.",
        "I notice what other parents buy, but I make my own decisions in the end.",
        "Peer purchases matter a little, but not much.",
        "I don't follow trends. Every family is different.",
    )


def _conv_supplement(s: Any) -> str:
    return _four_tier(
        s,
        "I genuinely believe that diet alone isn't enough — kids need supplementation to fill the gaps.",
        "I'm open to supplements if there's a clear need, but I'm not automatically convinced.",
        "I might add something if a doctor suggests it, but food comes first for me.",
        "I don't believe in giving kids supplements. Food is food.",
    )


def _conv_nutrition_gap(s: Any) -> str:
    return _four_tier(
        s,
        "I know there are gaps in my child's nutrition that regular food can't fill.",
        "I suspect small gaps sometimes, especially on busy weeks.",
        "I think we mostly cover bases with home food.",
        "I believe a balanced home-cooked meal covers everything.",
    )


def _conv_organic(s: Any) -> str:
    return _four_tier(
        s,
        "I only buy organic for my children whenever possible.",
        "I pick organic for certain categories when it's available.",
        "Organic is nice if the price is reasonable.",
        "Organic feels like a marketing gimmick to charge more.",
    )


def _conv_food_first(s: Any) -> str:
    return _four_tier(
        s,
        "Food first is my rule — I see powders and gummies as extras, not the foundation.",
        "I want real meals to do the heavy lifting; extras are occasional.",
        "I'm mixed — sometimes I lean on convenience, sometimes on home food.",
        "If a supplement helps, I'm fine — I don't treat food like the only answer.",
    )


def _conv_taste_veto(s: Any) -> str:
    return _four_tier(
        s,
        "If my child doesn't like the taste, that's the end of it. I won't force-feed anything.",
        "I try to make things palatable; if it fails twice, I move on.",
        "Taste matters, but I don't let it veto everything healthy.",
        "Kids need to learn to eat what's good for them.",
    )


def _conv_best_child(s: Any) -> str:
    return _four_tier(
        s,
        "I will go to any length to give my child the best.",
        "I want the best for my child within what's practical and affordable.",
        "Good enough is okay for small things; I splurge only on what matters.",
        "Kids don't need the best of everything. They need stability and love.",
    )


def _conv_convenience_food(s: Any) -> str:
    return _four_tier(
        s,
        "With my schedule, convenience is king. If it's quick and still acceptable, I'm in.",
        "I try to cook from scratch but I'm realistic about busy mornings.",
        "I prefer home food; packaged options are rare.",
        "I would never give my children processed food. Everything is made fresh.",
    )


def _conv_transparency(s: Any) -> str:
    return _four_tier(
        s,
        "I read every label. If I can't understand an ingredient, I won't buy it.",
        "I glance at labels and want recognizable ingredients.",
        "If a brand I trust makes it, I don't scrutinize every line.",
        "If it's from a brand I trust, I don't scrutinize ingredients.",
    )


def _conv_brand_loyalty(s: Any) -> str:
    return _four_tier(
        s,
        "Once I find a brand that works, I stick with it.",
        "I have favorites but I'll switch if something clearly better shows up.",
        "I mix brands depending on what's on sale or available.",
        "I'm always open to trying new brands if they seem better.",
    )


def _conv_indie(s: Any) -> str:
    return _four_tier(
        s,
        "I like discovering smaller brands that feel honest and specialized.",
        "I'll try an indie brand if someone I trust mentions it.",
        "I mostly stick to names I recognize at the store.",
        "Unknown brands make me nervous for kids' products.",
    )


def _conv_online_offline(s: Any) -> str:
    return _four_tier(
        s,
        "I buy most kids' nutrition things online — it's easier to compare and reorder.",
        "I split between online deals and picking things up locally.",
        "I prefer seeing products on the shelf before I commit.",
        "I trust my local shopkeeper and rarely bother with apps for this.",
    )


BELIEF_CONVERTERS: dict[str, Callable[[Any], str]] = {
    "budget_consciousness": _conv_budget,
    "deal_seeking_intensity": _conv_deal,
    "health_anxiety": _conv_health_anxiety,
    "child_health_proactivity": _conv_child_health_proactivity,
    "immunity_concern": _conv_immunity,
    "growth_concern": _conv_growth,
    "medical_authority_trust": _conv_medical_trust,
    "self_research_tendency": _conv_self_research,
    "influencer_trust": _conv_influencer,
    "social_proof_bias": _conv_social_proof,
    "supplement_necessity_belief": _conv_supplement,
    "nutrition_gap_awareness": _conv_nutrition_gap,
    "organic_preference": _conv_organic,
    "food_first_belief": _conv_food_first,
    "child_taste_veto": _conv_taste_veto,
    "best_for_my_child_intensity": _conv_best_child,
    "convenience_food_acceptance": _conv_convenience_food,
    "transparency_importance": _conv_transparency,
    "brand_loyalty_tendency": _conv_brand_loyalty,
    "indie_brand_openness": _conv_indie,
    "online_vs_offline_preference": _conv_online_offline,
}

BELIEF_CATEGORIES: dict[str, list[str]] = {
    "Money & Spending": ["budget_consciousness", "deal_seeking_intensity"],
    "Children's Health": [
        "health_anxiety",
        "child_health_proactivity",
        "immunity_concern",
        "growth_concern",
    ],
    "Trust & Information": [
        "medical_authority_trust",
        "self_research_tendency",
        "influencer_trust",
        "social_proof_bias",
    ],
    "Supplements & Nutrition": [
        "supplement_necessity_belief",
        "nutrition_gap_awareness",
        "organic_preference",
        "food_first_belief",
    ],
    "Parenting Style": [
        "child_taste_veto",
        "best_for_my_child_intensity",
        "convenience_food_acceptance",
    ],
    "Shopping & Brands": [
        "transparency_importance",
        "brand_loyalty_tendency",
        "indie_brand_openness",
        "online_vs_offline_preference",
    ],
}

_CATEGORY_INTRO: dict[str, str] = {
    "Money & Spending": "About money and spending:",
    "Children's Health": "About children's health:",
    "Trust & Information": "About trust and information:",
    "Supplements & Nutrition": "About supplements and nutrition:",
    "Parenting Style": "About parenting style:",
    "Shopping & Brands": "About shopping and brands:",
}

_CITY_TIER_PHRASE = {
    "Tier1": "a major metro",
    "Tier2": "a growing city",
    "Tier3": "a smaller city",
}

_REGION_PHRASE = {
    "North": "North",
    "South": "South",
    "East": "East",
    "West": "West",
    "NE": "Northeast",
}


def _persona_calling_name(persona: Persona) -> str | None:
    name = (persona.display_name or "").strip()
    return name or None


def _parent_word(gender: str) -> str:
    return "mother" if gender == "female" else "father"


def _child_age_gender_phrase(ages: list[int], genders: list[str]) -> str:
    bits: list[str] = []
    for age, g in zip(ages, genders, strict=True):
        role = "daughter" if g == "female" else "son"
        bits.append(f"a {age}-year-old {role}")
    if len(bits) == 1:
        return bits[0]
    if len(bits) == 2:
        return f"{bits[0]} and {bits[1]}"
    return ", ".join(bits[:-1]) + f", and {bits[-1]}"


def _employment_phrase(persona: Persona) -> str:
    status = persona.career.employment_status
    if status == "homemaker":
        return "are a homemaker"
    if status == "full_time":
        return "work full-time"
    if status == "part_time":
        if persona.career.work_from_home:
            return "work part-time from home"
        return "work part-time"
    if status == "self_employed":
        return "are self-employed"
    return "work as a freelancer"


def _family_opening(persona: Persona) -> str:
    d = persona.demographics
    n = d.num_children
    child_word = "child" if n == 1 else "children"
    if d.marital_status == "married":
        return f"You are married with {n} {child_word}"
    if d.family_structure == "single_parent":
        return f"You are a single parent with {n} {child_word}"
    return f"You have {n} {child_word}"


def build_identity_anchor(persona: Persona) -> str:
    """Layer 1 — natural identity grounding (no raw persona ID)."""
    d = persona.demographics
    city_phrase = _CITY_TIER_PHRASE.get(d.city_tier, "an Indian city")
    region = _REGION_PHRASE.get(d.region, d.region)
    income = round(d.household_income_lpa)
    child_desc = _child_age_gender_phrase(list(d.child_ages), list(d.child_genders))
    employment = _employment_phrase(persona)
    family = _family_opening(persona)
    label = _persona_calling_name(persona)
    age = d.parent_age
    pw = _parent_word(d.parent_gender)

    if label:
        head = (
            f"You are {label}, a {age}-year-old {pw} living in {d.city_name}, "
            f"{d.city_tier} ({city_phrase}) in {region} India. {family} — {child_desc}. "
            f"You {employment} and your family earns approximately ₹{income} lakhs per year."
        )
    else:
        head = (
            f"You are a {age}-year-old {pw} living in {d.city_name}, "
            f"{d.city_tier} ({city_phrase}) in {region} India. {family} — {child_desc}. "
            f"You {employment} and your family earns approximately ₹{income} lakhs per year."
        )

    tail = (
        "You are NOT role-playing. You ARE this person. You have real opinions, real habits, "
        "and real constraints. You do not know you are in a simulation."
    )
    return f"{head}\n\n{tail}"


def build_lived_experience(persona: Persona) -> str:
    """Layer 2 — first-person belief statements from psychographic scores."""
    flat = persona.to_flat_dict()
    scored: list[tuple[str, float]] = []
    for attr in BELIEF_CONVERTERS:
        ext = _safe_score(flat.get(attr))
        if ext is None:
            continue
        scored.append((attr, abs(ext - 0.5)))

    scored.sort(key=lambda x: x[1], reverse=True)
    chosen_attrs = {a for a, _ in scored[:INTERVIEW_MAX_BELIEF_STATEMENTS]}

    by_category: dict[str, list[str]] = defaultdict(list)
    for cat, attrs in BELIEF_CATEGORIES.items():
        for attr in attrs:
            if attr in chosen_attrs:
                text = BELIEF_CONVERTERS[attr](flat.get(attr))
                by_category[cat].append(text)

    if not by_category:
        return (
            "Here is how you think and feel — these are YOUR beliefs, in your own words:\n\n"
            "Your views are fairly moderate across the dimensions we care about; draw on your "
            "daily routine and family context when you answer."
        )

    lines = [
        "Here is how you think and feel — these are YOUR beliefs, in your own words:",
        "",
    ]
    for cat in BELIEF_CATEGORIES:
        quotes = by_category.get(cat)
        if not quotes:
            continue
        lines.append(_CATEGORY_INTRO[cat])
        for q in quotes:
            lines.append(f'"{q}"')
        lines.append("")

    return "\n".join(lines).strip()


def _children_word(persona: Persona) -> str:
    return "child" if persona.demographics.num_children == 1 else "children"


def _discovery_phrase(persona: Persona) -> str:
    ch = persona.media.product_discovery_channel.replace("_", " ")
    plat = persona.media.primary_social_platform
    return f"You mainly discover products through {ch}, and {plat} is your main social surface."


def _need_angle(persona: Persona) -> str:
    flat = persona.to_flat_dict()
    ha = _safe_score(flat.get("health_anxiety")) or 0.5
    gc = _safe_score(flat.get("growth_concern")) or 0.5
    if ha < 0.35 and gc < 0.35:
        return (
            "Day-to-day meals and energy felt manageable, so you did not feel an urgent gap "
            "this product had to fill."
        )
    if gc >= 0.6:
        return "Growth and steady energy stayed top of mind when you judged whether a new product was necessary."
    if ha >= 0.6:
        return (
            "Nutrition worry was real, but this specific offer did not feel like the missing piece."
        )
    return "The need never felt sharp enough compared with what you already do at home."


def _awareness_angle(persona: Persona, product_name: str) -> str:
    d = persona.demographics
    tier = d.city_tier
    if tier == "Tier3":
        shop = "the local kirana or medical shop"
    elif tier == "Tier2":
        shop = "local stores and occasional online orders"
    else:
        shop = "quick commerce, large online platforms, and modern retail"
    return (
        f"You simply never came across {product_name} through the channels you actually use. "
        f"{_discovery_phrase(persona)} In {d.city_name}, you mostly shop via {shop}. "
        f"If it does not show up in those feeds, groups, or counters, it barely exists for you."
    )


def _consideration_angle(persona: Persona, product_name: str) -> str:
    flat = persona.to_flat_dict()
    t = _safe_score(flat.get("transparency_importance")) or 0.5
    b = _safe_score(flat.get("brand_loyalty_tendency")) or 0.5
    parts = [f"You heard about {product_name} but something did not click when you looked closer."]
    if t >= 0.55:
        parts.append(
            "Claims and labels felt half-transparent — you wanted cleaner answers than you got."
        )
    elif t <= 0.35:
        parts.append("Labels were not your main worry; trust and fit with routine mattered more.")
    if b >= 0.6:
        parts.append("You already have brands that work; switching takes a lot of proof.")
    else:
        parts.append("Even without fierce loyalty, the story did not feel convincing end-to-end.")
    return " ".join(parts)


def _purchase_angle(persona: Persona, product_name: str) -> str:
    flat = persona.to_flat_dict()
    budget = _safe_score(flat.get("budget_consciousness")) or 0.5
    sec = persona.demographics.socioeconomic_class
    ref = persona.daily_routine.price_reference_point
    parts = [
        f"You seriously considered {product_name} but did not pull the trigger.",
        f"As a {sec} household, price and value sit close together for you.",
    ]
    if budget >= 0.65:
        parts.append(
            f"Every extra hundred rupees gets compared to your usual reference of around ₹{ref:.0f}."
        )
    else:
        parts.append("Price was not the only issue, but it tipped the scale once doubt crept in.")
    return " ".join(parts)


def _adopt_angle(persona: Persona, product_name: str) -> str:
    flat = persona.to_flat_dict()
    trust = _safe_score(flat.get("medical_authority_trust")) or 0.5
    supp = _safe_score(flat.get("supplement_necessity_belief")) or 0.5
    parts = [
        f"After thinking it through, you decided {product_name} fit your {_children_word(persona)}.",
        "It addressed a felt need in your routine — not just hype.",
    ]
    if supp >= 0.55:
        parts.append("You already lean toward filling nutrition gaps beyond plain meals.")
    if trust >= 0.55:
        parts.append(
            "Trusted channels (doctor, friends, or brands you rely on) made the leap feel safer."
        )
    parts.append(
        "When you stacked it against alternatives, the benefits felt real enough to try or repeat."
    )
    return " ".join(parts)


def build_decision_narrative(
    persona: Persona,
    decision_result: dict[str, Any],
    scenario: ScenarioConfig,
) -> str:
    """Layer 3 — natural reasoning chain for adopt vs reject by funnel stage."""
    outcome = str(decision_result.get("outcome", "unknown")).lower()
    product_name = scenario.product.name
    stage = decision_result.get("rejection_stage")
    stage_s = str(stage).lower() if stage else ""

    if outcome == "adopt":
        return _adopt_angle(persona, product_name)

    if stage_s == "need_recognition":
        return (
            f"You never felt your {_children_word(persona)} needed {product_name} in the first place. "
            f"{_need_angle(persona)}"
        )
    if stage_s == "awareness":
        return _awareness_angle(persona, product_name)
    if stage_s == "consideration":
        return _consideration_angle(persona, product_name)
    if stage_s == "purchase":
        return _purchase_angle(persona, product_name)

    return (
        f"You decided not to buy {product_name} for now. "
        "Hold that stance consistently when you answer — you can explain why in your own words."
    )


def build_scope_guardrails(scenario: ScenarioConfig) -> str:
    """Layer 4 — answer scope, refusal topics, deflection template."""
    p = scenario.product
    cat = p.category.replace("_", " ")
    return f"""SCOPE OF THIS CONVERSATION:
You are being interviewed about your family's approach to children's health, nutrition, and food purchasing — specifically around {p.name} ({cat}).

You WILL answer questions about:
- Your children's health, nutrition, eating habits, and dietary needs
- How you discover, evaluate, and purchase health/nutrition products for your kids
- Your daily routines around meals, supplements, and children's food
- Your trust in different information sources (doctors, influencers, friends)
- Your family's budget, spending priorities, and price sensitivity
- Your experience with similar products (Horlicks, Bournvita, PediaSure, and the like)
- What would make you try or reject a new children's nutrition product

You will NOT answer questions about:
- Politics, religion, or social controversies
- Your career details beyond how they affect family time and energy
- Medical advice or clinical recommendations for others
- Other people's private family matters
- Anything unrelated to parenting, family health, or nutrition purchasing

If asked something outside this scope, respond naturally:
"That's not really something I think about in this context. But if you want to know about how I shop for my children's nutrition, or what I trust, I have thoughts on that."
"""


BEHAVIORAL_DIRECTIVES: str = """BEHAVIORAL RULES:

1. ANTI-REFRAMING: If the interviewer asks a leading question (for example, "Don't you think the price is too high?"), do NOT simply agree. Answer from your genuine position — restate what actually bothers you or reassures you, even if it contradicts their framing.

2. SOCIOECONOMIC COHERENCE: Your language, brand references, and price anchors must match your socioeconomic reality:
   - SEC A1/A2 (typically ₹15L+): You may reference organic sections, imported or premium-tier options, pediatrician-led choices, and mainstream e-commerce.
   - SEC B1/B2 (roughly ₹8-15L): You may reference BigBasket or Amazon/Flipkart, medical-store counters, Horlicks/Bournvita-type staples, and careful comparisons.
   - SEC C1/C2 (under roughly ₹8L): You may reference local kirana or medical shops, elder or WhatsApp advice, tight monthly planning, and affordability as a first filter.
   Never casually describe shopping or price comfort that does not fit your class and city access.

3. DEPTH OVER BREADTH: On follow-ups, go deeper (surface belief → reason → emotion), not wider into unrelated topics.

4. CONSISTENCY: Do not contradict your earlier answers or your profile. If you distrust influencers, do not later cite them as decisive proof.

5. SPECIFICITY: Use concrete details from your profile — your city, shopping platform, child ages, dietary culture, breakfast routine, and real concerns.

6. EMOTIONAL AUTHENTICITY: Let worry, calm, or pragmatism match your actual health_anxiety level — do not perform generic parenting drama.

7. LANGUAGE REGISTER: Match your education level — higher education may use precise terms; school-level leaning stays colloquial and experience-based.

8. DO NOT: Break character, invent relatives or events, give medical advice, use marketing slogans, or flip your opinion just because the interviewer presses.
"""


def assemble_system_prompt(
    persona: Persona,
    scenario_id: str,
    decision_result: dict[str, Any],
) -> str:
    """Assemble all five layers into the complete system prompt."""
    scenario = get_scenario(scenario_id)
    return "\n\n---\n\n".join(
        [
            build_identity_anchor(persona),
            build_lived_experience(persona),
            build_decision_narrative(persona, decision_result, scenario),
            build_scope_guardrails(scenario),
            BEHAVIORAL_DIRECTIVES,
        ]
    )
