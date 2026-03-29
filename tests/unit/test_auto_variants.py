"""Unit tests for business-meaningful auto-variant generation (Sprint 13)."""

from __future__ import annotations

import pytest
import math
from src.decision.scenarios import get_scenario
from src.simulation.auto_variants import generate_business_variants

@pytest.fixture(params=["nutrimix_2_6", "nutrimix_7_14", "magnesium_gummies", "protein_mix"])
def scenario(request):
    """Fixture to iterate through all 4 key scenarios."""
    return get_scenario(request.param)

def test_variant_count(scenario) -> None:
    """Default call produces between 40 and 55 variants (including baseline)."""
    batch = generate_business_variants(scenario)
    assert 40 <= len(batch.variants) <= 55

def test_baseline_included(scenario) -> None:
    """First variant has is_baseline=True and empty parameter_changes."""
    batch = generate_business_variants(scenario)
    baseline = batch.variants[0]
    assert baseline.is_baseline is True
    assert baseline.parameter_changes == {}
    assert "baseline" in baseline.variant_id

def test_all_categories_present(scenario) -> None:
    """Variants span all 5 categories: pricing, trust, awareness, product, combined."""
    batch = generate_business_variants(scenario)
    categories = {v.category for v in batch.variants}
    expected = {"baseline", "pricing", "trust", "awareness", "product", "combined"}
    assert expected.issubset(categories)

def test_no_duplicate_variant_ids(scenario) -> None:
    """All variant IDs are unique."""
    batch = generate_business_variants(scenario)
    ids = [v.variant_id for v in batch.variants]
    assert len(ids) == len(set(ids))

def test_channel_mix_valid(scenario) -> None:
    """For every variant, sum(channel_mix) is between 0.99 and 1.01."""
    batch = generate_business_variants(scenario)
    for v in batch.variants:
        mix = v.scenario_config.marketing.channel_mix
        if mix:
            total = sum(float(w) for w in mix.values())
            assert math.isclose(total, 1.0, abs_tol=1e-3)

def test_business_rationale_non_empty(scenario) -> None:
    """Every variant has a non-empty business_rationale string."""
    batch = generate_business_variants(scenario)
    for v in batch.variants:
        assert len(v.business_rationale) > 10

def test_business_rationale_mentions_product(scenario) -> None:
    """For pricing variants, the business_rationale mentions the product name."""
    batch = generate_business_variants(scenario)
    product_name = scenario.product.name
    pricing_variants = [v for v in batch.variants if v.category == "pricing"]
    for v in pricing_variants:
        assert product_name.lower() in v.business_rationale.lower()

def test_deterministic(scenario) -> None:
    """Same base scenario + seed produces identical variant IDs."""
    batch1 = generate_business_variants(scenario, seed=42)
    batch2 = generate_business_variants(scenario, seed=42)
    ids1 = [v.variant_id for v in batch1.variants]
    ids2 = [v.variant_id for v in batch2.variants]
    assert ids1 == ids2

def test_max_variants_respected(scenario) -> None:
    """generate_business_variants(base, max_variants=20) returns at most 20 variants."""
    batch = generate_business_variants(scenario, max_variants=20)
    assert len(batch.variants) <= 20

def test_all_scenarios() -> None:
    """Run generator for each of the 4 scenarios. All produce valid VariantBatch objects."""
    scenarios = ["nutrimix_2_6", "nutrimix_7_14", "magnesium_gummies", "protein_mix"]
    for sid in scenarios:
        s = get_scenario(sid)
        batch = generate_business_variants(s)
        assert batch.base_scenario_id == sid
        assert len(batch.variants) > 0
