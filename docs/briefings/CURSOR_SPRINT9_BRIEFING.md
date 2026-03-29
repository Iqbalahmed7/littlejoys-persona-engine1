# Cursor — Sprint 9 Track A: Interview Prompt System (5-Layer Architecture)

**Branch:** `sprint-9-track-a-interview-prompts`
**Base:** `main`

## Context

The persona interview system (`src/analysis/interviews.py`) has a shallow system prompt that dumps raw attribute scores, has no scope guardrails, and produces generic responses. Sprint 9 replaces it with a 5-layer prompt architecture that produces deep, persona-consistent, product-contextual interview responses.

**Design doc:** `docs/designs/INTERVIEW-PROMPT-ARCHITECTURE.md`

## Deliverables

### 1. Create `src/analysis/interview_prompts.py` (NEW)

This module builds the complete system prompt from 5 layers.

#### Layer 1: Identity Anchor

```python
def build_identity_anchor(persona: Persona) -> str:
```

Produces natural-language identity grounding. Example output:

> "You are Priya, a 32-year-old mother living in Mumbai, a Tier 1 metro in West India. You are married with 2 children — a 4-year-old daughter and a 7-year-old son. You work full-time and your family earns approximately ₹18 lakhs per year."

Rules:
- Use `display_name` or persona's `display_name` field, NOT the raw persona ID
- Map `parent_gender` to natural word ("mother"/"father")
- Describe children by count + ages from `child_ages`
- Map `employment_status` to natural phrase ("work full-time", "work part-time from home", "are a homemaker")
- Map `city_tier` to natural description: Tier1 → "a major metro", Tier2 → "a growing city", Tier3 → "a smaller city"
- End with: "You are NOT role-playing. You ARE this person. You have real opinions, real habits, and real constraints. You do not know you are in a simulation."

#### Layer 2: Lived Experience (Belief Converters)

```python
BELIEF_CONVERTERS: dict[str, Callable[[float], str]] = { ... }
BELIEF_CATEGORIES: dict[str, list[str]] = { ... }

def build_lived_experience(persona: Persona) -> str:
```

Convert psychographic scores (0.0-1.0) into first-person belief statements. Each converter maps a score to one of 4 natural-language tiers.

**Required converters (minimum 15):**

| Attribute | Category | High (≥0.75) example | Low (<0.25) example |
|-----------|----------|---------------------|---------------------|
| `budget_consciousness` | Money & Spending | "Every rupee matters in our household..." | "If something is good quality, I don't think twice about the price." |
| `deal_seeking_intensity` | Money & Spending | "I always wait for offers and compare prices across apps..." | "I rarely chase discounts — I buy what I need when I need it." |
| `health_anxiety` | Children's Health | "I worry constantly about whether my kids are getting proper nutrition..." | "I don't stress about nutrition. Kids have been growing up fine for generations." |
| `child_health_proactivity` | Children's Health | "I'm always researching new ways to improve my child's diet..." | "I trust that a normal diet handles most of what kids need." |
| `immunity_concern` | Children's Health | "Ever since COVID, immunity is always on my mind for the kids..." | "I don't obsess over immunity — kids build it naturally." |
| `medical_authority_trust` | Trust & Information | "If my pediatrician recommends something, that's usually enough for me..." | "I rely more on what other mothers say than what doctors prescribe." |
| `self_research_tendency` | Trust & Information | "I read every article and watch every review before buying anything health-related..." | "I don't have time for deep research — I go with trusted brands." |
| `influencer_trust` | Trust & Information | "I follow several mom influencers and their recommendations carry real weight..." | "I don't trust influencers at all. It's all paid promotion." |
| `social_proof_bias` | Trust & Information | "When I see other mothers buying something, it definitely influences me..." | "I don't follow trends. Every family is different." |
| `supplement_necessity_belief` | Supplements & Nutrition | "I genuinely believe that diet alone isn't enough — kids need supplementation..." | "I don't believe in giving kids supplements. Food is food." |
| `nutrition_gap_awareness` | Supplements & Nutrition | "I know there are gaps in my child's nutrition that regular food can't fill..." | "I believe a balanced home-cooked meal covers everything." |
| `organic_preference` | Supplements & Nutrition | "I only buy organic for my children whenever possible..." | "Organic feels like a marketing gimmick to charge more." |
| `child_taste_veto` | Parenting Style | "If my child doesn't like the taste, that's the end of it..." | "Kids need to learn to eat what's good for them." |
| `best_for_my_child_intensity` | Parenting Style | "I will go to any length to give my child the best..." | "Kids don't need the best of everything. They need stability and love." |
| `transparency_importance` | Shopping & Brands | "I read every label. If I can't understand an ingredient, I won't buy it..." | "If it's from a brand I trust, I don't scrutinize ingredients." |
| `brand_loyalty_tendency` | Shopping & Brands | "Once I find a brand that works, I stick with it..." | "I'm always open to trying new brands if they seem better." |
| `convenience_food_acceptance` | Parenting Style | "With my schedule, convenience is king..." | "I would never give my children processed food. Everything is made fresh." |

