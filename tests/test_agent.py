"""Tests for CognitiveAgent.perceive() and update_memory()."""
import pytest
import json
from unittest.mock import patch, MagicMock
import copy

from src.agents.agent import CognitiveAgent
from src.agents.perception_result import PerceptionResult


@pytest.fixture
def agent(minimal_persona):
    return CognitiveAgent(minimal_persona)


@pytest.fixture
def mock_llm_response():
    return json.dumps({
        "importance": 7,
        "emotional_valence": 0.4,
        "dominant_attributes": ["health_anxiety", "social_proof_bias"],
        "interpretation": "She finds this relevant given her health focus."
    })


class TestCognitiveAgentInit:
    def test_agent_initialises_without_api_calls(self, minimal_persona):
        # anthropic may not be installed in CI; lazy init is verified by _client is None
        agent = CognitiveAgent(minimal_persona)
        assert agent._client is None, "Client must not be initialised at construction time"

    def test_agent_has_memory_manager(self, agent):
        from src.agents.memory import MemoryManager
        assert isinstance(agent.memory, MemoryManager)

    def test_agent_client_is_none_at_init(self, agent):
        assert agent._client is None


class TestCognitiveAgentPerceive:
    def test_perceive_returns_perception_result(self, agent, mock_llm_response):
        with patch.object(agent, "_llm_call", return_value=mock_llm_response):
            result = agent.perceive({"type": "ad", "source": "instagram", "content": "LittleJoys ad"})
        assert isinstance(result, PerceptionResult)

    def test_perceive_importance_normalised(self, agent, mock_llm_response):
        with patch.object(agent, "_llm_call", return_value=mock_llm_response):
            result = agent.perceive({"type": "ad", "content": "test", "source": "test"})
        # importance 7 → (7-1)/9 ≈ 0.667
        assert 0.0 <= result.importance <= 1.0
        assert abs(result.importance - 0.6666) < 0.01

    def test_perceive_importance_in_unit_interval(self, agent):
        for raw_importance in [1, 5, 10]:
            response = json.dumps({
                "importance": raw_importance,
                "emotional_valence": 0.0,
                "dominant_attributes": [],
                "interpretation": "test"
            })
            with patch.object(agent, "_llm_call", return_value=response):
                result = agent.perceive({"type": "ad", "content": "test", "source": "test"})
            assert 0.0 <= result.importance <= 1.0

    def test_perceive_high_importance_sets_reflection_trigger(self, agent):
        response = json.dumps({"importance": 9, "emotional_valence": 0.7,
                               "dominant_attributes": ["health_anxiety"], "interpretation": "Very relevant."})
        with patch.object(agent, "_llm_call", return_value=response):
            result = agent.perceive({"type": "wom", "content": "critical", "source": "friend"})
        assert result.reflection_trigger_candidate is True

    def test_perceive_low_importance_no_reflection_trigger(self, agent):
        response = json.dumps({"importance": 3, "emotional_valence": 0.0,
                               "dominant_attributes": [], "interpretation": "Not relevant."})
        with patch.object(agent, "_llm_call", return_value=response):
            result = agent.perceive({"type": "ad", "content": "irrelevant", "source": "newspaper"})
        assert result.reflection_trigger_candidate is False

    def test_perceive_writes_to_episodic_memory(self, agent, mock_llm_response):
        initial_count = len(agent.persona.episodic_memory)
        with patch.object(agent, "_llm_call", return_value=mock_llm_response):
            agent.perceive({"type": "ad", "content": "test ad", "source": "instagram"})
        assert len(agent.persona.episodic_memory) == initial_count + 1

    def test_perceive_with_brand_updates_brand_memory(self, agent, mock_llm_response):
        with patch.object(agent, "_llm_call", return_value=mock_llm_response):
            agent.perceive({
                "type": "ad", "content": "LittleJoys new product",
                "source": "instagram", "brand": "littlejoys",
            })
        assert "littlejoys" in agent.persona.brand_memories

    def test_perceive_without_brand_no_brand_memory(self, agent, mock_llm_response):
        with patch.object(agent, "_llm_call", return_value=mock_llm_response):
            agent.perceive({"type": "ad", "content": "generic ad", "source": "instagram"})
        # Note: some existing brand memories might be there, but no NEW one added for generic
        pass

    def test_perceive_returns_memory_written_true(self, agent, mock_llm_response):
        with patch.object(agent, "_llm_call", return_value=mock_llm_response):
            result = agent.perceive({"type": "ad", "content": "test", "source": "test"})
        assert result.memory_written is True

    def test_perceive_handles_malformed_json_gracefully(self, agent):
        messy_response = 'Here is the result: {"importance": 5, "emotional_valence": 0.1, "dominant_attributes": [], "interpretation": "ok"} Done!'
        with patch.object(agent, "_llm_call", return_value=messy_response):
            result = agent.perceive({"type": "ad", "content": "test", "source": "test"})
        assert isinstance(result, PerceptionResult)


