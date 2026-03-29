# Cursor — Sprint 10 Track A: Scenario Variant Generator

**Branch:** `sprint-10-track-a-variant-generator`
**Base:** `main`

## Context

The Auto-Scenario Explorer lets users generate hundreds of scenario variations from a base scenario, run them all against the population, and discover which configurations perform best. This track builds the variant generation engine — the module that takes a `ScenarioConfig` and produces N modified variants using different strategies.

**Design doc:** `docs/designs/AUTO-SCENARIO-EXPLORATION.md`

## Deliverables

### 1. Create `src/simulation/explorer.py` (NEW)

#### 1.1 Data Models

```python
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field
from typing import Any
from src.decision.scenarios import ScenarioConfig

class VariantStrategy(StrEnum):
    SWEEP = "sweep"
    GRID = "grid"
    RANDOM = "random"
    SMART = "smart"

class ScenarioVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant_id: str
    variant_name: str
    strategy: str
    modifications: dict[str, Any]
    scenario_config: ScenarioConfig
    is_baseline: bool = False
```

#### 1.2 Parameter Space Definition

Define the tunable parameters and their ranges:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ParameterSpec:
    path: str              # Dot-notation path into ScenarioConfig
    display_name: str      # Human label
    min_val: float | bool
    max_val: float | bool
    step: float | None = None  # For sweep
    is_bool: bool = False

PARAMETER_SPACE: list[ParameterSpec] = [
    ParameterSpec("product.price_inr", "Price (₹)", 199, 999, step=100),
    ParameterSpec("product.taste_appeal", "Taste Appeal", 0.3, 0.95, step=0.1),
    ParameterSpec("product.effort_to_acquire", "Effort to Acquire", 0.1, 0.7, step=0.1),
    ParameterSpec("product.clean_label_score", "Clean Label Score", 0.4, 1.0, step=0.1),
    ParameterSpec("product.premium_positioning", "Premium Positioning", 0.2, 0.8, step=0.1),
    ParameterSpec("marketing.awareness_budget", "Awareness Budget", 0.15, 0.85, step=0.1),
    ParameterSpec("marketing.perceived_quality", "Perceived Quality", 0.3, 0.9, step=0.1),
    ParameterSpec("marketing.trust_signal", "Trust Signal", 0.2, 0.9, step=0.1),
    ParameterSpec("marketing.social_proof", "Social Proof", 0.1, 0.8, step=0.1),
    ParameterSpec("marketing.influencer_signal", "Influencer Signal", 0.1, 0.7, step=0.1),
    ParameterSpec("marketing.social_buzz", "Social Buzz", 0.1, 0.7, step=0.1),
    ParameterSpec("marketing.discount_available", "Discount Available", 0.0, 0.3, step=0.1),
    ParameterSpec("marketing.school_partnership", "School Partnership", False, True, is_bool=True),
    ParameterSpec("marketing.influencer_campaign", "Influencer Campaign", False, True, is_bool=True),
    ParameterSpec("marketing.pediatrician_endorsement", "Pediatrician Endorsement", False, True, is_bool=True),
]
```

#### 1.3 Core Helper: Apply Modifications

Reuse the approach from `src/simulation/counterfactual.py` to apply dot-path modifications:

```python
def _apply_modifications(
    base: ScenarioConfig,
    modifications: dict[str, Any],
) -> ScenarioConfig:
    """
    Create a modified copy of a ScenarioConfig.

    Uses model_copy(update=...) with nested path resolution.
    Dot-notation paths like "product.price_inr" are resolved into
    nested Pydantic model updates.
    """
```

**Important:** Read `src/simulation/counterfactual.py` to see how `_apply_nested_modification()` works (lines 58-92). Reuse that pattern — do NOT duplicate the logic. Either import it or factor it into a shared helper in a common location.

If the counterfactual module's helper is private (prefixed with `_`), create a shared version:

```python
# In src/simulation/explorer.py or a shared utils
def apply_scenario_modifications(
    base: ScenarioConfig,
    modifications: dict[str, Any],
) -> ScenarioConfig:
```

#### 1.4 Channel Mix Normalization

```python
def _normalize_channel_mix(channel_mix: dict[str, float]) -> dict[str, float]:
    """Ensure channel weights sum to 1.0 after perturbation."""
    total = sum(channel_mix.values())
    if total <= 0:
        n = len(channel_mix)
        return {k: 1.0 / n for k in channel_mix}
    return {k: v / total for k, v in channel_mix.items()}

