# Probing Tree System Design

## The Problem

A CMO doesn't ask "what is the adoption rate?" They ask:

> "Repeat purchase is low despite high NPS. Why? And what should we do?"

Our current system answers the first question well (42% adoption, top barriers are price and trust). But it can't decompose a strategic problem into testable hypotheses, run structured investigations across hundreds of personas, and converge on actionable recommendations with traceable evidence.

The Probing Tree is the intelligence layer that sits between the business question and the simulation engine.

---

## Core Concept

```
PROBLEM STATEMENT
"Repeat purchase is low despite high NPS"
    │
    ├── Hypothesis 1: Price memory fades after first purchase
    │     ├── Probe: "After finishing the first pack, what made you pause?"
    │     ├── Probe: "Did the price feel different the second time?"
    │     └── Probe: "What would make reordering automatic?"
    │           │
    │           ├── [Sample 30 personas, stratified by SEC + outcome]
    │           ├── [Cluster responses via LLM]
    │           └── Confidence: 0.73 — "62% of rejectors cite price re-evaluation"
    │
    ├── Hypothesis 2: Child taste fatigue
    │     ├── Probe: "Did your child's enthusiasm change after the first week?"
    │     └── Probe: "How did you vary the serving routine?"
    │           │
    │           └── Confidence: 0.41 — "Only 28% mention taste decline"
    │
    ├── Hypothesis 3: No re-engagement after first purchase
    │     ├── Probe: "Did you see any follow-up from the brand?"
    │     └── Probe: "What would have reminded you to reorder?"
    │           │
    │           └── Confidence: 0.82 — "78% say they simply forgot"
    │
    └── [SYNTHESIS]
          "The dominant driver is re-engagement failure (0.82),
           not price (0.73) or taste (0.41). Recommendation:
           automated reorder reminders + LJ Pass trial."
```

The user can:
- See all hypotheses and their confidence scores
- Disable/enable branches ("skip the taste hypothesis")
- See how disabling a branch changes overall insight confidence
- Drill into any probe to see individual persona responses
- Add custom probes or hypotheses

---

## Data Model

### ProblemStatement

The root node. Maps to one of the four business scenarios but expressed as a strategic question, not a simulation config.

```python
class ProblemStatement(BaseModel):
    """A business question that the probing tree investigates."""

    model_config = ConfigDict(extra="forbid")

    id: str                                    # "repeat_purchase_low"
    title: str                                 # "Why is repeat purchase low despite high NPS?"
    scenario_id: str                           # "nutrimix_2_6" — links to existing scenario
    context: str                               # Business context paragraph
    success_metric: str                        # "repeat_purchase_rate" or "adoption_rate"
    target_population_filter: dict[str, Any]   # Optional demographic filter
```

### Hypothesis

A testable explanation for the problem. Each hypothesis has a direction ("this could be why") and maps to specific persona attributes that would confirm or deny it.

```python
class Hypothesis(BaseModel):
    """One testable explanation for the problem statement."""

    model_config = ConfigDict(extra="forbid")

    id: str                                    # "h1_price_memory"
    problem_id: str                            # Parent problem
    title: str                                 # "Price feels different on repeat"
    rationale: str                             # Why this hypothesis matters
    indicator_attributes: list[str]            # ["budget_consciousness", "price_reference_point", ...]
    counterfactual_modifications: dict[str, Any] | None  # Optional scenario tweak to test
    enabled: bool = True                       # User can disable
    order: int = 0                             # Display ordering
```

`indicator_attributes` is the key design choice. Each hypothesis is grounded in specific persona attributes. When probes run, the response patterns are cross-referenced against these attributes to compute confidence.

### Probe

A specific question or simulation task that tests one aspect of a hypothesis. Probes come in three types:

```python
class ProbeType(str, Enum):
    INTERVIEW = "interview"           # Ask personas a question
    SIMULATION = "simulation"         # Run a modified scenario and compare
    ATTRIBUTE_ANALYSIS = "attribute"  # Statistical analysis of persona attributes vs outcomes

class Probe(BaseModel):
    """A single investigation step within a hypothesis."""

    model_config = ConfigDict(extra="forbid")

    id: str                                    # "h1_p1_price_pause"
    hypothesis_id: str
    probe_type: ProbeType
    order: int = 0

    # For INTERVIEW probes
    question_template: str | None = None       # "After finishing the first pack, what made you {outcome_verb}?"
    target_outcome: str | None = None          # "reject" — only ask rejectors, or None for all
    follow_up_questions: list[str] = []        # Deeper follow-ups based on initial response

    # For SIMULATION probes
    scenario_modifications: dict[str, Any] | None = None  # {"product.price_inr": 399}
    comparison_metric: str | None = None       # "adoption_rate" or "repeat_rate"

    # For ATTRIBUTE_ANALYSIS probes
    analysis_attributes: list[str] = []        # ["budget_consciousness", "deal_seeking_intensity"]
    split_by: str | None = None                # "outcome" — compare adopters vs rejectors

    # Results (populated after execution)
    status: str = "pending"                    # "pending" | "running" | "complete"
    result: ProbeResult | None = None
```

### ProbeResult

The output of running a probe. Different structure per probe type, but all produce a confidence score and evidence summary.

```python
class ResponseCluster(BaseModel):
    """A group of similar persona responses."""

    theme: str                                 # "price_re_evaluation"
    description: str                           # "Parents who recalculated value after first purchase"
    persona_count: int                         # 124 out of 200
    percentage: float                          # 0.62
    representative_quotes: list[str]           # Top 3 persona quotes
    dominant_attributes: dict[str, float]      # {"budget_consciousness": 0.78, ...}

class AttributeSplit(BaseModel):
    """Statistical comparison of an attribute between two groups."""

    attribute: str
    adopter_mean: float
    rejector_mean: float
    effect_size: float                         # Cohen's d or similar
    significant: bool                          # Is the difference meaningful?

class ProbeResult(BaseModel):
    """Result of executing a single probe."""

    model_config = ConfigDict(extra="forbid")

    probe_id: str
    confidence: float                          # 0.0 to 1.0
    evidence_summary: str                      # One-paragraph natural language
    sample_size: int                           # How many personas were analysed
    population_size: int | None = None         # Total population (for "30/200 sampled" display)

    # For INTERVIEW probes
    response_clusters: list[ResponseCluster] = []
    clustering_method: str | None = None       # "keyword" (mock) or "semantic" (LLM)

    # For SIMULATION probes
    baseline_metric: float | None = None
    modified_metric: float | None = None
    lift: float | None = None

    # For ATTRIBUTE_ANALYSIS probes
    attribute_splits: list[AttributeSplit] = []
```

