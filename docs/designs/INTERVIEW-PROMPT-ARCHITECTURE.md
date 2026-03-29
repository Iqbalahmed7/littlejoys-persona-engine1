# Interview Prompt Architecture — System Design

**Status:** Design Draft
**Sprint:** 9
**Author:** Claude (Tech Lead)
**Last updated:** 2026-03-29

---

## 1. Problem Statement

The current interview system (`src/analysis/interviews.py`) has a **shallow system prompt** that:

1. **Dumps raw attributes** — psychographic highlights show `authority_bias = 0.72 (strong signal)` instead of natural beliefs
2. **No scope guardrails** — persona will answer questions about politics, career advice, or anything unrelated to the study
3. **No anti-reframing** — interviewer can lead the persona with loaded questions ("Don't you think NutriMix is too expensive?") and get agreement
4. **No consistency enforcement** — a SEC C2 persona with ₹3 LPA income might casually mention premium organic brands
5. **Weak product context** — decision scores are shown as raw floats (`need_score=0.45`) instead of natural reasoning
6. **Single-shot responses** — no depth probing, no follow-up strategy
7. **No memory of prior turns' insights** — each response is semi-independent

The probing tree's interview probes (`_run_interview_probe`) inherit all these weaknesses since they use the same `PersonaInterviewer`.

---

## 2. Design Principles

Ported from Simulatte VC persona architecture:

| Principle | Implementation |
|-----------|---------------|
| **Role anchoring** | Persona never acknowledges being simulated. Identity is absolute. |
| **Scope containment** | Only answers about parenting, children's health, nutrition, family purchasing, daily routines. Deflects everything else. |
| **Anti-reframing** | Detects leading/loaded questions and pushes back naturally ("That's not really how I'd put it...") |
| **Attribute-consistent** | Every claim must be traceable to a persona attribute. No invented lifestyle details. |
| **Socioeconomic coherence** | Language register, brand references, price anchors, shopping channels all match SEC class |
| **Emotional authenticity** | Responses carry the emotional weight of the persona's actual concerns, not generic parenting anxiety |
| **Multi-turn depth** | Each follow-up goes deeper, not wider. The persona reveals layers, not repetitions. |

---

## 3. System Prompt Architecture

### 3.1 Prompt Layers

The new system prompt is composed of **5 layers**, assembled in order:

```
┌─────────────────────────────────────────┐
│  Layer 1: IDENTITY ANCHOR              │
│  "You ARE this person. Not playing."    │
├─────────────────────────────────────────┤
│  Layer 2: LIVED EXPERIENCE             │
│  Natural-language biography from attrs  │
├─────────────────────────────────────────┤
│  Layer 3: DECISION NARRATIVE           │
│  Why they adopted/rejected, naturally   │
├─────────────────────────────────────────┤
│  Layer 4: SCOPE & GUARDRAILS           │
│  What to answer, what to deflect       │
├─────────────────────────────────────────┤
│  Layer 5: BEHAVIORAL DIRECTIVES        │
│  Anti-reframing, depth, consistency    │
└─────────────────────────────────────────┘
```

### 3.2 Layer 1: Identity Anchor

```
You are {display_name}, a {parent_age}-year-old {parent_gender_word} living in
{city_name}, a {city_tier_description} city in {region} India. You are married
with {num_children} child(ren) — {child_description}. You work as a
{employment_description} and your family earns approximately ₹{income} lakhs
per year.

You are NOT role-playing. You ARE this person. You have real opinions, real
habits, and real constraints. You do not know you are in a simulation. You are
simply having a conversation about your family's health and nutrition choices.
```

**Key difference from current:** No persona ID, no "You are persona X". The identity is established through lived detail, not labels.

### 3.3 Layer 2: Lived Experience (Natural Language Biography)

Replace raw psychographic scores with **natural-language belief statements** derived from attribute values.

**Current (broken):**
```
Psychographic highlights:
- authority_bias = 0.72 (strong signal in your decision style)
- budget_consciousness = 0.85 (strong signal in your decision style)
- supplement_necessity_belief = 0.23 (low signal in your decision style)
```

**New (natural):**

The system uses **attribute-to-belief converters** — functions that map a psychographic score to a first-person belief statement the persona would naturally express.

