"""
Scenario configuration for the 4 LittleJoys business problems.

Each scenario defines a product, target segment, and marketing parameters.
See ARCHITECTURE.md §3 for business problem definitions.
Full implementation in PRD-005 (Codex).
"""

from __future__ import annotations

from pydantic import BaseModel, confloat


class ProductConfig(BaseModel):
    """Product attributes for simulation."""

    name: str
    category: str
    price_inr: float
    age_range: tuple[int, int]
    key_benefits: list[str]
    form_factor: str
    taste_appeal: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]
    effort_to_acquire: confloat(ge=0, le=1) = 0.5  # type: ignore[valid-type]


class MarketingConfig(BaseModel):
    """Marketing and distribution parameters."""

    awareness_budget: confloat(ge=0, le=1) = 0.3  # type: ignore[valid-type]
    channel_mix: dict[str, float] = {}
    trust_signals: list[str] = []
    school_partnership: bool = False
    influencer_campaign: bool = False
    pediatrician_endorsement: bool = False


class ScenarioConfig(BaseModel):
    """Complete scenario configuration for a business problem."""

    id: str
    name: str
    description: str
    product: ProductConfig
    marketing: MarketingConfig
    target_age_range: tuple[int, int]
    lj_pass_available: bool = False


def get_scenario(scenario_id: str) -> ScenarioConfig:
    """Get a predefined scenario configuration by ID."""
    raise NotImplementedError("Full implementation in PRD-005")


def get_all_scenarios() -> list[ScenarioConfig]:
    """Get all 4 predefined scenario configurations."""
    raise NotImplementedError("Full implementation in PRD-005")