### HypothesisVerdict

After all probes in a hypothesis run, the system produces a verdict.

```python
class HypothesisVerdict(BaseModel):
    """Synthesized conclusion for one hypothesis."""

    hypothesis_id: str
    confidence: float                          # Weighted average of probe confidences
    status: str                                # "confirmed" | "partially_confirmed" | "rejected" | "inconclusive"
    evidence_summary: str                      # Natural language synthesis
    key_persona_segments: list[str]            # ["SEC_B2_mothers", "tier2_city_parents"]
    recommended_actions: list[str]             # ["Implement automated reorder reminders"]
    consistency_score: float                   # Do the probes agree with each other?
```

### TreeSynthesis

The final output combining all hypothesis verdicts.

```python
class TreeSynthesis(BaseModel):
    """Final synthesis across all hypotheses for a problem statement."""

    problem_id: str
    hypotheses_tested: int
    hypotheses_confirmed: int
    dominant_hypothesis: str                   # ID of highest-confidence hypothesis
    confidence_ranking: list[tuple[str, float]]  # Ordered by confidence
    synthesis_narrative: str                   # 2-3 paragraph executive summary
    recommended_actions: list[str]             # Prioritized action list
    overall_confidence: float                  # Weighted across enabled hypotheses
    disabled_hypotheses: list[str]             # What the user chose to skip
    confidence_impact_of_disabled: float       # How much confidence drops from skipping
```

---

## Confidence Computation

### Probe-Level Confidence

Each probe type computes confidence differently:

**Interview probes**: Confidence = dominant cluster percentage × response coherence score.
If 62% of personas cluster around "price re-evaluation" and their responses are internally consistent (referencing similar attributes), confidence is high.

```python
def compute_interview_confidence(clusters: list[ResponseCluster]) -> float:
    if not clusters:
        return 0.0
    dominant = max(clusters, key=lambda c: c.percentage)
    # High confidence when one cluster dominates AND the cluster is coherent
    dominance = dominant.percentage                    # 0.0-1.0
    coherence = _attribute_coherence(dominant)         # Do cluster members share attribute patterns?
    return dominance * 0.6 + coherence * 0.4
```

**Simulation probes**: Confidence = magnitude of lift × statistical significance.

```python
def compute_simulation_confidence(baseline: float, modified: float, sample_size: int) -> float:
    lift = abs(modified - baseline)
    # Larger lift + larger sample = higher confidence
    significance = min(1.0, sample_size / 100)        # Need ~100 personas for strong signal
    return min(1.0, lift * 3.0) * significance         # Scale lift (0.33 lift → 1.0 confidence)
```

**Attribute analysis probes**: Confidence = effect size × sample coverage.

```python
def compute_attribute_confidence(splits: list[AttributeSplit]) -> float:
    significant_splits = [s for s in splits if s.significant]
    if not splits:
        return 0.0
    coverage = len(significant_splits) / len(splits)
    mean_effect = sum(abs(s.effect_size) for s in significant_splits) / max(len(significant_splits), 1)
    return coverage * 0.5 + min(1.0, mean_effect) * 0.5
```

### Hypothesis-Level Confidence

Weighted average of probe confidences, with a consistency bonus/penalty.

```python
def compute_hypothesis_confidence(probes: list[Probe]) -> tuple[float, float]:
    completed = [p for p in probes if p.result is not None]
    if not completed:
        return 0.0, 0.0

    confidences = [p.result.confidence for p in completed]
    mean_confidence = sum(confidences) / len(confidences)

    # Consistency: do probes agree? Low variance = bonus
    variance = sum((c - mean_confidence) ** 2 for c in confidences) / len(confidences)
    consistency = max(0.0, 1.0 - variance * 4)        # Penalize high variance

    final_confidence = mean_confidence * 0.8 + consistency * 0.2
    return final_confidence, consistency
```

### Tree-Level Confidence and Disabled Branch Impact

```python
def compute_tree_synthesis(
    hypotheses: list[Hypothesis],
    verdicts: dict[str, HypothesisVerdict],
) -> TreeSynthesis:
    enabled = [h for h in hypotheses if h.enabled]
    disabled = [h for h in hypotheses if not h.enabled]

    # Overall confidence from enabled hypotheses
    if not enabled:
        overall = 0.0
    else:
        overall = max(v.confidence for h_id, v in verdicts.items()
                      if any(h.id == h_id for h in enabled))

    # Impact of disabled branches: what would confidence be with them?
    # Re-compute as if all were enabled
    all_confidences = [v.confidence for v in verdicts.values()]
    full_confidence = max(all_confidences) if all_confidences else 0.0
    disabled_impact = full_confidence - overall

    return TreeSynthesis(
        confidence_impact_of_disabled=disabled_impact,
        overall_confidence=overall,
        ...
    )
```

This gives the user the "if you skip the taste hypothesis, your confidence drops from 0.82 to 0.73" feedback loop.

---

## Cost Architecture

Running probes against real LLMs costs money. The design optimises for **under $1 per tree execution** in standard mode and **under $5 at full scale**.

### Tiered Model Strategy

Not every LLM call needs the same intelligence. We use three tiers:

| Task | Model | Why this tier | Cost per call |
|---|---|---|---|
| **Persona interview responses** | Claude Haiku | Persona voice is semi-structured; we control the prompt tightly. Haiku produces natural conversational responses at 10x lower cost. | ~$0.0007 |
| **Response clustering** | Claude Sonnet | Intelligence-critical step. Bad clustering = bad confidence scores. Sonnet catches semantic similarities that keywords miss (e.g., "my husband questioned the cost" clusters with "price felt high"). | ~$0.015 |
| **Tree synthesis narrative** | Claude Sonnet | User-facing text. Quality of the final recommendation paragraph matters for credibility. | ~$0.02 |
| **Attribute analysis** | None (local computation) | Statistical splits use numpy/scipy, no LLM needed. | $0.00 |
| **Simulation probes** | None (local computation) | Counterfactual runs use the existing deterministic funnel. | $0.00 |

### Sampling Strategy

Interview probes do NOT run against the full population. Instead:

