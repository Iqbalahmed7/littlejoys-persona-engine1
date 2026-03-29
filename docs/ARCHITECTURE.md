# LittleJoys Persona Simulation Engine — Architecture Document

> **Owner**: Technical Lead (Claude Opus)
> **Version**: 2.0
> **Date**: 2026-03-29
> **Status**: Active — Phase 1 complete, Phase 2 in progress (Sprint 16)

---

## 1. Vision

LittleJoys is a simulation engine that models how Indian parents make purchasing decisions about children's nutrition products. Rather than surveying real people, it generates a synthetic population of 200+ deeply-modelled personas, simulates their behaviour over time, and produces insights that are faster, cheaper, and more exploratory than traditional market research.

The core value proposition: **a product manager can ask "why is repeat purchase low?" and receive temporal behavioural trajectories, causal drivers, intervention comparisons, and segment-level strategies — in minutes, not weeks.**

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                     │
│  Streamlit App (4 pages)                                │
│  Home │ Personas │ Research Design │ Results │ Interviews │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   RESEARCH LAYER                         │
│  ResearchRunner: orchestrates full hybrid pipeline       │
│  Smart Sampling │ LLM Interviews │ Auto-Variants         │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   ANALYSIS LAYER                         │
│  ConsolidatedReport │ Trajectory Clustering              │
│  Causal Analysis │ Qualitative Clustering │ Segments     │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   SIMULATION LAYER                        │
│  Static Funnel │ Temporal Simulation │ WOM Propagation    │
│  Counterfactual Engine │ Auto-Variant Explorer           │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   DECISION LAYER                         │
│  4-Layer Funnel (Need → Awareness → Consideration →     │
│  Purchase) │ Repeat Purchase │ Churn Model               │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   STATE LAYER (Sprint 17+)               │
│  Canonical State Model: 10 mutable variables per persona │
│  Event Grammar │ Daily Update Loop │ Decision Rules       │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   PERSONA LAYER                          │
│  Taxonomy (145+ attributes) │ Gaussian Copula Generator  │
│  LLM Narrative Enrichment │ Immutable Identity           │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Persona Layer

### 3.1 Taxonomy Schema

Each persona carries 145+ immutable identity attributes across 12 categories:

| Category | Key Attributes | Purpose |
|----------|---------------|---------|
| **Demographics** | city_tier (1/2/3), household_income_lpa, family_structure, youngest_child_age | Segmentation, need recognition |
| **Health** | health_anxiety, nutrition_gap_awareness, medical_authority_trust, immunity/growth concern | Need + trust drivers |
| **Psychology** | social_proof_bias, risk_tolerance, status_quo_bias, regret_sensitivity | Decision style modifiers |
| **Cultural** | dietary_culture (vegetarian/non-veg/vegan), cultural_region, religious_influence | Product-persona fit |
| **Relationships** | wom_transmitter_tendency, wom_receiver_openness, peer_influence_strength | Social dynamics |
| **Daily Routine** | budget_consciousness, price_reference_point, subscription_comfort, milk_supplement_current | Purchase barriers, competitive context |
| **Values** | brand_loyalty_tendency, indie_brand_openness, transparency_importance | Brand perception |
| **Education** | science_literacy, research_before_purchase, ingredient_awareness | Consideration depth |
| **Lifestyle** | wellness_trend_follower, organic_preference | Category alignment |
| **Media** | ad_receptivity, primary_platform, instagram/youtube/whatsapp usage | Channel matching |
| **Emotional** | guilt_driven_spending, best_for_my_child_intensity, emotional_persuasion_susceptibility | Emotional purchase drivers |
| **Career** | working_status, perceived_time_scarcity | Effort barrier context |

### 3.2 Population Generation

The `PopulationGenerator` creates 200 personas using:

1. **Demographic sampling** — India-specific distributions conditional on city tier (Tier 1: 45%, Tier 2: 35%, Tier 3: 20%). Income, education, family structure, and dietary culture are all conditional on tier.
2. **Gaussian copula** — Generates correlated psychographic attributes (e.g., Tier 3 parents get higher authority_bias, working mothers get higher time_scarcity, first-child parents get higher health_anxiety).
3. **Conditional rules** — 50+ correlation rules ensure internal consistency.
4. **LLM narrative enrichment** — Each persona gets a 2-3 paragraph narrative grounding their attributes in a coherent life story.

