# Sprint 13 Brief — Codex (GPT 5.3 Medium)
## Business-Meaningful Auto-Variant Generator

### Context
The current explorer generates parameter variants using mathematical strategies (sweep, grid, random, smart). For Option C, we need variants that map to **business-meaningful actions** — each with a plain-English rationale a product manager can understand. This module replaces the silent "100 alternatives" concept with actionable what-if scenarios.

### Task: Build `src/simulation/auto_variants.py`
**New file.** The existing `src/simulation/explorer.py` stays untouched — we build alongside it and the ResearchRunner can switch to this module later.

#### Models

```python
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from src.decision.scenarios import ScenarioConfig

class BusinessVariant(BaseModel):
    """A scenario variant with business-meaningful rationale."""
    model_config = ConfigDict(extra="forbid")

    variant_id: str
    variant_name: str           # e.g. "Price Reduction (-15%)"
    category: str               # e.g. "pricing", "trust", "awareness", "product", "channel"
    business_rationale: str     # Plain English: "What if we dropped price by 15% to ₹509?"
    parameter_changes: dict[str, object]  # Nested path → value changes
    scenario_config: ScenarioConfig       # The full modified scenario
    is_baseline: bool = False

class VariantBatch(BaseModel):
    """Collection of business variants with metadata."""
    model_config = ConfigDict(extra="forbid")

    variants: list[BusinessVariant]
    base_scenario_id: str
    generation_seed: int
```

#### Generator Function

```python
def generate_business_variants(
    base: ScenarioConfig,
    *,
    seed: int = 42,
    max_variants: int = 50,
) -> VariantBatch:
    """Generate business-meaningful scenario variants.

    Each variant represents a concrete action a product/marketing team could take.
    Variants are organized into categories.
    """
```

#### Variant Categories and Templates

Generate variants across these 5 categories. Each category should produce 8-12 variants for a total of ~50.

**1. Pricing (8-10 variants)**
- Price reductions: -5%, -10%, -15%, -20%, -25%
- Price increases: +10%, +20% (test premium positioning)
- Discount promotions: discount_available = 0.10, 0.15, 0.20
- Example rationale: "What if we reduced NutriMix price by 15% to ₹509? Tests whether price is the primary barrier for budget-conscious families."

**2. Trust & Endorsements (8-10 variants)**
- Toggle pediatrician_endorsement on/off
- Toggle school_partnership on/off
- Toggle sports_club_partnership on/off
- Increase expert_endorsement to 0.7, 0.8, 0.9
- Increase trust_signal to 0.7, 0.8, 0.9
- Increase social_proof to 0.6, 0.7, 0.8
- Example rationale: "What if we secured pediatrician endorsement? Tests whether medical authority is the missing trust signal for health-anxious parents."

**3. Awareness & Reach (8-10 variants)**
- Awareness budget: 0.4, 0.6, 0.8 (from whatever base is)
- Awareness level: 0.5, 0.7, 0.9
- Social buzz: 0.4, 0.6, 0.8
- Influencer campaign toggle
- Channel mix shifts: heavy Instagram (0.6/0.2/0.2), heavy YouTube (0.2/0.6/0.2), heavy WhatsApp (0.2/0.2/0.6)
- Example rationale: "What if we doubled awareness budget to 0.60? Tests whether low awareness rather than product-market fit is limiting response rates."

**4. Product Attributes (8-10 variants)**
- Taste appeal: 0.7, 0.8, 0.9
- Effort to acquire: 0.1, 0.2 (easier)
- Clean label score: 0.9, 0.95
- Health relevance: 0.7, 0.8, 0.9
- Example rationale: "What if we improved taste appeal to 0.85? Tests whether child acceptance is the primary usage barrier."

**5. Combined Moves (6-8 variants)**
- "Full push": high awareness + pediatrician endorsement + discount
- "Premium play": higher price + max trust + expert endorsement
- "Value play": lower price + higher awareness + discount
- "Community play": WhatsApp-heavy + high social proof + influencer
- "Medical authority": pediatrician + expert endorsement + trust signal
- "Low barrier entry": lower price + lower effort + discount + taste
- Example rationale: "Full marketing push: what if we simultaneously increased awareness to 0.8, added pediatrician endorsement, and offered a 10% discount? Tests the combined ceiling for this scenario."

#### Implementation Details

1. **Always include baseline** as the first variant (`is_baseline=True`, no changes).

2. **Apply modifications** to the base scenario using `copy.deepcopy()`:
   ```python
   import copy
   variant_scenario = copy.deepcopy(base)
   variant_scenario.product.price_inr = new_price
   # etc.
   ```

3. **Validate channel mix** sums to 1.0 after modification. If a channel mix variant doesn't sum to 1.0, skip it.

4. **Variant IDs**: Use format `{category}_{index}`, e.g. `pricing_01`, `trust_03`, `combined_05`.

5. **Deterministic**: Same base + seed = same variants. Use seed only for any randomized elements (there shouldn't be many — most variants are template-driven).

6. **Respect max_variants**: If templates generate > max_variants, prioritize: 1 baseline + proportional from each category.

7. **Business rationale** must be specific to the base scenario. Use `base.product.name` and `base.product.price_inr` in the text. E.g. "What if we reduced **NutriMix** price by 15% to **₹509**?" not "What if we reduced price by 15%?"

### Deliverables
1. `src/simulation/auto_variants.py` — BusinessVariant, VariantBatch models + `generate_business_variants()` function
2. File must be importable without errors
3. Quick self-test: `generate_business_variants(get_scenario("nutrimix_2_6"))` returns a VariantBatch with ~50 variants across 5 categories

### Do NOT
- Modify existing files (additive only)
- Delete or modify `src/simulation/explorer.py`
- Create Streamlit pages
- Add dependencies
