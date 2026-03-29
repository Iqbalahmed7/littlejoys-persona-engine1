"""
Scenario variant generator for Auto-Scenario Exploration (Sprint 10).

Produces modified ScenarioConfig instances from a base scenario using sweep, grid,
random (LHS-style), or smart (rejection-driven) strategies.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum
from itertools import islice, product
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.decision.scenarios import ScenarioConfig  # noqa: TC001
from src.simulation.counterfactual import apply_scenario_modifications
from src.simulation.static import StaticSimulationResult  # noqa: TC001


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


@dataclass(frozen=True)
class ParameterSpec:
    path: str
    display_name: str
    min_val: float | bool
    max_val: float | bool
    step: float | None = None
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

GRID_PARAMETERS: list[str] = [
    "product.price_inr",
    "marketing.awareness_budget",
    "product.taste_appeal",
]

GRID_VALUES: dict[str, list[Any]] = {
    "product.price_inr": [299, 499, 699, 899],
    "marketing.awareness_budget": [0.25, 0.45, 0.65, 0.85],
    "product.taste_appeal": [0.5, 0.7, 0.9],
}

CHANNEL_PRESETS: dict[str, dict[str, float]] = {
    "instagram_heavy": {"instagram": 0.50, "youtube": 0.20, "whatsapp": 0.15, "pediatrician": 0.15},
    "whatsapp_organic": {"instagram": 0.15, "youtube": 0.15, "whatsapp": 0.50, "pediatrician": 0.20},
    "doctor_driven": {"instagram": 0.10, "youtube": 0.15, "whatsapp": 0.15, "pediatrician": 0.60},
    "youtube_education": {"instagram": 0.15, "youtube": 0.50, "whatsapp": 0.15, "pediatrician": 0.20},
    "balanced": {"instagram": 0.25, "youtube": 0.25, "whatsapp": 0.25, "pediatrician": 0.25},
}

CHANNEL_PRESET_LABELS: dict[str, str] = {
    "instagram_heavy": "Channel: Instagram Heavy",
    "whatsapp_organic": "Channel: WhatsApp Organic",
    "doctor_driven": "Channel: Doctor Driven",
    "youtube_education": "Channel: YouTube Education",
    "balanced": "Channel: Balanced Mix",
}

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

_REMEDIATION_SHORT: dict[str, str] = {
    "marketing.awareness_budget": "+Budget",
    "marketing.influencer_campaign": "Influencer ON",
    "marketing.social_buzz": "+Social Buzz",
    "marketing.trust_signal": "+Trust Signal",
    "marketing.pediatrician_endorsement": "Pediatrician ON",
    "marketing.school_partnership": "School ON",
    "marketing.perceived_quality": "+Quality",
    "product.price_inr": "-Price",
    "marketing.discount_available": "+Discount",
    "product.taste_appeal": "+Taste",
    "product.effort_to_acquire": "-Effort",
    "product.health_relevance": "+Health Fit",
    "product.category_need_baseline": "+Category Need",
}

PRICE_MIN = 199.0
PRICE_MAX = 999.0


def _normalize_channel_mix(channel_mix: dict[str, float]) -> dict[str, float]:
    if not channel_mix:
        return {}
    total = sum(channel_mix.values())
    if total <= 0:
        n = len(channel_mix)
        return {k: 1.0 / n for k in channel_mix}
    return {k: v / total for k, v in channel_mix.items()}


def _get_path_value(obj: object, path: str) -> Any:
    cur: object = obj
    for part in path.split("."):
        cur = getattr(cur, part)
    return cur


def _clamp_unit(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _clamp_price(x: float) -> float:
    return max(PRICE_MIN, min(PRICE_MAX, float(x)))


def _finalize_scenario(base: ScenarioConfig, modifications: dict[str, Any]) -> ScenarioConfig:
    """Apply modifications and renormalize marketing channel_mix to sum to 1."""

    s = apply_scenario_modifications(base, modifications)
    mix = dict(s.marketing.channel_mix)
    nmix = _normalize_channel_mix(mix)
    if mix != nmix:
        s = apply_scenario_modifications(s, {"marketing.channel_mix": nmix})
    return s


def _float_linear_values(spec: ParameterSpec) -> list[float]:
    mn = float(spec.min_val)
    mx = float(spec.max_val)
    st = float(spec.step) if spec.step is not None else 0.0
    if st <= 0:
        return []
    out: list[float] = []
    x = mn
    guard = 0
    while x <= mx + 1e-9 and guard < 10_000:
        out.append(round(x, 6))
        x += st
        guard += 1
    return out


def _values_close(a: float, b: float, tol: float = 1e-5) -> bool:
    return abs(float(a) - float(b)) <= tol


def _sweep_variant_name(spec: ParameterSpec, value: Any) -> str:
    if spec.is_bool:
        return f"{spec.display_name} {'ON' if value else 'OFF'}"
    if spec.path.endswith("price_inr"):
        return f"Price ₹{int(value)}"
    if spec.path.startswith("marketing.") and float(spec.max_val) <= 1.01:
        return f"{spec.display_name} {round(float(value) * 100)}%"
    if spec.path.startswith("product.") and float(spec.max_val) <= 1.01:
        return f"{spec.display_name} {round(float(value) * 100)}%"
    return f"{spec.display_name} {value}"


def _channel_preset_equals_base(base: ScenarioConfig, preset: dict[str, float]) -> bool:
    base_mix = _normalize_channel_mix(dict(base.marketing.channel_mix))
    preset_n = _normalize_channel_mix(dict(preset))
    if set(base_mix.keys()) != set(preset_n.keys()):
        return False
    return all(_values_close(base_mix[k], preset_n[k], 1e-4) for k in base_mix)


def generate_sweep_variants(
    base: ScenarioConfig,
    parameters: list[ParameterSpec] | None = None,
) -> list[ScenarioVariant]:
    """
    Vary one parameter at a time across its range; add channel-mix presets.

    Skips values equal to the baseline. Bool params emit only the non-baseline value when possible.
    """
    specs = parameters or PARAMETER_SPACE
    variants: list[ScenarioVariant] = []
    idx = 0

    for spec in specs:
        baseline_val = _get_path_value(base, spec.path)
        if spec.is_bool:
            candidates = [True, False]
            for val in candidates:
                if val == baseline_val:
                    continue
                idx += 1
                mods = {spec.path: val}
                variants.append(
                    ScenarioVariant(
                        variant_id=f"sweep_{idx:03d}",
                        variant_name=_sweep_variant_name(spec, val),
                        strategy=VariantStrategy.SWEEP.value,
                        modifications=mods,
                        scenario_config=_finalize_scenario(base, mods),
                    )
                )
            continue

        if spec.step is None:
            continue

        for val in _float_linear_values(spec):
            if isinstance(baseline_val, (int, float)) and _values_close(float(val), float(baseline_val)):
                continue
            idx += 1
            mods = {spec.path: val}
            variants.append(
                ScenarioVariant(
                    variant_id=f"sweep_{idx:03d}",
                    variant_name=_sweep_variant_name(spec, val),
                    strategy=VariantStrategy.SWEEP.value,
                    modifications=mods,
                    scenario_config=_finalize_scenario(base, mods),
                )
            )

    for preset_key, preset_mix in CHANNEL_PRESETS.items():
        if _channel_preset_equals_base(base, preset_mix):
            continue
        idx += 1
        mods = {"marketing.channel_mix": dict(preset_mix)}
        variants.append(
            ScenarioVariant(
                variant_id=f"sweep_{idx:03d}",
                variant_name=CHANNEL_PRESET_LABELS.get(preset_key, preset_key),
                strategy=VariantStrategy.SWEEP.value,
                modifications=mods,
                scenario_config=_finalize_scenario(base, mods),
            )
        )

    return variants


def _grid_variant_name(mods: dict[str, Any]) -> str:
    parts: list[str] = []
    if "product.price_inr" in mods:
        parts.append(f"P₹{int(mods['product.price_inr'])}")
    if "marketing.awareness_budget" in mods:
        parts.append(f"Aw{round(float(mods['marketing.awareness_budget']) * 100)}%")
    if "product.taste_appeal" in mods:
        parts.append(f"Ta{round(float(mods['product.taste_appeal']) * 100)}%")
    for k, v in sorted(mods.items()):
        if k in ("product.price_inr", "marketing.awareness_budget", "product.taste_appeal"):
            continue
        parts.append(f"{k}={v}")
    return " / ".join(parts) if parts else "Grid variant"


def generate_grid_variants(
    base: ScenarioConfig,
    grid_params: dict[str, list[Any]] | None = None,
    max_combinations: int = 500,
) -> list[ScenarioVariant]:
    """Cartesian product of grid parameter values, capped at ``max_combinations``."""

    grid = grid_params or {k: GRID_VALUES[k] for k in GRID_PARAMETERS}
    paths = sorted(grid.keys())
    value_lists = [grid[p] for p in paths]
    variants: list[ScenarioVariant] = []
    for combo_idx, combo in enumerate(islice(product(*value_lists), max_combinations), start=1):
        mods = dict(zip(paths, combo, strict=True))
        variants.append(
            ScenarioVariant(
                variant_id=f"grid_{combo_idx:03d}",
                variant_name=_grid_variant_name(mods),
                strategy=VariantStrategy.GRID.value,
                modifications=mods,
                scenario_config=_finalize_scenario(base, mods),
            )
        )
    return variants


def generate_random_variants(
    base: ScenarioConfig,
    n_variants: int = 100,
    seed: int = 42,
    parameters: list[ParameterSpec] | None = None,
) -> list[ScenarioVariant]:
    """
    Stratified random sampling (Latin-hypercube style) over float parameters;
    independent fair coin for each bool parameter per variant.
    """
    rng = random.Random(seed)
    specs = parameters or PARAMETER_SPACE
    float_params = [p for p in specs if not p.is_bool and p.step is not None]
    bool_params = [p for p in specs if p.is_bool]

    stratum_order: dict[str, list[int]] = {}
    for p in float_params:
        perm = list(range(n_variants))
        rng.shuffle(perm)
        stratum_order[p.path] = perm

    variants: list[ScenarioVariant] = []
    for i in range(n_variants):
        mods: dict[str, Any] = {}
        for p in float_params:
            strat_idx = stratum_order[p.path][i]
            mn = float(p.min_val)
            mx = float(p.max_val)
            lo = mn + (mx - mn) * strat_idx / n_variants
            hi = mn + (mx - mn) * (strat_idx + 1) / n_variants
            val = lo + rng.random() * (hi - lo)
            val = _clamp_price(round(val, 2)) if p.path.endswith("price_inr") else _clamp_unit(val)
            mods[p.path] = val
        for p in bool_params:
            mods[p.path] = rng.random() < 0.5
        variants.append(
            ScenarioVariant(
                variant_id=f"random_{i + 1:03d}",
                variant_name=f"Random #{i + 1:03d}",
                strategy=VariantStrategy.RANDOM.value,
                modifications=mods,
                scenario_config=_finalize_scenario(base, mods),
            )
        )
    return variants


def _remediation_mods(base: ScenarioConfig, rems: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply a sequence of remediations; each delta uses the latest value for that path."""

    running: dict[str, Any] = {}
    for rem in rems:
        path = rem["path"]
        base_v = _get_path_value(base, path)
        prev = running.get(path, base_v)
        if "value" in rem:
            running[path] = rem["value"]
        elif path.endswith("price_inr"):
            running[path] = _clamp_price(float(prev) + float(rem["delta"]))
        else:
            running[path] = _clamp_unit(float(prev) + float(rem["delta"]))
    return running