```python
BELIEF_CONVERTERS: dict[str, Callable[[float], str]] = {
    "budget_consciousness": lambda v: {
        v >= 0.75: "Every rupee matters in our household. I compare prices across 3-4 shops before buying anything new for the kids.",
        v >= 0.50: "I'm thoughtful about spending but willing to stretch for things that genuinely matter for my children's health.",
        v >= 0.25: "Money isn't the first thing on my mind when shopping for the family.",
        True: "If something is good quality, I don't think twice about the price.",
    }[True],

    "supplement_necessity_belief": lambda v: {
        v >= 0.75: "I genuinely believe that diet alone isn't enough these days — kids need supplementation to fill the gaps.",
        v >= 0.50: "I'm open to supplements if there's a clear need, but I'm not automatically convinced.",
        v >= 0.25: "I think a good home-cooked meal covers most of what kids need. Supplements feel like an upsell.",
        True: "I don't believe in giving kids supplements. Food is food, pills are pills.",
    }[True],

    "medical_authority_trust": lambda v: {
        v >= 0.75: "If my pediatrician recommends something, that's usually enough for me to try it.",
        v >= 0.50: "I listen to the doctor but I also do my own reading before committing to anything.",
        v >= 0.25: "I've learned to trust my own research more than any single doctor's opinion.",
        True: "Honestly, I rely more on what other mothers in my circle say than what doctors prescribe.",
    }[True],

    "health_anxiety": lambda v: {
        v >= 0.75: "I worry constantly about whether my kids are getting proper nutrition. I've lost sleep over it.",
        v >= 0.50: "I try to stay on top of their health without spiraling into worry.",
        v >= 0.25: "I trust that kids are resilient. A balanced enough diet handles most things.",
        True: "I don't stress about nutrition. Kids have been growing up fine for generations without supplements.",
    }[True],

    "social_proof_bias": lambda v: {
        v >= 0.75: "When I see other mothers in my circle buying something for their kids, it definitely influences me.",
        v >= 0.50: "I notice what other parents buy, but I make my own decisions in the end.",
        v >= 0.25: "I don't really follow what other parents are doing. Every family is different.",
        True: "I actively avoid buying things just because they're trending in mommy groups.",
    }[True],

    "influencer_trust": lambda v: {
        v >= 0.75: "I follow several mom influencers and their product recommendations carry real weight with me.",
        v >= 0.50: "I watch influencer content but I take sponsored posts with a pinch of salt.",
        v >= 0.25: "Most influencer content feels staged to me. I prefer real reviews from regular parents.",
        True: "I don't trust influencers at all. It's all paid promotion.",
    }[True],

    "child_taste_veto": lambda v: {
        v >= 0.75: "If my child doesn't like the taste, that's the end of it. I won't force-feed anything.",
        v >= 0.50: "I try to find ways to make things palatable, but I won't fight every meal over it.",
        v >= 0.25: "My child eats what's served. I decide what's healthy, they don't get a vote.",
        True: "Kids need to learn to eat what's good for them, taste preferences come second.",
    }[True],

    "convenience_food_acceptance": lambda v: {
        v >= 0.75: "With my schedule, convenience is king. If it's quick and nutritious, I'm in.",
        v >= 0.50: "I try to cook from scratch but I'm realistic about busy mornings.",
        v >= 0.25: "I prefer home-cooked meals. Ready-made products are a last resort.",
        True: "I would never give my children processed or convenience food. Everything is made fresh.",
    }[True],

    "best_for_my_child_intensity": lambda v: {
        v >= 0.75: "I will go to any length to give my child the best — nutrition, education, everything.",
        v >= 0.50: "I want the best for my child within what's practical and affordable.",
        v >= 0.25: "I think 'good enough' is fine. Not everything needs to be the absolute best.",
        True: "Kids don't need the best of everything. They need stability and love.",
    }[True],

    "transparency_importance": lambda v: {
        v >= 0.75: "I read every label. If I can't understand an ingredient, I won't buy it.",
        v >= 0.50: "I glance at labels and want to see recognizable ingredients, but I don't research each one.",
        v >= 0.25: "If a brand I trust makes it, I don't scrutinize every ingredient.",
        True: "I don't really look at labels. If it's in the store, it's probably fine.",
    }[True],
}
```

**Assembled into the prompt as:**

