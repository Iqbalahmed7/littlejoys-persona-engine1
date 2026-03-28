# LittleJoys Persona Simulation Engine — Master Architecture Document

> **Purpose**: This document contains the complete architectural specification, design rationale, persona taxonomy, agent infrastructure design, and implementation plan for the LittleJoys Persona Simulation POC. It is intended as the **primary context document** for any coding agent (Cursor, Claude Code, Copilot) working on this project.

> **Last Updated**: 2026-03-27

---

## TABLE OF CONTENTS

1. [Project Context & Business Problems](#1-project-context--business-problems)
2. [Theoretical Foundations](#2-theoretical-foundations)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [The Human Attribute Taxonomy](#4-the-human-attribute-taxonomy)
5. [Complete Persona Schema](#5-complete-persona-schema)
6. [Persona Generation Engine](#6-persona-generation-engine)
7. [Decision Engine](#7-decision-engine)
8. [Simulation Engine](#8-simulation-engine)
9. [Analysis & Reporting Engine](#9-analysis--reporting-engine)
10. [Autonomous Agent Infrastructure](#10-autonomous-agent-infrastructure)
11. [Implementation Plan — Compressed Timeline](#11-implementation-plan--compressed-timeline)
12. [Tech Stack & Project Structure](#12-tech-stack--project-structure)
13. [Appendix: Scenario Configurations](#appendix-scenario-configurations)

---

## 1. PROJECT CONTEXT & BUSINESS PROBLEMS

### Client: LittleJoys (ourlittlejoys.com)
- **Parent Company**: Mosaic Wellness PVT LTD (founded 2019)
- **Positioning**: "One Stop Digital Health & Wellness Platform for Kids" — "Approved by Moms, Loved by Kids"
- **Key Products**:
  - **Nutrimix** (flagship): Chocolate nutrition powder. ₹599/350g. 1.1M units sold, 4.4★. Age variants: 2-6, 7-12, 13-18, Moms. Plant-based (moong dal, peas, brown rice), superfoods (ragi, bajra), zero white sugar.
  - **Magnesium Gummies**: ₹499/30ct, 5.0★, 3.4K units. Magnesium + B6 + Vegan D3. Targets calm/focus/mood.
  - **ProteinMix** (new): ₹549/250g, 4.6★, 1.6K units. 12g protein/scoop, flavorless, mixes into roti/dosa/pancake. Zero whey.
  - **Gummies Range**: Multivitamin, DHA Omega3, Calcium, Eye Health. All ₹499.
  - **Healthy Snacks**: Millet Choco Fills, Spreads, Sauces.
- **Programs**: LJ Wallet (up to 30% cashback), Little Joys Pass (90-day, 5% cashback on every order)
- **Trust Signals**: "Honest Reports" — batch-level lab test results viewable by customers. 3rd-party tested. Age-segmented formulations.
- **Demographics**: Urban Indian mothers, middle to upper-middle class, health-conscious. Age segments for children: 2-6, 7-12, 13-18.

### The Four Business Problems

| # | Problem | Core Question | Simulation Type |
|---|---------|--------------|-----------------|
| 1 | **Repeat Purchase** | NPS is high but repeat purchase needs improvement. How does the LJ Pass impact this? | Temporal (multi-month) |
| 2 | **Nutrimix 7-14 Expansion** | Nutrimix dominates 2-6 segment. How to establish it in the 7-14 age group? | Static snapshot + barrier analysis |
| 3 | **Magnesium Gummies Growth** | How to increase sales of a niche, less-understood supplement? | Static + awareness sensitivity |
| 4 | **ProteinMix Adoption** (lower priority) | New product with high effort barrier (must cook with it). How to drive trial? | Static + effort analysis |

### Our Pitch
We build **custom synthetic personas** of LittleJoys' target demographics — not shallow survey respondents, but deeply-modeled autonomous agents with realistic psychographics, behavioral histories, and decision-making processes. These agents are run through purchase decision simulations to produce **causal insights** (not correlations) and **actionable recommendations**.

### Stakes
If the POC delivers, this converts into a paid engagement. This is an intensive showcase of Simulatte's capabilities, not a full production build.

---

## 2. THEORETICAL FOUNDATIONS

This system combines two complementary approaches to persona synthesis. Understanding both is critical for implementation.

### 2.1 DeepPersona (Google/UCSD, NeurIPS 2025)

**Paper**: "DeepPersona: A Generative Engine for Scaling Deep Synthetic Personas" (Wang et al., 2025)

**Core Innovation**: A two-stage, taxonomy-guided method for generating "narrative-complete" synthetic personas with 200+ structured attributes.

**Stage 1 — Human Attribute Taxonomy Construction**:
- Mine real user-ChatGPT conversations (62,224 high-quality personalized QA pairs) to extract attributes humans actually self-disclose
- Organize into a hierarchical tree: 12 first-level categories → ~8,496 unique attribute nodes across 3 levels
- The 12 first-level categories:
  1. Demographic Information
  2. Physical and Health Characteristics
  3. Psychological and Cognitive Aspects
  4. Cultural and Social Context
  5. Relationships and Social Networks
  6. Career and Work Identity
  7. Education and Learning
  8. Hobbies, Interests, and Lifestyle
  9. Lifestyle and Daily Routine
  10. Core Values, Beliefs, and Philosophy
  11. Emotional and Relational Skills
  12. Media Consumption and Engagement
- Semantic validation: filter out non-personalizable attributes, merge redundant branches, validate parent-child relationships

**Stage 2 — Progressive Attribute Sampling**:
- **Anchor a stable core**: Fix age, location, career, personal values, life attitude, personal story, hobbies/interests first
- **Bias-free value assignment**: For demographics (age, gender, occupation, location), draw from predefined distribution tables, NOT the LLM — avoids majority-culture defaults
- **Balanced attribute diversification**: Embed candidate attributes in vector space, compute cosine similarity with core, divide into near/middle/far strata, sample at 5:3:2 ratio (coherence balanced with novelty)
- **Progressive LLM filling**: Stochastic breadth-first traversal of taxonomy tree, each attribute value conditioned on growing profile to maintain coherence
- **Optimal depth**: 200-250 attributes. Beyond 300, performance degrades (noise).

**Key Results**:
- 32% higher attribute coverage, 44% greater uniqueness vs. baselines
- 31.7% reduction in gap between simulated and real human survey responses
- 11.6% improvement in personalized QA accuracy

**What we adopt**:
- The taxonomy-guided generation approach (not random attribute stuffing)
- The two-tier architecture (statistical + narrative)
- The anchor → progressive fill pattern
- Bias-free demographic sampling from distribution tables
- The 200-250 attribute sweet spot

### 2.2 MiroFish (Multi-Agent Simulation)

**Repo**: github.com/666ghj/MiroFish

**Core Innovation**: A five-stage pipeline turning documents into simulated worlds of autonomous agents.

**Pipeline**:
1. **Graph Building** — Document → LLM ontology extraction → knowledge graph (Zep Cloud)
2. **Environment Setup** — 5-phase state machine: DB init → profile synthesis → parameter generation → environment validation → user approval
3. **Simulation** — Dual-platform parallel sim via OASIS engine (CAMEL-AI), agents post/comment/like/debate, temporal memory updates
4. **Report Generation** — ReACT-loop ReportAgent with tools: InsightForge, PanoramaSearch, InterviewSubAgent
5. **Deep Interaction** — Chat with any agent, survey broadcasts, ReportAgent follow-ups

**What we adopt**:
- Factory pattern for agent generation
- Dual LLM configuration (reasoning model for analysis, fast model for bulk generation)
- Temporal memory coherence (agents remember past interactions)
- ReACT report agent with specialized tools
- State machine for multi-step workflows
- The "chat with any agent" interaction pattern

### 2.3 Our Synthesis: What's Original

Neither DeepPersona nor MiroFish alone solves our problem. DeepPersona generates deep personas but has no decision engine. MiroFish simulates agent interactions but uses shallow personas in social media contexts.

**Our original contribution**:

1. **Domain-Specific Taxonomy Construction**: Instead of mining generic ChatGPT conversations, we build our attribute taxonomy from **real signals in the Indian parenting/child-nutrition domain** — scraping forums (BabyChakra, ParentCircle), product reviews (Amazon, Flipkart), social discussions (Reddit, Quora), and health data. This grounds our personas in the actual decision landscape.

2. **Purchase Decision Modeling on Deep Personas**: We bridge the gap between deep persona generation and actionable business simulation. Each persona's 200+ attributes feed into a multi-layer purchase decision model (awareness → consideration → purchase → repeat) that produces causal, attributable results.

3. **Temporal State on Top of Static Identity**: DeepPersona generates static profiles. We add a mutable behavioral state layer that evolves across simulation steps — enabling repeat purchase and churn modeling (Problem #1).

4. **Reusable Agent Infrastructure**: Personas are designed as autonomous agents with immutable identity + mutable memory + perception interface. The same agent can be deployed against different business contexts by injecting new environmental information, not by regenerating the persona.

5. **Counterfactual Engine**: Neither predecessor offers systematic "what-if" analysis. We build this as a first-class feature — any scenario parameter can be perturbed and the entire simulation re-run to measure causal impact.

---

## 3. SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SIMULATTE PERSONA ENGINE                          │
│                                                                      │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
│  │   DATA        │   │  TAXONOMY     │   │  PERSONA GENERATION     │ │
│  │   ENRICHMENT  │──▶│  BUILDER      │──▶│  ENGINE                 │ │
│  │   PIPELINE    │   │              │   │                          │ │
│  │  (scraping,   │   │ (hierarchy,  │   │ Tier 1: Statistical     │ │
│  │   surveys,    │   │  validation, │   │ (N=300-1000, numerical) │ │
│  │   reviews)    │   │  distribution│   │                          │ │
│  │              │   │  fitting)    │   │ Tier 2: Deep Narrative   │ │
│  │              │   │              │   │ (N=30-50, LLM-enriched)  │ │
│  └──────────────┘   └──────────────┘   └───────────┬──────────────┘ │
│                                                      │                │
│  ┌──────────────────────────────────────────────────▼──────────────┐ │
│  │                     AGENT RUNTIME LAYER                          │ │
│  │  ┌──────────┐  ┌──────────────┐  ┌───────────────────────────┐  │ │
│  │  │ Identity │  │   Memory     │  │   Perception Interface    │  │ │
│  │  │ (frozen) │  │   (mutable)  │  │   (scenario injection)    │  │ │
│  │  └──────────┘  └──────────────┘  └───────────────────────────┘  │ │
│  └──────────────────────────────────────────────────┬──────────────┘ │
│                                                      │                │
│  ┌──────────────────────────────────────────────────▼──────────────┐ │
│  │                     SIMULATION ENGINE                            │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                 │ │
│  │  │ Awareness  │─▶│ Consider-  │─▶│ Purchase   │─▶ Repeat Loop  │ │
│  │  │ Filter     │  │ ation      │  │ Decision   │   (temporal)    │ │
│  │  └────────────┘  └────────────┘  └────────────┘                 │ │
│  │                                                                   │ │
│  │  ┌────────────────────────────────────────────────────────────┐  │ │
│  │  │              COUNTERFACTUAL ENGINE                          │  │ │
│  │  │  Perturb any parameter → re-run → diff results            │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────┬──────────────┘ │
│                                                      │                │
│  ┌──────────────────────────────────────────────────▼──────────────┐ │
│  │                   ANALYSIS & REPORTING                           │ │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────────────┐  │ │
│  │  │ Segment  │  │ Causal    │  │ Counter- │  │ ReportAgent   │  │ │
│  │  │ Analyzer │  │ Attributor│  │ factual  │  │ (LLM ReACT)   │  │ │
│  │  │          │  │           │  │ Comparator│  │               │  │ │
│  │  └──────────┘  └───────────┘  └──────────┘  └───────────────┘  │ │
│  │                                                                   │ │
│  │  ┌────────────────────────────────────────────────────────────┐  │ │
│  │  │            DEEP PERSONA INTERVIEW MODE                     │  │ │
│  │  │  Chat with any Tier 2 persona about their decisions       │  │ │
│  │  └────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                   PRESENTATION LAYER                             │ │
│  │  Streamlit dashboard with interactive controls                   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. THE HUMAN ATTRIBUTE TAXONOMY

### 4.1 Taxonomy Design Philosophy

Following DeepPersona, our taxonomy is:
- **Hierarchical**: 3 levels max (Category → Subcategory → Attribute). Deeper nesting creates sparse, unusable leaf nodes.
- **Domain-grounded**: Unlike DeepPersona's generic taxonomy mined from ChatGPT conversations, ours is built for the **Indian parent making child health/nutrition decisions**. We retain DeepPersona's 12 universal categories but extend them with domain-specific branches.
- **Data-driven**: Attribute distributions are derived from real-world signals (see §4.2), not assumed.
- **Filterable**: Each attribute is tagged with relevance to our four business problems, allowing focused simulation.

### 4.2 Data Sources for Taxonomy Grounding

These sources inform both the taxonomy structure AND the distribution parameters for each attribute.

| Source | Method | What We Extract | Attributes Informed |
|--------|--------|----------------|-------------------|
| **Amazon/Flipkart reviews** (Protinex, Pediasure, Horlicks, LittleJoys, Cerelac) | Scrape reviews + ratings | Price objections, trust language, switching triggers, competitor awareness, satisfaction drivers | price_sensitivity distribution, trust_requirement, brand_loyalty, switching_triggers |
| **BabyChakra, ParentCircle forums** | Scrape discussion threads | Health concerns by child age, information sources mothers trust, peer recommendation patterns | health_anxiety by child_age, authority_bias, peer_influence, information_channels |
| **Reddit r/IndianParents, Quora parenting** | Scrape Q&A threads | Skepticism patterns, word-of-mouth dynamics, brand perception | trust_formation, skepticism_level, wom_sensitivity |
| **Google Trends** (kids nutrition India, kids supplements, magnesium for kids) | Trends API | Geographic demand, seasonal patterns, relative search interest | awareness_level distributions by tier/region, seasonal_sensitivity |
| **NFHS-5 / NPI data** (publicly available) | Download datasets | Child nutrition gaps by income/geography, supplementation rates | health_need_objective, category_awareness baselines |
| **LittleJoys own reviews** (scraped from site) | Scrape product pages | What existing customers value, repeat purchase language, Pass references | satisfaction_drivers, repeat_triggers, pass_perception |
| **Instagram parenting influencer content** | Scrape hashtags #momlife #indianmom #kidsnutrition | Content themes, influencer trust patterns, aesthetic preferences | channel_effectiveness, influencer_trust, content_resonance |

### 4.3 Full Taxonomy Tree

```
SIMULATTE HUMAN ATTRIBUTE TAXONOMY v1.0
├── 1. DEMOGRAPHIC INFORMATION
│   ├── 1.1 Personal Demographics
│   │   ├── age (parent age, 22-45)
│   │   ├── gender
│   │   ├── marital_status
│   │   └── birth_order (firstborn parent vs. experienced)
│   ├── 1.2 Family Structure
│   │   ├── num_children (1-4)
│   │   ├── child_ages[] (array of ages, 0-18)
│   │   ├── child_genders[]
│   │   ├── joint_vs_nuclear_family
│   │   ├── elder_influence (grandparent involvement in child-rearing decisions)
│   │   └── spouse_involvement_in_purchases (0-1)
│   ├── 1.3 Socioeconomic
│   │   ├── household_income_lpa (₹ LPA, 3-50)
│   │   ├── income_stability (salaried/business/freelance/gig)
│   │   ├── socioeconomic_class (SEC A1/A2/B1/B2/C1/C2) — standard Indian classification
│   │   └── dual_income_household (boolean)
│   └── 1.4 Geographic
│       ├── city_tier (Tier1 / Tier2 / Tier3)
│       ├── city_name
│       ├── region (North/South/East/West/NE)
│       └── urban_vs_periurban
│
├── 2. PHYSICAL AND HEALTH CHARACTERISTICS
│   ├── 2.1 Child Health Context
│   │   ├── child_health_status (healthy/recurring_issues/chronic_condition)
│   │   ├── child_nutrition_concerns[] (underweight/picky_eater/low_immunity/low_energy/focus_issues)
│   │   ├── child_dietary_restrictions[] (lactose_intolerant/vegetarian/vegan/allergies)
│   │   ├── pediatrician_visit_frequency (monthly/quarterly/rarely/only_when_sick)
│   │   └── vaccination_attitude (proactive/follows_schedule/skeptical)
│   ├── 2.2 Parent Health Consciousness
│   │   ├── own_supplement_usage (boolean)
│   │   ├── fitness_engagement (0-1)
│   │   ├── diet_consciousness (0-1) — how much they think about diet quality
│   │   └── organic_preference (0-1)
│   └── 2.3 Health Information Behavior
│       ├── health_info_sources[] (pediatrician/google/instagram/friends/family_elders/apps)
│       ├── medical_authority_trust (0-1) — how much doctor's word weighs
│       └── self_research_tendency (0-1) — tendency to verify/research independently
│
├── 3. PSYCHOLOGICAL AND COGNITIVE ASPECTS
│   ├── 3.1 Decision-Making Style
│   │   ├── decision_speed (impulsive ← 0-1 → deliberate)
│   │   ├── information_need (low ← 0-1 → exhaustive_researcher)
│   │   ├── risk_tolerance (risk_averse ← 0-1 → risk_seeking)
│   │   ├── analysis_paralysis_tendency (0-1)
│   │   └── regret_sensitivity (0-1) — fear of making wrong choice for child
│   ├── 3.2 Cognitive Biases (relevant to purchase decisions)
│   │   ├── authority_bias (0-1) — influenced by experts/doctors/certifications
│   │   ├── social_proof_bias (0-1) — influenced by reviews/ratings/popularity
│   │   ├── anchoring_bias (0-1) — first price/brand encountered anchors expectations
│   │   ├── status_quo_bias (0-1) — preference for current solution over switching
│   │   ├── loss_aversion (0-1) — fear of losing money on something that "doesn't work"
│   │   └── halo_effect_susceptibility (0-1) — one positive attribute colors entire perception
│   ├── 3.3 Parenting Anxiety Profile
│   │   ├── health_anxiety (0-1) — worry about child's nutritional adequacy
│   │   ├── comparison_anxiety (0-1) — worry child is behind peers in growth/development
│   │   ├── guilt_sensitivity (0-1) — guilt about not doing enough for child's health
│   │   └── control_need (0-1) — need to control every aspect of child's intake
│   └── 3.4 Cognitive Load Context
│       ├── mental_bandwidth (0-1) — available cognitive capacity for new decisions
│       ├── decision_fatigue_level (0-1) — exhaustion from constant parenting decisions
│       └── simplicity_preference (0-1) — preference for simple/default options
│
├── 4. CULTURAL AND SOCIAL CONTEXT
│   ├── 4.1 Cultural Identity
│   │   ├── cultural_region (Punjabi/Tamil/Bengali/Marathi/Gujarati/etc.)
│   │   ├── dietary_culture (vegetarian/eggetarian/non_vegetarian/jain)
│   │   ├── traditional_vs_modern_spectrum (0-1) — traditional health beliefs ↔ modern medicine
│   │   ├── ayurveda_affinity (0-1) — trust in traditional Indian remedies
│   │   └── western_brand_trust (0-1) — trust in Western/international vs. Indian brands
│   ├── 4.2 Social Environment
│   │   ├── social_circle_ses (similar/aspirational/mixed)
│   │   ├── mommy_group_membership (boolean) — active in WhatsApp/FB parenting groups
│   │   ├── social_media_active (boolean)
│   │   └── community_orientation (individualist ← 0-1 → collectivist)
│   └── 4.3 Language & Communication
│       ├── primary_language
│       ├── english_proficiency (0-1)
│       └── content_language_preference (hindi/english/regional/bilingual)
│
├── 5. RELATIONSHIPS AND SOCIAL NETWORKS
│   ├── 5.1 Purchase Influence Network
│   │   ├── primary_decision_maker (self/spouse/joint/elder)
│   │   ├── peer_influence_strength (0-1) — how much friends' choices matter
│   │   ├── influencer_trust (0-1) — trust in social media parenting influencers
│   │   ├── elder_advice_weight (0-1) — how much in-laws/parents influence decisions
│   │   └── pediatrician_influence (0-1) — how much doctor recommendations drive purchases
│   ├── 5.2 Word of Mouth Dynamics
│   │   ├── wom_receiver_openness (0-1) — receptivity to recommendations
│   │   ├── wom_transmitter_tendency (0-1) — likelihood to recommend products to others
│   │   └── negative_wom_amplification (0-1) — how much bad experiences get shared
│   └── 5.3 Child Influence
│       ├── child_pester_power (0-1) — how much child's demands influence purchase (age-dependent)
│       ├── child_taste_veto (0-1) — will child's taste rejection override parent's decision
│       └── child_autonomy_given (0-1) — how much say does child have in what they consume
│
├── 6. CAREER AND WORK IDENTITY
│   ├── 6.1 Employment Context
│   │   ├── employment_status (working_fulltime/working_parttime/homemaker/freelance/business_owner)
│   │   ├── work_hours_per_week
│   │   ├── work_from_home (boolean)
│   │   └── career_ambition (0-1) — how career-focused vs family-focused
│   └── 6.2 Time Poverty
│       ├── perceived_time_scarcity (0-1)
│       ├── morning_routine_complexity (0-1) — how rushed is the morning routine
│       └── cooking_time_available (0-1) — time available for meal preparation
│
├── 7. EDUCATION AND LEARNING
│   ├── 7.1 Educational Background
│   │   ├── education_level (10th/12th/graduate/postgraduate/professional)
│   │   ├── science_literacy (0-1) — ability to evaluate nutritional claims
│   │   └── nutrition_knowledge (0-1) — specific knowledge about child nutrition
│   └── 7.2 Learning Behavior
│       ├── label_reading_habit (0-1) — reads ingredient lists/nutrition facts
│       ├── research_before_purchase (0-1) — googles before buying health products
│       └── content_consumption_depth (skimmer ← 0-1 → deep_reader)
│
├── 8. HOBBIES, INTERESTS, AND LIFESTYLE
│   ├── 8.1 Food and Cooking
│   │   ├── cooking_enthusiasm (0-1)
│   │   ├── recipe_experimentation (0-1) — willingness to try new recipes/ingredients
│   │   ├── meal_planning_habit (0-1)
│   │   └── convenience_food_acceptance (0-1) — comfort with packaged/processed foods
│   ├── 8.2 Health & Wellness Interest
│   │   ├── wellness_trend_follower (0-1)
│   │   ├── clean_label_importance (0-1) — importance of "no preservatives, no sugar" etc.
│   │   └── superfood_awareness (0-1) — knowledge of ragi, bajra, chia, etc.
│   └── 8.3 Parenting Style
│       ├── parenting_philosophy (helicopter/free_range/authoritative/permissive)
│       ├── screen_time_strictness (0-1)
│       └── structured_vs_intuitive_feeding (0-1)
│
├── 9. LIFESTYLE AND DAILY ROUTINE
│   ├── 9.1 Shopping Behavior
│   │   ├── online_vs_offline_preference (0-1) — 0=all offline, 1=all online
│   │   ├── primary_shopping_platform (amazon/flipkart/bigbasket/dmart/local_store/brand_website)
│   │   ├── subscription_comfort (0-1) — comfort with auto-replenishment
│   │   ├── bulk_buying_tendency (0-1)
│   │   ├── deal_seeking_intensity (0-1) — how much effort spent finding discounts
│   │   └── impulse_purchase_tendency (0-1)
│   ├── 9.2 Financial Behavior
│   │   ├── budget_consciousness (0-1)
│   │   ├── health_spend_priority (0-1) — willingness to spend more on health products
│   │   ├── price_reference_point (₹) — what they consider "normal" for a kids' supplement
│   │   ├── value_perception_driver (price_per_unit/brand/ingredients/results)
│   │   └── cashback_coupon_sensitivity (0-1) — how much discounts drive behavior
│   └── 9.3 Daily Routine
│       ├── breakfast_routine (elaborate/quick/skipped)
│       ├── milk_supplement_current (horlicks/bournvita/pediasure/none/other)
│       ├── gummy_vitamin_usage (boolean)
│       └── snacking_pattern (structured/grazing/restricted)
│
├── 10. CORE VALUES, BELIEFS, AND PHILOSOPHY
│   ├── 10.1 Health Beliefs
│   │   ├── supplement_necessity_belief (0-1) — "kids need supplements beyond food"
│   │   ├── natural_vs_synthetic_preference (0-1) — preference for plant-based/natural
│   │   ├── "food_first" belief (0-1) — "real food is enough, supplements are marketing"
│   │   └── preventive_vs_reactive_health (0-1) — invest in prevention vs. treat when sick
│   ├── 10.2 Brand Values
│   │   ├── brand_loyalty_tendency (0-1)
│   │   ├── indie_brand_openness (0-1) — openness to newer/smaller brands vs. established
│   │   ├── transparency_importance (0-1) — how much lab reports/ingredient disclosure matters
│   │   └── made_in_india_preference (0-1)
│   └── 10.3 Parenting Values
│       ├── "best_for_my_child" intensity (0-1) — willingness to pay premium for perceived best
│       ├── guilt_driven_spending (0-1) — compensates for time away with purchases
│       └── peer_comparison_drive (0-1) — keeping up with what other parents provide
│
├── 11. EMOTIONAL AND RELATIONAL SKILLS
│   ├── 11.1 Emotional Response to Marketing
│   │   ├── emotional_persuasion_susceptibility (0-1)
│   │   ├── fear_appeal_responsiveness (0-1) — "your child might be deficient" messaging
│   │   ├── aspirational_messaging_responsiveness (0-1) — "help your child reach full potential"
│   │   └── testimonial_impact (0-1) — "real mom stories" effectiveness
│   └── 11.2 Post-Purchase Emotional Processing
│       ├── buyer_remorse_tendency (0-1)
│       ├── confirmation_bias_strength (0-1) — tendency to see results because they paid
│       └── review_writing_tendency (0-1) — likelihood to leave reviews
│
└── 12. MEDIA CONSUMPTION AND ENGAGEMENT
    ├── 12.1 Digital Presence
    │   ├── primary_social_platform (instagram/facebook/youtube/whatsapp/none)
    │   ├── daily_social_media_hours (0-5)
    │   ├── content_format_preference (reels/stories/long_video/text_posts/podcasts)
    │   └── ad_receptivity (0-1) — how much they engage with vs. skip ads
    ├── 12.2 Information Discovery
    │   ├── product_discovery_channel (social_media/search/friend/doctor/store_shelf/ad)
    │   ├── review_platform_trust (amazon_reviews/google/instagram/youtube/mom_blogs)
    │   └── search_behavior (active_seeker/passive_absorber/recommendation_dependent)
    └── 12.3 App and E-commerce Behavior
        ├── app_download_willingness (0-1) — willingness to download a brand's app
        ├── wallet_topup_comfort (0-1) — comfort preloading money into brand wallet
        └── digital_payment_comfort (0-1) — UPI/card vs COD preference
```

**Total unique attributes: ~145 structured + expandable to 200+ with LLM narrative enrichment for Tier 2 personas**

---

## 5. COMPLETE PERSONA SCHEMA

### 5.1 Schema Structure

Every persona is composed of three layers with fundamentally different mutability characteristics:

```python
class Persona:
    """
    A synthetic persona representing one Indian parent in the LittleJoys
    target demographic. Designed as a reusable autonomous agent.
    """

    # ══════════════════════════════════════════════════════════════
    # LAYER 1: IDENTITY (IMMUTABLE)
    # Generated once. Never changes. This IS the person.
    # Derived from taxonomy via progressive attribute sampling.
    # ══════════════════════════════════════════════════════════════

    id: str                     # UUID
    generation_seed: int        # For reproducibility
    generation_timestamp: str
    tier: Literal["statistical", "deep"]

    # All 145 attributes from the taxonomy above, organized by category
    demographics: DemographicAttributes
    health: HealthAttributes
    psychology: PsychologyAttributes
    cultural: CulturalAttributes
    relationships: RelationshipAttributes
    career: CareerAttributes
    education: EducationAttributes
    lifestyle_interests: LifestyleInterestAttributes
    daily_routine: DailyRoutineAttributes
    values: ValueAttributes
    emotional: EmotionalAttributes
    media: MediaAttributes

    # Tier 2 only: LLM-generated narrative (~1-2 pages of biographical text)
    narrative: Optional[str]

    # ══════════════════════════════════════════════════════════════
    # LAYER 2: MEMORY (MUTABLE)
    # Accumulates over simulation steps and across business contexts.
    # This is what makes the agent reusable.
    # ══════════════════════════════════════════════════════════════

    episodic_memory: List[MemoryEntry]   # Specific events/interactions
    semantic_memory: Dict[str, Any]      # Learned facts/beliefs
    brand_memories: Dict[str, BrandMemory]  # Per-brand relationship history

    # ══════════════════════════════════════════════════════════════
    # LAYER 3: STATE (VOLATILE)
    # Changes per simulation step. Reset between scenarios.
    # ══════════════════════════════════════════════════════════════

    current_awareness: Dict[str, float]     # Product → awareness level
    current_consideration_set: List[str]    # Products being evaluated
    current_satisfaction: Dict[str, float]  # Product → satisfaction
    purchase_history: List[PurchaseEvent]
    time_state: TemporalState               # For multi-step simulations


class BrandMemory:
    """What this persona knows/feels about a specific brand."""
    brand_name: str
    first_exposure: Optional[str]       # When they first heard of it
    exposure_channel: Optional[str]     # How they first heard
    trust_level: float                  # 0-1, evolves over time
    purchase_count: int
    last_purchase_date: Optional[str]
    satisfaction_history: List[float]
    has_pass: bool                      # For LJ Pass modeling
    word_of_mouth_received: List[str]   # What they've heard from others
    word_of_mouth_given: List[str]      # What they've told others


class MemoryEntry:
    """A single episodic memory."""
    timestamp: str
    event_type: str     # "ad_exposure", "purchase", "product_use", "friend_recommendation", etc.
    content: str        # What happened
    emotional_valence: float  # -1 to 1 (negative to positive experience)
    salience: float     # 0-1 (how memorable/impactful)


class PurchaseEvent:
    timestamp: str
    product: str
    price_paid: float
    channel: str
    trigger: str        # What caused this purchase
    satisfaction: float # Post-purchase satisfaction
```

### 5.2 Correlation Rules (Enforced During Generation)

These are not suggestions — the generator MUST enforce these correlations to produce realistic personas. Implementation: Gaussian copula on the continuous (0-1) attributes, with demographic-conditional marginals.

```python
CORRELATION_RULES = {
    # ── DEMOGRAPHICS → PSYCHOGRAPHICS ──
    ("household_income_lpa", "budget_consciousness"): -0.55,
    ("household_income_lpa", "deal_seeking_intensity"): -0.40,
    ("household_income_lpa", "health_spend_priority"): 0.35,
    ("household_income_lpa", "indie_brand_openness"): 0.25,
    ("city_tier=Tier3", "medical_authority_trust"): 0.50,
    ("city_tier=Tier3", "authority_bias"): 0.45,
    ("city_tier=Tier3", "digital_payment_comfort"): -0.35,
    ("city_tier=Tier3", "elder_advice_weight"): 0.40,
    ("city_tier=Tier1", "online_vs_offline_preference"): 0.45,
    ("city_tier=Tier1", "app_download_willingness"): 0.35,
    ("education_level=postgraduate+", "science_literacy"): 0.50,
    ("education_level=postgraduate+", "label_reading_habit"): 0.40,
    ("education_level=postgraduate+", "self_research_tendency"): 0.45,
    ("joint_vs_nuclear_family=joint", "elder_advice_weight"): 0.55,
    ("num_children>2", "budget_consciousness"): 0.35,
    ("num_children=1", "health_anxiety"): 0.40,  # First-time parents more anxious
    ("num_children=1", "guilt_sensitivity"): 0.35,

    # ── DEMOGRAPHICS → BEHAVIOR ──
    ("employment_status=working_fulltime", "perceived_time_scarcity"): 0.55,
    ("employment_status=working_fulltime", "cooking_time_available"): -0.50,
    ("employment_status=working_fulltime", "convenience_food_acceptance"): 0.40,
    ("employment_status=working_fulltime", "guilt_driven_spending"): 0.35,
    ("employment_status=homemaker", "cooking_enthusiasm"): 0.35,
    ("employment_status=homemaker", "recipe_experimentation"): 0.30,
    ("dual_income_household", "health_spend_priority"): 0.30,

    # ── PSYCHOGRAPHIC → PSYCHOGRAPHIC ──
    ("health_anxiety", "supplement_necessity_belief"): 0.55,
    ("health_anxiety", "preventive_vs_reactive_health"): 0.45,
    ("health_anxiety", "health_spend_priority"): 0.50,
    ("health_anxiety", "budget_consciousness"): -0.25,  # Will overspend for child health
    ("comparison_anxiety", "peer_influence_strength"): 0.50,
    ("comparison_anxiety", "social_proof_bias"): 0.45,
    ("guilt_sensitivity", "best_for_my_child_intensity"): 0.55,
    ("guilt_sensitivity", "emotional_persuasion_susceptibility"): 0.40,
    ("science_literacy", "authority_bias"): -0.30,  # More literate → less blindly trusting authority
    ("science_literacy", "food_first_belief"): 0.25,  # More literate → may believe food suffices
    ("status_quo_bias", "brand_loyalty_tendency"): 0.50,
    ("status_quo_bias", "risk_tolerance"): -0.40,
    ("simplicity_preference", "decision_speed"): -0.30,  # Prefer simple → decide faster
    ("traditional_vs_modern_spectrum", "ayurveda_affinity"): -0.55,  # More traditional → more ayurveda
    ("traditional_vs_modern_spectrum", "western_brand_trust"): 0.45,

    # ── CHILD AGE EFFECTS (critical for LittleJoys) ──
    ("child_age<4", "health_anxiety"): 0.40,  # Younger child → more anxious
    ("child_age>7", "child_taste_veto"): 0.50,  # Older child → more taste influence
    ("child_age>7", "child_pester_power"): 0.45,
    ("child_age>10", "child_autonomy_given"): 0.55,
    ("child_age>7", "supplement_necessity_belief"): -0.20,  # "Older kids don't need supplements"

    # ── BEHAVIORAL CHAINS ──
    ("label_reading_habit", "transparency_importance"): 0.55,
    ("label_reading_habit", "clean_label_importance"): 0.50,
    ("research_before_purchase", "information_need"): 0.60,
    ("research_before_purchase", "decision_speed"): 0.40,  # Research → more deliberate
    ("online_vs_offline_preference", "subscription_comfort"): 0.40,
    ("online_vs_offline_preference", "digital_payment_comfort"): 0.50,
    ("mommy_group_membership", "peer_influence_strength"): 0.45,
    ("mommy_group_membership", "wom_receiver_openness"): 0.40,
    ("mommy_group_membership", "wom_transmitter_tendency"): 0.35,
    ("cooking_enthusiasm", "recipe_experimentation"): 0.50,
    ("cooking_time_available", "recipe_experimentation"): 0.35,
}

# ── CONDITIONAL DISTRIBUTIONS (non-linear relationships) ──
CONDITIONAL_RULES = {
    # If parent currently uses a milk supplement, they understand the category
    "milk_supplement_current != 'none'": {
        "supplement_necessity_belief": "shift_up_0.2",
        "price_reference_point": "set_range_300_700",
    },
    # If child has specific health concerns, certain attributes shift
    "child_nutrition_concerns contains 'picky_eater'": {
        "cooking_enthusiasm": "shift_down_0.15",
        "convenience_food_acceptance": "shift_up_0.2",
        "health_anxiety": "shift_up_0.15",
    },
    # If in a mommy group AND social_proof_bias high → amplified peer influence
    "mommy_group_membership AND social_proof_bias > 0.6": {
        "peer_influence_strength": "shift_up_0.2",
    },
}
```

### 5.3 Demographic Distribution Tables (Bias-Free Assignment)

Following DeepPersona's principle: draw demographic values from real distribution tables, NOT the LLM.

```python
DEMOGRAPHIC_DISTRIBUTIONS = {
    "city_tier": {"Tier1": 0.45, "Tier2": 0.35, "Tier3": 0.20},
    # Based on India's D2C e-commerce customer distribution

    "household_income_lpa": {
        "Tier1": {"distribution": "lognormal", "mean": 12, "std": 8, "min": 4, "max": 50},
        "Tier2": {"distribution": "lognormal", "mean": 7, "std": 4, "min": 3, "max": 25},
        "Tier3": {"distribution": "lognormal", "mean": 5, "std": 3, "min": 2, "max": 15},
    },

    "parent_age": {
        "distribution": "truncated_normal", "mean": 32, "std": 5, "min": 22, "max": 45
    },

    "child_age": {
        # For LittleJoys simulation, we oversample 2-14 range
        "distribution": "uniform", "min": 2, "max": 14
    },

    "num_children": {
        1: 0.40, 2: 0.45, 3: 0.12, 4: 0.03
    },

    "education_level": {
        "Tier1": {"10th": 0.02, "12th": 0.08, "graduate": 0.45, "postgraduate": 0.35, "professional": 0.10},
        "Tier2": {"10th": 0.05, "12th": 0.15, "graduate": 0.50, "postgraduate": 0.25, "professional": 0.05},
        "Tier3": {"10th": 0.10, "12th": 0.25, "graduate": 0.45, "postgraduate": 0.15, "professional": 0.05},
    },

    "employment_status": {
        "working_fulltime": 0.35, "working_parttime": 0.10, "homemaker": 0.40,
        "freelance": 0.08, "business_owner": 0.07
    },

    "dietary_culture": {
        "North": {"vegetarian": 0.35, "eggetarian": 0.15, "non_vegetarian": 0.50},
        "South": {"vegetarian": 0.20, "eggetarian": 0.10, "non_vegetarian": 0.70},
        "West": {"vegetarian": 0.45, "eggetarian": 0.10, "non_vegetarian": 0.35, "jain": 0.10},
        "East": {"vegetarian": 0.10, "eggetarian": 0.10, "non_vegetarian": 0.80},
    },

    "joint_vs_nuclear_family": {
        "Tier1": {"nuclear": 0.70, "joint": 0.30},
        "Tier2": {"nuclear": 0.55, "joint": 0.45},
        "Tier3": {"nuclear": 0.40, "joint": 0.60},
    },

    "milk_supplement_current": {
        "horlicks": 0.25, "bournvita": 0.20, "pediasure": 0.10,
        "complan": 0.05, "littlejoys": 0.05, "other": 0.05, "none": 0.30
    },
}
```

---

## 6. PERSONA GENERATION ENGINE

### 6.1 Two-Tier Architecture

**Tier 1: Statistical Personas (N=300-1000)**
- Pure numerical/categorical attributes from the taxonomy
- Generated via Gaussian copula sampling with enforced correlations
- Used for all quantitative simulations
- Generation time: seconds (no LLM calls)
- Deterministic and reproducible given a seed

**Tier 2: Deep Narrative Personas (N=30-50, subset of Tier 1)**
- Same numerical attributes PLUS LLM-generated biographical narrative
- Following DeepPersona's progressive attribute sampling: anchor core → diversify → fill progressively
- Target: 200-250 total attributes per persona (including narrative-embedded implicit attributes)
- Narrative is ~1-2 pages of coherent biographical text grounded in the numerical attributes
- Used for: qualitative interviews, demo "wow factor", messaging testing
- Generation time: ~30-60 seconds per persona (LLM calls required)

### 6.2 Generation Pipeline

```
Step 1: Sample Demographics (from distribution tables, NO LLM)
    → age, city_tier, income, num_children, child_ages, education, employment, dietary_culture

Step 2: Generate Correlated Psychographics (Gaussian copula)
    → All 0-1 scale attributes, enforcing correlation rules
    → Apply conditional rules (e.g., if picky_eater child → shift attributes)

Step 3: Assign Categorical Behaviors (conditional sampling)
    → shopping_platform, health_info_sources, primary_social_platform, etc.
    → Conditioned on demographics + psychographics

Step 4: Validate Consistency
    → Run constraint checks (no contradictions: e.g., Tier3 + low digital comfort + primary platform = app)
    → Flag and regenerate inconsistent personas

Step 5 (Tier 2 only): Generate Narrative via LLM
    → Progressive attribute sampling following DeepPersona
    → Anchor: demographics + top 5 psychographics + life situation
    → Expand: values → life attitude → personal story → interests → detailed preferences
    → Result: Coherent biographical narrative + 50-100 additional implicit attributes

Step 6: Initialize Memory and State
    → Empty episodic memory
    → Semantic memory seeded with general category knowledge based on attributes
    → Brand memories initialized from milk_supplement_current + gummy_vitamin_usage
    → State zeroed out (will be set per scenario)
```

### 6.3 Persona Validation Checks

Before any persona enters simulation:
```python
VALIDATION_RULES = [
    # Logical consistency
    "child_age >= 2 AND child_age <= 14",
    "parent_age >= child_age + 18",
    "parent_age >= 22",
    "household_income_lpa >= 2",

    # Correlational sanity (soft checks — flag but don't reject)
    "IF city_tier == 'Tier3' AND online_vs_offline_preference > 0.9 THEN WARN",
    "IF household_income_lpa < 5 AND health_spend_priority > 0.9 THEN WARN",
    "IF education_level == '10th' AND science_literacy > 0.8 THEN WARN",

    # Distribution checks (across population)
    "population.city_tier.distribution ~= target_distribution (chi-square p > 0.05)",
    "population.income.mean within 20% of target",
    "population.child_age.distribution ~= uniform(2,14)",
]
```

---

## 7. DECISION ENGINE

### 7.1 Multi-Layer Purchase Funnel

The decision engine models a realistic purchase funnel, not a single utility calculation.

```
LAYER 0: NEED RECOGNITION
    "Does this parent even perceive a need for this product category?"
         │
         ▼
LAYER 1: AWARENESS
    "Has this parent heard of this specific product?"
         │
         ▼
LAYER 2: CONSIDERATION
    "Is this parent willing to evaluate this product?"
         │
         ▼
LAYER 3: PURCHASE DECISION
    "Will this parent actually buy?"
         │
         ▼
LAYER 4: POST-PURCHASE & REPEAT (temporal mode only)
    "Will they buy again? Will they churn?"
```

### 7.2 Layer Equations

```python
# ══════════════════════════════════════════════════════════════
# LAYER 0: NEED RECOGNITION
# ══════════════════════════════════════════════════════════════

def compute_need_recognition(persona, product):
    """Does this parent perceive a need for this product category?"""

    base_need = product.category_need_baseline  # Set per product

    # Amplifiers
    need = base_need
    need += persona.health_anxiety * 0.3
    need += persona.supplement_necessity_belief * 0.3
    need += persona.comparison_anxiety * 0.1
    need += persona.guilt_sensitivity * 0.1

    # Dampeners
    need -= persona.food_first_belief * 0.3

    # Child-age modifier (critical for Problem #2)
    if product.target_age_min > 6:
        # Parents of older kids perceive less need for supplements
        age_penalty = 0.15 * (1 - persona.health_anxiety)
        need -= age_penalty

    # Child health concerns boost need
    if any(concern in product.addresses_concerns for concern in persona.child_nutrition_concerns):
        need += 0.2

    return clip(need, 0, 1)


# ══════════════════════════════════════════════════════════════
# LAYER 1: AWARENESS FILTER
# ══════════════════════════════════════════════════════════════

def compute_awareness(persona, scenario):
    """Has this parent heard of this specific product?"""

    base_awareness = scenario.awareness_level

    # Channel-specific awareness boost
    channel_match = 0
    for channel in scenario.marketing_channels:
        if channel in persona.product_discovery_channels:
            channel_match += scenario.channel_intensity[channel] * persona.ad_receptivity

    # Social proof boost
    if persona.mommy_group_membership:
        channel_match += scenario.social_buzz * persona.wom_receiver_openness * 0.3

    awareness = base_awareness + channel_match

    # Existing brand customer → already aware
    if persona.brand_memories.get("littlejoys", {}).get("purchase_count", 0) > 0:
        awareness = max(awareness, 0.9)

    return clip(awareness, 0, 1)


# ══════════════════════════════════════════════════════════════
# LAYER 2: CONSIDERATION GATE
# ══════════════════════════════════════════════════════════════

def compute_consideration(persona, product, scenario, awareness):
    """Is this parent willing to seriously evaluate this product?"""

    # Must clear awareness threshold
    if awareness < 0.3:
        return 0.0

    # Switching cost (if currently using a competitor)
    switching_barrier = 0
    if persona.milk_supplement_current != "none" and persona.milk_supplement_current != "littlejoys":
        switching_barrier = (
            persona.status_quo_bias * 0.4
            + persona.brand_loyalty_tendency * 0.3
            + persona.loss_aversion * 0.2
        )

    # Trust gate
    trust_score = (
        scenario.trust_signal * 0.3
        + persona.authority_bias * scenario.expert_endorsement * 0.25
        + persona.social_proof_bias * scenario.social_proof * 0.25
        + persona.influencer_trust * scenario.influencer_signal * 0.2
    )

    # Persona's trust requirement must be met
    trust_gap = max(0, persona.trust_requirement - trust_score)

    consideration = awareness * (1 - switching_barrier) * (1 - trust_gap)

    return clip(consideration, 0, 1)


# ══════════════════════════════════════════════════════════════
# LAYER 3: PURCHASE DECISION
# ══════════════════════════════════════════════════════════════

def compute_purchase(persona, product, scenario, consideration):
    """Will this parent actually buy?"""

    if consideration < 0.3:
        return 0.0, "did_not_consider"

    # Value perception
    income_factor = persona.household_income_lpa / 10
    price_pain = persona.budget_consciousness * (product.price / (income_factor * 100))

    perceived_value = (
        persona.quality_preference * scenario.perceived_quality * 0.3
        + persona.clean_label_importance * product.clean_label_score * 0.2
        + persona.health_anxiety * product.health_relevance * 0.25
        + persona.best_for_my_child_intensity * product.premium_positioning * 0.15
        + persona.superfood_awareness * product.superfood_score * 0.1
    )

    # Effort barrier
    effort_pain = persona.perceived_time_scarcity * product.effort_required * 0.4
    effort_pain += persona.simplicity_preference * product.complexity * 0.3
    effort_pain += (1 - persona.cooking_enthusiasm) * product.cooking_required * 0.3

    # Deal sweetener
    deal_boost = persona.cashback_coupon_sensitivity * scenario.discount_available * 0.15

    # Final utility
    utility = (
        perceived_value * consideration
        - price_pain
        - effort_pain
        + deal_boost
    )

    # Threshold (calibrated, not hardcoded)
    threshold = scenario.calibrated_threshold  # Default 0.35, adjusted per scenario

    if utility > threshold:
        return utility, "adopt"
    else:
        # Classify rejection reason (for causal analysis)
        if price_pain > perceived_value * 0.5:
            return utility, "price_barrier"
        elif effort_pain > 0.3:
            return utility, "effort_barrier"
        elif consideration < 0.5:
            return utility, "trust_barrier"
        else:
            return utility, "low_perceived_value"


# ══════════════════════════════════════════════════════════════
# LAYER 4: REPEAT PURCHASE (Temporal Mode)
# ══════════════════════════════════════════════════════════════

def compute_repeat(persona, product, month, purchase_history):
    """Will they repurchase this month? (Called each simulation month)"""

    if len(purchase_history) == 0:
        return 0.0

    # Satisfaction from last purchase
    last_satisfaction = purchase_history[-1].satisfaction

    # Habit formation (increases with consecutive purchases)
    consecutive_months = count_consecutive(purchase_history)
    habit_factor = 1 - math.exp(-0.3 * consecutive_months)  # Approaches 1 asymptotically

    # Price fatigue (diminishes with habit)
    income_factor = persona.household_income_lpa / 10
    price_fatigue = persona.budget_consciousness * (product.price / (income_factor * 100)) * (1 - habit_factor * 0.5)

    # Reorder friction
    if persona.subscription_comfort > 0.7 and product.subscription_available:
        reorder_friction = 0.05  # Auto-replenishment = near-zero friction
    else:
        reorder_friction = persona.perceived_time_scarcity * 0.3

    # LJ Pass effect (Problem #1 specific)
    pass_multiplier = 1.0
    if persona.brand_memories.get("littlejoys", {}).get("has_pass", False):
        pass_multiplier = 1.0 + (
            persona.cashback_coupon_sensitivity * 0.15  # 5% cashback matters more to deal-seekers
            + persona.brand_loyalty_tendency * 0.10     # Pass reinforces loyalty
            + (1 - persona.loss_aversion) * 0.05        # Sunk cost of pass purchase
        )

    repeat_prob = (
        last_satisfaction * 0.35
        + habit_factor * 0.25
        - price_fatigue * 0.20
        - reorder_friction * 0.10
        + persona.brand_loyalty_tendency * 0.10
    ) * pass_multiplier

    return clip(repeat_prob, 0, 1)
```

### 7.3 Threshold Calibration Strategy

DO NOT hardcode thresholds. Instead:

1. **Baseline Scenario**: Run Nutrimix 2-6 (the known strong seller) against the population
2. **Target**: LittleJoys' actual conversion rate (ask client, or estimate ~8-15% for D2C health products)
3. **Calibrate**: Adjust `calibrated_threshold` until simulated adoption matches target
4. **Lock**: Use this threshold across all scenarios
5. **Result**: Relative comparisons between scenarios are meaningful even if absolute rates are approximate

---

## 8. SIMULATION ENGINE

### 8.1 Mode A: Static Snapshot (Problems 2, 3, 4)

Single-pass evaluation of all personas against a scenario.

```python
def run_static_simulation(population, scenario):
    results = []
    for persona in population:
        need = compute_need_recognition(persona, scenario.product)
        awareness = compute_awareness(persona, scenario)
        consideration = compute_consideration(persona, scenario.product, scenario, awareness)
        utility, decision = compute_purchase(persona, scenario.product, scenario, consideration)

        results.append({
            "persona_id": persona.id,
            "need": need,
            "awareness": awareness,
            "consideration": consideration,
            "utility": utility,
            "decision": decision,
            # Store all intermediate values for causal analysis
            "funnel_stage_reached": determine_funnel_stage(need, awareness, consideration, decision),
            "primary_barrier": decision if decision != "adopt" else None,
        })

    return SimulationResult(results, population, scenario)
```

### 8.2 Mode B: Temporal Simulation (Problem 1)

Multi-step simulation with state evolution.

```python
def run_temporal_simulation(population, scenario, months=6):
    monthly_results = []

    for month in range(1, months + 1):
        month_result = {"month": month, "new_adopters": 0, "repeat_purchasers": 0, "churned": 0}

        for persona in population:
            if persona.has_purchased(scenario.product):
                # Existing customer → repeat decision
                repeat_prob = compute_repeat(persona, scenario.product, month, persona.purchase_history)
                if random.random() < repeat_prob:
                    persona.record_purchase(scenario.product, month)
                    month_result["repeat_purchasers"] += 1
                else:
                    month_result["churned"] += 1
            else:
                # Non-customer → run full funnel
                # Awareness may increase month-over-month (word of mouth, ads)
                scenario_month = evolve_scenario(scenario, month, population)
                _, decision = run_single_persona(persona, scenario_month)
                if decision == "adopt":
                    persona.record_purchase(scenario.product, month)
                    month_result["new_adopters"] += 1

        # Word-of-mouth propagation between months
        propagate_wom(population, scenario.product, month)

        monthly_results.append(month_result)

    return TemporalSimulationResult(monthly_results, population, scenario)
```

### 8.3 Counterfactual Engine

```python
def run_counterfactual(population, base_scenario, perturbations):
    """
    perturbations = [
        {"name": "Price -20%", "changes": {"price": lambda x: x * 0.8}},
        {"name": "Doctor endorsement", "changes": {"expert_endorsement": 0.9, "trust_signal": 0.85}},
        {"name": "Free trial sachet", "changes": {"effort_required": 0.1, "price": 0, "trial_mode": True}},
        {"name": "Momfluencer campaign", "changes": {"social_proof": 0.8, "influencer_signal": 0.9, "awareness_level": lambda x: min(x * 1.5, 1.0)}},
        {"name": "LJ Pass 10% cashback", "changes": {"pass_cashback": 0.10}},
        {"name": "Reduce to ₹399", "changes": {"price": 399}},
    ]
    """
    base_result = run_static_simulation(population, base_scenario)

    counterfactual_results = [{"name": "Baseline", "result": base_result}]

    for cf in perturbations:
        modified_scenario = base_scenario.copy()
        for param, change in cf["changes"].items():
            if callable(change):
                setattr(modified_scenario, param, change(getattr(modified_scenario, param)))
            else:
                setattr(modified_scenario, param, change)

        cf_result = run_static_simulation(population, modified_scenario)
        counterfactual_results.append({"name": cf["name"], "result": cf_result})

    return CounterfactualComparison(counterfactual_results)
```

---

## 9. ANALYSIS & REPORTING ENGINE

### 9.1 Automated Analysis Pipeline

Every simulation run produces:

1. **Funnel Waterfall**: How many personas drop at each stage (need → awareness → consideration → purchase)
2. **Segment Adoption Heatmaps**: 2D grid of adoption rates by any two attributes
3. **Variable Importance**: Logistic regression / SHAP on persona attributes predicting adoption — which attributes matter most?
4. **Barrier Distribution**: Pie chart of WHY non-adopters rejected (price / effort / trust / awareness / perceived value)
5. **Causal Statements**: Machine-generated, variable-grounded insights (NOT "users found it expensive" but "personas with budget_consciousness > 0.7 AND household_income_lpa < 8 had 73% rejection rate, primarily due to price_pain exceeding perceived_value by 0.3+ in the utility calculation")
6. **Counterfactual Delta Table**: Which intervention moves the needle most, for which segments?

### 9.2 LLM ReportAgent (for Tier 2 Deep Insights)

Inspired by MiroFish's ReACT ReportAgent pattern.

```python
REPORT_AGENT_TOOLS = {
    "query_segment": "Get adoption metrics for a filtered segment (e.g., Tier2 mothers with child_age 7-10)",
    "compare_segments": "Compare two segments head-to-head on any metric",
    "explain_persona": "Get full decision trace for a specific persona — why they adopted/rejected",
    "run_counterfactual": "Perturb a scenario parameter and get new results",
    "interview_persona": "Chat with a Tier 2 persona about their decision (LLM role-play)",
    "get_barrier_distribution": "Get distribution of rejection reasons for a segment",
    "get_variable_importance": "Get ranked list of attributes driving adoption/rejection",
}
```

The ReportAgent:
1. Receives raw simulation results
2. Uses tools to dig into interesting patterns
3. Generates a structured markdown report with sections: Executive Summary, Key Findings, Segment Analysis, Barrier Analysis, Recommendations, Counterfactual Results
4. Can answer follow-up questions from the client interactively

### 9.3 Deep Persona Interviews

For the 30-50 Tier 2 personas, enable interactive conversation:

```python
INTERVIEW_SYSTEM_PROMPT = """
You are {persona.name}, a {persona.demographics.age}-year-old {persona.demographics.employment_status}
living in {persona.demographics.city_name} ({persona.demographics.city_tier}).
You have {persona.demographics.num_children} child(ren) aged {persona.demographics.child_ages}.

Your full profile:
{persona.narrative}

Your decision about {product.name}:
You {persona.decision} this product.
{'You bought it because: ' + persona.adoption_reason if persona.decision == 'adopt' else 'You did not buy it because: ' + persona.rejection_reason}

RULES:
- Stay completely in character
- Reference specific details from your profile
- If asked about price, relate it to your actual income and spending patterns
- If asked about trust, reference your actual information sources and decision style
- Do not break character or acknowledge you are an AI
- Speak naturally, as this person would speak (use Hindi-English code-mixing if it fits the persona)
"""
```

---

## 10. AUTONOMOUS AGENT INFRASTRUCTURE

### 10.1 Design Philosophy: Agents as Reusable Building Blocks

These personas are NOT disposable simulation inputs. They are **persistent autonomous agents** that form the core infrastructure of Simulatte's product. The same agent must be deployable across multiple business contexts:

- Today: "Would you buy LittleJoys Nutrimix 7+?"
- Tomorrow: "Would you switch to Brand X baby food?"
- Next week: "How would you respond to a ₹200 price increase on your current supplement?"

This is achieved through the **three-layer separation** (Identity / Memory / State):

```
┌─────────────────────────────────────────────┐
│              AUTONOMOUS AGENT                 │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │  IDENTITY (Immutable)                    │ │
│  │  Who this person IS                      │ │
│  │  Demographics, psychographics, values,   │ │
│  │  cognitive style, daily routine, etc.    │ │
│  │  Generated ONCE. Never changes.          │ │
│  └─────────────────────────────────────────┘ │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │  MEMORY (Persistent, Mutable)            │ │
│  │  What this person has EXPERIENCED        │ │
│  │  Episodic: specific events, purchases    │ │
│  │  Semantic: learned facts, beliefs        │ │
│  │  Brand: relationship with each brand     │ │
│  │  Grows over time. Survives across sims.  │ │
│  └─────────────────────────────────────────┘ │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │  PERCEPTION (Injected per scenario)      │ │
│  │  What this person is being SHOWN         │ │
│  │  Product attributes, price, marketing    │ │
│  │  channels, trust signals, social proof.  │ │
│  │  Changes per simulation. Scenario-owned. │ │
│  └─────────────────────────────────────────┘ │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │  DECISION INTERFACE                      │ │
│  │  How this person DECIDES                 │ │
│  │  Takes: Identity + Memory + Perception   │ │
│  │  Returns: Decision + Reasoning trace     │ │
│  │  Deterministic for Tier 1                │ │
│  │  LLM-augmented for Tier 2               │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### 10.2 Agent Serialization & Storage

```
/agents/
  /population_v1/
    /metadata.json          # Population generation parameters, seed, timestamp
    /tier1/
      /agents.parquet       # All N statistical agents in columnar format (fast bulk ops)
    /tier2/
      /agent_{uuid}.json    # Individual deep agents with full narrative
    /memories/
      /agent_{uuid}_memory.json  # Separate memory files (grow independently)
    /validation_report.json # Population distribution validation results
```

### 10.3 Agent Reuse Protocol

When deploying the same population against a new client/scenario:

```python
def deploy_population_for_new_context(population, new_context):
    """
    Reuse existing agents with a new business context.
    Identity stays. Memory can be selectively updated. State resets.
    """
    for agent in population:
        # Identity: UNCHANGED

        # Memory: Inject new context-specific knowledge
        agent.memory.inject_semantic({
            "brand_awareness": new_context.brand_info,
            "category_knowledge": new_context.category_info,
            "market_context": new_context.market_info,
        })

        # State: RESET for new simulation
        agent.state = fresh_state()

        # Perception: Will be injected by the new scenario

    return population
```

### 10.4 Future Agent Capabilities (Post-POC Roadmap)

- **Inter-agent communication**: Agents influence each other's decisions (word-of-mouth propagation)
- **Longitudinal tracking**: Same agent tracked over months/years, accumulating real purchase history
- **Cross-category deployment**: Same agent evaluated on food, personal care, education products
- **Agent-to-agent markets**: Simulated social environments where agents share opinions
- **Reinforcement learning**: Agents that learn and update their decision patterns based on outcomes

---

## 11. IMPLEMENTATION PLAN — COMPRESSED TIMELINE

### Philosophy: Build Deep, Demo Smart

We have ~10-12 working days. The key insight: we don't need to build everything production-ready. We need to build the **core engine correctly** and wrap it in a **demo layer that showcases the full vision**. The client buys the vision backed by real results, not the polish.

### Sprint Structure

```
DAY 1-2: FOUNDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Day 1 (Full Day):
  Morning:
    □ Project scaffolding (Python project, deps, folder structure)
    □ Implement Persona data classes (all 145 attributes, 3 layers)
    □ Implement demographic distribution tables
    □ Implement Gaussian copula generator for correlated psychographics

  Afternoon:
    □ Implement correlation enforcement rules
    □ Implement conditional distribution rules
    □ Implement validation checks
    □ Generate first population of 300 Tier 1 personas
    □ Validate distributions (histograms, correlation matrix heatmap)

Day 2 (Full Day):
  Morning:
    □ Web scraping pipeline (Amazon reviews, BabyChakra, Google Trends)
    □ Process scraped data into distribution parameters
    □ Refine attribute distributions with real data

  Afternoon:
    □ Tier 2 persona generation (LLM narrative engine)
    □ Generate 30 deep personas with biographical narratives
    □ Implement persona serialization/storage

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DAY 3-4: DECISION & SIMULATION ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Day 3 (Full Day):
  Morning:
    □ Implement Layer 0-3 decision functions
    □ Implement scenario configuration system
    □ Calibration run: Nutrimix 2-6 baseline scenario
    □ Threshold calibration

  Afternoon:
    □ Implement all 4 business problem scenarios
    □ Run static simulations for Problems 2, 3, 4
    □ Implement counterfactual engine
    □ Run counterfactuals for each scenario

Day 4 (Full Day):
  Morning:
    □ Implement temporal simulation (Mode B) for Problem #1
    □ Implement repeat purchase model + LJ Pass effect
    □ Implement word-of-mouth propagation between months

  Afternoon:
    □ Run 6-month temporal simulation for LJ Pass scenarios
    □ Implement automated analysis pipeline
    □ Generate segment breakdowns, barrier distributions, variable importance

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DAY 5-6: ANALYSIS, REPORTING, INTERVIEWS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Day 5 (Full Day):
  Morning:
    □ Implement causal attribution engine
    □ Implement SHAP / logistic regression for variable importance
    □ Generate causal insight statements (grounded in variables)

  Afternoon:
    □ Implement LLM ReportAgent with tool access
    □ Generate structured reports for all 4 business problems
    □ Test ReportAgent follow-up question capability

Day 6 (Full Day):
  Morning:
    □ Implement Deep Persona interview system
    □ Test interviews with 5 personas (adopters + rejectors)
    □ Fine-tune interview prompts for realism

  Afternoon:
    □ Run complete end-to-end pipeline for all 4 scenarios
    □ Validate all results for consistency and realism
    □ Fix any calibration issues

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DAY 7-8: PRESENTATION LAYER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Day 7 (Full Day):
  Morning:
    □ Streamlit app scaffolding
    □ Population explorer page (scatter plots, distribution charts)
    □ Scenario configurator page (input sliders, product selector)

  Afternoon:
    □ Results dashboard (funnel waterfall, segment heatmaps, barrier pie charts)
    □ Counterfactual comparison page (before/after tables, delta charts)

Day 8 (Full Day):
  Morning:
    □ Persona interview chat interface
    □ ReportAgent interactive page
    □ "What-if?" mode (client changes parameters, re-runs live)

  Afternoon:
    □ Visual polish, loading states, transitions
    □ Pre-load all 4 scenario results for instant demo
    □ Test full demo flow end-to-end

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DAY 9-10: HARDENING & DEMO PREP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Day 9:
  □ Edge case handling, error states
  □ Pre-compute all demo scenarios (no live failures during demo)
  □ Write narrative wrapper for each business problem
    (opening slide: problem → what we did → key finding → recommendation)

Day 10:
  □ Full dry-run of demo
  □ Prepare backup static results (in case of live demo failure)
  □ Documentation: methodology doc for client
  □ Record demo video as backup
```

### Critical Path

The minimum viable demo requires Days 1-5. Days 6-8 elevate it from "interesting analysis" to "holy shit" demo. Days 9-10 are insurance.

If time is even tighter (7 days), cut:
- Day 6 morning (interviews can be shown as a concept with 2-3 pre-recorded examples)
- Day 8 afternoon polish (functional > pretty)
- Day 9 edge cases (pre-compute everything, no live computation during demo)

---

## 12. TECH STACK & PROJECT STRUCTURE

### Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Language** | Python 3.11+ | Data ecosystem, LLM libraries, Streamlit compat |
| **Persona Generation** | NumPy + SciPy (copula) | Efficient correlated sampling, no heavy deps |
| **Decision Engine** | Pure Python / NumPy | Deterministic, auditable, fast |
| **LLM (bulk generation)** | Claude Sonnet 4 | Cost-effective for persona narrative generation |
| **LLM (analysis/reports)** | Claude Opus 4 | Best reasoning for causal analysis and interviews |
| **Data Store** | Parquet (Tier 1) + JSON (Tier 2, Memory) | Fast columnar queries + flexible document store |
| **Analysis** | scikit-learn (logistic reg), shap | Variable importance, SHAP values |
| **Visualization** | Plotly | Interactive charts, Streamlit integration |
| **Dashboard** | Streamlit | Fastest path to interactive demo |
| **Web Scraping** | BeautifulSoup + requests / Playwright | Reviews, forums, product pages |
| **Package Manager** | uv | Fast, modern Python packaging |

### Project Structure

```
littlejoys-persona-engine/
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md                  # This document
│
├── src/
│   ├── __init__.py
│   │
│   ├── taxonomy/
│   │   ├── __init__.py
│   │   ├── schema.py               # Pydantic models for all persona attributes
│   │   ├── distributions.py        # Demographic distribution tables
│   │   ├── correlations.py         # Correlation rules + Gaussian copula
│   │   └── validation.py           # Persona consistency checks
│   │
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── tier1_generator.py      # Statistical persona generator
│   │   ├── tier2_generator.py      # Deep narrative persona generator (LLM)
│   │   ├── population.py           # Population-level generation + validation
│   │   └── prompts/
│   │       ├── narrative_generation.py
│   │       └── attribute_expansion.py
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── agent.py                # AutonomousAgent class (identity + memory + state)
│   │   ├── memory.py               # Memory system (episodic, semantic, brand)
│   │   ├── perception.py           # Scenario injection / environment interface
│   │   └── serialization.py        # Save/load agents
│   │
│   ├── decision/
│   │   ├── __init__.py
│   │   ├── funnel.py               # Layer 0-3 decision functions
│   │   ├── repeat.py               # Layer 4 repeat purchase model
│   │   ├── calibration.py          # Threshold calibration
│   │   └── scenarios.py            # Scenario definitions for all 4 problems
│   │
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── static.py               # Mode A: Static snapshot simulation
│   │   ├── temporal.py             # Mode B: Multi-month temporal simulation
│   │   ├── counterfactual.py       # Counterfactual engine
│   │   └── wom.py                  # Word-of-mouth propagation model
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── segments.py             # Segment breakdown + heatmaps
│   │   ├── barriers.py             # Barrier distribution analysis
│   │   ├── causal.py               # Causal attribution + variable importance
│   │   ├── report_agent.py         # LLM ReACT ReportAgent
│   │   └── interviews.py           # Deep persona interview system
│   │
│   ├── scraping/
│   │   ├── __init__.py
│   │   ├── amazon_reviews.py
│   │   ├── parenting_forums.py
│   │   ├── google_trends.py
│   │   └── littlejoys_site.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── llm.py                  # Claude API wrapper (Sonnet + Opus routing)
│       └── viz.py                  # Plotly chart helpers
│
├── app/
│   ├── streamlit_app.py            # Main Streamlit entry point
│   ├── pages/
│   │   ├── 1_population.py         # Population explorer
│   │   ├── 2_scenario.py           # Scenario configurator
│   │   ├── 3_results.py            # Results dashboard
│   │   ├── 4_counterfactual.py     # Counterfactual comparison
│   │   ├── 5_interviews.py         # Persona interviews
│   │   └── 6_report.py             # ReportAgent interactive
│   └── components/
│       ├── persona_card.py
│       ├── funnel_chart.py
│       └── heatmap.py
│
├── data/
│   ├── scraped/                    # Raw scraped data
│   ├── distributions/              # Processed distribution parameters
│   ├── populations/                # Generated populations
│   └── results/                    # Simulation results
│
├── notebooks/
│   ├── 01_exploration.ipynb        # Data exploration
│   ├── 02_calibration.ipynb        # Model calibration
│   └── 03_validation.ipynb         # Population validation
│
└── tests/
    ├── test_generation.py
    ├── test_decision.py
    ├── test_simulation.py
    └── test_analysis.py
```

---

## APPENDIX: SCENARIO CONFIGURATIONS

### A.1 Problem 1: Repeat Purchase / LJ Pass Impact

```python
SCENARIO_REPEAT_PURCHASE = {
    "name": "LJ Pass Impact on Repeat Purchase",
    "mode": "temporal",
    "months": 6,
    "product": {
        "name": "Nutrimix 2-6",
        "price": 599,
        "category_need_baseline": 0.65,
        "clean_label_score": 0.85,
        "health_relevance": 0.75,
        "effort_required": 0.2,     # Mix with milk — easy
        "complexity": 0.1,
        "cooking_required": 0.0,
        "premium_positioning": 0.6,
        "superfood_score": 0.7,
        "subscription_available": True,
        "target_age_min": 2,
        "target_age_max": 6,
        "addresses_concerns": ["low_immunity", "underweight", "picky_eater", "low_energy"],
    },
    "scenario": {
        "perceived_quality": 0.75,
        "trust_signal": 0.7,
        "expert_endorsement": 0.5,
        "social_proof": 0.7,        # 1.1M units sold = strong social proof
        "influencer_signal": 0.5,
        "awareness_level": 0.6,
        "marketing_channels": ["instagram", "google_search", "mom_blogs"],
        "channel_intensity": {"instagram": 0.6, "google_search": 0.5, "mom_blogs": 0.4},
        "social_buzz": 0.5,
        "discount_available": 0.07,  # ~7% standard discount
        "calibrated_threshold": 0.35,
    },
    "pass_config": {
        "pass_price": 299,           # Hypothetical
        "cashback_rate": 0.05,       # 5% per order
        "pass_duration_months": 3,
        "pass_adoption_scenario": "offered_at_checkout_post_first_purchase",
    },
    "counterfactuals": [
        {"name": "Pass 10% cashback", "changes": {"pass_config.cashback_rate": 0.10}},
        {"name": "Pass free for first 3 months", "changes": {"pass_config.pass_price": 0}},
        {"name": "Subscription auto-delivery", "changes": {"product.subscription_available": True, "product.effort_required": 0.05}},
        {"name": "Monthly WhatsApp reminder + reorder link", "changes": {"product.effort_required": 0.1, "scenario.social_buzz": 0.7}},
    ],
    "target_population_filter": {"child_age": [2, 6]},
    "key_metrics": ["month_over_month_retention", "6_month_LTV", "pass_adoption_rate", "churn_rate_with_vs_without_pass"],
}
```

### A.2 Problem 2: Nutrimix 7-14 Expansion

```python
SCENARIO_NUTRIMIX_EXPANSION = {
    "name": "Nutrimix 7-14 Age Segment Expansion",
    "mode": "static",
    "product": {
        "name": "Nutrimix 7+",
        "price": 599,
        "category_need_baseline": 0.45,  # LOWER — parents of older kids see less need
        "clean_label_score": 0.85,
        "health_relevance": 0.6,          # Less urgency vs toddler nutrition
        "effort_required": 0.25,
        "complexity": 0.1,
        "cooking_required": 0.0,
        "premium_positioning": 0.55,
        "superfood_score": 0.7,
        "subscription_available": True,
        "target_age_min": 7,
        "target_age_max": 14,
        "addresses_concerns": ["low_immunity", "low_energy", "focus_issues", "picky_eater"],
    },
    "scenario": {
        "perceived_quality": 0.65,
        "trust_signal": 0.55,            # Less established in this segment
        "expert_endorsement": 0.4,
        "social_proof": 0.4,              # Less proven here
        "influencer_signal": 0.4,
        "awareness_level": 0.35,          # LOW — new segment
        "marketing_channels": ["instagram", "google_search", "youtube"],
        "channel_intensity": {"instagram": 0.5, "google_search": 0.4, "youtube": 0.4},
        "social_buzz": 0.3,
        "discount_available": 0.07,
        "calibrated_threshold": 0.35,
    },
    "counterfactuals": [
        {"name": "Awareness +50% (heavy marketing)", "changes": {"awareness_level": 0.525}},
        {"name": "School partnership (doctor + teacher endorsement)", "changes": {"expert_endorsement": 0.8, "trust_signal": 0.75, "awareness_level": 0.5}},
        {"name": "Child-friendly flavor (cookie dough)", "changes": {"product.effort_required": 0.15, "product.health_relevance": 0.65}},
        {"name": "Free trial with existing 2-6 customers", "changes": {"awareness_level": 0.8, "trust_signal": 0.75, "product.price": 0}},
        {"name": "Focus/brain positioning (not general nutrition)", "changes": {"product.addresses_concerns": ["focus_issues", "brain_health"], "product.health_relevance": 0.75, "product.category_need_baseline": 0.55}},
    ],
    "target_population_filter": {"child_age": [7, 14]},
    "key_metrics": ["adoption_rate", "primary_barrier", "segment_with_highest_adoption", "awareness_sensitivity", "optimal_positioning"],
}
```

### A.3 Problem 3: Magnesium Gummies Growth

```python
SCENARIO_MAGNESIUM_GUMMIES = {
    "name": "Magnesium Gummies for Kids — Growth Strategy",
    "mode": "static",
    "product": {
        "name": "Magnesium Gummies",
        "price": 499,
        "category_need_baseline": 0.30,  # VERY LOW — most parents don't know kids need Mg
        "clean_label_score": 0.85,
        "health_relevance": 0.55,
        "effort_required": 0.15,         # Gummies = very easy
        "complexity": 0.05,
        "cooking_required": 0.0,
        "premium_positioning": 0.5,
        "superfood_score": 0.3,
        "subscription_available": True,
        "target_age_min": 2,
        "target_age_max": 14,
        "addresses_concerns": ["focus_issues", "low_energy", "low_immunity"],
    },
    "scenario": {
        "perceived_quality": 0.6,
        "trust_signal": 0.5,
        "expert_endorsement": 0.3,        # Few parents have heard doctors recommend Mg for kids
        "social_proof": 0.25,
        "influencer_signal": 0.3,
        "awareness_level": 0.20,          # VERY LOW — niche product
        "marketing_channels": ["instagram", "google_search", "pediatrician"],
        "channel_intensity": {"instagram": 0.4, "google_search": 0.3, "pediatrician": 0.5},
        "social_buzz": 0.15,
        "discount_available": 0.09,
        "calibrated_threshold": 0.35,
    },
    "counterfactuals": [
        {"name": "Pediatrician recommendation campaign", "changes": {"expert_endorsement": 0.8, "awareness_level": 0.45, "trust_signal": 0.75}},
        {"name": "Position as 'calm & focus' (not 'magnesium')", "changes": {"product.category_need_baseline": 0.50, "product.health_relevance": 0.70, "awareness_level": 0.35}},
        {"name": "Bundle with Multivitamin gummies", "changes": {"product.price": 399, "awareness_level": 0.5, "social_proof": 0.5}},
        {"name": "Free sample with Nutrimix orders", "changes": {"awareness_level": 0.7, "product.price": 0, "trust_signal": 0.65}},
        {"name": "Instagram education campaign (why kids need Mg)", "changes": {"product.category_need_baseline": 0.45, "awareness_level": 0.40, "scenario.influencer_signal": 0.7}},
    ],
    "target_population_filter": {"child_age": [2, 14]},
    "key_metrics": ["adoption_rate", "need_recognition_rate", "awareness_as_bottleneck", "doctor_vs_social_channel_effectiveness", "price_sensitivity_at_499"],
}
```

### A.4 Problem 4: ProteinMix Adoption

```python
SCENARIO_PROTEINMIX = {
    "name": "ProteinMix Adoption — New Product Launch",
    "mode": "static",
    "product": {
        "name": "ProteinMix",
        "price": 549,
        "category_need_baseline": 0.40,
        "clean_label_score": 0.85,
        "health_relevance": 0.60,
        "effort_required": 0.65,          # HIGH — must mix into roti/dosa/pancake while cooking
        "complexity": 0.6,                # Multi-step usage
        "cooking_required": 0.8,          # REQUIRES cooking
        "premium_positioning": 0.5,
        "superfood_score": 0.6,
        "subscription_available": True,
        "target_age_min": 2,
        "target_age_max": 14,
        "addresses_concerns": ["underweight", "picky_eater", "low_energy"],
    },
    "scenario": {
        "perceived_quality": 0.6,
        "trust_signal": 0.5,
        "expert_endorsement": 0.3,
        "social_proof": 0.15,             # Very new product, low social proof
        "influencer_signal": 0.3,
        "awareness_level": 0.20,
        "marketing_channels": ["instagram", "youtube", "google_search"],
        "channel_intensity": {"instagram": 0.4, "youtube": 0.5, "google_search": 0.3},
        "social_buzz": 0.15,
        "discount_available": 0.08,
        "calibrated_threshold": 0.35,
    },
    "counterfactuals": [
        {"name": "Recipe video campaign (reduce perceived effort)", "changes": {"product.effort_required": 0.4, "product.complexity": 0.35, "awareness_level": 0.4}},
        {"name": "Position for working mothers (guilt + convenience)", "changes": {"product.health_relevance": 0.7, "product.category_need_baseline": 0.5}},
        {"name": "Reduce price to ₹399", "changes": {"product.price": 399}},
        {"name": "Pre-mixed pancake packet (zero cooking effort)", "changes": {"product.effort_required": 0.2, "product.cooking_required": 0.1, "product.complexity": 0.15, "product.price": 349}},
        {"name": "Bundle: ProteinMix + Nutrimix trial", "changes": {"product.price": 449, "trust_signal": 0.65, "social_proof": 0.5}},
    ],
    "target_population_filter": {"child_age": [2, 14]},
    "key_metrics": ["adoption_rate", "effort_as_primary_barrier", "working_vs_homemaker_split", "cooking_enthusiasm_correlation", "price_vs_effort_tradeoff"],
}
```

---

## APPENDIX: KEY DESIGN DECISIONS LOG

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Persona depth | 145 structured + 200+ with narrative | DeepPersona shows 200-250 optimal. We use 145 structured (fast, deterministic) and expand to 200+ for Tier 2 (LLM-enriched) |
| Copula vs. manual rules | Gaussian copula | Handles 50+ correlated continuous variables cleanly; manual rules don't scale |
| Threshold calibration | Calibrate against known product | Makes relative comparisons meaningful. Avoids "garbage in, garbage out" |
| Two-tier personas | Statistical (bulk) + Deep (subset) | Quantitative rigor from Tier 1, qualitative wow from Tier 2. Cost-efficient. |
| Agent reusability | Identity/Memory/State separation | Core infrastructure investment. Same agents serve multiple clients. |
| LLM routing | Sonnet for bulk, Opus for reasoning | 10x cost difference. Bulk gen doesn't need Opus. Analysis does. |
| Dashboard | Streamlit over React | 5x faster to build. Acceptable for POC. Upgrade to React for production. |
| Data store | Parquet + JSON over DB | No infra overhead. Fast columnar queries for 1000 agents. Portable. |

---

*This document is the single source of truth for the LittleJoys Persona Simulation Engine. Any coding agent working on this project should read this document first.*
