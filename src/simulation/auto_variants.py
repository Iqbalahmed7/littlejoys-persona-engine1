"""Business-meaningful auto-variant generator for scenario exploration."""

from __future__ import annotations

import copy
import math
import random
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from src.decision.scenarios import ScenarioConfig


class BusinessVariant(BaseModel):
    """A scenario variant with business-meaningful rationale."""

    model_config = ConfigDict(extra="forbid")

    variant_id: str
    variant_name: str
    category: str
    business_rationale: str
    parameter_changes: dict[str, object]
    scenario_config: ScenarioConfig
    is_baseline: bool = False


class VariantBatch(BaseModel):
    """Collection of business variants with metadata."""

    model_config = ConfigDict(extra="forbid")

    variants: list[BusinessVariant]
    base_scenario_id: str
    generation_seed: int


def _rebuild_models() -> None:
    from src.decision.scenarios import ScenarioConfig as _ScenarioConfig

    BusinessVariant.model_rebuild(_types_namespace={"ScenarioConfig": _ScenarioConfig})


_rebuild_models()


def _set_nested_attr(obj: Any, path: str, value: object) -> None:
    parts = path.split(".")
    current = obj
    for part in parts[:-1]:
        current = current[part] if isinstance(current, dict) else getattr(current, part)

    leaf = parts[-1]
    if isinstance(current, dict):
        current[leaf] = value
    else:
        setattr(current, leaf, value)


def _apply_changes(base: ScenarioConfig, changes: dict[str, object]) -> ScenarioConfig | None:
    variant = copy.deepcopy(base)
    for path, value in changes.items():
        try:
            _set_nested_attr(variant, path, value)
        except (AttributeError, KeyError):
            return None

    if "marketing.channel_mix" in changes:
        channel_mix = dict(variant.marketing.channel_mix)
        total = sum(float(v) for v in channel_mix.values())
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            return None

    return variant


def _candidate(
    *,
    base: ScenarioConfig,
    category: str,
    variant_name: str,
    rationale: str,
    changes: dict[str, object],
) -> BusinessVariant | None:
    scenario_config = _apply_changes(base, changes)
    if scenario_config is None:
        return None
    return BusinessVariant(
        variant_id=f"{category}_00",
        variant_name=variant_name,
        category=category,
        business_rationale=rationale,
        parameter_changes=changes,
        scenario_config=scenario_config,
        is_baseline=False,
    )


def _pricing_variants(base: ScenarioConfig) -> list[BusinessVariant]:
    name = base.product.name
    base_price = float(base.product.price_inr)
    items: list[BusinessVariant] = []

    for pct in (5, 10, 15, 20, 25):
        new_price = round(base_price * (1 - pct / 100))
        item = _candidate(
            base=base,
            category="pricing",
            variant_name=f"Price Reduction (-{pct}%)",
            rationale=(
                f"What if we reduced {name} price by {pct}% to ₹{new_price:.0f}? "
                "Tests whether price is the primary barrier for budget-conscious families."
            ),
            changes={"product.price_inr": float(new_price)},
        )
        if item:
            items.append(item)

    for pct in (10, 20):
        new_price = round(base_price * (1 + pct / 100))
        item = _candidate(
            base=base,
            category="pricing",
            variant_name=f"Price Increase (+{pct}%)",
            rationale=(
                f"What if we increased {name} price by {pct}% to ₹{new_price:.0f}? "
                "Tests whether premium positioning improves trust without collapsing adoption."
            ),
            changes={"product.price_inr": float(new_price)},
        )
        if item:
            items.append(item)

    for discount in (0.10, 0.15, 0.20):
        item = _candidate(
            base=base,
            category="pricing",
            variant_name=f"Promo Discount ({discount:.0%})",
            rationale=(
                f"What if we offered a {discount:.0%} promotional discount on {name}? "
                "Tests whether temporary value unlocks trial and conversion."
            ),
            changes={"marketing.discount_available": discount},
        )
        if item:
            items.append(item)
    return items


