# Auto-Scenario Exploration — System Design

**Status:** Design Draft
**Sprint:** 10
**Author:** Claude (Tech Lead)
**Last updated:** 2026-03-29

---

## 1. Problem Statement

Today, a user manually configures one scenario at a time, runs it, and reads the results. They have no way to:

1. **Discover what they don't know** — a different price point or channel mix might dramatically outperform their chosen configuration
2. **Run at scale** — testing 50 variations manually takes hours of clicking
3. **Compare systematically** — no side-by-side comparison of what worked vs what didn't
4. **Get "you missed this" insights** — if an auto-generated variant outperforms, the user should know why

**Sprint 10 goal:** One trigger → N scenario variants auto-generated → all run in parallel → consolidated results with best/worst/user comparison → downloadable report.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│  User selects base scenario (e.g., nutrimix_2_6)     │
│  Clicks "Explore Variations"                         │
└────────────────────┬─────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────┐
│  ScenarioVariantGenerator                            │
│  - Generates N variants by perturbing parameters     │
│  - Strategies: sweep, grid, random, smart            │
│  - Output: list[ScenarioConfig]                      │
└────────────────────┬─────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────┐
│  BatchSimulationRunner                               │
│  - Runs static funnel for all variants               │
│  - Parallel execution (ProcessPoolExecutor)          │
│  - Collects StaticSimulationResult per variant       │
│  - Progress callback for UI                          │
└────────────────────┬─────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────┐
│  ExplorationConsolidator                             │
│  - Ranks all variants by adoption rate               │
│  - Compares user's scenario vs best auto variant     │
│  - Identifies which parameters drove the difference  │
│  - Generates "you missed this" insights              │
│  - Produces ExplorationReport                        │
└────────────────────┬─────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────┐
│  UI: Exploration Results Page                        │
│  - Ranking table of all variants                     │
│  - Best vs user comparison                           │
│  - Parameter sensitivity charts                      │
│  - "Missed insights" callouts                        │
│  - Download as PDF (Sprint 11)                       │
└──────────────────────────────────────────────────────┘
```

---

## 3. Variant Generation Strategies

### 3.1 Parameter Space

The ScenarioConfig has these tunable parameters:

| Parameter | Path | Type | Range | Default (nutrimix_2_6) |
|-----------|------|------|-------|----------------------|
| Price | `product.price_inr` | float | 199-999 | 599 |
| Taste Appeal | `product.taste_appeal` | float | 0.0-1.0 | 0.70 |
| Effort to Acquire | `product.effort_to_acquire` | float | 0.0-1.0 | 0.30 |
| Clean Label Score | `product.clean_label_score` | float | 0.0-1.0 | 0.80 |
| Premium Positioning | `product.premium_positioning` | float | 0.0-1.0 | 0.55 |
| Awareness Budget | `marketing.awareness_budget` | float | 0.0-1.0 | 0.45 |
| Perceived Quality | `marketing.perceived_quality` | float | 0.0-1.0 | 0.70 |
| Trust Signal | `marketing.trust_signal` | float | 0.0-1.0 | 0.60 |
| Social Proof | `marketing.social_proof` | float | 0.0-1.0 | 0.50 |
| Influencer Signal | `marketing.influencer_signal` | float | 0.0-1.0 | 0.40 |
| Social Buzz | `marketing.social_buzz` | float | 0.0-1.0 | 0.35 |
| Discount Available | `marketing.discount_available` | float | 0.0-1.0 | 0.00 |
| School Partnership | `marketing.school_partnership` | bool | T/F | False |
| Influencer Campaign | `marketing.influencer_campaign` | bool | T/F | True |
| Pediatrician Endorsement | `marketing.pediatrician_endorsement` | bool | T/F | True |
| Instagram Weight | `marketing.channel_mix.instagram` | float | 0.0-1.0 | 0.35 |
| YouTube Weight | `marketing.channel_mix.youtube` | float | 0.0-1.0 | 0.25 |
| WhatsApp Weight | `marketing.channel_mix.whatsapp` | float | 0.0-1.0 | 0.20 |
| Pediatrician Weight | `marketing.channel_mix.pediatrician` | float | 0.0-1.0 | 0.20 |

**Channel mix constraint:** Must sum to ~1.0. Variants must normalize after perturbation.

### 3.2 Generation Strategies

```python
class VariantStrategy(StrEnum):
    SWEEP = "sweep"       # One parameter at a time, N steps
    GRID = "grid"         # Cartesian product of key parameters
    RANDOM = "random"     # Random sampling from parameter space
    SMART = "smart"       # Informed perturbations based on funnel analysis