CHANNEL_PRESETS: dict[str, dict[str, float]] = {
    "instagram_heavy": {"instagram": 0.50, "youtube": 0.20, "whatsapp": 0.15, "pediatrician": 0.15},
    "whatsapp_organic": {"instagram": 0.15, "youtube": 0.15, "whatsapp": 0.50, "pediatrician": 0.20},
    "doctor_driven": {"instagram": 0.10, "youtube": 0.15, "whatsapp": 0.15, "pediatrician": 0.60},
    "youtube_education": {"instagram": 0.15, "youtube": 0.50, "whatsapp": 0.15, "pediatrician": 0.20},
    "balanced": {"instagram": 0.25, "youtube": 0.25, "whatsapp": 0.25, "pediatrician": 0.25},
}
```

#### 1.5 Strategy 1: Sweep

```python
def generate_sweep_variants(
    base: ScenarioConfig,
    parameters: list[ParameterSpec] | None = None,
) -> list[ScenarioVariant]:
    """
    Vary one parameter at a time across its range while holding others at baseline.

    For each parameter:
    - Float params: Generate values from min to max at step intervals
    - Bool params: Generate True and False variants
    - Skip the value that matches the baseline (no duplicate of base)

    Also add channel mix presets as additional variants.

    Returns ~30-40 variants.
    """
```

Variant naming: `"Price ₹399"`, `"Awareness Budget 70%"`, `"School Partnership ON"`, `"Channel: WhatsApp Organic"`, etc.

#### 1.6 Strategy 2: Grid

```python
GRID_PARAMETERS: list[str] = [
    "product.price_inr",
    "marketing.awareness_budget",
    "product.taste_appeal",
]
GRID_VALUES: dict[str, list] = {
    "product.price_inr": [299, 499, 699, 899],
    "marketing.awareness_budget": [0.25, 0.45, 0.65, 0.85],
    "product.taste_appeal": [0.5, 0.7, 0.9],
}

def generate_grid_variants(
    base: ScenarioConfig,
    grid_params: dict[str, list] | None = None,
    max_combinations: int = 500,
) -> list[ScenarioVariant]:
    """
    Generate Cartesian product of parameter values.

    Default: 4 × 4 × 3 = 48 variants.
    Cap at max_combinations to prevent explosion.
    """
```

Use `itertools.product` for combinations. Variant naming: `"P₹299 / Aw25% / Ta50%"`.

#### 1.7 Strategy 3: Random (Latin Hypercube Sampling)

```python
def generate_random_variants(
    base: ScenarioConfig,
    n_variants: int = 100,
    seed: int = 42,
    parameters: list[ParameterSpec] | None = None,
) -> list[ScenarioVariant]:
    """
    Sample n_variants from the parameter space.

    Uses stratified random sampling (Latin Hypercube):
    - Divide each parameter's range into n_variants equal bins
    - Sample one value per bin per parameter
    - Shuffle assignments to decorrelate

    For bool parameters: sample True/False with 50% probability.
    """
```

Variant naming: `"Random #001"`, `"Random #002"`, etc.

#### 1.8 Strategy 4: Smart

```python
from src.simulation.static import StaticSimulationResult

REJECTION_REMEDIATIONS: dict[str, list[dict[str, Any]]] = {
    "awareness": [
        {"path": "marketing.awareness_budget", "delta": +0.15},
        {"path": "marketing.influencer_campaign", "value": True},
        {"path": "marketing.social_buzz", "delta": +0.20},
    ],
    "consideration": [
        {"path": "marketing.trust_signal", "delta": +0.15},
        {"path": "marketing.pediatrician_endorsement", "value": True},
        {"path": "marketing.school_partnership", "value": True},
        {"path": "marketing.perceived_quality", "delta": +0.15},
    ],
    "purchase": [
        {"path": "product.price_inr", "delta": -100},
        {"path": "marketing.discount_available", "delta": +0.15},
        {"path": "product.taste_appeal", "delta": +0.10},
        {"path": "product.effort_to_acquire", "delta": -0.10},
    ],
    "need_recognition": [
        {"path": "product.health_relevance", "delta": +0.15},
        {"path": "product.category_need_baseline", "delta": +0.10},
    ],
}