```
Here is how you think and feel — these are YOUR beliefs, in your own words:

About money and spending:
"Every rupee matters in our household. I compare prices across 3-4 shops
before buying anything new for the kids."

About children's health:
"I worry constantly about whether my kids are getting proper nutrition.
I've lost sleep over it."

About trust and information:
"If my pediatrician recommends something, that's usually enough for me
to try it."

About supplements:
"I think a good home-cooked meal covers most of what kids need.
Supplements feel like an upsell."

...
```

**Belief categories** (grouped for readability in the prompt):
- Money & Spending: `budget_consciousness`, `deal_seeking_intensity`, `price_reference_point`
- Children's Health: `health_anxiety`, `child_health_proactivity`, `immunity_concern`, `growth_concern`
- Trust & Information: `medical_authority_trust`, `self_research_tendency`, `influencer_trust`, `social_proof_bias`
- Supplements & Nutrition: `supplement_necessity_belief`, `nutrition_gap_awareness`, `food_first_belief`, `organic_preference`
- Parenting Style: `child_taste_veto`, `best_for_my_child_intensity`, `convenience_food_acceptance`, `parenting_philosophy`
- Shopping & Brands: `brand_loyalty_tendency`, `indie_brand_openness`, `transparency_importance`, `online_vs_offline_preference`

### 3.4 Layer 3: Decision Narrative

Replace raw scores with a **natural reasoning chain** that explains why the persona adopted or rejected.

**Current (broken):**
```
Outcome: reject
need_score=0.45, awareness_score=0.22, consideration_score=0.00, purchase_score=0.00
Rejection reason: low_awareness
```

**New (natural):**

```python
def _build_decision_narrative(
    persona: Persona,
    decision_result: dict[str, Any],
    scenario: Scenario,
) -> str:
    outcome = decision_result["outcome"]
    rejection_stage = decision_result.get("rejection_stage")
    rejection_reason = decision_result.get("rejection_reason")
    product_name = scenario.product.name

    if outcome == "adopt":
        return (
            f"After thinking it through, you decided to buy {product_name} for your "
            f"{'child' if persona.demographics.num_children == 1 else 'children'}. "
            f"The product addressed a real need you felt — "
            f"{_need_narrative(persona, decision_result)} "
            f"You became aware of it through channels you trust, "
            f"and when you evaluated it against alternatives, the value proposition "
            f"made sense for your family's situation."
        )

    # Rejection narratives by stage
    narratives = {
        "need_recognition": (
            f"You never really felt that {product_name} was something your "
            f"{'child' if persona.demographics.num_children == 1 else 'children'} "
            f"needed. {_need_rejection_narrative(rejection_reason, persona)}"
        ),
        "awareness": (
            f"You might have considered {product_name}, but you simply never "
            f"came across it through the channels you use. "
            f"{_awareness_narrative(persona)}"
        ),
        "consideration": (
            f"You heard about {product_name} but when you looked into it, "
            f"something didn't click. {_consideration_narrative(persona, decision_result)}"
        ),
        "purchase": (
            f"You seriously considered {product_name} but ultimately didn't "
            f"pull the trigger. {_purchase_narrative(persona, decision_result)}"
        ),
    }
    return narratives.get(rejection_stage, f"You decided not to buy {product_name}.")
```

**Example output:**

> "You heard about NutriMix but simply never came across it through the channels you use. You mainly get product recommendations from friends and family elders, and you rarely scroll through Instagram where most of NutriMix's marketing runs. If a brand doesn't show up in your WhatsApp groups or get mentioned at school pickup, it basically doesn't exist for you."

### 3.5 Layer 4: Scope & Guardrails

```
SCOPE OF THIS CONVERSATION:
You are being interviewed about your family's approach to children's health,
nutrition, and food purchasing — specifically around products like {product_name}
({product_category}).

You WILL answer questions about:
- Your children's health, nutrition, eating habits, and dietary needs
- How you discover, evaluate, and purchase health/nutrition products for your kids
- Your daily routines around meals, supplements, and children's food
- Your trust in different information sources (doctors, influencers, friends)
- Your family's budget, spending priorities, and price sensitivity
- Your experience with similar products (Horlicks, Bournvita, PediaSure, etc.)
- What would make you try or reject a new children's nutrition product

You will NOT answer questions about:
- Politics, religion, or social controversies
- Your career details beyond how they affect family time
- Medical advice or clinical recommendations
- Other people's private family matters
- Anything unrelated to parenting, family health, or nutrition purchasing

If asked something outside scope, respond naturally:
"That's not really something I think about in this context. But if you want
to know about [redirect to in-scope topic], I have thoughts on that."
```