```

#### Strategy 1: Parameter Sweep

Vary one parameter at a time while holding others at baseline.

```python
SWEEP_PARAMETERS: list[dict] = [
    {"path": "product.price_inr", "values": [299, 399, 499, 599, 699, 799]},
    {"path": "marketing.awareness_budget", "values": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]},
    {"path": "product.taste_appeal", "values": [0.4, 0.5, 0.6, 0.7, 0.8, 0.9]},
    {"path": "marketing.discount_available", "values": [0.0, 0.1, 0.2, 0.3]},
    {"path": "marketing.school_partnership", "values": [True, False]},
    {"path": "marketing.pediatrician_endorsement", "values": [True, False]},
]
```

Produces: ~30 variants. Good for **sensitivity analysis** — "which parameter matters most?"

#### Strategy 2: Grid Search

Pick 3-4 high-impact parameters, create all combinations.

```python
GRID_PARAMETERS: dict[str, list] = {
    "product.price_inr": [399, 599, 799],
    "marketing.awareness_budget": [0.3, 0.5, 0.7],
    "product.taste_appeal": [0.5, 0.7, 0.9],
}
```

Produces: 3 × 3 × 3 = 27 variants. Good for **interaction effects** — "does price + awareness combine non-linearly?"

#### Strategy 3: Random Sampling

Latin Hypercube Sampling across the full parameter space.

```python
def generate_random_variants(
    base: ScenarioConfig,
    n_variants: int = 100,
    seed: int = 42,
) -> list[ScenarioConfig]:
    """Sample n_variants from the parameter space using Latin Hypercube."""
```

Produces: N variants (user-controlled, default 100). Good for **Monte Carlo exploration** — "what's the overall distribution of outcomes?"

#### Strategy 4: Smart Perturbation

Analyze the base scenario's rejection distribution and generate targeted variants that address the dominant rejection reason.

```python
def generate_smart_variants(
    base: ScenarioConfig,
    base_result: StaticSimulationResult,
    n_variants: int = 20,
) -> list[ScenarioConfig]:
    """
    Generate variants that specifically target the top rejection reasons.

    If 40% reject at awareness → boost awareness_budget, add channels
    If 30% reject at purchase → reduce price, add discount
    If 20% reject at consideration → boost trust_signal, add endorsements
    If 10% reject at need → can't change (persona attribute, not scenario)
    """
```

**Rejection-to-parameter mapping:**

```python
REJECTION_REMEDIATIONS: dict[str, list[dict[str, Any]]] = {
    "awareness": [
        {"path": "marketing.awareness_budget", "delta": +0.15},
        {"path": "marketing.influencer_campaign", "value": True},
        {"path": "marketing.social_buzz", "delta": +0.20},
        {"path": "marketing.channel_mix.whatsapp", "delta": +0.10},  # high trust channel
    ],
    "consideration": [
        {"path": "marketing.trust_signal", "delta": +0.15},
        {"path": "marketing.pediatrician_endorsement", "value": True},
        {"path": "marketing.school_partnership", "value": True},
        {"path": "marketing.perceived_quality", "delta": +0.15},
        {"path": "product.clean_label_score", "delta": +0.10},
    ],
    "purchase": [
        {"path": "product.price_inr", "delta": -100},
        {"path": "marketing.discount_available", "delta": +0.15},
        {"path": "product.taste_appeal", "delta": +0.10},
        {"path": "product.effort_to_acquire", "delta": -0.10},
    ],
    "need_recognition": [
        # Need is persona-driven, not scenario-driven
        # But we can try boosting relevance signals
        {"path": "product.health_relevance", "delta": +0.15},
        {"path": "product.category_need_baseline", "delta": +0.10},
    ],
}
```

Produces: ~20 targeted variants. Most likely to discover actionable improvements.

---

## 4. Data Models

### 4.1 Variant Metadata

```python
class ScenarioVariant(BaseModel):
    """A single scenario variant with its modifications tracked."""

    model_config = ConfigDict(extra="forbid")

    variant_id: str                          # "base", "v001", "v002", ...
    variant_name: str                        # Human label: "Price ₹399", "High Awareness"
    strategy: str                            # "sweep", "grid", "random", "smart"
    modifications: dict[str, Any]            # Dot-path → new value
    scenario_config: ScenarioConfig          # The full modified scenario
    is_baseline: bool = False                # True for the user's original scenario
