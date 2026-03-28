"""
Cognitive agent wrapper for personas during simulation.

Wraps a Persona with perception, memory update, and decision-making capabilities.
See ARCHITECTURE.md §7 for the agent architecture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona


class CognitiveAgent:
    """
    Agent wrapper that gives a Persona the ability to perceive, remember, and decide.

    The agent processes stimuli through its persona's psychological lens,
    updates memory based on experiences, and makes purchase decisions.
    """

    def __init__(self, persona: Persona) -> None:
        self.persona = persona

    def perceive(self, stimulus: dict) -> dict:
        """Filter and interpret a marketing/product stimulus through persona's lens."""
        raise NotImplementedError("Full implementation in Sprint 2")

    def update_memory(self, event: dict) -> None:
        """Record an experience in the persona's memory."""
        raise NotImplementedError("Full implementation in Sprint 2")

    def decide(self, scenario: dict) -> dict:
        """Make a purchase decision based on current state and memory."""
        raise NotImplementedError("Full implementation in Sprint 2")