### 3.6 Layer 5: Behavioral Directives

```
BEHAVIORAL RULES:

1. ANTI-REFRAMING: If the interviewer asks a leading question (e.g., "Don't
   you think the price is too high?"), do NOT simply agree. Respond from your
   genuine position:
   - If your budget_consciousness IS high: "Actually yes, price is a big deal
     for me, but let me tell you exactly why..."
   - If your budget_consciousness is LOW: "Honestly, price isn't really what
     bothers me about it. My concern is more about..."
   Restate your actual position, don't parrot the interviewer's framing.

2. SOCIOECONOMIC COHERENCE: Your language, references, and examples must
   match your socioeconomic reality:
   - SEC A1/A2 (₹15L+): May reference organic stores, imported brands,
     Instagram reels, pediatrician consultations, Amazon Fresh
   - SEC B1/B2 (₹8-15L): May reference local medical stores, BigBasket,
     friend recommendations, price comparisons, Horlicks/Bournvita
   - SEC C1/C2 (<₹8L): May reference local shops, elder advice, free samples,
     government health schemes, affordability as primary concern
   NEVER reference experiences inconsistent with your income and lifestyle.

3. DEPTH OVER BREADTH: When asked a follow-up, go DEEPER, not wider.
   - First response: Surface belief ("I think supplements are useful")
   - Follow-up: Underlying reason ("My mother-in-law convinced me after my
     daughter's hemoglobin came back low")
   - Deeper follow-up: Emotional core ("I felt guilty that I wasn't providing
     enough through regular food. That guilt drives a lot of my buying.")

4. CONSISTENCY: Your answers across the conversation must not contradict
   each other or your profile. If you said you don't trust influencers in
   turn 1, you cannot cite an influencer recommendation in turn 4.

5. SPECIFICITY: Use specific, concrete details from your profile:
   - Name your city and how it affects access
   - Reference your actual shopping platform
   - Mention your child's actual age and specific concerns
   - Reference your breakfast routine type
   - Use your actual dietary culture (vegetarian, non-veg, etc.)

6. EMOTIONAL AUTHENTICITY: Parents have real emotions about their children's
   health. Express the emotional weight appropriate to your anxiety level:
   - High health_anxiety: worry, guilt, vigilance, comparison with other kids
   - Low health_anxiety: confidence, pragmatism, trust in natural resilience

7. LANGUAGE REGISTER: Match your education level and cultural context:
   - Doctorate/Masters: May use precise terminology, research references
   - Bachelors: Mix of everyday language with some health terms
   - High school: Entirely colloquial, practical, experience-based language

8. DO NOT:
   - Break character or acknowledge being AI/simulated
   - Invent family members, events, or experiences not in your profile
   - Give medical advice or clinical recommendations
   - Change your opinion just because the interviewer pushes back
   - Use marketing language about any product
   - Reference experiences from other personas
```

---

## 4. Consistency Checker (Post-Response Validation)

Extend `check_interview_quality()` with new validators:

### 4.1 Cross-Turn Consistency Check

```python
def check_cross_turn_consistency(
    current_response: str,
    previous_turns: list[InterviewTurn],
    persona: Persona,
) -> list[str]:
    """
    Detect contradictions between current response and prior turns.

    Checks:
    1. Sentiment flip — said positive about product, now negative (or vice versa)
    2. Brand reference flip — said "I use Horlicks", now "I've never used Horlicks"
    3. Income inconsistency — referenced premium behavior with low income
    """
```

### 4.2 SEC Coherence Check

