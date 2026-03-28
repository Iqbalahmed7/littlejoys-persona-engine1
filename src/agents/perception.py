"""
Perception module — filters stimuli through the persona's psychological attributes.

Determines how a persona perceives marketing messages, product attributes,
and social signals based on their psychology and cultural context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


class PerceptionEngine:
    """Filters external stimuli through persona's psychological lens."""

    def perceive_ad(self, persona: Persona, ad: dict) -> dict:
        """How does this persona perceive a given advertisement?"""
        raise NotImplementedError("Full implementation in Sprint 2")

    def perceive_product(self, persona: Persona, product: dict) -> dict:
        """How does this persona perceive a product's attributes?"""
        raise NotImplementedError("Full implementation in Sprint 2")

    def perceive_social_signal(self, persona: Persona, signal: dict) -> dict:
        """How does this persona perceive word-of-mouth or social proof?"""
        raise NotImplementedError("Full implementation in Sprint 2")