**Output**: `Population` object with immutable `Persona` objects. Deterministic given seed.

### 3.3 Agent Model (Sprint 17+)

Each persona will be wrapped in a `CognitiveAgent` with:

- **Identity** (immutable) — The 145+ taxonomy attributes. Never changes.
- **Memory** (mutable) — Episodic memory (timestamped events), semantic memory (beliefs), brand memories (per-brand trust, purchase count, satisfaction history).
- **Perception interface** — Filters external events through the persona's psychological lens (ad receptivity, cultural fit, platform match).

Stubs exist in `src/agents/`. Full implementation planned for Sprint 17.

---

## 4. Decision Layer

### 4.1 Four-Layer Purchase Funnel

The funnel is a deterministic layered classifier. Each persona is scored at each stage; failure to pass a threshold causes early exit with a diagnostic rejection reason.

```
Layer 0: NEED RECOGNITION
  Inputs: health_anxiety, nutrition_gap_awareness, child_health_proactivity,
          immunity_concern, growth_concern, age_relevance
  Weights: 0.20 / 0.25 / 0.20 / 0.15 / 0.15
  Threshold: 0.35
  Rejection: "age_irrelevant" or "low_need"

Layer 1: AWARENESS
  Inputs: marketing_budget × channel_persona_match + partnership boosts
  Channel match: instagram_match + youtube_match + whatsapp_match (weighted by mix)
  Boosts: +0.15 pediatrician endorsement, +0.20 school partnership, +0.10 influencer
  Threshold: 0.30
  Rejection: "low_awareness"

Layer 2: CONSIDERATION
  Inputs: trust_factor, research_factor, cultural_fit, brand_factor, risk_factor
  Weights: 0.30 / 0.20 / 0.15 / 0.20 / 0.15
  Threshold: 0.40
  Rejection: "dietary_incompatible", "insufficient_trust", "insufficient_research"

Layer 3: PURCHASE
  Inputs: value (transparency × benefit_mix) + emotional (guilt + best-for-child)
          - price_barrier (budget_consciousness × price_ratio)
          - effort_barrier (effort × (1 - online_comfort))
  Threshold: 0.30
  Rejection: "price_too_high", "effort_too_high", "insufficient_trust"
```

**Output**: `DecisionResult` per persona with all 4 scores, outcome ("adopt"/"reject"), rejection stage and reason.

### 4.2 Repeat Purchase Model

Post-adoption behaviour is modelled by three functions:

**Satisfaction** (evaluated monthly):
```
taste_alignment   = taste_appeal × (1 - 0.5 × child_taste_veto)     [35%]
perceived_efficacy = taste_appeal × 0.45 + science_literacy × 0.55   [40%]
price_value       = 1 - (price_ratio - 1) × 0.35                     [25%]
satisfaction      = weighted_sum(taste, efficacy, price_value)
```

**Repeat probability**:
```
habit    = 0.3 + 0.1 × consecutive_months    (caps at 1.0 by month 7)
repeat   = satisfaction × habit × (1.1 if LJ Pass else 1.0)
```

**Churn probability**:
```
base_churn = 1 - mean(last 3 months satisfaction)
churn      = base_churn × (0.8 if LJ Pass else 1.0)
```

---

## 5. Simulation Layer

### 5.1 Static Simulation

Runs each persona through the 4-layer funnel exactly once. No temporal dynamics. Used for quick scenario comparison and as the first step in the research pipeline.

**Output**: `StaticSimulationResult` — adoption count, adoption rate, rejection distribution by stage, per-persona decision results.

### 5.2 Temporal Simulation (Current — Monthly)

Simulates a 12-month journey for each persona. Each month:

1. **Awareness growth**: +0.02 × marketing budget, capped at 1.0
2. **WOM propagation**: Active adopters spread awareness to 3-5 non-adopters. Transmission rate 0.15, exponential decay 0.85^month. Only high-transmitter personas (>0.3) spread.
3. **New adoption**: Non-adopters run through the funnel with accumulated awareness boost.
4. **Repeat/churn**: Active personas compute satisfaction, evaluate churn probability, evaluate repeat probability. LJ Pass holders get +10% repeat, -20% churn.
5. **Snapshot**: Monthly aggregate metrics (new_adopters, repeat_purchasers, churned, total_active, awareness_mean, LJ Pass holders).