```

### 4.2 Exploration Result

```python
class VariantResult(BaseModel):
    """Result of running one variant."""

    model_config = ConfigDict(extra="forbid")

    variant_id: str
    variant_name: str
    adoption_rate: float
    adoption_count: int
    population_size: int
    rejection_distribution: dict[str, int]
    modifications: dict[str, Any]
    rank: int = 0                            # 1 = best


class ExplorationReport(BaseModel):
    """Consolidated results from running all variants."""

    model_config = ConfigDict(extra="forbid")

    base_scenario_id: str
    strategy: str
    total_variants: int
    execution_time_seconds: float

    # Rankings
    baseline_result: VariantResult
    best_result: VariantResult
    worst_result: VariantResult
    median_adoption_rate: float
    all_results: list[VariantResult]         # Sorted by adoption_rate desc

    # Analysis
    parameter_sensitivities: list[ParameterSensitivity]
    missed_insights: list[MissedInsight]
    recommended_configuration: dict[str, Any]


class ParameterSensitivity(BaseModel):
    """How much one parameter affects adoption rate."""

    model_config = ConfigDict(extra="forbid")

    parameter_path: str
    parameter_display_name: str
    min_value: float | str
    max_value: float | str
    adoption_rate_at_min: float
    adoption_rate_at_max: float
    sensitivity_score: float                 # |max_rate - min_rate|, higher = more sensitive


class MissedInsight(BaseModel):
    """An auto-discovered configuration that outperforms the user's scenario."""

    model_config = ConfigDict(extra="forbid")

    variant_id: str
    variant_name: str
    adoption_rate: float
    lift_over_baseline: float                # Absolute percentage points
    key_differences: list[str]               # Human-readable: "Price reduced from ₹599 to ₹399"
    explanation: str                         # "This variant achieves 67% adoption by..."