def _trust_variants(base: ScenarioConfig) -> list[BusinessVariant]:
    name = base.product.name
    items: list[BusinessVariant] = []

    toggles = [
        ("marketing.pediatrician_endorsement", "Pediatrician Endorsement"),
        ("marketing.school_partnership", "School Partnership"),
        ("marketing.sports_club_partnership", "Sports Club Partnership"),
    ]
    for path, label in toggles:
        for state in (True, False):
            action = "enabled" if state else "disabled"
            item = _candidate(
                base=base,
                category="trust",
                variant_name=f"{label} ({action.title()})",
                rationale=(
                    f"What if we {action} {label.lower()} for {name}? "
                    "Tests whether authority-led trust signals are the missing conversion trigger."
                ),
                changes={path: state},
            )
            if item:
                items.append(item)

    for val in (0.7, 0.8, 0.9):
        for path, label in (
            ("marketing.expert_endorsement", "Expert Endorsement"),
            ("marketing.trust_signal", "Trust Signal"),
            ("marketing.social_proof", "Social Proof"),
        ):
            item = _candidate(
                base=base,
                category="trust",
                variant_name=f"{label} ({val:.0%})",
                rationale=(
                    f"What if we strengthened {label.lower()} to {val:.0%} for {name}? "
                    "Tests whether stronger credibility cues reduce hesitation."
                ),
                changes={path: val},
            )
            if item:
                items.append(item)
    return items


def _awareness_variants(base: ScenarioConfig) -> list[BusinessVariant]:
    name = base.product.name
    items: list[BusinessVariant] = []
    base_awareness_budget = float(base.marketing.awareness_budget)

    for budget in (0.4, 0.6, 0.8):
        item = _candidate(
            base=base,
            category="awareness",
            variant_name=f"Awareness Budget ({budget:.0%})",
            rationale=(
                f"What if we moved {name} awareness budget from {base_awareness_budget:.0%} to {budget:.0%}? "
                "Tests whether low awareness is limiting response rates."
            ),
            changes={"marketing.awareness_budget": budget},
        )
        if item:
            items.append(item)

    for level in (0.5, 0.7, 0.9):
        item = _candidate(
            base=base,
            category="awareness",
            variant_name=f"Awareness Level ({level:.0%})",
            rationale=(
                f"What if campaign intensity raised awareness level to {level:.0%} for {name}? "
                "Tests top-of-funnel reach constraints."
            ),
            changes={"marketing.awareness_level": level},
        )
        if item:
            items.append(item)

    for buzz in (0.4, 0.6, 0.8):
        item = _candidate(
            base=base,
            category="awareness",
            variant_name=f"Social Buzz ({buzz:.0%})",
            rationale=(
                f"What if we increased social buzz for {name} to {buzz:.0%}? "
                "Tests whether peer conversation unlocks discovery and trial."
            ),
            changes={"marketing.social_buzz": buzz},
        )
        if item:
            items.append(item)

    for state in (True, False):
        action = "On" if state else "Off"
        item = _candidate(
            base=base,
            category="awareness",
            variant_name=f"Influencer Campaign ({action})",
            rationale=(
                f"What if we turned influencer campaigns {action.lower()} for {name}? "
                "Tests whether creator-led reach materially changes consideration."
            ),
            changes={"marketing.influencer_campaign": state},
        )
        if item:
            items.append(item)

    channel_templates = [
        (
            "Instagram-Heavy Channel Mix",
            {"instagram": 0.6, "youtube": 0.2, "whatsapp": 0.2},
            "heavy Instagram discovery",
        ),
        (
            "YouTube-Heavy Channel Mix",
            {"instagram": 0.2, "youtube": 0.6, "whatsapp": 0.2},
            "long-form YouTube education",
        ),
        (
            "WhatsApp-Heavy Channel Mix",
            {"instagram": 0.2, "youtube": 0.2, "whatsapp": 0.6},
            "community-led WhatsApp spread",
        ),
    ]
    for label, mix, phrase in channel_templates:
        item = _candidate(
            base=base,
            category="awareness",
            variant_name=label,
            rationale=(
                f"What if {name} relied on {phrase}? "
                "Tests whether channel emphasis changes reachable parent segments."
            ),
            changes={"marketing.channel_mix": mix},
        )
        if item:
            items.append(item)
    return items


