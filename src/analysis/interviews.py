"""
Deep persona interview system — interactive conversations with Tier 2 personas.

The LLM role-plays as a specific persona, staying in character with their
attributes, narrative, and simulation history.
Full implementation in PRD-010 (Codex).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.taxonomy.schema import Persona
    from src.utils.llm import LLMClient


class PersonaInterviewer:
    """Conducts interactive interviews with Tier 2 personas via LLM."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    async def interview(
        self,
        persona: Persona,
        question: str,
        conversation_history: list[dict] | None = None,
    ) -> str:
        """
        Ask a Tier 2 persona a question and get an in-character response.

        The response must be consistent with all persona attributes and their
        simulation outcome (adopted/rejected and why).
        """
        raise NotImplementedError("Full implementation in PRD-010")
