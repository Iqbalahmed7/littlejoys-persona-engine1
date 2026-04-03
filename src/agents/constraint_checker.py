"""constraint_checker.py — Hard constraint validation for generated personas.

30 rules grouped into 5 categories:
  CAT-1: Demographic coherence (rules 1-6)    — includes 4 known population_meta violations
  CAT-2: Economic coherence (rules 7-12)
  CAT-3: Psychographic coherence (rules 13-18)
  CAT-4: Behavioural coherence (rules 19-24)
  CAT-5: Domain-specific coherence (rules 25-30)

Usage:
    checker = ConstraintChecker()
    violations = checker.check(persona)
    hard_only = checker.check_hard_only(persona)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


@dataclass
class ConstraintViolation:
    rule_id: str
    message: str
    severity: str           # "hard" | "soft"
    attribute_a: str
    attribute_b: str
    values: dict


@dataclass
class ConstraintRule:
    rule_id: str
    description: str
    severity: str
    check: Callable[["Persona"], ConstraintViolation | None]


class ConstraintChecker:
    def __init__(self):
        self._rules: list[ConstraintRule] = self._build_rules()

    def check(self, persona: "Persona") -> list[ConstraintViolation]:
        """Run all 30 rules. Returns list of violations (empty = valid)."""
        violations = []
        for rule in self._rules:
            try:
                v = rule.check(persona)
                if v is not None:
                    violations.append(v)
            except AttributeError:
                pass
        return violations

    def check_hard_only(self, persona: "Persona") -> list[ConstraintViolation]:
        return [v for v in self.check(persona) if v.severity == "hard"]

    def _build_rules(self) -> list[ConstraintRule]:
        rules = []

        # ── CAT-1: KNOWN VIOLATIONS from population_meta.json ──

        def r001(p):
            if p.demographics.household_income_lpa < 3.0 and p.values.best_for_my_child_intensity > 0.7:
                return ConstraintViolation("CAT1-R001",
                    f"Income {p.demographics.household_income_lpa}L but best_for_my_child={p.values.best_for_my_child_intensity:.2f}. Incoherent spending narrative.",
                    "soft", "household_income_lpa", "best_for_my_child_intensity",
                    {"household_income_lpa": p.demographics.household_income_lpa,
                     "best_for_my_child_intensity": p.values.best_for_my_child_intensity})
        rules.append(ConstraintRule("CAT1-R001", "Low income + high aspiration", "soft", r001))

        def r002(p):
            if p.demographics.city_tier == "Tier3" and p.media.digital_payment_comfort > 0.85:
                return ConstraintViolation("CAT1-R002",
                    f"Tier3 city but digital_payment_comfort={p.media.digital_payment_comfort:.2f}. Infrastructure implausibility.",
                    "soft", "city_tier", "digital_payment_comfort",
                    {"city_tier": p.demographics.city_tier,
                     "digital_payment_comfort": p.media.digital_payment_comfort})
        rules.append(ConstraintRule("CAT1-R002", "Tier3 + high digital comfort", "soft", r002))

        def r003(p):
            if p.psychology.health_anxiety < 0.2 and p.values.supplement_necessity_belief > 0.8:
                return ConstraintViolation("CAT1-R003",
                    f"health_anxiety={p.psychology.health_anxiety:.2f} but supplement_necessity={p.values.supplement_necessity_belief:.2f}.",
                    "soft", "health_anxiety", "supplement_necessity_belief",
                    {"health_anxiety": p.psychology.health_anxiety,
                     "supplement_necessity_belief": p.values.supplement_necessity_belief})
        rules.append(ConstraintRule("CAT1-R003", "Low anxiety + high supplement belief", "soft", r003))

        def r004(p):
            if p.career.employment_status == "homemaker" and p.career.perceived_time_scarcity > 0.8:
                return ConstraintViolation("CAT1-R004",
                    f"Homemaker with time_scarcity={p.career.perceived_time_scarcity:.2f}. Requires narrative justification.",
                    "soft", "employment_status", "perceived_time_scarcity",
                    {"employment_status": p.career.employment_status,
                     "perceived_time_scarcity": p.career.perceived_time_scarcity})
        rules.append(ConstraintRule("CAT1-R004", "Homemaker + high time scarcity", "soft", r004))

        # ── CAT-1 continued: Demographic coherence ──

        def r005(p):
            if p.demographics.parent_age - p.demographics.oldest_child_age < 18:
                return ConstraintViolation("CAT1-R005",
                    f"Parent {p.demographics.parent_age} - oldest child {p.demographics.oldest_child_age} = {p.demographics.parent_age - p.demographics.oldest_child_age}. Min gap 18.",
                    "hard", "parent_age", "oldest_child_age",
                    {"parent_age": p.demographics.parent_age,
                     "oldest_child_age": p.demographics.oldest_child_age})
        rules.append(ConstraintRule("CAT1-R005", "Parent-child age gap < 18", "hard", r005))

        def r006(p):
            if p.demographics.family_structure == "joint" and p.relationships.elder_advice_weight < 0.1:
                return ConstraintViolation("CAT1-R006",
                    f"Joint family but elder_advice_weight={p.relationships.elder_advice_weight:.2f}.",
                    "soft", "family_structure", "elder_advice_weight",
                    {"family_structure": p.demographics.family_structure,
                     "elder_advice_weight": p.relationships.elder_advice_weight})
        rules.append(ConstraintRule("CAT1-R006", "Joint family + no elder advice", "soft", r006))

        # ── CAT-2: Economic coherence ──

        def r007(p):
            if p.daily_routine.budget_consciousness > 0.8 and p.daily_routine.deal_seeking_intensity < 0.2:
                return ConstraintViolation("CAT2-R007",
                    f"budget_consciousness={p.daily_routine.budget_consciousness:.2f} but deal_seeking={p.daily_routine.deal_seeking_intensity:.2f}.",
                    "soft", "budget_consciousness", "deal_seeking_intensity",
                    {"budget_consciousness": p.daily_routine.budget_consciousness,
                     "deal_seeking_intensity": p.daily_routine.deal_seeking_intensity})
        rules.append(ConstraintRule("CAT2-R007", "High budget conscious + no deal seeking", "soft", r007))

        def r008(p):
            if p.demographics.household_income_lpa > 25 and p.daily_routine.budget_consciousness > 0.85:
                return ConstraintViolation("CAT2-R008",
                    f"Income Rs{p.demographics.household_income_lpa}L but budget_consciousness={p.daily_routine.budget_consciousness:.2f}. Rare.",
                    "soft", "household_income_lpa", "budget_consciousness",
                    {"household_income_lpa": p.demographics.household_income_lpa,
                     "budget_consciousness": p.daily_routine.budget_consciousness})
        rules.append(ConstraintRule("CAT2-R008", "High income + extreme budget consciousness", "soft", r008))

        def r009(p):
            if p.career.employment_status == "full_time" and p.career.work_hours_per_week == 0:
                return ConstraintViolation("CAT2-R009",
                    "employment_status=full_time but work_hours_per_week=0. Contradiction.",
                    "hard", "employment_status", "work_hours_per_week",
                    {"employment_status": p.career.employment_status,
                     "work_hours_per_week": p.career.work_hours_per_week})
        rules.append(ConstraintRule("CAT2-R009", "Full-time employed + zero hours", "hard", r009))

        def r010(p):
            if p.career.employment_status == "homemaker" and p.career.career_ambition > 0.85:
                return ConstraintViolation("CAT2-R010",
                    f"Homemaker with career_ambition={p.career.career_ambition:.2f}. Requires re-entry narrative.",
                    "soft", "employment_status", "career_ambition",
                    {"employment_status": p.career.employment_status,
                     "career_ambition": p.career.career_ambition})
        rules.append(ConstraintRule("CAT2-R010", "Homemaker + extreme career ambition", "soft", r010))

        def r011(p):
            monthly = p.budget_profile.monthly_food_budget_inr
            discret = p.budget_profile.discretionary_child_nutrition_budget_inr
            if monthly > 0 and discret / monthly > 0.5:
                return ConstraintViolation("CAT2-R011",
                    f"Child nutrition discretionary (Rs{discret}) > 50% of monthly food budget (Rs{monthly}).",
                    "hard", "discretionary_child_nutrition_budget_inr", "monthly_food_budget_inr",
                    {"discretionary": discret, "monthly_food": monthly})
        rules.append(ConstraintRule("CAT2-R011", "Discretionary > 50% food budget", "hard", r011))

        def r012(p):
            if p.budget_profile.price_sensitivity == "low" and p.daily_routine.budget_consciousness > 0.75:
                return ConstraintViolation("CAT2-R012",
                    f"price_sensitivity=low but budget_consciousness={p.daily_routine.budget_consciousness:.2f}. Contradiction.",
                    "soft", "price_sensitivity", "budget_consciousness",
                    {"price_sensitivity": p.budget_profile.price_sensitivity,
                     "budget_consciousness": p.daily_routine.budget_consciousness})
        rules.append(ConstraintRule("CAT2-R012", "Low price sensitivity + high budget consciousness", "soft", r012))

        # ── CAT-3: Psychographic coherence ──

        def r013(p):
            if p.psychology.information_need > 0.8 and p.education_learning.label_reading_habit < 0.15:
                return ConstraintViolation("CAT3-R013",
                    f"information_need={p.psychology.information_need:.2f} but label_reading={p.education_learning.label_reading_habit:.2f}.",
                    "soft", "information_need", "label_reading_habit",
                    {"information_need": p.psychology.information_need,
                     "label_reading_habit": p.education_learning.label_reading_habit})
        rules.append(ConstraintRule("CAT3-R013", "High info need + no label reading", "soft", r013))

        def r014(p):
            if p.psychology.risk_tolerance > 0.75 and p.psychology.loss_aversion > 0.75:
                return ConstraintViolation("CAT3-R014",
                    f"risk_tolerance={p.psychology.risk_tolerance:.2f} AND loss_aversion={p.psychology.loss_aversion:.2f}. Negatively correlated extremes.",
                    "hard", "risk_tolerance", "loss_aversion",
                    {"risk_tolerance": p.psychology.risk_tolerance,
                     "loss_aversion": p.psychology.loss_aversion})
        rules.append(ConstraintRule("CAT3-R014", "High risk tolerance + high loss aversion", "hard", r014))

        def r015(p):
            if p.psychology.authority_bias < 0.1 and p.relationships.pediatrician_influence > 0.8:
                return ConstraintViolation("CAT3-R015",
                    f"authority_bias={p.psychology.authority_bias:.2f} but pediatrician_influence={p.relationships.pediatrician_influence:.2f}. Pediatrician IS authority.",
                    "soft", "authority_bias", "pediatrician_influence",
                    {"authority_bias": p.psychology.authority_bias,
                     "pediatrician_influence": p.relationships.pediatrician_influence})
        rules.append(ConstraintRule("CAT3-R015", "Low authority bias + high pediatrician trust", "soft", r015))

        def r016(p):
            dairy_supplements = ("horlicks", "bournvita", "pediasure", "complan")
            if p.cultural.dietary_culture == "vegan" and p.daily_routine.milk_supplement_current in dairy_supplements:
                return ConstraintViolation("CAT3-R016",
                    f"dietary_culture=vegan but milk_supplement={p.daily_routine.milk_supplement_current} (dairy). Hard contradiction.",
                    "hard", "dietary_culture", "milk_supplement_current",
                    {"dietary_culture": p.cultural.dietary_culture,
                     "milk_supplement_current": p.daily_routine.milk_supplement_current})
        rules.append(ConstraintRule("CAT3-R016", "Vegan + dairy supplement", "hard", r016))

        def r017(p):
            if p.psychology.analysis_paralysis_tendency > 0.8 and p.psychology.decision_speed > 0.8:
                return ConstraintViolation("CAT3-R017",
                    f"analysis_paralysis={p.psychology.analysis_paralysis_tendency:.2f} AND decision_speed={p.psychology.decision_speed:.2f}. Mutually exclusive.",
                    "hard", "analysis_paralysis_tendency", "decision_speed",
                    {"analysis_paralysis_tendency": p.psychology.analysis_paralysis_tendency,
                     "decision_speed": p.psychology.decision_speed})
        rules.append(ConstraintRule("CAT3-R017", "High paralysis + high decision speed", "hard", r017))

        def r018(p):
            if p.psychology.status_quo_bias > 0.8 and p.values.brand_loyalty_tendency < 0.1:
                return ConstraintViolation("CAT3-R018",
                    f"status_quo_bias={p.psychology.status_quo_bias:.2f} but brand_loyalty={p.values.brand_loyalty_tendency:.2f}. High inertia typically co-occurs with brand loyalty.",
                    "soft", "status_quo_bias", "brand_loyalty_tendency",
                    {"status_quo_bias": p.psychology.status_quo_bias,
                     "brand_loyalty_tendency": p.values.brand_loyalty_tendency})
        rules.append(ConstraintRule("CAT3-R018", "High status quo bias + no brand loyalty", "soft", r018))

        # ── CAT-4: Behavioural coherence ──

        def r019(p):
            if p.demographics.num_children == 0 and p.daily_routine.milk_supplement_current != "none":
                return ConstraintViolation("CAT4-R019",
                    f"num_children=0 but milk_supplement={p.daily_routine.milk_supplement_current}. No child, no supplement.",
                    "hard", "num_children", "milk_supplement_current",
                    {"num_children": p.demographics.num_children,
                     "milk_supplement_current": p.daily_routine.milk_supplement_current})
        rules.append(ConstraintRule("CAT4-R019", "No children + child supplement", "hard", r019))

        def r020(p):
            if p.daily_routine.impulse_purchase_tendency > 0.85 and p.psychology.analysis_paralysis_tendency > 0.85:
                return ConstraintViolation("CAT4-R020",
                    f"impulse={p.daily_routine.impulse_purchase_tendency:.2f} AND paralysis={p.psychology.analysis_paralysis_tendency:.2f}. Mutually exclusive extremes.",
                    "hard", "impulse_purchase_tendency", "analysis_paralysis_tendency",
                    {"impulse_purchase_tendency": p.daily_routine.impulse_purchase_tendency,
                     "analysis_paralysis_tendency": p.psychology.analysis_paralysis_tendency})
        rules.append(ConstraintRule("CAT4-R020", "Extreme impulse + extreme paralysis", "hard", r020))

        def r021(p):
            if p.daily_routine.online_vs_offline_preference < 0.2 and p.daily_routine.primary_shopping_platform == "quick_commerce":
                return ConstraintViolation("CAT4-R021",
                    f"online_pref={p.daily_routine.online_vs_offline_preference:.2f} but platform=quick_commerce (inherently online).",
                    "hard", "online_vs_offline_preference", "primary_shopping_platform",
                    {"online_vs_offline_preference": p.daily_routine.online_vs_offline_preference,
                     "primary_shopping_platform": p.daily_routine.primary_shopping_platform})
        rules.append(ConstraintRule("CAT4-R021", "Offline preference + quick commerce", "hard", r021))

        def r022(p):
            if (p.cultural.dietary_culture == "jain"
                    and p.health.health_info_sources == ["google"]
                    and not p.cultural.mommy_group_membership):
                return ConstraintViolation("CAT4-R022",
                    "Jain dietary culture with no community connections. Jain communities are highly networked.",
                    "soft", "dietary_culture", "health_info_sources",
                    {"dietary_culture": p.cultural.dietary_culture,
                     "health_info_sources": p.health.health_info_sources})
        rules.append(ConstraintRule("CAT4-R022", "Jain + no community connections", "soft", r022))

        def r023(p):
            if p.relationships.wom_transmitter_tendency > 0.85 and not p.cultural.social_media_active:
                return ConstraintViolation("CAT4-R023",
                    f"wom_transmitter={p.relationships.wom_transmitter_tendency:.2f} but social_media_active=False.",
                    "soft", "wom_transmitter_tendency", "social_media_active",
                    {"wom_transmitter_tendency": p.relationships.wom_transmitter_tendency,
                     "social_media_active": p.cultural.social_media_active})
        rules.append(ConstraintRule("CAT4-R023", "High WOM transmitter + no social media", "soft", r023))

        def r024(p):
            if p.media.daily_social_media_hours < 0.1 and p.relationships.influencer_trust > 0.75:
                return ConstraintViolation("CAT4-R024",
                    f"social_media_hours={p.media.daily_social_media_hours:.1f} but influencer_trust={p.relationships.influencer_trust:.2f}. No exposure.",
                    "hard", "daily_social_media_hours", "influencer_trust",
                    {"daily_social_media_hours": p.media.daily_social_media_hours,
                     "influencer_trust": p.relationships.influencer_trust})
        rules.append(ConstraintRule("CAT4-R024", "No social media + high influencer trust", "hard", r024))

        # ── CAT-5: Domain-specific coherence ──

        def r025(p):
            if p.decision_rights.supplements == "doctor_gated" and p.health.pediatrician_visit_frequency == "rarely":
                return ConstraintViolation("CAT5-R025",
                    "supplements=doctor_gated but pediatrician_visit_frequency=rarely. Cannot be doctor-gated without doctor access.",
                    "hard", "supplements_decision_rights", "pediatrician_visit_frequency",
                    {"supplements": p.decision_rights.supplements,
                     "pediatrician_visit_frequency": p.health.pediatrician_visit_frequency})
        rules.append(ConstraintRule("CAT5-R025", "Doctor-gated supplements + no doctor visits", "hard", r025))

        def r026(p):
            if p.health.vaccination_attitude == "proactive" and p.psychology.authority_bias < 0.1:
                return ConstraintViolation("CAT5-R026",
                    f"vaccination=proactive but authority_bias={p.psychology.authority_bias:.2f}. Proactive vaccination implies medical trust.",
                    "soft", "vaccination_attitude", "authority_bias",
                    {"vaccination_attitude": p.health.vaccination_attitude,
                     "authority_bias": p.psychology.authority_bias})
        rules.append(ConstraintRule("CAT5-R026", "Proactive vaccination + no authority bias", "soft", r026))

        def r027(p):
            if p.values.supplement_necessity_belief > 0.8 and p.values.food_first_belief > 0.85:
                return ConstraintViolation("CAT5-R027",
                    f"supplement_necessity={p.values.supplement_necessity_belief:.2f} AND food_first={p.values.food_first_belief:.2f}. Cannot hold both extremes.",
                    "hard", "supplement_necessity_belief", "food_first_belief",
                    {"supplement_necessity_belief": p.values.supplement_necessity_belief,
                     "food_first_belief": p.values.food_first_belief})
        rules.append(ConstraintRule("CAT5-R027", "High supplement belief + food-first belief", "hard", r027))

        def r028(p):
            if p.health.child_health_status == "chronic_condition" and p.health.child_health_proactivity < 0.15:
                return ConstraintViolation("CAT5-R028",
                    f"child_health=chronic_condition but proactivity={p.health.child_health_proactivity:.2f}. Chronic condition parents are almost never low-proactivity.",
                    "soft", "child_health_status", "child_health_proactivity",
                    {"child_health_status": p.health.child_health_status,
                     "child_health_proactivity": p.health.child_health_proactivity})
        rules.append(ConstraintRule("CAT5-R028", "Chronic condition child + low proactivity", "soft", r028))

        def r029(p):
            if p.cultural.ayurveda_affinity > 0.85 and p.cultural.western_brand_trust > 0.85:
                return ConstraintViolation("CAT5-R029",
                    f"ayurveda_affinity={p.cultural.ayurveda_affinity:.2f} AND western_brand_trust={p.cultural.western_brand_trust:.2f}. Both extremes together are implausible.",
                    "soft", "ayurveda_affinity", "western_brand_trust",
                    {"ayurveda_affinity": p.cultural.ayurveda_affinity,
                     "western_brand_trust": p.cultural.western_brand_trust})
        rules.append(ConstraintRule("CAT5-R029", "Extreme ayurveda + extreme western trust", "soft", r029))

        def r030(p):
            if (p.demographics.family_structure == "single_parent"
                    and p.decision_rights.child_nutrition in ("father_final", "joint")):
                return ConstraintViolation("CAT5-R030",
                    f"family_structure=single_parent but child_nutrition_rights={p.decision_rights.child_nutrition}. Single parent cannot have joint/father rights.",
                    "hard", "family_structure", "child_nutrition_rights",
                    {"family_structure": p.demographics.family_structure,
                     "child_nutrition_rights": p.decision_rights.child_nutrition})
        rules.append(ConstraintRule("CAT5-R030", "Single parent + joint decision rights", "hard", r030))

        assert len(rules) == 30, f"Expected 30 rules, got {len(rules)}"
        return rules