def _product_variants(base: ScenarioConfig) -> list[BusinessVariant]:
    name = base.product.name
    items: list[BusinessVariant] = []

    for val in (0.7, 0.8, 0.9):
        item = _candidate(
            base=base,
            category="product",
            variant_name=f"Taste Appeal ({val:.0%})",
            rationale=(
                f"What if we improved taste appeal of {name} to {val:.0%}? "
                "Tests whether child acceptance is the primary usage barrier."
            ),
            changes={"product.taste_appeal": val},
        )
        if item:
            items.append(item)

    for val in (0.1, 0.2):
        item = _candidate(
            base=base,
            category="product",
            variant_name=f"Lower Effort to Acquire ({val:.1f})",
            rationale=(
                f"What if we lowered effort-to-acquire for {name} to {val:.1f}? "
                "Tests whether convenience friction is suppressing purchases."
            ),
            changes={"product.effort_to_acquire": val},
        )
        if item:
            items.append(item)

    for val in (0.9, 0.95):
        item = _candidate(
            base=base,
            category="product",
            variant_name=f"Clean Label Score ({val:.0%})",
            rationale=(
                f"What if we improved {name} clean-label score to {val:.0%}? "
                "Tests whether ingredient transparency drives trust conversion."
            ),
            changes={"product.clean_label_score": val},
        )
        if item:
            items.append(item)

    for val in (0.7, 0.8, 0.9):
        item = _candidate(
            base=base,
            category="product",
            variant_name=f"Health Relevance ({val:.0%})",
            rationale=(
                f"What if we repositioned {name} health relevance to {val:.0%}? "
                "Tests whether clearer need-fit improves adoption intent."
            ),
            changes={"product.health_relevance": val},
        )
        if item:
            items.append(item)
    return items


def _combined_variants(base: ScenarioConfig) -> list[BusinessVariant]:
    name = base.product.name
    base_price = float(base.product.price_inr)
    items: list[BusinessVariant] = []

    templates: list[tuple[str, str, dict[str, object]]] = [
        (
            "Full Push",
            (
                f"Full marketing push for {name}: increased awareness, medical endorsement, and a discount. "
                "Tests the practical ceiling of coordinated demand stimulation."
            ),
            {
                "marketing.awareness_budget": 0.8,
                "marketing.pediatrician_endorsement": True,
                "marketing.discount_available": 0.1,
            },
        ),
        (
            "Premium Play",
            (
                f"Premium play for {name}: higher price with stronger trust and expert endorsement. "
                "Tests premium narrative viability versus price sensitivity."
            ),
            {
                "product.price_inr": round(base_price * 1.2),
                "marketing.trust_signal": 0.9,
                "marketing.expert_endorsement": 0.9,
            },
        ),
        (
            "Value Play",
            (
                f"Value play for {name}: lower price, higher awareness, and discount support. "
                "Tests whether affordability plus visibility drives broad-based lift."
            ),
            {
                "product.price_inr": round(base_price * 0.85),
                "marketing.awareness_budget": 0.7,
                "marketing.discount_available": 0.15,
            },
        ),
        (
            "Community Play",
            (
                f"Community play for {name}: WhatsApp-heavy channel mix with stronger social proof and influencer support. "
                "Tests social validation as the core growth engine."
            ),
            {
                "marketing.channel_mix": {"instagram": 0.2, "youtube": 0.2, "whatsapp": 0.6},
                "marketing.social_proof": 0.8,
                "marketing.influencer_campaign": True,
            },
        ),
        (
            "Medical Authority",
            (
                f"Medical authority play for {name}: pediatrician endorsement plus expert and trust signals. "
                "Tests whether clinical confidence resolves hesitation."
            ),
            {
                "marketing.pediatrician_endorsement": True,
                "marketing.expert_endorsement": 0.85,
                "marketing.trust_signal": 0.85,
            },
        ),
        (
            "Low Barrier Entry",
            (
                f"Low barrier entry for {name}: lower price, easier access, promo discount, and better taste. "
                "Tests whether reducing friction unlocks trial at scale."
            ),
            {
                "product.price_inr": round(base_price * 0.8),
                "product.effort_to_acquire": 0.1,
                "marketing.discount_available": 0.1,
                "product.taste_appeal": 0.9,
            },
        ),
        (
            "Trust + Reach Bundle",
            (
                f"Trust plus reach for {name}: school partnership, stronger social proof, and higher awareness. "
                "Tests whether coordinated trust and top-of-funnel improvements compound."
            ),
            {
                "marketing.school_partnership": True,
                "marketing.social_proof": 0.75,
                "marketing.awareness_budget": 0.75,
            },
        ),
    ]

    for variant_name, rationale, changes in templates:
        item = _candidate(
            base=base,
            category="combined",
            variant_name=variant_name,
            rationale=rationale,
            changes=changes,
        )
        if item:
            items.append(item)
    return items