**Belief categories for prompt grouping:**

```python
BELIEF_CATEGORIES: dict[str, list[str]] = {
    "Money & Spending": ["budget_consciousness", "deal_seeking_intensity"],
    "Children's Health": ["health_anxiety", "child_health_proactivity", "immunity_concern", "growth_concern"],
    "Trust & Information": ["medical_authority_trust", "self_research_tendency", "influencer_trust", "social_proof_bias"],
    "Supplements & Nutrition": ["supplement_necessity_belief", "nutrition_gap_awareness", "organic_preference", "food_first_belief"],
    "Parenting Style": ["child_taste_veto", "best_for_my_child_intensity", "convenience_food_acceptance"],
    "Shopping & Brands": ["transparency_importance", "brand_loyalty_tendency", "indie_brand_openness", "online_vs_offline_preference"],
}
```

**Output format:**

```
Here is how you think and feel — these are YOUR beliefs, in your own words:

About money and spending:
"Every rupee matters in our household. I compare prices across 3-4 shops before buying anything new for the kids."

About children's health:
"I worry constantly about whether my kids are getting proper nutrition. I've lost sleep over it."

...
```

**Implementation:** Use `persona.to_flat_dict()` to get all scores, select the top `INTERVIEW_MAX_BELIEF_STATEMENTS` (8) most extreme beliefs (furthest from 0.5), grouped by category.

#### Layer 3: Decision Narrative

```python
def build_decision_narrative(
    persona: Persona,
    decision_result: dict[str, Any],
    scenario: Scenario,
) -> str:
```

Translate raw outcome + rejection stage into a natural reasoning chain.

**For adopters:** Explain why the product resonated — connect to persona's actual needs, trust sources, and shopping behavior.

**For rejectors by stage:**
- `need_recognition` → "You never felt your child needed this product." Connect to low `health_anxiety` or `growth_concern`.
- `awareness` → "You simply never came across this product through your usual channels." Connect to persona's `product_discovery_channel`, `primary_social_platform`, city tier.
- `consideration` → "You heard about it but something didn't click." Connect to `transparency_importance`, `brand_loyalty_tendency`, trust sources.
- `purchase` → "You seriously considered it but didn't pull the trigger." Connect to `budget_consciousness`, `price_reference_point`, SEC class.

**Important:** Use the scenario's `product.name` throughout, not generic "the product".

#### Layer 4: Scope Guardrails

```python
def build_scope_guardrails(scenario: Scenario) -> str:
```

Static text block that specifies:
- **WILL answer:** children's health, nutrition purchasing, daily routines, trust sources, family budget, experience with competitors (Horlicks, Bournvita, PediaSure), what would make them try/reject a new product
- **WILL NOT answer:** politics, religion, career details beyond family time impact, medical advice, other people's private matters, anything unrelated to parenting/health/nutrition
- **Deflection template:** "That's not really something I think about in this context. But if you want to know about [redirect], I have thoughts on that."