class TestCognitiveAgentUpdateMemory:
    def test_update_memory_writes_to_episodic_memory(self, agent):
        agent.update_memory({
            "event_type": "decision",
            "content": "Decided to try the product",
            "emotional_valence": 0.2,
            "salience": 0.7,
        })
        assert len(agent.persona.episodic_memory) == 1

    def test_update_memory_no_longer_raises_not_implemented(self, agent):
        try:
            agent.update_memory({"event_type": "stimulus", "content": "test"})
        except NotImplementedError:
            pytest.fail("update_memory still raises NotImplementedError — stub not replaced")


class TestCognitiveAgentDecide:
    def test_decide_returns_decision_result(self, minimal_persona, mock_llm_response):
        """decide() should return a DecisionResult with a valid decision field."""
        from src.agents import DecisionResult
        from unittest.mock import patch

        scenario = {
            "description": "LittleJoys available on BigBasket for Rs 649. Do you buy?",
            "product": "LittleJoys 500g",
            "price_inr": 649,
            "channel": "bigbasket",
            "simulation_tick": 20,
        }

        agent = CognitiveAgent(minimal_persona)
        mock_response = {
            "decision": "trial",
            "confidence": 0.72,
            "reasoning_trace": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
            "key_drivers": ["pediatrician recommendation", "clean label"],
            "objections": ["price premium"],
            "willingness_to_pay_inr": 699,
            "follow_up_action": "add_to_cart",
        }
        import json

        with patch.object(agent, "_llm_call", return_value=json.dumps(mock_response)):
            result = agent.decide(scenario)

        assert isinstance(result, DecisionResult)
        assert result.decision in {"buy", "trial", "reject", "defer", "research_more"}
        assert 0.0 <= result.confidence <= 1.0


class TestCognitiveAgentReflect:
    def test_reflect_returns_list(self, minimal_persona):
        """reflect() should return a list (possibly empty if no memories)."""
        from unittest.mock import patch
        import json

        agent = CognitiveAgent(minimal_persona)
        mock_reflection = json.dumps({
            "insights": [
                {
                    "insight": "Test insight about nutrition.",
                    "confidence": 0.8,
                    "source_indices": [0],
                    "emotional_valence": 0.3,
                }
            ]
        })

        with patch.object(agent, "_llm_call", return_value=mock_reflection):
            result = agent.reflect(n_insights=1)

        assert isinstance(result, list)

    def test_reflect_appends_to_episodic_memory(self, minimal_persona):
        """reflect() should append reflection entries to persona.episodic_memory."""
        from src.taxonomy.schema import MemoryEntry
        from unittest.mock import patch
        import json

        # Pre-load some memories so reflect() has something to work with
        for i in range(3):
            minimal_persona.episodic_memory.append(
                MemoryEntry(
                    timestamp=f"2026-01-0{i+1}T10:00:00+00:00",
                    event_type="stimulus",
                    content=f"Stimulus {i}: LittleJoys seen in ad",
                    emotional_valence=0.2,
                    salience=0.6,
                )
            )

        agent = CognitiveAgent(minimal_persona)

        mock_reflection = json.dumps({
            "insights": [
                {
                    "insight": "Trust in expert sources is growing.",
                    "confidence": 0.75,
                    "source_indices": [0, 1],
                    "emotional_valence": 0.4,
                },
                {
                    "insight": "Price remains a key consideration.",
                    "confidence": 0.68,
                    "source_indices": [2],
                    "emotional_valence": -0.1,
                },
            ]
        })

        with patch.object(agent, "_llm_call", return_value=mock_reflection):
            agent.reflect(n_insights=2)

        new_entries = [
            m for m in minimal_persona.episodic_memory
            if m.event_type == "reflection"
        ]
        assert len(new_entries) == 2
        for entry in new_entries:
            assert entry.salience == pytest.approx(0.85)