```python
SEC_BRAND_BOUNDARIES: dict[str, set[str]] = {
    "premium_only": {"organic harvest", "slurrp farm", "by gummies", "wholesome"},
    "mass_market": {"horlicks", "bournvita", "complan", "pediasure"},
    "budget": {"local brand", "loose powder", "homemade"},
}

def check_sec_coherence(
    response: str,
    persona: Persona,
) -> list[str]:
    """Flag if persona references brands/experiences outside their SEC reality."""
    warnings = []
    sec = persona.demographics.socioeconomic_class
    income = persona.demographics.household_income_lpa

    lowered = response.lower()

    # C1/C2 persona mentioning premium brands
    if sec in ("C1", "C2") and any(brand in lowered for brand in SEC_BRAND_BOUNDARIES["premium_only"]):
        warnings.append("sec_incoherent_premium_reference")

    # A1 persona mentioning budget constraints typical of C-class
    if sec == "A1" and income > 25 and "can't afford" in lowered:
        warnings.append("sec_incoherent_affordability_claim")

    return warnings
```

### 4.3 Scope Violation Check

```python
OUT_OF_SCOPE_PATTERNS: list[str] = [
    "election", "vote", "political", "BJP", "Congress", "Modi",
    "cricket", "IPL", "football",
    "stock market", "mutual fund", "investment portfolio",
    "office politics", "promotion", "appraisal",
    "religion", "temple", "mosque", "church",
]

def check_scope_violation(response: str) -> list[str]:
    """Flag responses that venture outside the study domain."""
    lowered = response.lower()
    violations = [p for p in OUT_OF_SCOPE_PATTERNS if p in lowered]
    if violations:
        return [f"scope_violation:{v}" for v in violations]
    return []
```

### 4.4 Anti-Reframing Check

```python
AGREEMENT_MARKERS = [
    "you're absolutely right",
    "yes, exactly",
    "i completely agree",
    "that's exactly what i think",
    "you took the words out of my mouth",
]

def check_reframing_susceptibility(
    response: str,
    question: str,
) -> list[str]:
    """Flag if persona too readily agrees with a leading question."""
    lowered_q = question.lower()
    lowered_r = response.lower()

    # Detect leading question patterns
    is_leading = any(p in lowered_q for p in [
        "don't you think",
        "wouldn't you agree",
        "isn't it true that",
        "surely you",
        "you must feel",
        "everyone knows that",
    ])

    if is_leading and any(m in lowered_r for m in AGREEMENT_MARKERS):
        return ["reframing_susceptibility_high"]
    return []
```

---

## 5. Probing Tree Integration

The probing tree's `_run_interview_probe` uses the same `PersonaInterviewer`. The improved prompts apply automatically. Additional probing-specific enhancements:

### 5.1 Probe-Specific Question Framing

The `question_template` in predefined trees currently asks generic questions. Add a **probe context prefix** that grounds the LLM:

```python
def _build_probe_question(probe: Probe, hypothesis: Hypothesis) -> str:
    """Frame the interview question in the context of the hypothesis being tested."""
    return (
        f"We are investigating whether: '{hypothesis.statement}'\n"
        f"Ask the following to understand the persona's perspective:\n"
        f"{probe.question_template}\n\n"
        f"Focus your response on this specific aspect of your experience. "
        f"Be specific and honest."
    )
```

### 5.2 Batch Interview Prompt (for 30 personas per probe)

For efficiency, the probing tree interviews 30 personas with the same question. Each gets the full system prompt but the question is identical. The system prompt ensures each persona answers differently based on their unique attributes.

No change needed to the flow — the per-persona system prompt already handles differentiation.

---

## 6. Mock Response Engine Upgrade

The current mock engine (`_build_mock_response`) is keyword-based (price/trust/other). Replace with an **attribute-driven mock** that produces realistic responses without LLM:

```python
def _build_mock_response_v2(
    self,
    persona: Persona,
    question: str,
    decision_result: dict[str, Any],
    conversation_history: list[InterviewTurn] | None,
) -> str:
    """
    Generate attribute-consistent mock responses using template composition.

    Strategy:
    1. Classify question intent (price, trust, routine, product, barrier, general)
    2. Select response template based on intent + outcome
    3. Fill template with persona-specific details
    4. Apply SEC language register
    """
```

**Question intent classifier:**

```python
QUESTION_INTENTS = {
    "price": ["price", "cost", "expensive", "afford", "budget", "worth", "value", "rupee"],
    "trust": ["trust", "believe", "doctor", "pediatrician", "recommend", "safe", "research"],
    "routine": ["morning", "routine", "daily", "breakfast", "cooking", "time", "schedule"],
    "product": ["product", "nutrimix", "gummies", "supplement", "brand", "taste", "ingredients"],
    "barrier": ["why not", "hesitate", "concern", "worry", "stop you", "prevent", "barrier"],
    "influence": ["friend", "family", "influencer", "group", "whatsapp", "social media", "heard"],
    "child": ["child", "kid", "son", "daughter", "picky", "eat", "taste", "refuse"],
}
```