```python
PROBE_SAMPLE_SIZE = 30          # Personas per interview probe
PROBE_STRATIFY_BY = [           # Ensure representation across key segments
    "socioeconomic_class",      # SEC A1/A2/B1/B2
    "city_tier",                # Tier 1/2/3
]
PROBE_OUTCOME_BALANCE = 0.5    # Target 50/50 adopter/rejector split when possible

def sample_personas_for_probe(
    personas: list[Persona],
    outcomes: dict[str, str],
    probe: Probe,
    sample_size: int = PROBE_SAMPLE_SIZE,
) -> list[Persona]:
    """Stratified sampling for interview probes.

    Ensures every SEC class and city tier is represented proportionally,
    while balancing adopters and rejectors for comparative insight.
    If probe.target_outcome is set, only sample from that outcome group.
    """

    pool = personas
    if probe.target_outcome:
        pool = [p for p in personas if outcomes.get(p.id) == probe.target_outcome]

    if len(pool) <= sample_size:
        return pool

    # Stratified sampling: group by SEC × city_tier, sample proportionally
    strata = _build_strata(pool, PROBE_STRATIFY_BY)
    sampled = _proportional_sample(strata, sample_size, seed=DEFAULT_SEED)

    # Balance adopter/rejector when no target_outcome filter
    if not probe.target_outcome:
        sampled = _balance_outcomes(sampled, outcomes, PROBE_OUTCOME_BALANCE)

    return sampled
```