**Output**: `TemporalSimulationResult` — 12 monthly snapshots, final adoption/active rates, revenue estimate.

**Per-persona trajectories**: `extract_persona_trajectories()` returns a `PersonaTrajectory` per persona with month-by-month state (is_active, satisfaction, consecutive_months, has_lj_pass, churned/adopted flags). Used for behavioural clustering.

### 5.3 Event-Driven Simulation (Sprint 17 — Planned)

Replaces the month-level loop with a day-level event-driven engine.

**Event Grammar V1** — 4 event categories:

| Category | Event Types | Firing Model |
|----------|------------|-------------|
| **Consumption** | pack_finished, usage_drop, usage_consistent | Deterministic (pack lasts ~20-25 days) |
| **Child** | child_positive_reaction, child_rejection, child_boredom | Stochastic (probability based on taste_appeal × child attributes) |
| **Economic** | budget_pressure_increase, payday_relief, competitor_discount | Stochastic (monthly economic cycles, competitor probability) |
| **Brand** | reminder, influencer_exposure, doctor_recommendation, pass_offer | Stochastic (probability based on marketing budget × channel match) |

Each event has: `id`, `type`, `timestamp` (day), `intensity` (0-1), optional attributes.

**Processing order**: Deterministic events fire first, then stochastic. Impacts update the Canonical State Model variables.

### 5.4 Canonical State Model (Sprint 17 — Planned)

10 mutable dynamic variables per persona, evolving daily:

| Variable | Range | Initialised From | Key Update Triggers |
|----------|-------|-------------------|---------------------|
| `trust` | [0,1] | medical_authority_trust × 0.3 + social_proof_bias × 0.2 | +doctor_rec, +positive_wom, -negative_experience |
| `habit_strength` | [0,1] | 0.0 | +0.08/month consecutive purchase, -0.15 on missed reorder |
| `child_acceptance` | [0,1] | taste_appeal × (1 - 0.3 × child_veto_power) | -child_rejection, -child_boredom, +recipe_variation |
| `price_salience` | [0,1] | budget_consciousness × 0.5 | +budget_pressure, -payday, +competitor_discount |
| `reorder_urgency` | [0,1] | 0.0 | +as pack depletes (linear ramp), reset on purchase |
| `fatigue` | [0,1] | 0.0 | +0.03/week consistent usage, -recipe_variation |
| `perceived_value` | [0,1] | taste × 0.5 + science_literacy × 0.3 + nutrition_gap × 0.2 | +visible_health_improvement, -fatigue > 0.5 |
| `brand_salience` | [0,1] | 0.0 (pre-awareness) | +ad_exposure, +peer_mention, decay 0.02/day without touchpoint |
| `effort_friction` | [0,1] | effort_to_acquire × (1 - online_comfort) | -subscription_setup, -quick_commerce |
| `discretionary_budget` | [0,1] | 1.0 - budget_consciousness | -budget_pressure, +payday, seasonal variation |

**Decision rules** compare state values against persona-specific thresholds derived from identity attributes. See `docs/designs/CANONICAL-STATE-MODEL-V1.md` for full specification.

### 5.5 WOM Propagation

Word-of-mouth spreads awareness from adopters to non-adopters each month:

- Only high-transmitter personas (wom_transmitter_tendency > 0.3) propagate
- Each transmitter reaches 3-5 random non-adopters
- Boost = transmitter_trait × 0.15 × 0.85^month × (1 + receiver.social_proof_bias)
- Per-receiver cap: +0.3 awareness per month
- WOM decays exponentially, preventing awareness explosion

### 5.6 Auto-Variant Explorer

Generates 50 alternative scenario variants for strategic comparison:

**Strategies**:
- **SMART** (primary): Targets dominant rejection stages with specific remediations. If consideration has the most rejections, variants boost trust signals, endorsements, and social proof.
- **SWEEP**: One-parameter-at-a-time across 15 product/marketing parameters.
- **GRID**: Cartesian product of price × awareness × taste.
- **RANDOM**: Latin-hypercube stratified sampling.

Each variant includes a `business_rationale` in PM-friendly language (e.g., "What if we added pediatrician endorsement and cut price by 15%?").