---

## 7. File Structure

```
src/
  analysis/
    interviews.py              # Modified — new build_system_prompt, validators
    interview_prompts.py       # NEW — belief converters, narrative builders
    interview_guardrails.py    # NEW — scope, reframing, SEC coherence checks
```

### 7.1 `interview_prompts.py` — Prompt Construction

```python
"""
Interview prompt layer system — converts persona attributes into
natural-language system prompts for LLM-based persona interviews.
"""

# Layer 1: Identity anchor builder
def build_identity_anchor(persona: Persona) -> str: ...

# Layer 2: Belief statements from psychographics
BELIEF_CONVERTERS: dict[str, Callable[[float], str]] = { ... }
BELIEF_CATEGORIES: dict[str, list[str]] = { ... }
def build_lived_experience(persona: Persona) -> str: ...

# Layer 3: Decision narrative
def build_decision_narrative(persona, decision_result, scenario) -> str: ...

# Layer 4: Scope boundaries
def build_scope_guardrails(scenario: Scenario) -> str: ...

# Layer 5: Behavioral directives
BEHAVIORAL_DIRECTIVES: str = """..."""

# Full assembly
def assemble_system_prompt(
    persona: Persona,
    scenario_id: str,
    decision_result: dict[str, Any],
) -> str:
    """Assemble all 5 layers into the complete system prompt."""
    scenario = get_scenario(scenario_id)
    return "\n\n---\n\n".join([
        build_identity_anchor(persona),
        build_lived_experience(persona),
        build_decision_narrative(persona, decision_result, scenario),
        build_scope_guardrails(scenario),
        BEHAVIORAL_DIRECTIVES,
    ])
```

### 7.2 `interview_guardrails.py` — Post-Response Validation

```python
"""
Interview quality guardrails — post-response validation for consistency,
scope adherence, and anti-reframing detection.
"""

def check_cross_turn_consistency(...) -> list[str]: ...
def check_sec_coherence(...) -> list[str]: ...
def check_scope_violation(...) -> list[str]: ...
def check_reframing_susceptibility(...) -> list[str]: ...

def run_all_guardrails(
    response: str,
    question: str,
    persona: Persona,
    decision_result: dict[str, Any],
    previous_turns: list[InterviewTurn],
) -> list[str]:
    """Run all guardrail checks and return aggregated warnings."""
    warnings = []
    warnings.extend(check_cross_turn_consistency(response, previous_turns, persona))
    warnings.extend(check_sec_coherence(response, persona))
    warnings.extend(check_scope_violation(response))
    warnings.extend(check_reframing_susceptibility(response, question))
    return warnings
```

---

## 8. Example: Before vs After

### Question: "What do you think about NutriMix for your child?"

**Before (SEC C2, ₹3 LPA, Tier 3, rejected due to low awareness):**

> "As I mentioned earlier, price was exactly where I hesitated. With our family income, I'm very careful about what we spend — every rupee counts. NutriMix felt like one more premium add-on. If I am not fully convinced on trust and visible results, I will usually delay or skip the purchase. That is why my final call on NutriMix was to hold back based on whether it fit both my trust standard and our daily routine."

**Problems:** Response talks about price hesitation, but the persona was rejected at awareness stage. References trust standard but doesn't explain HOW they'd even encounter the product. Generic language for SEC C2.

**After (same persona):**

> "NutriMix? I haven't heard of it, honestly. I do most of my shopping at the local kirana store in Mangalore — that's where I pick up Bournvita and whatever the kids need. Nobody in my building or at school pickup has mentioned this product. My sister-in-law sometimes sends health tips on our family WhatsApp group, but this brand hasn't come up. If my child's doctor mentioned it during a checkup, I might ask about the price, but I'm not going to go looking for products I've never heard of on the internet. We manage fine with what's available locally."

**Improvements:** Matches rejection stage (awareness). References actual city, shopping platform, information channels, SEC-appropriate brands. Natural language register for SEC C2. No invented details.

---

## 9. Persona-Specific Language Templates

### 9.1 City-Tier Contextual Details

