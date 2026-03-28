"""
Memory management for cognitive agents.

Handles episodic memory formation, semantic memory consolidation,
and brand memory updates during simulation.
"""

from __future__ import annotations


class MemoryManager:
    """Manages the three memory types for a cognitive agent."""

    def add_episodic(self, event: dict) -> None:
        """Record a new episodic memory from an experience."""
        raise NotImplementedError("Full implementation in Sprint 2")

    def update_semantic(self, key: str, value: object) -> None:
        """Update a semantic memory (general knowledge/belief)."""
        raise NotImplementedError("Full implementation in Sprint 2")

    def update_brand_memory(self, brand: str, touchpoint: dict) -> None:
        """Update accumulated brand impressions after an interaction."""
        raise NotImplementedError("Full implementation in Sprint 2")