Parameterize with the scenario's product name and category.

#### Layer 5: Behavioral Directives

```python
BEHAVIORAL_DIRECTIVES: str = """..."""
```

A constant string containing 8 rules:
1. **Anti-reframing:** Don't agree with leading questions. Restate your genuine position.
2. **SEC coherence:** Language, brand references, price anchors must match socioeconomic reality. Include SEC-specific reference tables.
3. **Depth over breadth:** Follow-ups go deeper (surface → reason → emotion), not wider.
4. **Consistency:** No contradictions across the conversation.
5. **Specificity:** Reference actual city, shopping platform, child age, dietary culture, breakfast routine.
6. **Emotional authenticity:** Match emotional weight to health_anxiety level.
7. **Language register:** Match education level (doctorate = precise terms, high school = colloquial).
8. **Do NOT:** Break character, invent events, give medical advice, use marketing language, change opinion under pressure.

#### Assembly Function

```python
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

### 2. Modify `src/analysis/interviews.py`

Replace `build_system_prompt()` in the `PersonaInterviewer` class:

```python
from src.analysis.interview_prompts import assemble_system_prompt

class PersonaInterviewer:
    def build_system_prompt(self, persona, scenario_id, decision_result) -> str:
        return assemble_system_prompt(persona, scenario_id, decision_result)
```

Keep the method signature identical for backward compatibility. The old implementation (~40 lines) is entirely replaced by the call to the new module.

### 3. Upgrade `_build_mock_response` (in `interviews.py`)

Improve the mock response engine with:
- **Question intent classifier:** Detect price/trust/routine/product/barrier/influence/child intents from keywords
- **SEC-appropriate language:** Different vocabulary for A1 vs C2
- **Reference persona's actual attributes:** city, shopping platform, dietary culture, child ages
- **Match rejection stage:** If rejected at awareness, don't talk about price. If rejected at purchase, talk about price.

Keep the mock mode fast (no LLM calls) but make responses more realistic and differentiated.

## Files to Read Before Starting

1. `src/analysis/interviews.py` — **full file** (416 lines) — current implementation you're modifying
2. `src/taxonomy/schema.py` — Persona model (lines 40-370 for identity categories, 426-540 for Persona class)
3. `src/decision/scenarios.py` — `get_scenario()` and Scenario model
4. `src/constants.py` — INTERVIEW_* constants (lines 234-255)
5. `src/utils/display.py` — `display_name()` function
6. `docs/designs/INTERVIEW-PROMPT-ARCHITECTURE.md` — full design doc

## Constraints

- Python 3.11+, Pydantic v2
- Do NOT change the `PersonaInterviewer` public API (`interview()`, `start_session()`)
- Do NOT change `InterviewSession`, `InterviewTurn`, `InterviewQualityCheck` models
- The probing tree engine (`src/probing/engine.py`) uses `PersonaInterviewer` — it must keep working unchanged
- Keep `check_interview_quality()` in `interviews.py` — guardrails are separate (Track B)
- No new pip dependencies
- Belief converters must handle edge cases: NaN values, missing attributes
- Each belief converter must have exactly 4 tiers: ≥0.75, ≥0.50, ≥0.25, <0.25

## Acceptance Criteria

- [ ] `interview_prompts.py` created with all 5 layer builders
- [ ] At least 15 belief converters covering all 6 categories
- [ ] `assemble_system_prompt()` produces a well-formatted multi-section prompt
- [ ] `PersonaInterviewer.build_system_prompt()` delegates to new module
- [ ] Mock responses reference persona's actual city, shopping platform, child age
- [ ] Mock responses match rejection stage (no price talk for awareness rejections)
- [ ] All existing tests still pass
- [ ] No changes to public API signatures