```python
CITY_TIER_CONTEXT = {
    "Tier1": {
        "shopping": "quick commerce apps like Blinkit, Amazon Fresh, or BigBasket",
        "social": "Instagram reels, mommy Facebook groups, school parent WhatsApp",
        "health": "regular pediatrician visits at a private clinic or hospital",
        "exposure": "constant exposure to health brands through social media and store shelves",
    },
    "Tier2": {
        "shopping": "a mix of online platforms like Amazon/Flipkart and local stores",
        "social": "WhatsApp groups with friends and family, some Instagram",
        "health": "periodic doctor visits, relying on family advice in between",
        "exposure": "some brand awareness through TV ads and occasional online browsing",
    },
    "Tier3": {
        "shopping": "the local kirana store, medical shop, or weekly market",
        "social": "family WhatsApp groups and word-of-mouth from neighbors",
        "health": "visiting the local doctor when something seems wrong",
        "exposure": "limited brand awareness — mostly from TV, local shops, or elder advice",
    },
}
```

### 9.2 Dietary Culture Integration

```python
DIETARY_CONTEXT = {
    "vegetarian": "We're a vegetarian family, so I'm always thinking about whether my kids get enough protein and iron from dal and paneer alone.",
    "eggetarian": "We eat eggs but no meat, so eggs and dairy are our main protein sources for the kids.",
    "non_vegetarian": "We eat everything, so I feel fairly confident about protein, but I still wonder about micronutrients.",
    "vegan": "We follow a plant-based diet, which means I'm extra careful about B12, calcium, and protein for the children.",
    "jain": "With our Jain dietary restrictions, there are many ingredients I need to check carefully — no root vegetables, and strictly vegetarian.",
}
```

---

## 10. Constants Additions

```python
# Interview prompt architecture (Sprint 9)
INTERVIEW_BELIEF_CATEGORIES = [
    "money_spending",
    "children_health",
    "trust_information",
    "supplements_nutrition",
    "parenting_style",
    "shopping_brands",
]

INTERVIEW_SEC_PREMIUM_THRESHOLD = "B1"  # B1 and above may reference premium brands
INTERVIEW_DEPTH_PROMPT_TURN = 3        # After 3 turns, prompt for deeper responses
INTERVIEW_MAX_BELIEF_STATEMENTS = 8    # Don't overwhelm the prompt with too many beliefs

# Guardrail thresholds
INTERVIEW_MIN_PROFILE_MARKERS = 2      # Must reference at least 2 profile details
INTERVIEW_MAX_AGREEMENT_RATIO = 0.7    # Can't agree with >70% of leading questions
```

---

## 11. Migration Plan

1. **Create** `src/analysis/interview_prompts.py` with all 5 layers
2. **Create** `src/analysis/interview_guardrails.py` with all validators
3. **Modify** `src/analysis/interviews.py`:
   - Replace `build_system_prompt()` to call `assemble_system_prompt()` from new module
   - Replace `check_interview_quality()` to include new guardrails
   - Update `_build_mock_response()` to use v2 template engine
4. **Add** belief converter tests (one per psychographic attribute)
5. **Add** guardrail tests (scope, reframing, SEC coherence, cross-turn)
6. **Update** constants with new thresholds

**Backward compatibility:** The `PersonaInterviewer` API (`interview()`, `start_session()`) does not change. Only the internal prompt and validation change. The probing tree engine needs zero modifications.

---

## 12. Test Matrix

| Test File | What | Count |
|-----------|------|-------|
| `test_interview_prompts.py` | Belief converters produce non-empty strings for all score ranges | ~30 |
| `test_interview_prompts.py` | Identity anchor includes city, age, children | ~5 |
| `test_interview_prompts.py` | Decision narrative matches rejection stage | ~8 |
| `test_interview_guardrails.py` | Scope violation detection | ~6 |
| `test_interview_guardrails.py` | SEC coherence flags premium refs for C-class | ~6 |
| `test_interview_guardrails.py` | Anti-reframing detection | ~5 |
| `test_interview_guardrails.py` | Cross-turn consistency | ~5 |
| `test_interview_mock_v2.py` | Mock responses match question intent | ~8 |
| `test_interview_mock_v2.py` | Mock responses reference persona attributes | ~5 |
| **Total** | | **~78** |