def _assign_ids(variants_by_category: dict[str, list[BusinessVariant]]) -> dict[str, list[BusinessVariant]]:
    out: dict[str, list[BusinessVariant]] = {}
    for category, variants in variants_by_category.items():
        with_ids: list[BusinessVariant] = []
        for idx, variant in enumerate(variants, start=1):
            with_ids.append(variant.model_copy(update={"variant_id": f"{category}_{idx:02d}"}))
        out[category] = with_ids
    return out


def _select_proportional(
    by_category: dict[str, list[BusinessVariant]],
    *,
    max_take: int,
) -> list[BusinessVariant]:
    categories = [key for key in ("pricing", "trust", "awareness", "product", "combined") if by_category.get(key)]
    if max_take <= 0 or not categories:
        return []

    available_total = sum(len(by_category[key]) for key in categories)
    if available_total <= max_take:
        picked: list[BusinessVariant] = []
        for key in categories:
            picked.extend(by_category[key])
        return picked

    raw_targets: dict[str, float] = {
        key: (len(by_category[key]) / available_total) * max_take for key in categories
    }
    quotas: dict[str, int] = {
        key: min(len(by_category[key]), math.floor(raw_targets[key])) for key in categories
    }
    used = sum(quotas.values())

    # Ensure each populated category gets at least one slot when possible.
    if max_take >= len(categories):
        for key in categories:
            if quotas[key] == 0:
                quotas[key] = 1
        used = sum(quotas.values())

    # Rebalance down if min-allocation overshot.
    while used > max_take:
        for key in reversed(categories):
            if used <= max_take:
                break
            if quotas[key] > 1:
                quotas[key] -= 1
                used -= 1

    # Distribute remaining slots by fractional target, then by category order.
    if used < max_take:
        fractions = sorted(
            ((key, raw_targets[key] - math.floor(raw_targets[key])) for key in categories),
            key=lambda item: item[1],
            reverse=True,
        )
        idx = 0
        while used < max_take and fractions:
            key = fractions[idx % len(fractions)][0]
            if quotas[key] < len(by_category[key]):
                quotas[key] += 1
                used += 1
            idx += 1
            if idx > max_take * 10:
                break

    picked: list[BusinessVariant] = []
    for key in categories:
        picked.extend(by_category[key][: quotas[key]])
    return picked[:max_take]


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

    random.seed(seed)

    baseline = BusinessVariant(
        variant_id="baseline_00",
        variant_name="Your Scenario (baseline)",
        category="baseline",
        business_rationale=f"Current {base.product.name} configuration used as the comparison point.",
        parameter_changes={},
        scenario_config=copy.deepcopy(base),
        is_baseline=True,
    )

    variants_by_category = {
        "pricing": _pricing_variants(base),
        "trust": _trust_variants(base),
        "awareness": _awareness_variants(base),
        "product": _product_variants(base),
        "combined": _combined_variants(base),
    }
    variants_by_category = _assign_ids(variants_by_category)

    remaining = max(0, max_variants - 1)
    selected = _select_proportional(variants_by_category, max_take=remaining)

    return VariantBatch(
        variants=[baseline, *selected],
        base_scenario_id=base.id,
        generation_seed=seed,
    )