**Why 30?** Statistical power analysis: with 30 samples, a medium effect size (Cohen's d=0.5) is detectable at 80% power. Below 20 we lose reliability; above 50 the marginal insight gain doesn't justify the cost.

### Cost Per Run Breakdown

A typical problem tree has 4 hypotheses × 3-4 probes = ~15 probes total. Of those, roughly:
- 8-10 are interview probes
- 2-3 are simulation probes (free)
- 2-3 are attribute analysis probes (free)

| Component | Calls | Cost per call | Subtotal |
|---|---|---|---|
| Interview responses (Haiku) | 10 probes × 30 personas = 300 | $0.0007 | **$0.21** |
| Response clustering (Sonnet) | 10 probes × 1 clustering call | $0.015 | **$0.15** |
| Hypothesis verdicts (Sonnet) | 4 hypotheses × 1 synthesis call | $0.015 | **$0.06** |
| Tree synthesis (Sonnet) | 1 final narrative | $0.02 | **$0.02** |
| Simulation probes | 3 counterfactual runs | $0.00 | **$0.00** |
| Attribute probes | 3 statistical analyses | $0.00 | **$0.00** |
| **Total per tree run** | | | **~$0.44** |

At this cost, a user can iterate 10 times on a single problem for under $5. Full-day exploration across all 4 problem trees costs ~$2.

### Mock Mode

Mock mode replaces all LLM calls with deterministic responses:
- Interview responses: template-based with persona attribute interpolation (existing `PersonaInterviewer` mock)
- Clustering: keyword-matching against a predefined theme dictionary per probe
- Synthesis: template sentences referencing computed confidence scores

Mock mode costs $0.00 and runs in <5 seconds. This is the default for demos and development.

### Clustering: Mock vs LLM Detail

**Mock clustering** (keyword matching):

When a probe asks 30 personas "What made you hesitate before reordering?", mock mode scans each response for keyword groups:

```python
CLUSTER_KEYWORDS = {
    "price_sensitivity": ["price", "cost", "expensive", "afford", "worth", "₹", "budget"],
    "forgetfulness": ["forgot", "busy", "remind", "remember", "slipped"],
    "taste_decline": ["taste", "refused", "didn't like", "boring", "same"],
    "alternatives": ["switched", "horlicks", "homemade", "another brand"],
}
```

Each response is assigned to its highest-matching cluster. Ties go to the first match. This is fast and free but misses semantic nuance — "my husband asked why we spend on this when dal has protein" matches no keywords but is actually a price concern.

**LLM clustering** (semantic analysis):

All 30 responses are sent to Sonnet in a single call:

```
You are analyzing responses from 30 synthetic consumer personas.
Question: "What made you hesitate before reordering?"

Responses:
[P1]: "The price hit differently the second time around..."
[P2]: "Honestly I just forgot. Life got hectic."
[P3]: "My husband asked why we're spending on this..."
...

Group these into 2-5 thematic clusters. For each cluster, return:
- theme_id: snake_case identifier
- theme_label: 2-4 word human label
- description: one sentence explaining the shared concern
- persona_ids: which personas belong
- confidence: how clearly this theme emerged (0.0-1.0)

Return as JSON array.
```

Sonnet correctly groups P1 and P3 into the same "value_questioning" cluster despite zero keyword overlap. This is where the $0.015 per clustering call pays for itself.

**UI indicator**: Every probe result shows a small badge:

- `🔧 Mock clustering` — keyword-based, instant, $0
- `🧠 Semantic clustering` — LLM-powered, ~2s, ~$0.015

So the user knows the quality level of every insight.

---

## Predefined Problem Trees

### Problem 1: Repeat Purchase Despite High NPS

```yaml
problem:
  id: repeat_purchase_low
  title: "Repeat purchase is low despite high NPS — why?"
  scenario_id: nutrimix_2_6
  success_metric: repeat_rate
  context: >
    LittleJoys Nutrimix has strong first-purchase adoption and high customer
    satisfaction scores. But month-over-month repeat rates are below target.
    Something breaks between "I liked it" and "I bought it again."

hypotheses:
  - id: h1_price_reeval
    title: "Price feels different on repeat vs. first purchase"
    rationale: >
      First purchase is driven by curiosity and emotional appeal. Second
      purchase faces rational cost-benefit re-evaluation against alternatives.
    indicator_attributes:
      - budget_consciousness
      - price_reference_point
      - deal_seeking_intensity
      - value_perception_driver
    probes:
      - id: h1_p1_pause_reason
        type: interview
        question: "After finishing the first pack, what made you hesitate before reordering?"
        target_outcome: reject  # Only ask churned/non-repeaters
      - id: h1_p2_price_comparison
        type: interview
        question: "Did you compare the price to alternatives before your second purchase?"
      - id: h1_p3_price_cut_sim
        type: simulation
        modifications: {"product.price_inr": 479}
        comparison_metric: repeat_rate
      - id: h1_p4_budget_split
        type: attribute
        analysis_attributes: [budget_consciousness, deal_seeking_intensity, price_reference_point]
        split_by: repeat_status

  - id: h2_taste_fatigue
    title: "Child taste fatigue after novelty wears off"
    rationale: >
      Children's taste preferences are volatile. High initial acceptance
      doesn't guarantee sustained consumption, especially for health products.
    indicator_attributes:
      - child_taste_veto
      - snacking_pattern
      - breakfast_routine
    probes:
      - id: h2_p1_enthusiasm
        type: interview
        question: "Did your child's enthusiasm for the product change after the first week?"
      - id: h2_p2_serving_variety
        type: interview
        question: "Did you try different ways of serving it, or kept the same routine?"
      - id: h2_p3_taste_sim
        type: simulation
        modifications: {"product.taste_appeal": 0.9}
        comparison_metric: repeat_rate

  - id: h3_no_reengagement
    title: "No brand re-engagement after first purchase"
    rationale: >
      Without proactive reminders, the product exits working memory. Parents
      who liked it simply forget to reorder amid busy routines.
    indicator_attributes:
      - perceived_time_scarcity
      - ad_receptivity
      - subscription_comfort
      - impulse_purchase_tendency
    probes:
      - id: h3_p1_followup
        type: interview
        question: "After your first purchase, did you see or hear anything from the brand that reminded you?"
      - id: h3_p2_reorder_trigger
        type: interview
        question: "What would make reordering feel automatic rather than a decision?"
      - id: h3_p3_subscription_sim
        type: simulation
        modifications: {"lj_pass_available": true, "marketing.awareness_budget": 0.7}
        comparison_metric: repeat_rate
      - id: h3_p4_time_scarcity
        type: attribute
        analysis_attributes: [perceived_time_scarcity, subscription_comfort, impulse_purchase_tendency]
        split_by: repeat_status

  - id: h4_competitive_substitution
    title: "Switched to a competitor or home remedy"
    rationale: >
      Parents may have found an alternative (Horlicks, Pediasure, homemade
      alternatives) that feels safer, cheaper, or more familiar.
    indicator_attributes:
      - brand_loyalty_tendency
      - indie_brand_openness
      - food_first_belief
      - milk_supplement_current
    probes:
      - id: h4_p1_alternatives
        type: interview
        question: "Between your first and potential second purchase, did you try anything else for nutrition?"
      - id: h4_p2_why_switch
        type: interview
        question: "What made the alternative feel easier or better than continuing with this product?"
        target_outcome: reject
      - id: h4_p3_loyalty_split
        type: attribute
        analysis_attributes: [brand_loyalty_tendency, food_first_belief, indie_brand_openness]
        split_by: repeat_status
```

### Problem 2: Nutrimix 7-14 Expansion

```yaml
problem:
  id: nutrimix_7_14_expansion
  title: "How to establish Nutrimix in the 7-14 age category?"
  scenario_id: nutrimix_7_14
  success_metric: adoption_rate

hypotheses:
  - id: h1_taste_barrier
    title: "Older kids reject the taste or format"
    indicator_attributes: [child_taste_veto, snacking_pattern]
    probes:
      - type: interview
        question: "Would your 8-year-old accept a powder mixed into milk, or would they resist?"
      - type: simulation
        modifications: {"product.taste_appeal": 0.80, "product.form_factor": "chewable_tablet"}

  - id: h2_perceived_irrelevance
    title: "Parents don't see nutrition gaps in older kids"
    indicator_attributes: [nutrition_gap_awareness, health_anxiety, growth_concern]
    probes:
      - type: interview
        question: "At this age, do you still worry about nutritional gaps or feel they eat well enough?"
      - type: attribute
        analysis_attributes: [nutrition_gap_awareness, health_anxiety, supplement_necessity_belief]
        split_by: outcome

  - id: h3_category_confusion
    title: "Parents associate Nutrimix with toddlers, not school-age kids"
    indicator_attributes: [brand_loyalty_tendency, indie_brand_openness]
    probes:
      - type: interview
        question: "When you hear 'Nutrimix', what age group comes to mind?"
      - type: interview
        question: "Would a separate brand name for older kids make you more interested?"

  - id: h4_school_influence
    title: "School and peer channels matter more than social media for this age"
    indicator_attributes: [community_orientation, peer_influence_strength]
    probes:
      - type: simulation
        modifications: {"marketing.school_partnership": true, "marketing.awareness_budget": 0.6}
      - type: interview
        question: "Where do you get recommendations for products your school-age child uses?"
```

### Problem 3: Magnesium Gummies Growth

```yaml
problem:
  id: magnesium_gummies_growth
  title: "How to increase sales of magnesium gummies for kids?"
  scenario_id: magnesium_gummies
  success_metric: adoption_rate

hypotheses:
  - id: h1_category_awareness
    title: "Parents don't know kids need magnesium"
    indicator_attributes: [nutrition_gap_awareness, science_literacy, research_before_purchase]
    probes:
      - type: interview
        question: "Before today, were you aware that magnesium plays a role in your child's sleep and focus?"
      - type: simulation
        modifications: {"marketing.awareness_budget": 0.65, "marketing.pediatrician_endorsement": true}
      - type: attribute
        analysis_attributes: [science_literacy, nutrition_gap_awareness]
        split_by: outcome

  - id: h2_supplement_skepticism
    title: "Parents doubt gummy supplements can meaningfully support their child's overall development"
    indicator_attributes: [supplement_necessity_belief, natural_vs_synthetic_preference, food_first_belief]
    probes:
      - type: interview
        question: "Do gummy vitamins feel like real supplements to you, or more like candy?"
      - type: interview
        question: "Would you trust a gummy more if it came with a doctor's recommendation?"

  - id: h3_price_vs_perceived_value
    title: "₹499 for gummies feels expensive vs. established alternatives"
    indicator_attributes: [budget_consciousness, price_reference_point, health_spend_priority]
    probes:
      - type: interview
        question: "How does ₹499 for a month's supply of gummies compare to what you currently spend on vitamins?"
      - type: simulation
        modifications: {"product.price_inr": 349}
```

### Problem 4: ProteinMix Launch

```yaml
problem:
  id: protein_mix_launch
  title: "How to increase adoption of ProteinMix for kids?"
  scenario_id: protein_mix
  success_metric: adoption_rate

hypotheses:
  - id: h1_effort_barrier
    title: "Cooking requirement is too high a barrier"
    indicator_attributes: [perceived_time_scarcity, cooking_time_available, simplicity_preference]
    probes:
      - type: interview
        question: "Would you add a protein powder to pancake batter or roti dough on a busy morning?"
      - type: simulation
        modifications: {"product.effort_to_acquire": 0.15, "product.cooking_required": 0.2, "product.form_factor": "ready_to_drink"}
      - type: attribute
        analysis_attributes: [perceived_time_scarcity, cooking_time_available, simplicity_preference, morning_routine_complexity]
        split_by: outcome

  - id: h2_category_unfamiliarity
    title: "Parents don't think kids need protein supplementation"
    indicator_attributes: [supplement_necessity_belief, nutrition_gap_awareness]
    probes:
      - type: interview
        question: "Do you feel your child gets enough protein from regular meals?"
      - type: interview
        question: "What would convince you that a protein supplement is worth adding to their diet?"

  - id: h3_taste_concern
    title: "Parents doubt their child will eat protein-fortified food"
    indicator_attributes: [child_taste_veto]
    probes:
      - type: interview
        question: "If your child could taste the protein powder in their pancake, would they refuse to eat it?"
      - type: simulation
        modifications: {"product.taste_appeal": 0.75}
```

---

## Coverage Matrix

Every persona attribute category must be tested by at least one hypothesis across the four problem trees. Gaps = blind spots.

### By Funnel Stage

| Funnel Stage | Which hypotheses test it | Coverage |
|---|---|---|
| **Need Recognition** | P2-H2 (perceived irrelevance), P3-H1 (category awareness), P4-H2 (category unfamiliarity) | ⚠️ Weak — no hypothesis tests whether *parents with an existing need still fail to act* |
| **Awareness** | P3-H1 (category awareness), P1-H3 (re-engagement), P2-H4 (school channels) | ✅ Good |
| **Consideration** | P1-H4 (competitive substitution), P3-H2 (supplement skepticism), P2-H3 (category confusion) | ✅ Good |
| **Purchase** | P1-H1 (price memory), P3-H3 (price vs value), P4-H1 (effort barrier) | ✅ Good |
| **Repeat** | P1-H1 (price re-eval), P1-H2 (taste fatigue), P1-H3 (no re-engagement) | ✅ Deep (Problem 1 is repeat-focused) |

**Gap to fix**: Add a Need Recognition hypothesis to Problem 1 — "Parents who adopted once may not perceive an *ongoing* need for supplementation" (tests `nutrition_gap_awareness`, `supplement_necessity_belief` among adopters who didn't repeat).

### By Persona Attribute Category

| Attribute Category | Attributes | Trees that test them | Untested attributes |
|---|---|---|---|
| **Financial** | budget_consciousness, price_reference_point, deal_seeking_intensity, health_spend_priority | P1-H1, P3-H3, P4-H1 | ✅ All covered |
| **Health beliefs** | nutrition_gap_awareness, supplement_necessity_belief, health_anxiety, food_first_belief | P2-H2, P3-H1, P3-H2, P4-H2 | ✅ All covered |
| **Trust & authority** | medical_authority_trust, brand_loyalty_tendency, indie_brand_openness | P1-H4, P2-H3, P3-H2 | ✅ All covered |
| **Child factors** | child_taste_veto, snacking_pattern, breakfast_routine | P1-H2, P2-H1, P4-H3 | ✅ All covered |
| **Time & convenience** | perceived_time_scarcity, cooking_time_available, simplicity_preference, morning_routine_complexity | P1-H3, P4-H1 | ⚠️ Only tested in 2 of 4 trees |
| **Social influence** | community_orientation, peer_influence_strength, joint_family_influence, whatsapp_group_trust | P2-H4 (school influence) | ⚠️ **Major gap** — `joint_family_influence` and `whatsapp_group_trust` appear in zero hypotheses |
| **Media & digital** | ad_receptivity, social_media_hours, digital_payment_comfort, app_download_willingness | P1-H3 (ad_receptivity) | ⚠️ `social_media_hours`, `digital_payment_comfort` untested |
| **Cultural** | traditional_vs_modern_spectrum, ayurveda_affinity, western_brand_trust, made_in_india_preference | None directly | ❌ **No tree tests cultural attributes** |

### Gaps to Address

1. **Social influence is undertested**. Add a hypothesis to Problems 2 or 3: "Word-of-mouth in parent communities drives (or blocks) adoption" — tests `whatsapp_group_trust`, `community_orientation`, `joint_family_influence`.

2. **Cultural attributes are orphaned**. Add to Problem 3 (gummies): "Gummies feel 'Western' and parents prefer Ayurvedic alternatives" — tests `ayurveda_affinity`, `made_in_india_preference`, `western_brand_trust`.

3. **Adopter probing is missing**. Most interview probes target rejectors. Add symmetric probes: "What made you decide to reorder?" (Problem 1), "What convinced you to try this for your older child?" (Problem 2).

### Probe Type Triangulation

Each hypothesis should ideally use at least 2 of the 3 probe types for triangulation:

| Tree | Hypothesis | Interview | Simulation | Attribute | Triangulated? |
|---|---|---|---|---|---|
| P1 | H1 Price memory | ✅ 2 probes | ✅ price cut | ✅ budget split | ✅ Full |
| P1 | H2 Taste fatigue | ✅ 2 probes | ✅ taste sim | ❌ | ⚠️ Add attribute probe |
| P1 | H3 No re-engagement | ✅ 2 probes | ✅ subscription | ✅ time scarcity | ✅ Full |
| P1 | H4 Competitive sub. | ✅ 2 probes | ❌ | ✅ loyalty split | ⚠️ Add simulation |
| P2 | H1 Taste barrier | ✅ 1 probe | ✅ format sim | ❌ | ⚠️ Add attribute |
| P2 | H2 Perceived irrelevance | ✅ 1 probe | ❌ | ✅ awareness split | ⚠️ Add simulation |
| P2 | H3 Category confusion | ✅ 2 probes | ❌ | ❌ | ❌ Interview-only |
| P2 | H4 School influence | ❌ | ✅ school sim | ✅ 1 interview | ⚠️ Add attribute |
| P3 | H1 Category awareness | ✅ 1 probe | ✅ awareness sim | ✅ literacy split | ✅ Full |
| P3 | H2 Supplement skepticism | ✅ 2 probes | ❌ | ❌ | ❌ Interview-only |
| P3 | H3 Price vs value | ✅ 1 probe | ✅ price sim | ❌ | ⚠️ Add attribute |
| P4 | H1 Effort barrier | ✅ 1 probe | ✅ convenience sim | ✅ time split | ✅ Full |
| P4 | H2 Category unfamiliarity | ✅ 2 probes | ❌ | ❌ | ❌ Interview-only |
| P4 | H3 Taste concern | ✅ 1 probe | ✅ taste sim | ❌ | ⚠️ Add attribute |

**Summary**: 4 of 15 hypotheses have full 3-way triangulation. 6 are interview-only or missing a probe type. During implementation, fill gaps before marking the tree as "ready".

---

## Execution Engine

### How Probes Run

```python
class ProbingTreeEngine:
    """Orchestrates probe execution across the persona population.

    Cost-optimised: interview probes use Haiku for responses (cheap),
    Sonnet for clustering and synthesis (intelligence-critical).
    Simulation and attribute probes use no LLM at all.
    """

    def __init__(
        self,
        population: Population,
        scenario_id: str,
        llm_client: LLMClient,              # Sonnet — used for clustering + synthesis
        interview_client: LLMClient | None,  # Haiku — used for persona responses (cheaper)
    ) -> None:
        self.population = population
        self.scenario = get_scenario(scenario_id)
        self.llm = llm_client                                          # Sonnet
        self.interview_llm = interview_client or llm_client            # Haiku (falls back to Sonnet)
        self.interviewer = PersonaInterviewer(self.interview_llm)      # Uses cheap model
        self._outcomes: dict[str, str] = {}                            # Cached funnel outcomes
        self._precompute_outcomes()

    def _precompute_outcomes(self) -> None:
        """Run funnel once for all personas. Reused across probes."""
        for persona in self.population.tier1_personas:
            result = run_funnel(persona, self.scenario)
            self._outcomes[persona.id] = result.to_dict()["outcome"]

    async def execute_probe(self, probe: Probe) -> ProbeResult:
        if probe.probe_type == ProbeType.INTERVIEW:
            return await self._run_interview_probe(probe)
        if probe.probe_type == ProbeType.SIMULATION:
            return self._run_simulation_probe(probe)
        if probe.probe_type == ProbeType.ATTRIBUTE_ANALYSIS:
            return self._run_attribute_probe(probe)

    async def _run_interview_probe(self, probe: Probe) -> ProbeResult:
        """Ask the question to a SAMPLED subset and cluster responses.

        Cost: ~30 Haiku calls ($0.021) + 1 Sonnet clustering call ($0.015)
        """

        # 1. Select target personas (full pool for filtering)
        personas = list(self.population.tier1_personas)

        # 2. Sample — stratified by SEC + city_tier, balanced by outcome
        sampled = sample_personas_for_probe(
            personas=personas,
            outcomes=self._outcomes,
            probe=probe,
            sample_size=PROBE_SAMPLE_SIZE,          # Default: 30
        )

        # 3. Run interviews via HAIKU (cheap model)
        responses: list[tuple[Persona, str]] = []
        for persona in sampled:
            decision = run_funnel(persona, self.scenario)
            turn = await self.interviewer.interview(   # Uses self.interview_llm (Haiku)
                persona=persona,
                question=probe.question_template,
                scenario_id=self.scenario.id,
                decision_result=decision.to_dict(),
            )
            responses.append((persona, turn.content))

        # 4. Cluster responses via SONNET (intelligence-critical)
        clusters = await self._cluster_responses(responses, probe)  # Uses self.llm (Sonnet)

        # 5. Compute confidence
        confidence = compute_interview_confidence(clusters)

        return ProbeResult(
            probe_id=probe.id,
            confidence=confidence,
            evidence_summary=self._summarize_clusters(clusters),
            sample_size=len(responses),
            population_size=len(personas),           # Track total vs sampled
            response_clusters=clusters,
            clustering_method="semantic" if not self.llm.config.llm_mock_enabled else "keyword",
        )

    def _run_simulation_probe(self, probe: Probe) -> ProbeResult:
        """Run a counterfactual simulation and compare metrics.

        Cost: $0.00 — uses deterministic funnel, no LLM calls.
        Runs against FULL population (simulation is cheap).
        """

        from src.simulation.counterfactual import run_counterfactual

        result = run_counterfactual(
            population=self.population,
            baseline_scenario=self.scenario,
            modifications=probe.scenario_modifications,
            counterfactual_name=probe.id,
            seed=DEFAULT_SEED,
        )

        confidence = compute_simulation_confidence(
            result.baseline_adoption_rate,
            result.counterfactual_adoption_rate,
            len(self.population.tier1_personas),
        )

        return ProbeResult(
            probe_id=probe.id,
            confidence=confidence,
            evidence_summary=(
                f"Changing {probe.scenario_modifications} moved "
                f"{probe.comparison_metric or 'adoption'} from "
                f"{result.baseline_adoption_rate:.0%} to "
                f"{result.counterfactual_adoption_rate:.0%} "
                f"(lift: {result.absolute_lift:+.1%})"
            ),
            sample_size=len(self.population.tier1_personas),
            baseline_metric=result.baseline_adoption_rate,
            modified_metric=result.counterfactual_adoption_rate,
            lift=result.absolute_lift,
            clustering_method=None,                  # No clustering for simulation probes
        )

    def _run_attribute_probe(self, probe: Probe) -> ProbeResult:
        """Statistical comparison of attributes between outcome groups.

        Cost: $0.00 — pure numpy/scipy computation, no LLM calls.
        Runs against FULL population (computation is cheap).
        """

        flat_data = []
        for persona in self.population.tier1_personas:
            flat = persona.to_flat_dict()
            flat["_outcome"] = self._outcomes[persona.id]   # Use cached outcomes
            flat_data.append(flat)

        splits = []
        for attr in probe.analysis_attributes:
            adopter_vals = [r[attr] for r in flat_data if r["_outcome"] == "adopt" and attr in r]
            rejector_vals = [r[attr] for r in flat_data if r["_outcome"] == "reject" and attr in r]

            if adopter_vals and rejector_vals:
                adopter_mean = sum(adopter_vals) / len(adopter_vals)
                rejector_mean = sum(rejector_vals) / len(rejector_vals)
                pooled_std = _pooled_std(adopter_vals, rejector_vals)
                effect_size = (adopter_mean - rejector_mean) / pooled_std if pooled_std > 0 else 0
                splits.append(AttributeSplit(
                    attribute=attr,
                    adopter_mean=adopter_mean,
                    rejector_mean=rejector_mean,
                    effect_size=effect_size,
                    significant=abs(effect_size) > 0.3,  # Medium effect size threshold
                ))

        confidence = compute_attribute_confidence(splits)

        return ProbeResult(
            probe_id=probe.id,
            confidence=confidence,
            evidence_summary=_format_attribute_summary(splits),
            sample_size=len(flat_data),
            attribute_splits=splits,
            clustering_method=None,                  # No clustering for attribute probes
        )
```

### Response Clustering

Covered in detail in the **Cost Architecture** section above. Summary:

- **Mock mode**: Keyword matching against predefined theme dictionaries. Free, instant, deterministic.
- **Real mode**: Single Sonnet call per probe clusters all 30 responses semantically. ~$0.015, ~2 seconds.
- **UI badge**: Every probe result shows its clustering method so the user knows the quality level.

---

## Visualization: The Tree UI

### Layout

The Streamlit page would be structured as:

```
┌──────────────────────────────────────────────────────────────┐
│  Problem: "Why is repeat purchase low despite high NPS?"     │
│  Overall Confidence: ████████░░ 0.78                         │
│  Dominant finding: Re-engagement failure (0.82)              │
│  Run cost: $0.42 · 300 Haiku + 14 Sonnet calls              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ☑ H1: Price memory (0.73)         ████████░░                │
│    ├── 🎤 Pause reason              ✅ 0.68  30/200 sampled  │
│    ├── 🎤 Price comparison          ✅ 0.71  30/200 sampled  │
│    ├── 🔬 Price cut sim             ✅ 0.82  200/200 (+7pp)  │
│    └── 📊 Budget split              ✅ 0.70  200/200         │
│                                                              │
│  ☑ H2: Taste fatigue (0.41)        █████░░░░░                │
│    ├── 🎤 Enthusiasm change         ✅ 0.38  30/200 sampled  │
│    ├── 🎤 Serving variety           ✅ 0.42  30/200 sampled  │
│    └── 🔬 Taste sim                 ✅ 0.44  200/200 (+3pp)  │
│                                                              │
│  ☑ H3: No re-engagement (0.82)     █████████░  ← BEST       │
│    ├── 🎤 Brand follow-up           ✅ 0.88  30/200 sampled  │
│    ├── 🎤 Reorder triggers          ✅ 0.79  30/200 sampled  │
│    ├── 🔬 Subscription sim          ✅ 0.85  200/200 (+12pp) │
│    └── 📊 Time scarcity             ✅ 0.76  200/200         │
│                                                              │
│  ☐ H4: Competitive subst. (skip)   ░░░░░░░░░░                │
│    ⚠ Skipping reduces confidence by 0.04                    │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  SYNTHESIS                                                   │
│  The primary driver is re-engagement failure: 78% of         │
│  non-repeaters simply forgot to reorder. Price is a          │
│  secondary factor (mainly for SEC B2+ families). Taste       │
│  fatigue is not a significant contributor.                   │
│                                                              │
│  Recommended actions:                                        │
│  1. Implement automated reorder reminders (WhatsApp)         │
│  2. LJ Pass free trial for first-time buyers                 │
│  3. Targeted price messaging for B2 segment                  │
│                                                              │
│  🎤 = Interview (Haiku, sampled)                             │
│  🔬 = Simulation (no LLM, full population)                   │
│  📊 = Attribute analysis (no LLM, full population)           │
└──────────────────────────────────────────────────────────────┘
```

### Interactions

1. **Toggle hypotheses**: Checkbox next to each hypothesis. Disabling one greys it out and shows confidence impact.

2. **Expand probes**: Click any probe to see full results — persona quotes, attribute distributions, simulation charts.

3. **Add custom probe**: Button at the bottom of each hypothesis to add a freeform question.

4. **Add custom hypothesis**: Button below all hypotheses to define a new one with custom probes.

5. **Re-run with different population**: Change demographic filters and re-execute the tree.

6. **Export**: Generate a PDF/markdown report of the full tree with evidence.

---

## Integration with Existing Architecture

### What changes

| Component | Current | With Probing Tree |
|---|---|---|
| `src/decision/scenarios.py` | 4 hardcoded scenarios | Unchanged — probing tree references scenarios by ID |
| `src/analysis/interviews.py` | Single-persona Q&A | Unchanged — probing tree loops existing `interview()` over sampled personas |
| `src/simulation/counterfactual.py` | Predefined counterfactuals | Unchanged — probing tree calls `run_counterfactual` with custom modifications |
| `src/analysis/causal.py` | Global variable importance | Extended for per-hypothesis attribute analysis |
| `app/pages/` | 6 pages | Add page 6: Probing Tree |

### New files

```
src/probing/
    __init__.py
    models.py              # ProblemStatement, Hypothesis, Probe, ProbeResult, etc.
    engine.py              # ProbingTreeEngine — orchestrates execution
    confidence.py          # All confidence computation functions
    clustering.py          # Response clustering (mock keyword + LLM semantic)
    sampling.py            # Stratified persona sampling for interview probes
    synthesis.py           # TreeSynthesis generation (Sonnet)
    predefined_trees.py    # The 4 problem trees defined above
    tree_generator.py      # v2: LLM-powered dynamic tree generation from user scenario description

app/pages/
    6_probing_tree.py      # Streamlit UI

tests/unit/
    test_probing_models.py
    test_probing_engine.py
    test_probing_confidence.py
    test_probing_sampling.py
    test_probing_clustering.py
```

### What stays the same

The probing tree is a **consumer** of existing infrastructure, not a replacement:
- Personas are generated the same way
- The funnel runs the same way
- Counterfactuals work the same way
- Interviews use the same PersonaInterviewer

The tree is an orchestration layer that sequences these existing tools in a hypothesis-driven investigation flow.

---

## Design Decisions (Resolved)

| # | Question | Decision | Rationale |
|---|---|---|---|
| 1 | Mock vs LLM at scale | **Sample 30 personas per interview probe**, stratified by SEC + city_tier + outcome. Full population for simulation and attribute probes (free). | 30 is the statistical minimum for medium effect size detection. Keeps cost at ~$0.44/tree. |
| 2 | Clustering quality | **Two-tier**: keyword matching (mock, $0), semantic LLM clustering (real, $0.015/probe). UI shows which method was used. | Keyword clustering is good enough for structure/demo. Semantic clustering is the value-add that justifies real LLM spend. |
| 3 | Model selection | **Haiku for interviews, Sonnet for clustering + synthesis**. No Opus anywhere. | Interview responses are semi-structured (persona template + question). Clustering and synthesis are intelligence-critical. Haiku is 10x cheaper. |
| 4 | User-defined hypotheses | **v1: Structured** (pick from attribute categories, pick probe type, write question). **v2: Free-text** with LLM structuring. | Structured first ensures data model integrity. Free-text v2 uses the same tree generator agent as dynamic scenarios. |
| 5 | Persistence | **Yes — save to JSON** in `data/results/probing/`. Resume partial trees across sessions. | Long-running trees (15+ probes with real LLM) take 2-3 minutes. Losing progress to a page refresh is unacceptable. |

## Open Design Questions (Remaining)

1. **Temporal probes**: The repeat purchase problem needs multi-month simulation (run 6 months, check churn at month 3). Should we add `ProbeType.TEMPORAL` as a fourth type, or model it as a simulation probe with `months` parameter?

2. **Cross-scenario probing**: "Does LJ Pass impact gummies too, not just Nutrimix?" requires running probes across multiple scenarios. Allow per-probe `scenario_id` override, or keep trees single-scenario?

3. **Confidence calibration**: The confidence formulas are designed but untested. After v1 implementation, we need to run all 4 trees and check whether the confidence scores produce sensible orderings. May need to tune weights.

---

## v2: Dynamic Tree Generation

### The Vision

In v1, users pick from 4 predefined problem trees. In v2, users **describe a scenario in natural language** and the system generates the entire probing tree.

### User Flow

```
┌──────────────────────────────────────────────────────────────┐
│  Describe your scenario:                                     │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ We're launching a probiotic yogurt drink for kids aged   ││
│  │ 3-8, priced at ₹149, sold through quick commerce in     ││
│  │ Tier 1 cities. Will it work?                             ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  [Generate Investigation Tree]                               │
│                                                              │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│    Loading... Generating hypotheses (Sonnet, ~$0.03)       │ │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│                                                              │
│  Generated tree: "Will probiotic yogurt succeed in Tier 1?"  │
│                                                              │
│  ☑ H1: Category awareness gap                               │
│  │  ├── 🎤 Do parents know kids need probiotics?             │
│  │  ├── 🎤 Is "probiotic" trusted or confusing?              │
│  │  └── 🔬 Awareness campaign simulation                     │
│  │                                                           │
│  ☑ H2: Price positioning vs Yakult (₹80)                    │
│  │  ├── 🎤 How does ₹149 compare to what you pay now?       │
│  │  ├── 🔬 Price at ₹99 simulation                          │
│  │  └── 📊 Budget consciousness vs outcome                   │
│  │                                                           │
│  ☑ H3: Quick commerce discovery behaviour                   │
│  │  ├── 🎤 Do you impulse-buy health products on Blinkit?   │
│  │  ├── 🎤 Would free sampling at delivery change your mind? │
│  │  └── 📊 Digital comfort vs adoption                       │
│  │                                                           │
│  ☑ H4: Taste and format — daily yogurt compliance           │
│  │  ├── 🎤 Will your child drink this daily?                │
│  │  └── 🔬 Taste appeal 0.85 simulation                     │
│  │                                                           │
│  ☐ H5: Trust — live cultures safety concern                 │
│  │  ├── 🎤 Does "live cultures" worry or reassure you?      │
│  │  └── 🔬 Pediatrician endorsement simulation              │
│  │  ⚠ Disabling reduces confidence by ~0.06                │
│  │                                                           │
│  Estimated run cost: $0.38 · ~270 Haiku + 12 Sonnet calls   │
│                                                              │
│  [Run Investigation]  [Edit Tree]  [Configure Scenario →]    │
└──────────────────────────────────────────────────────────────┘
```

### How Tree Generation Works

A single Sonnet call with structured output:

```python
class TreeGeneratorAgent:
    """Generates a probing tree from a natural-language scenario description.

    Cost: 1 Sonnet call (~$0.03) for the full tree structure.
    """

    SYSTEM_PROMPT = """You are a consumer research strategist for the Indian
    kids' nutrition market. Given a product scenario description, generate a
    structured investigation tree.

    Rules:
    - Generate 3-5 hypotheses, ordered by likely impact
    - Each hypothesis MUST have 2-4 probes
    - Each hypothesis MUST use at least 2 probe types (triangulation)
    - Interview probes: natural questions a parent would understand
    - Simulation probes: specific parameter modifications with values
    - Attribute probes: pick from the available persona attributes
    - Ground every hypothesis in specific persona attributes
    - Think about the Indian market context: price sensitivity, trust in
      doctors, family influence, regional differences

    Available persona attributes for indicator_attributes and analysis:
    {ATTRIBUTE_LIST}

    Available scenario parameters for simulation modifications:
    {SCENARIO_PARAMS}

    Return a JSON object matching the ProblemStatement + Hypothesis + Probe
    schema exactly.
    """

    async def generate_tree(
        self,
        scenario_description: str,
    ) -> tuple[ProblemStatement, list[Hypothesis]]:
        """Generate a complete probing tree from user's description.

        Returns:
            ProblemStatement + list of Hypothesis objects with nested Probes.
        """
        prompt = self.SYSTEM_PROMPT.format(
            ATTRIBUTE_LIST=_format_attribute_list(),
            SCENARIO_PARAMS=_format_scenario_params(),
        )
        response = await self.llm.generate(
            system=prompt,
            user=scenario_description,
            response_format=ProbingTreeSchema,       # Pydantic model for structured output
        )
        return _parse_tree_response(response)
```

### Auto-Configured Scenario

After the user approves the tree, clicking "Configure Scenario →" pre-populates a `ScenarioConfig` from the description:

```python
async def generate_scenario_config(
    self,
    scenario_description: str,
    problem: ProblemStatement,
) -> ScenarioConfig:
    """Map natural language to ScenarioConfig parameters.

    Extracts: product name, price, age range, form factor, category,
    and reasonable defaults for taste_appeal, effort_to_acquire, etc.
    """
    ...
```

The user can then adjust any parameter before running the tree. This bridges the gap between "I have an idea" and "I have a fully configured simulation."

### Cost of Tree Generation

| Step | Model | Cost |
|---|---|---|
| Generate tree structure | 1 Sonnet call | ~$0.03 |
| Generate scenario config | 1 Sonnet call | ~$0.02 |
| User edits tree (free) | — | $0.00 |
| Run tree | See Cost Architecture | ~$0.44 |
| **Total from idea to insight** | | **~$0.49** |

### v1 → v2 Migration

The data model is identical. v1 hardcodes trees in `predefined_trees.py`. v2 generates them via `tree_generator.py`. The engine, confidence computation, clustering, and UI are the same.

```
v1: predefined_trees.py → ProblemStatement + Hypotheses → ProbingTreeEngine → UI
v2: tree_generator.py   → ProblemStatement + Hypotheses → ProbingTreeEngine → UI
                           ↑                                  (same)          (same)
                    LLM generates this
```