For temporal scenarios, the top 10 variants (by static adoption) are also run through the temporal simulation to compare month-12 active rates.

---

## 6. Analysis Layer

### 6.1 Research Consolidator

Transforms raw `ResearchResult` into a structured `ConsolidatedReport`:

| Section | Content | Source |
|---------|---------|--------|
| Funnel Summary | Adoption count/rate, population size, rejection distribution | Static funnel |
| Segments by Tier | Adoption rate per city tier with delta vs population | Merged persona + funnel data |
| Segments by Income | Adoption rate per income bracket | Merged persona + funnel data |
| Key Decision Variables | Top 8 variables by importance (logistic regression + SHAP) | Persona attributes × funnel outcomes |
| Qualitative Clusters | Keyword-based theme grouping of interview responses | LLM interviews |
| Top Alternatives | Top 10 variants ranked by adoption lift | Auto-variant explorer |
| Worst Alternatives | Bottom 3 variants | Auto-variant explorer |
| Temporal Snapshots | Month-by-month metrics (if temporal) | Temporal simulation |
| Behaviour Clusters | Trajectory-based segments (if temporal) | Trajectory clustering |
| Temporal Metrics | Month-12 active rate, peak churn month, revenue estimate | Temporal simulation |

### 6.2 Trajectory Clustering

Groups personas into 6 behavioural segments based on trajectory shape:

| Cluster | Definition | Key Signal |
|---------|-----------|------------|
| **Loyal Repeaters** | Adopted early (month 1-2), never churned, high satisfaction (>0.55) | Long-term customers |
| **Late Adopters** | Adopted after month 2 (via WOM) | Growth potential |
| **Taste-Fatigued Droppers** | Churned early (month 2-4), declining satisfaction slope (<-0.03) | Product intervention needed |
| **Price-Triggered Switchers** | Churned + high budget_consciousness (>0.7) | Price strategy opportunity |
| **Forgot-to-Reorder** | Low consecutive months (<=2), sporadic | Re-engagement opportunity |
| **Never Reached** | Never adopted (split by rejection stage) | Awareness/trust gap |

Each cluster reports: size, percentage, average lifetime, average satisfaction, and top 5 distinguishing persona attributes (by deviation from population mean).

### 6.3 Causal Analysis

Logistic regression + SHAP values on persona attributes vs adoption outcome. Produces top 8 variables with importance scores, direction (positive/negative), and segment-level breakdowns.

