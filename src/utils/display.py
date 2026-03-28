"""Human-readable display names and descriptions for persona attributes."""

from __future__ import annotations

from typing import Any

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
    "anchoring_bias": "Anchoring Bias",
    # Cultural
    "traditional_vs_modern_spectrum": "Traditional vs Modern",
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
    "persona_id": "Persona Identifier",
}

SEC_DESCRIPTIONS: dict[str, str] = {
    "A1": "Urban Affluent — highest disposable income, premium brand affinity",
    "A2": "Upper Middle — professional households, quality-conscious spending",
    "B1": "Middle Class — stable salaried, value-for-money seekers",
    "B2": "Lower Middle — budget-conscious, need-based purchasing",
    "C1": "Economy — price-driven, essential spending focus",
    "C2": "Value Segment — bare essentials, highly price-sensitive",
}

ATTRIBUTE_CATEGORIES: dict[str, list[str]] = {
    "Health & Nutrition": [
        "fitness_engagement",
        "diet_consciousness",
        "organic_preference",
        "medical_authority_trust",
        "self_research_tendency",
        "child_health_proactivity",
        "immunity_concern",
        "growth_concern",
        "nutrition_gap_awareness",
    ],
    "Psychology & Decisions": [
        "decision_speed",
        "information_need",
        "risk_tolerance",
        "social_proof_bias",
        "authority_bias",
        "health_anxiety",
        "loss_aversion",
        "simplicity_preference",
        "mental_bandwidth",
    ],
    "Values & Beliefs": [
        "brand_loyalty_tendency",
        "indie_brand_openness",
        "transparency_importance",
        "best_for_my_child_intensity",
        "guilt_driven_spending",
        "made_in_india_preference",
        "supplement_necessity_belief",
    ],
    "Cultural & Social": [
        "traditional_vs_modern_spectrum",
        "ayurveda_affinity",
        "western_brand_trust",
        "community_orientation",
    ],
    "Media & Digital": [
        "ad_receptivity",
        "digital_payment_comfort",
        "app_download_willingness",
        "online_vs_offline_preference",
    ],
    "Lifestyle & Routine": [
        "convenience_food_acceptance",
        "wellness_trend_follower",
        "deal_seeking_intensity",
        "impulse_purchase_tendency",
        "budget_consciousness",
        "subscription_comfort",
    ],
}

OUTCOME_DISPLAY: dict[str, str] = {
    "adopt": "Adopted",
    "reject": "Did not adopt",
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


def outcome_label(code: str | None) -> str:
    """Map simulation outcome codes to UI copy."""

    if not code:
        return "Unknown"
    return OUTCOME_DISPLAY.get(str(code).lower(), display_name(str(code)))


def persona_display_name(persona: Any) -> str:
    """
    Primary human-facing label for a persona (city and parent context).

    Use alongside :attr:`~src.taxonomy.schema.Persona.id` when the stable
    identifier must be visible.
    """

    demo = persona.demographics
    return f"{demo.city_name} · {display_name('parent_age')} {demo.parent_age}"
