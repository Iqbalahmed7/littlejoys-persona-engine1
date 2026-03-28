# Cursor — Sprint 6 Briefing

**PRD**: PRD-013 Persona Depth & UX Overhaul
**Branch**: `feat/PRD-013-persona-depth`
**Priority**: P0 — **WAVE 1** (send immediately, Antigravity depends on your output)

---

## Your Task: Attribute Display Layer + Population Page UX

### 1. Create `src/utils/display.py`

This is the **shared mapping layer** that translates raw field names to human-readable labels. Other engineers will import from this file.

```python
"""Human-readable display names and descriptions for persona attributes."""

from __future__ import annotations

ATTRIBUTE_DISPLAY_NAMES: dict[str, str] = {
    # Demographics
    "city_tier": "City Classification",
    "city_name": "City",
    "region": "Region",
    "urban_vs_periurban": "Urban/Peri-urban",
    "household_income_lpa": "Household Income (₹ Lakhs/year)",
    "parent_age": "Parent's Age",
    "parent_gender": "Parent Gender",
    "num_children": "Number of Children",
    "family_structure": "Family Type",
    "employment_status": "Work Status",
    "education_level": "Education",
    "socioeconomic_class": "SEC Class",
    "income_stability": "Income Source",
    "dual_income_household": "Dual Income",

    # Health & Nutrition
    "health_anxiety": "Health Worry Level",
    "diet_consciousness": "Dietary Awareness",
    "organic_preference": "Organic Preference",
    "medical_authority_trust": "Doctor Trust",
    "self_research_tendency": "Self-Research Drive",
    "child_health_proactivity": "Child Health Proactiveness",
    "immunity_concern": "Immunity Concern",
    "growth_concern": "Growth Concern",
    "nutrition_gap_awareness": "Nutrition Gap Awareness",
    "fitness_engagement": "Fitness Engagement",

    # Psychology & Decision-Making
    "budget_consciousness": "Price Sensitivity",
    "decision_speed": "Decision Speed",
    "information_need": "Information Need",
    "risk_tolerance": "Risk Tolerance",
    "social_proof_bias": "Peer Influence",
    "authority_bias": "Authority Influence",
    "health_anxiety": "Health Worry",
    "loss_aversion": "Loss Aversion",
    "simplicity_preference": "Simplicity Preference",
    "mental_bandwidth": "Mental Bandwidth",
    "analysis_paralysis_tendency": "Overthinking Tendency",
    "regret_sensitivity": "Regret Sensitivity",
    "status_quo_bias": "Status Quo Preference",
    "halo_effect_susceptibility": "Brand Halo Effect",
    "comparison_anxiety": "Comparison Anxiety",
    "guilt_sensitivity": "Guilt Sensitivity",
    "control_need": "Need for Control",
    "decision_fatigue_level": "Decision Fatigue",

    # Cultural
    "traditional_vs_modern_spectrum": "Traditional ↔ Modern",
    "ayurveda_affinity": "Ayurveda Affinity",
    "western_brand_trust": "Western Brand Trust",
    "community_orientation": "Community Orientation",
    "dietary_culture": "Dietary Culture",

    # Values & Beliefs
    "brand_loyalty_tendency": "Brand Loyalty",
    "indie_brand_openness": "Open to New Brands",
    "transparency_importance": "Transparency Importance",
    "best_for_my_child_intensity": "Best-for-My-Child Drive",
    "guilt_driven_spending": "Guilt-Driven Spending",
    "made_in_india_preference": "Made in India Preference",
    "supplement_necessity_belief": "Supplement Belief",
    "natural_vs_synthetic_preference": "Natural vs Synthetic Preference",
    "food_first_belief": "Food-First Belief",
    "preventive_vs_reactive_health": "Preventive Health Mindset",

    # Media & Digital
    "ad_receptivity": "Ad Receptivity",
    "digital_payment_comfort": "Digital Payment Comfort",
    "app_download_willingness": "App Download Willingness",
    "online_vs_offline_preference": "Online Shopping Preference",

    # Relationships
    "peer_influence_strength": "Peer Influence Strength",
    "influencer_trust": "Influencer Trust",
    "elder_advice_weight": "Elder Advice Weight",
    "pediatrician_influence": "Pediatrician Influence",
    "wom_receiver_openness": "Word-of-Mouth Receptivity",
    "child_pester_power": "Child's Influence on Purchases",

    # Lifestyle
    "convenience_food_acceptance": "Convenience Food Acceptance",
    "wellness_trend_follower": "Wellness Trend Follower",
    "deal_seeking_intensity": "Deal-Seeking Intensity",
    "impulse_purchase_tendency": "Impulse Purchase Tendency",
    "subscription_comfort": "Subscription Comfort",

    # Emotional
    "emotional_persuasion_susceptibility": "Emotional Persuasion",
    "fear_appeal_responsiveness": "Fear Appeal Response",
    "aspirational_messaging_responsiveness": "Aspirational Message Response",
    "testimonial_impact": "Testimonial Impact",

    # Simulation outcomes
    "outcome": "Decision Outcome",
    "need_score": "Need Score",
    "awareness_score": "Awareness Score",
    "consideration_score": "Consideration Score",
    "purchase_score": "Purchase Score",
    "rejection_stage": "Rejection Stage",
    "rejection_reason": "Rejection Reason",
}

SEC_DESCRIPTIONS: dict[str, str] = {
    "A1": "Urban Affluent — highest disposable income, premium brand affinity",
    "A2": "Upper Middle — professional households, quality-conscious spending",
    "B1": "Middle Class — stable salaried, value-for-money seekers",
    "B2": "Lower Middle — budget-conscious, need-based purchasing",
    "C1": "Economy — price-driven, essential spending focus",
    "C2": "Value Segment — bare essentials, highly price-sensitive",
}

# Attribute categories for grouped selection in UI
ATTRIBUTE_CATEGORIES: dict[str, list[str]] = {
    "Health & Nutrition": [
        "fitness_engagement", "diet_consciousness", "organic_preference",
        "medical_authority_trust", "self_research_tendency", "child_health_proactivity",
        "immunity_concern", "growth_concern", "nutrition_gap_awareness",
    ],
    "Psychology & Decisions": [
        "decision_speed", "information_need", "risk_tolerance",
        "social_proof_bias", "authority_bias", "health_anxiety",
        "loss_aversion", "simplicity_preference", "mental_bandwidth",
    ],
    "Values & Beliefs": [
        "brand_loyalty_tendency", "indie_brand_openness", "transparency_importance",
        "best_for_my_child_intensity", "guilt_driven_spending",
        "made_in_india_preference", "supplement_necessity_belief",
    ],
    "Cultural & Social": [
        "traditional_vs_modern_spectrum", "ayurveda_affinity",
        "western_brand_trust", "community_orientation",
    ],
    "Media & Digital": [
        "ad_receptivity", "digital_payment_comfort",
        "app_download_willingness", "online_vs_offline_preference",
    ],
    "Lifestyle & Routine": [
        "convenience_food_acceptance", "wellness_trend_follower",
        "deal_seeking_intensity", "impulse_purchase_tendency",
        "budget_consciousness", "subscription_comfort",
    ],
}


def display_name(field: str) -> str:
    """Convert raw field name to human-readable label."""
    return ATTRIBUTE_DISPLAY_NAMES.get(field, field.replace("_", " ").title())


def describe_attribute_value(field: str, value: float) -> str:
    """Natural language description of a 0-1 attribute value."""
    label = display_name(field).lower()
    if value >= 0.8:
        return f"very high {label}"
    if value >= 0.6:
        return f"fairly strong {label}"
    if value >= 0.4:
        return f"moderate {label}"
    if value >= 0.2:
        return f"somewhat low {label}"
    return f"low {label}"
```