def generate_smart_variants(
    base: ScenarioConfig,
    base_result: StaticSimulationResult,
    n_variants: int = 20,
) -> list[ScenarioVariant]:
    """
    Generate variants that target the dominant rejection reasons.

    1. Analyze base_result.rejection_distribution
    2. Sort rejection stages by count (descending)
    3. For each top rejection stage, apply its remediations
    4. Generate single-remediation AND combination variants
    5. Also generate "kitchen sink" variant (all remediations at once)
    """
```

For delta-based modifications: read the current value from the base scenario and add the delta, clamping to valid range [0.0, 1.0] for floats or [min_price, max_price] for price.

Variant naming: `"Fix Awareness: +Budget"`, `"Fix Purchase: -Price"`, `"Fix All: Kitchen Sink"`, etc.

#### 1.9 Master Generator

```python
def generate_variants(
    base: ScenarioConfig,
    strategy: VariantStrategy,
    n_variants: int = 100,
    base_result: StaticSimulationResult | None = None,
    seed: int = 42,
) -> list[ScenarioVariant]:
    """
    Generate scenario variants using the specified strategy.

    Always includes the baseline scenario as variant_id="baseline".
    """
    # Always include baseline
    baseline = ScenarioVariant(
        variant_id="baseline",
        variant_name="Your Scenario (baseline)",
        strategy=strategy.value,
        modifications={},
        scenario_config=base,
        is_baseline=True,
    )

    if strategy == VariantStrategy.SWEEP:
        variants = generate_sweep_variants(base)
    elif strategy == VariantStrategy.GRID:
        variants = generate_grid_variants(base)
    elif strategy == VariantStrategy.RANDOM:
        variants = generate_random_variants(base, n_variants, seed)
    elif strategy == VariantStrategy.SMART:
        if base_result is None:
            raise ValueError("Smart strategy requires base_result")
        variants = generate_smart_variants(base, base_result)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    return [baseline] + variants
```

## Files to Read Before Starting

1. `src/decision/scenarios.py` — **full file** (381 lines) — ScenarioConfig, ProductConfig, MarketingConfig models
2. `src/simulation/counterfactual.py` — **lines 58-92** — `_apply_nested_modification()` for dot-path updates
3. `src/simulation/static.py` — `StaticSimulationResult` model
4. `src/constants.py` — scenario IDs, decision thresholds
5. `docs/designs/AUTO-SCENARIO-EXPLORATION.md` — full design doc

## Constraints

- Python 3.11+, Pydantic v2 with `ConfigDict(extra="forbid")`
- All generated ScenarioConfigs must be valid (pass Pydantic validation)
- Channel mix must always sum to ~1.0 (normalize after modification)
- Price must stay within [199, 999] range
- UnitInterval attributes must stay within [0.0, 1.0]
- No new pip dependencies
- Variant IDs: `"baseline"`, `"sweep_001"`, `"grid_001"`, `"random_001"`, `"smart_001"`, etc.

## Acceptance Criteria

- [ ] `ScenarioVariant` and `VariantStrategy` models defined
- [ ] `PARAMETER_SPACE` covers all tunable parameters
- [ ] Sweep generates ~30-40 variants (one param at a time + channel presets)
- [ ] Grid generates Cartesian product capped at max_combinations
- [ ] Random uses stratified sampling with deterministic seed
- [ ] Smart analyzes rejection distribution and generates targeted fixes
- [ ] Channel mix normalized to 1.0 in all variants
- [ ] All generated ScenarioConfigs pass Pydantic validation
- [ ] `generate_variants()` always includes baseline as first variant
- [ ] Variant names are human-readable
