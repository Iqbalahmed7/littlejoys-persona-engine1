"""Agent state serialization for saving/loading simulation checkpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from src.agents.agent import CognitiveAgent


def save_agent_state(agent: CognitiveAgent, path: Path) -> None:
    """Serialize agent state (persona + memory + temporal state) to disk."""
    raise NotImplementedError("Full implementation in Sprint 2")


def load_agent_state(path: Path) -> CognitiveAgent:
    """Deserialize an agent from a checkpoint file."""
    raise NotImplementedError("Full implementation in Sprint 2")