**Note**: In Phase 1, these are model sensitivity factors (recovering the funnel's own weights). In Phase 2 (Sprint 18+), counterfactual comparisons will provide genuine causal attribution.

### 6.4 Qualitative Clustering

Interview responses are clustered by keyword into 7 predefined themes:

price_sensitivity, forgetfulness, taste_decline, trust_concern, alternatives, convenience, positive_experience

Each cluster reports dominant persona attributes. In mock mode, responses are template-generated. In live LLM mode, responses are independently reasoned.

---

## 7. Research Layer

### 7.1 Research Runner Pipeline

The `ResearchRunner` orchestrates the full hybrid research pipeline:

```
Step 1: Static funnel on all 200 personas                    [10% progress]
Step 2: Smart sample selection (18 personas, 5 buckets)      [20%]
Step 3: LLM interviews on sample (or mock responses)         [20-70%]
Step 4: Generate 50 alternative scenario variants             [70-75%]
Step 5: Run static funnel on all variants                    [75-90%]
Step 6: Run temporal simulation (if scenario.mode=temporal)   [90-95%]
Step 7: Run temporal on top 10 alternatives                   [95-100%]
```

**Output**: `ResearchResult` containing primary funnel, smart sample, interview results, alternative runs, temporal result (optional), and metadata (timestamp, duration, cost, LLM calls).

### 7.2 Smart Sampling

Selects 18 personas for deep interviews across 5 insight buckets:

| Bucket | Count | Selection Logic |
|--------|-------|-----------------|
| Fragile Yes | 3-4 | Adopted but purchase score within 10% of threshold |
| Persuadable No | 3-4 | Rejected but score within 10% of threshold |
| Underrepresented | 3-4 | Adopters from minority segments (Tier 3, low income) |
| High-Need Rejecters | 3-4 | High need score but rejected — why the disconnect? |
| Control | 2-3 | Random, deterministic via seed |

### 7.3 Business Question Bank

13 business questions across 4 scenarios, each with a probing tree of hypotheses:

| Scenario | Questions | Example |
|----------|-----------|---------|
| Nutrimix 2-6 | 4 | "How can we improve repeat purchase for NutriMix?" |
| Nutrimix 7-14 | 3 | "Can the NutriMix brand extend credibly to older children?" |
| Magnesium Gummies | 3 | "What drives initial trial for a new gummy supplement?" |
| ProteinMix | 3 | "Why is ProteinMix seeing low trial despite marketing spend?" |

### 7.4 Probing Tree (Repositioned — Phase 2)

In Phase 1, the probing tree provides the question bank and hypothesis framing. In Phase 2 (Sprint 24+), it becomes a diagnostic overlay:

1. **Scenario interpretation** — Decomposes business problems into candidate causal lenses
2. **Persona parameterisation** — Targeted interview probes to initialise latent variables before simulation
3. **Counterfactual testing** — Maps hypotheses to scenario perturbations for the counterfactual engine
4. **Post-simulation diagnostics** — Samples representative personas from behavioural clusters for qualitative deep-dive
5. **User control** — PM can enable/disable hypotheses, affecting diagnostic overlays (not the simulation itself)

---

## 8. Presentation Layer

### 8.1 Streamlit App Structure

4 pages accessed via sidebar navigation:

| Page | Purpose | Key Components |
|------|---------|---------------|
| **Home** | Landing + population loading | Metrics (personas, narratives, scenarios), Getting Started guide, page links |
| **1. Personas** | Browse synthetic population | 4 demographic charts (tier, income, family, age), segment filters, persona browser with card + spider chart, narrative expander |
| **2. Research Design** | Configure and run research | Scenario selector, mode indicator (temporal/static), business question selector, hypothesis list (read-only), mock mode banner, run button with progress |
| **3. Results** | Research report | Funnel waterfall, temporal trajectory chart, behavioural segments, segment analysis, key decision variables, intervention comparison, interview themes, JSON export |
| **4. Interviews** | Deep-dive conversations | Smart sample overview, per-persona Q&A cards, theme clustering, persona comparison |

### 8.2 Session State Flow

```
Home (load population) → session_state["population"]
                ↓
Research Design (run pipeline) → session_state["research_result"]
                ↓
Results (consolidate + render) → ConsolidatedReport from research_result
                ↓
Interviews (deep-dive) → reads research_result.interview_results
```

---

## 9. Scenario Definitions

### 9.1 Priority Scenarios

| Scenario | Mode | Price | Age | Key Challenge | Priority |
|----------|------|-------|-----|---------------|----------|
| **Nutrimix 2-6** | Temporal (12 months) | Rs.599 | 2-6 | Repeat purchase, churn, LJ Pass | P0 — Primary |
| **Nutrimix 7-14** | Static | Rs.649 | 7-14 | Brand extension, school influence, taste barrier | P1 — Secondary |
| Magnesium Gummies | Static | Rs.499 | 4-12 | New category awareness, supplement skepticism | P2 — Deferred |
| ProteinMix | Static | Rs.799 | 6-14 | High effort barrier, cooking required | P2 — Deferred |

### 9.2 Nutrimix 2-6 Configuration

```
Product: powder_mix, Rs.599, taste_appeal=0.7, effort=0.3, health_relevance=0.75
Marketing: budget=0.5, instagram=40%, youtube=30%, whatsapp=30%
Partnerships: pediatrician=True, influencer=True, school=False
LJ Pass: Rs.299/mo, 15% discount, 1-month free trial
Mode: temporal, 12 months
```

### 9.3 Nutrimix 7-14 Configuration

```
Product: powder_mix, Rs.649, taste_appeal=0.55, effort=0.3, health_relevance=0.60
Marketing: budget=0.35, instagram=35%, youtube=40%, whatsapp=25%
Partnerships: pediatrician=False, school=True, influencer=False
LJ Pass: available but static mode (no temporal repeat modelling yet)
Mode: static (Sprint 18-19: convert to temporal with school/peer event grammar)
```

---

## 10. Cost Model

### 10.1 Per-Run Cost

| Component | Method | LLM Calls | Cost |
|-----------|--------|-----------|------|
| Static funnel (200 personas) | Rule-based | 0 | $0.00 |
| Temporal simulation (12 months) | Rule-based | 0 | $0.00 |
| Alternative variants (50 static + 10 temporal) | Rule-based | 0 | $0.00 |
| Trajectory clustering | Heuristic | 0 | $0.00 |
| Smart sample interviews (2-3 personas) | LLM (Haiku) | 6-10 | $0.01-0.02 |
| Executive summary generation | LLM (Sonnet) | 1 | $0.05-0.10 |
| **Total per run** | | **7-11** | **$0.06-0.12** |

### 10.2 Mock Mode

Without an API key, the system runs in mock mode: interview responses are template-generated, no LLM calls. All quantitative simulation runs identically. Mock mode is clearly disclosed in the UI.

---

## 11. Validation Strategy

Without real-world data (LittleJoys is pre-launch), validation is qualitative:

| Method | Description | When |
|--------|-------------|------|
| **Face validity** | Inspect 50-100 trajectories for realistic coherence | Sprint 18 |
| **Internal consistency** | Same persona + same seed = identical outcome | Continuous (526+ tests) |
| **Sensitivity testing** | Perturb price/reminder/awareness, verify plausible outcome changes | Sprint 18-19 (counterfactual engine) |
| **Expert review** | Present sample trajectories to domain experts for feedback | Sprint 20+ |

Goal: build a plausible engine that guides product decisions until real data calibrates it.

---

## 12. Implementation Roadmap

### Phase 1 — Hybrid Research Engine (COMPLETE)

| Sprint | Delivered |
|--------|-----------|
| 12 | Smart sampling, question bank, research runner, spider charts |
| 13 | Research Design page, auto-variants, personas dashboard |
| 14 | Results report page, interview deep-dive, research consolidator |
| 15 | Page cleanup, shared utilities, deployment, integration tests |
| 16.0 | UAT cleanup (hypothesis toggles, mock banner, driver rename) |
| **16** | **Temporal pipeline wired into research runner, trajectory clustering, temporal results page** (in progress) |

### Phase 2 — Simulation-Native Architecture

| Sprint | Goal | Key Deliverables |
|--------|------|------------------|
| **17** | Event-driven engine | Canonical State Model V1, event grammar, day-level simulation, competitive context |
| **18-19** | Intelligence layer | Counterfactual engine, LLM-calibrated thresholds, executive summary generation, Nutrimix 7-14 temporal |
| **20-21** | Presentation + demo | Cohort heatmaps, retention curves, intervention recommendation engine, guided demo walkthrough |

### Phase 3 — Platform Generalisation (Future)

| Sprint | Goal |
|--------|------|
| 24-26 | Probing tree as diagnostic overlay on simulation outputs |
| 27-29 | Cross-persona social influence, word-of-mouth network effects |
| 30-32 | Cross-scenario agent reuse, LLM-derived event grammars from natural language |

### Dependency Graph

```
Phase 1 (Done)                    Phase 2 (In Progress)
Sprints 12-15                     Sprint 16 ──→ Sprint 17 ──→ Sprint 18-19 ──→ Sprint 20-21
Static funnel                     Temporal in    Event engine   Counterfactual    Demo polish
+ interviews                      pipeline       + state model  + 7-14 scenario
+ variants                        + clustering   + day-level    + exec summary
+ consolidation                   + results UI   + competitive
```

---

## 13. Engineer Assignments

| Engineer | Model | Role | Typical Tasks |
|----------|-------|------|---------------|
| **Cursor** | Claude | Architecture, complex refactors | Page rewrites, system design, cross-module integration |
| **Codex** | GPT 5.3 Medium | Backend algorithms | Data models, pipeline logic, simulation engine |
| **OpenCode** | GPT 5.4 Nano | UI/Streamlit, frontend | Page cleanups, indicators, UX polish |
| **Antigravity** | Gemini 3 Flash | Tests, validation | Unit tests, integration tests, page import checks |

**Execution pattern**: Codex (backend first) → Cursor + OpenCode (parallel, frontend) → Antigravity (tests last).

---

## 14. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Decision engine** | Hybrid parametric rules (LLM only offline) | Scalable, deterministic, near-zero cost per run |
| **Event system** | Typed events with explicit schemas, basic stochastic firing | Predictable, debuggable, extensible |
| **Scale** | 200-500 personas, not thousands | Sufficient for POC; fast simulation (<30s per run) |
| **LLM usage** | Offline persona generation + 2-3 targeted interviews per run | Cost under $0.15/run while preserving qualitative depth |
| **Probing tree** | Phase 2 diagnostic overlay, not primary driver | Core value comes from simulation, not structured interviews |
| **Temporal granularity** | Monthly (Phase 1), daily (Phase 2) | Monthly is fast and demonstrable; daily adds event-level precision |
| **Validation** | Face validity + sensitivity testing + expert review | No ground truth data available pre-launch |

---

## 15. File Structure

```
src/
├── agents/                          # Agent framework (stubs, Sprint 17)
│   ├── agent.py                     # CognitiveAgent class
│   ├── memory.py                    # MemoryManager
│   └── perception.py                # PerceptionEngine
├── analysis/
│   ├── causal.py                    # SHAP-based variable importance
│   ├── interviews.py                # Interview response generation (mock + LLM)
│   ├── research_consolidator.py     # ResearchResult → ConsolidatedReport
│   └── trajectory_clustering.py     # Trajectory → BehaviourClusters
├── decision/
│   ├── funnel.py                    # 4-layer purchase decision funnel
│   ├── repeat.py                    # Satisfaction, repeat, churn models
│   ├── scenarios.py                 # Scenario configurations (4 scenarios)
│   └── scenario_registry/           # Scenario-specific overrides
├── generation/
│   └── population.py                # PopulationGenerator + Population model
├── probing/
│   ├── clustering.py                # Keyword-based response clustering
│   ├── question_bank.py             # 13 business questions + probing trees
│   └── smart_sample.py              # 5-bucket stratified persona sampling
├── simulation/
│   ├── auto_variants.py             # 50 business-meaningful scenario variants
│   ├── explorer.py                  # Variant generation strategies (SMART/SWEEP/GRID)
│   ├── interview_agent.py           # LLM interview orchestration
│   ├── research_runner.py           # Full hybrid research pipeline
│   ├── static.py                    # Single-pass funnel runner
│   ├── temporal.py                  # Month-by-month temporal simulation
│   └── wom.py                       # Word-of-mouth propagation
├── taxonomy/
│   └── schema.py                    # Persona attribute schema (145+ fields)
├── utils/
│   ├── api_keys.py                  # Shared Anthropic key resolution
│   ├── display.py                   # User-facing label formatting
│   └── llm.py                       # LLM client wrapper
├── config.py                        # Pydantic Settings config
└── constants.py                     # All numeric thresholds and weights

app/
├── streamlit_app.py                 # Home page + population loading
├── pages/
│   ├── 1_personas.py                # Population dashboard
│   ├── 2_research.py                # Research design + run
│   ├── 3_results.py                 # Consolidated report
│   └── 4_interviews.py              # Interview deep-dive
└── components/
    ├── persona_card.py              # Persona detail card
    └── persona_spider.py            # Radar chart component

tests/
├── unit/                            # 500+ unit tests
├── integration/                     # End-to-end pipeline tests
└── conftest.py                      # Shared fixtures

docs/
├── ARCHITECTURE.md                  # This document
├── SPRINT_PLAN_OPTION_C.md          # Sprint roadmap (Phase 1 + 2)
├── DEVELOPMENT_PRACTICES.md         # Git workflow, commit conventions
├── ENGINEER_PROFILES.md             # Team capabilities and scoring
├── PRODUCT_ROADMAP.md               # Original 6-sprint plan
├── DEPLOY.md                        # Streamlit Cloud deployment guide
├── briefs/                          # Per-sprint engineer briefs (sprint12-16)
├── designs/                         # System design documents
├── prds/                            # Product requirement documents
├── scorecards/                      # Sprint evaluation scorecards
└── qa/                              # QA agent specifications
```

---

## 16. Current Status

| Metric | Value |
|--------|-------|
| **Tests** | 532 passed, 2 skipped |
| **Lint** | Clean (ruff) |
| **Deployment** | Streamlit Cloud (live) |
| **GitHub** | Private repo |
| **Phase** | Phase 2, Sprint 16 in progress |
| **Priority Scenario** | Nutrimix Repeat Purchase (temporal) |
| **Next Milestone** | Sprint 17 — Event-driven simulation with Canonical State Model |
