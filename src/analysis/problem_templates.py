"""Scenario-specific problem decomposition templates for Cursor's decompose_problem()."""

from typing import Any

PROBLEM_TEMPLATES: dict[str, dict[str, Any]] = {
    "nutrimix_2_6": {
        "problem": "High NPS but low repeat purchase",
        "sub_problems": [
            "Perception decay over time",
            "Child taste fatigue / boredom",
            "Cost comparison with mainstream alternatives (Bournvita, Complan)",
            "Habit formation failure (seen as one-off, not daily essential)",
            "Re-engagement failure (no reminder to reorder)",
        ],
        "cohorts": {
            "first_time_buyers": "trust > 0.6, ever_adopted = False",
            "current_users": "is_active = True, consecutive_purchase_months >= 2",
            "lapsed_users": "ever_adopted = True, is_active = False, churned = True",
            "aware_not_tried": "brand_salience > 0.3, ever_adopted = False",
        },
        "probe_focus": {},  # Per cohort probe questions
        "research_objectives": ["Optimize repeat purchase drivers"],
    },
    "nutrimix_7_14": {
        "problem": "Nutrimix dominates 2-6, how to expand to 7-14?",
        "sub_problems": [
            "Age perception barrier ('my kid is too old for this')",
            "Peer pressure / social acceptability in older kids",
            "Competing with sports drinks and protein bars",
            "Reduced parental control over diet in 7-14 age group",
            "Different nutritional messaging needed (growth → performance)",
        ],
        "cohorts": {
            "parents_young_kids": "youngest_child_age < 7",
            "parents_older_kids": "youngest_child_age >= 7",
            "cross_age_families": "multiple children spanning both ranges",
            "health_conscious_parents": "health_anxiety > 0.7",
        },
        "probe_focus": {},
        "research_objectives": ["Tailor messaging for age expansion"],
    },
    "magnesium_gummies": {
        "problem": "How to grow sales of a niche supplement?",
        "sub_problems": [
            "Low awareness of magnesium benefits for children",
            "'Gummy = candy not medicine' perception",
            "Price sensitivity (₹499 for 30 gummies vs ₹599 for Nutrimix)",
            "Doctor recommendation dependency",
            "Competition from multivitamin gummies",
        ],
        "cohorts": {
            "supplement_aware": "knows about children's supplements",
            "nutrimix_users": "current Nutrimix buyers (cross-sell target)",
            "health_anxious": "high health_anxiety, researches supplements",
            "doctor_trusters": "high medical_authority_trust",
        },
        "probe_focus": {},
        "research_objectives": ["Drive niche awareness & trial"],
    },
    "protein_mix": {
        "problem": "High effort barrier — must cook with it",
        "sub_problems": [
            "Effort friction (not a drink, must mix into food)",
            "Unclear use cases (which recipes?)",
            "'My child won't notice' skepticism",
            "Price comparison with protein alternatives",
            "Working parent time constraints",
        ],
        "cohorts": {
            "time_constrained": "working_status = 'full_time'",
            "cooking_enthusiasts": "cooking_confidence > 0.7",
            "protein_seekers": "actively seeking protein for child",
            "convenience_driven": "high effort_friction sensitivity",
        },
        "probe_focus": {},
        "research_objectives": ["Reduce perceived effort"],
    },
}