def _remediation_title(stage: str, rem: dict[str, Any]) -> str:
    key = rem["path"]
    short = _REMEDIATION_SHORT.get(key, key.split(".")[-1])
    return f"Fix {stage.replace('_', ' ').title()}: {short}"


def generate_smart_variants(
    base: ScenarioConfig,
    base_result: StaticSimulationResult,
    n_variants: int = 20,
) -> list[ScenarioVariant]:
    """Target dominant rejection stages with single, combined, and kitchen-sink remediations."""

    dist = {k: int(v) for k, v in base_result.rejection_distribution.items() if v > 0}
    sorted_stages = sorted(dist.keys(), key=lambda s: dist[s], reverse=True)

    built: list[ScenarioVariant] = []
    idx = 0

    def push(mods: dict[str, Any], name: str) -> None:
        nonlocal idx
        if len(built) >= n_variants:
            return
        idx += 1
        built.append(
            ScenarioVariant(
                variant_id=f"smart_{idx:03d}",
                variant_name=name,
                strategy=VariantStrategy.SMART.value,
                modifications=mods,
                scenario_config=_finalize_scenario(base, mods),
            )
        )

    for stage in sorted_stages:
        rems = REJECTION_REMEDIATIONS.get(stage, [])
        if not rems:
            continue
        for rem in rems:
            mods = _remediation_mods(base, [rem])
            push(mods, _remediation_title(stage, rem))
            if len(built) >= n_variants:
                return built
        combo = _remediation_mods(base, rems)
        push(combo, f"Fix {stage.replace('_', ' ').title()}: All levers")
        if len(built) >= n_variants:
            return built

    all_rems: list[dict[str, Any]] = []
    for stage in sorted_stages:
        all_rems.extend(REJECTION_REMEDIATIONS.get(stage, []))
    if all_rems:
        sink = _remediation_mods(base, all_rems)
        push(sink, "Fix All: Kitchen Sink")

    return built[:n_variants]


def generate_variants(
    base: ScenarioConfig,
    strategy: VariantStrategy,
    n_variants: int = 100,
    base_result: StaticSimulationResult | None = None,
    seed: int = 42,
) -> list[ScenarioVariant]:
    """Generate scenario variants; baseline is always the first entry."""

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
        variants = generate_random_variants(base, n_variants=n_variants, seed=seed)
    elif strategy == VariantStrategy.SMART:
        if base_result is None:
            raise ValueError("Smart strategy requires base_result")
        variants = generate_smart_variants(base, base_result, n_variants=n_variants)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    return [baseline, *variants]