### 2. Update `app/pages/1_population.py`

Apply the display layer throughout:

**A. Replace raw column names in charts:**
Use `display_name()` for all axis labels, legends, selectbox options:
```python
from src.utils.display import display_name, SEC_DESCRIPTIONS, ATTRIBUTE_CATEGORIES

# Selectbox shows human-readable names
choice = st.selectbox(
    "Distribution",
    cat,
    format_func=display_name,
)
# Chart title uses display name
fig = px.bar(..., title=f"Count by {display_name(choice)}")
```

**B. Add SEC class explanation:**
When showing socioeconomic_class distribution, add a caption or expander:
```python
if choice == "socioeconomic_class":
    with st.expander("What do SEC classes mean?"):
        for cls, desc in SEC_DESCRIPTIONS.items():
            st.markdown(f"**{cls}**: {desc}")
```

**C. Psychographic scatter — grouped categories:**
Replace the flat list of 92 attributes with category-grouped selection:
```python
category = st.selectbox("Attribute Category", list(ATTRIBUTE_CATEGORIES.keys()))
attrs_in_category = [a for a in ATTRIBUTE_CATEGORIES[category] if a in df.columns]
x_attr = st.selectbox("X axis", attrs_in_category, format_func=display_name)
```

**D. Remove "Tier 1" / "Tier 2" language:**
- Replace `"Tier 1 (statistical)"` metric with `"Population Size"`
- Replace `"Tier 2 (deep)"` metric with `"Personas with Narratives"`
- Replace section header `"Tier 2 deep narratives"` with `"Persona Stories"`
- Show `persona.display_name` in expander titles instead of raw ID

**E. Persona lookup:**
Show `display_name` prominently, with ID as secondary info.

### 3. Update `app/components/persona_card.py`

Use `display_name()` for all field labels:
```python
st.write(f"- {display_name('household_income_lpa')}: {persona.demographics.household_income_lpa}")
```

### 4. Tests

**File**: `tests/unit/test_display.py` (new)

```python
def test_display_name_known_field():
    assert display_name("budget_consciousness") == "Price Sensitivity"

def test_display_name_unknown_field():
    """Unknown fields get title-cased with underscores removed."""
    assert display_name("some_random_field") == "Some Random Field"

def test_describe_attribute_value_high():
    result = describe_attribute_value("health_anxiety", 0.85)
    assert "very high" in result

def test_sec_descriptions_complete():
    """All 6 SEC classes have descriptions."""
    assert len(SEC_DESCRIPTIONS) == 6

def test_attribute_categories_reference_valid_attrs():
    """All attrs in categories exist in display names."""
    for cat, attrs in ATTRIBUTE_CATEGORIES.items():
        for attr in attrs:
            assert attr in ATTRIBUTE_DISPLAY_NAMES, f"{attr} in {cat} missing display name"
```

---

## Critical: Write Your Own Delivery Report
Describe the actual files you changed and what you built. Do NOT copy another engineer's report.

## Standards
- `from __future__ import annotations`
- No raw field names in any user-facing text
- All display mappings in `src/utils/display.py` (single source of truth)
- Target: 5+ new tests

## Run
```bash
uv run pytest tests/ -x -q
uv run ruff check src/utils/display.py app/pages/1_population.py
```