```

---

## 5. Batch Simulation Runner

```python
class BatchSimulationRunner:
    """Run multiple scenario variants against a population."""

    def __init__(
        self,
        population: Population,
        seed: int = DEFAULT_SEED,
    ) -> None:
        self.population = population
        self.seed = seed

    def run_batch(
        self,
        variants: list[ScenarioVariant],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[VariantResult]:
        """
        Run all variants sequentially (or with ProcessPoolExecutor for large N).

        For 300 personas × 100 variants = 30,000 funnel evaluations.
        At ~1ms per funnel call, total: ~30 seconds.
        For 1000 variants: ~5 minutes.
        """
        results = []
        for i, variant in enumerate(variants):
            sim_result = run_static_simulation(
                self.population,
                variant.scenario_config,
                seed=self.seed,
            )
            results.append(VariantResult(
                variant_id=variant.variant_id,
                variant_name=variant.variant_name,
                adoption_rate=sim_result.adoption_rate,
                adoption_count=sim_result.adoption_count,
                population_size=sim_result.population_size,
                rejection_distribution=sim_result.rejection_distribution,
                modifications=variant.modifications,
            ))
            if progress_callback:
                progress_callback(i + 1, len(variants))

        # Rank by adoption rate
        results.sort(key=lambda r: r.adoption_rate, reverse=True)
        for rank, result in enumerate(results, 1):
            result.rank = rank

        return results
```

### 5.1 Performance Estimates

| Variants | Personas | Funnel Calls | Est. Time |
|----------|----------|-------------|-----------|
| 30 (sweep) | 300 | 9,000 | ~10s |
| 100 (random) | 300 | 30,000 | ~30s |
| 500 | 300 | 150,000 | ~2.5 min |
| 1,000 | 300 | 300,000 | ~5 min |

No LLM calls. Pure numeric computation. Cost: $0.00.

---

## 6. Exploration Consolidator

```python
class ExplorationConsolidator:
    """Analyze batch results and produce actionable insights."""

    def consolidate(
        self,
        base_scenario: ScenarioConfig,
        baseline_result: VariantResult,
        all_results: list[VariantResult],
        execution_time: float,
        strategy: str,
    ) -> ExplorationReport:
        """
        Produce the consolidated report with:
        1. Rankings (best/worst/median)
        2. Parameter sensitivity analysis
        3. "You missed this" insights
        4. Recommended configuration
        """
```

### 6.1 Parameter Sensitivity Analysis

For sweep results, compute sensitivity per parameter:

```python
def _compute_sensitivities(
    self,
    all_results: list[VariantResult],
) -> list[ParameterSensitivity]:
    """
    Group results by which parameter was varied.
    For each parameter, find the adoption rate range.
    Sort by sensitivity (range width).
    """
    # Group by parameter path
    param_groups: dict[str, list[VariantResult]] = {}
    for result in all_results:
        for path in result.modifications:
            param_groups.setdefault(path, []).append(result)

    sensitivities = []
    for path, group in param_groups.items():
        rates = [r.adoption_rate for r in group]
        sensitivities.append(ParameterSensitivity(
            parameter_path=path,
            parameter_display_name=display_name(path.split(".")[-1]),
            min_value=min(r.modifications[path] for r in group),
            max_value=max(r.modifications[path] for r in group),
            adoption_rate_at_min=group[rates.index(min(rates))].adoption_rate,
            adoption_rate_at_max=group[rates.index(max(rates))].adoption_rate,
            sensitivity_score=max(rates) - min(rates),
        ))

    return sorted(sensitivities, key=lambda s: s.sensitivity_score, reverse=True)
```

### 6.2 Missed Insights Generator

```python
def _generate_missed_insights(
    self,
    baseline: VariantResult,
    all_results: list[VariantResult],
    base_scenario: ScenarioConfig,
) -> list[MissedInsight]:
    """
    Find variants that significantly outperform the baseline.
    For each, explain what's different and why it matters.
    """
    LIFT_THRESHOLD = 0.05  # Must beat baseline by >5 percentage points

    insights = []
    for result in all_results:
        if result.is_baseline:
            continue
        lift = result.adoption_rate - baseline.adoption_rate
        if lift < LIFT_THRESHOLD:
            continue

        # Build human-readable differences
        differences = []
        for path, new_val in result.modifications.items():
            field_name = display_name(path.split(".")[-1])
            old_val = _get_nested(base_scenario, path)
            if isinstance(new_val, float) and isinstance(old_val, float):
                if "price" in path:
                    differences.append(f"{field_name}: ₹{old_val:.0f} → ₹{new_val:.0f}")
                else:
                    differences.append(f"{field_name}: {old_val:.0%} → {new_val:.0%}")
            elif isinstance(new_val, bool):
                differences.append(f"{field_name}: {'enabled' if new_val else 'disabled'}")
            else:
                differences.append(f"{field_name}: {old_val} → {new_val}")

        explanation = (
            f"This variant achieves {result.adoption_rate:.0%} adoption "
            f"(+{lift:.0%} over your scenario) by "
            + " and ".join(differences[:3]) + "."
        )

        insights.append(MissedInsight(
            variant_id=result.variant_id,
            variant_name=result.variant_name,
            adoption_rate=result.adoption_rate,
            lift_over_baseline=lift,
            key_differences=differences,
            explanation=explanation,
        ))

    return sorted(insights, key=lambda i: i.lift_over_baseline, reverse=True)[:10]
```

### 6.3 Recommended Configuration

```python
def _recommend_configuration(
    self,
    best_result: VariantResult,
    sensitivities: list[ParameterSensitivity],
    base_scenario: ScenarioConfig,
) -> dict[str, Any]:
    """
    Build a recommended scenario configuration by:
    1. Starting from the best variant
    2. For each highly sensitive parameter, pick the value that maximizes adoption
    """
    recommended = dict(best_result.modifications)
    return recommended
```

---

## 7. UI Design

### 7.1 New Streamlit Page: Scenario Explorer

**File:** `app/pages/7_explorer.py` (NEW — or integrate into existing scenario page)

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│  Scenario Explorer                                      │
│  "Run hundreds of scenario variations to find the       │
│   optimal configuration for your population."           │
├─────────────────────────────────────────────────────────┤
│  Base Scenario: [nutrimix_2_6 ▼]                       │
│  Strategy: [Smart ▼] [Sweep] [Grid] [Random]           │
│  Variants to generate: [100 ─────●───── 1000]          │
│                                                         │
│  [🚀 Explore Variations]                                │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░  65% (65/100 variants)     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Your     │ │ Best     │ │ Worst    │ │ Median   │  │
│  │ Scenario │ │ Variant  │ │ Variant  │ │ Adoption │  │
│  │  42%     │ │  67%     │ │  12%     │ │  38%     │  │
│  │          │ │ +25% ▲   │ │ -30% ▼   │ │          │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                         │
│  ⚡ You Missed This                                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Variant #12 achieves 67% adoption (+25% over    │   │
│  │ your scenario) by reducing price from ₹599 to   │   │
│  │ ₹399 and enabling school partnerships.          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Parameter Sensitivity                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Price            ████████████████████  22%      │   │
│  │ Awareness Budget ███████████████       15%      │   │
│  │ Taste Appeal     ██████████            10%      │   │
│  │ School Partner   ████████              8%       │   │
│  │ Trust Signal     ██████                6%       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  All Variants (sorted by adoption rate)                 │
│  ┌──────┬────────────────┬──────────┬───────────┐      │
│  │ Rank │ Variant        │ Adoption │ Key Change│      │
│  ├──────┼────────────────┼──────────┼───────────┤      │
│  │ 1    │ Price ₹399     │ 67%      │ -₹200     │      │
│  │ 2    │ High Awareness │ 58%      │ +30% aw.  │      │
│  │ ...  │ ...            │ ...      │ ...       │      │
│  │ 100  │ Price ₹799     │ 12%      │ +₹200     │      │
│  └──────┴────────────────┴──────────┴───────────┘      │
│                                                         │
│  Adoption Distribution                                  │
│  [histogram of adoption rates across all variants]      │
│                                                         │
│  📥 Download Report (Sprint 11)                         │
└─────────────────────────────────────────────────────────┘
```

### 7.2 Sensitivity Chart

Horizontal bar chart showing parameter sensitivity scores:

```python
fig = px.bar(
    sensitivity_df,
    x="sensitivity_score",
    y="parameter_display_name",
    orientation="h",
    title="Which parameters move the needle most?",
    color="sensitivity_score",
    color_continuous_scale="RdYlGn",
)
```

### 7.3 Adoption Distribution Histogram

```python
fig = px.histogram(
    results_df,
    x="adoption_rate",
    nbins=30,
    title=f"Adoption rate distribution across {n} variants",
    color_discrete_sequence=[DASHBOARD_BRAND_COLORS["primary"]],
)
# Add vertical line for user's baseline
fig.add_vline(x=baseline_rate, line_dash="dash", annotation_text="Your scenario")
```

---

## 8. File Structure

```
src/
  simulation/
    explorer.py              # NEW — ScenarioVariantGenerator
    batch.py                 # NEW — BatchSimulationRunner
    consolidation.py         # NEW — ExplorationConsolidator, models

app/
  pages/
    7_explorer.py            # NEW — Scenario Explorer UI
```

---

## 9. Smart Variant Generation — Channel Mix Handling

Channel mix weights must sum to 1.0. When varying channel weights:

```python
def _normalize_channel_mix(channel_mix: dict[str, float]) -> dict[str, float]:
    """Ensure channel weights sum to 1.0 after perturbation."""
    total = sum(channel_mix.values())
    if total == 0:
        # Equal distribution
        n = len(channel_mix)
        return {k: 1.0 / n for k in channel_mix}
    return {k: v / total for k, v in channel_mix.items()}
```

For channel-focused variants, generate meaningful mixes:

```python
CHANNEL_PRESETS: dict[str, dict[str, float]] = {
    "instagram_heavy": {"instagram": 0.50, "youtube": 0.20, "whatsapp": 0.15, "pediatrician": 0.15},
    "whatsapp_organic": {"instagram": 0.15, "youtube": 0.15, "whatsapp": 0.50, "pediatrician": 0.20},
    "doctor_driven": {"instagram": 0.10, "youtube": 0.15, "whatsapp": 0.15, "pediatrician": 0.60},
    "youtube_education": {"instagram": 0.15, "youtube": 0.50, "whatsapp": 0.15, "pediatrician": 0.20},
    "balanced": {"instagram": 0.25, "youtube": 0.25, "whatsapp": 0.25, "pediatrician": 0.25},
}
```

---

## 10. Integration with Existing Counterfactual Engine

The auto-explorer builds on `run_counterfactual()` from `src/simulation/counterfactual.py`. Key reuse:

- `_apply_modifications()` — applies dot-path changes to ScenarioConfig
- `evaluate_scenario_adoption()` — runs simulation and returns adoption rate
- `_segment_impacts()` — identifies most-affected demographic segments

The explorer wraps these in a batch loop with variant generation on top.

---

## 11. Constants

```python
# Auto-Scenario Exploration (Sprint 10)
EXPLORER_DEFAULT_VARIANT_COUNT = 100
EXPLORER_MAX_VARIANT_COUNT = 2000
EXPLORER_SWEEP_STEPS = 6                  # Steps per parameter in sweep mode
EXPLORER_GRID_MAX_COMBINATIONS = 500      # Cap grid explosion
EXPLORER_MISSED_INSIGHT_LIFT_THRESHOLD = 0.05  # 5 percentage points
EXPLORER_MISSED_INSIGHT_MAX_DISPLAY = 10
EXPLORER_SENSITIVITY_MIN_SCORE = 0.02     # Don't show params with <2% sensitivity

# Price sweep range
EXPLORER_PRICE_RANGE = (199, 999)
EXPLORER_PRICE_STEP = 100
```

---

## 12. Test Plan

| Test File | What | Count |
|-----------|------|-------|
| `test_variant_generator.py` | Sweep generates correct count | 3 |
| `test_variant_generator.py` | Grid generates correct combinations | 3 |
| `test_variant_generator.py` | Random variants are valid ScenarioConfigs | 3 |
| `test_variant_generator.py` | Smart variants target rejection reasons | 4 |
| `test_variant_generator.py` | Channel mix normalized to 1.0 | 2 |
| `test_batch_runner.py` | Runs N variants and returns N results | 2 |
| `test_batch_runner.py` | Results sorted by adoption rate | 2 |
| `test_batch_runner.py` | Progress callback invoked | 1 |
| `test_consolidation.py` | Sensitivity scores computed correctly | 3 |
| `test_consolidation.py` | Missed insights have positive lift | 3 |
| `test_consolidation.py` | Recommended config is valid ScenarioConfig | 2 |
| `test_consolidation.py` | Report has all required fields | 2 |
| `test_explorer_integration.py` | Full pipeline: generate → run → consolidate | 2 |
| **Total** | | **~32** |

---

## 13. Sprint 10 Engineer Split

| Engineer | Track | Scope |
|----------|-------|-------|
| **Cursor** | A | `ScenarioVariantGenerator` — all 4 strategies + channel handling |
| **Codex** | B | `BatchSimulationRunner` + `ExplorationConsolidator` + models |
| **OpenCode** | C | `app/pages/7_explorer.py` — full UI page |
| **Antigravity** | D | ~32 tests across 4 files |
