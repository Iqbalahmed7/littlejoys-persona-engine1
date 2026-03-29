import pytest

from src.simulation.wom import propagate_wom


class MockRelationships:
    def __init__(self, wom):
        self.wom_transmitter_tendency = wom


class MockPsychology:
    def __init__(self, spb):
        self.social_proof_bias = spb


class MockPersona:
    def __init__(self, pid, wom, spb):
        self.id = pid
        self.relationships = MockRelationships(wom)
        self.psychology = MockPsychology(spb)
        self._flat = {"wom_transmitter_tendency": wom, "social_proof_bias": spb}

    def to_flat_dict(self):
        return self._flat


class MockPopulation:
    def __init__(self, tier1):
        self.tier1_personas = tier1
        self.tier2_personas = []

    @property
    def personas(self):
        return self.tier1_personas

    def get_persona(self, persona_id):
        for p in self.tier1_personas:
            if p.id == persona_id:
                return p
        raise KeyError(persona_id)


@pytest.fixture
def mock_pop():
    personas = [
        MockPersona("p1", 0.8, 0.5),  # adopter, high WOM
        MockPersona("p2", 0.1, 0.5),  # adopter, low WOM
        MockPersona("p3", 0.5, 0.8),  # non-adopter, high social proof
        MockPersona("p4", 0.5, 0.1),  # non-adopter, low social proof
        MockPersona("p5", 0.5, 0.5),  # non-adopter
        MockPersona("p6", 0.5, 0.5),  # non-adopter
        MockPersona("p7", 0.5, 0.5),  # non-adopter
        MockPersona("p8", 0.5, 0.5),  # non-adopter
    ]
    return MockPopulation(personas)


def test_wom_returns_awareness_boost_for_non_adopters(mock_pop):
    boosts = propagate_wom(mock_pop, ["p1", "p2"], 1)
    assert isinstance(boosts, dict)
    assert "p1" not in boosts
    assert "p2" not in boosts
    assert len(boosts) > 0


def test_wom_boost_decays_over_months(mock_pop):
    boosts_m1 = propagate_wom(mock_pop, ["p1"], 1, decay=0.5)
    boosts_m2 = propagate_wom(mock_pop, ["p1"], 2, decay=0.5)
    max1 = max(boosts_m1.values()) if boosts_m1 else 0
    max2 = max(boosts_m2.values()) if boosts_m2 else 0
    assert max1 > max2


def test_high_transmitter_spreads_more(mock_pop):
    boosts = propagate_wom(mock_pop, ["p2"], 1)  # p2 has WOM score 0.1 < 0.3
    assert len(boosts) == 0


def test_wom_does_not_affect_existing_adopters(mock_pop):
    all_ids = [p.id for p in mock_pop.tier1_personas]
    boosts = propagate_wom(mock_pop, all_ids, 1)
    assert len(boosts) == 0


def test_wom_boost_capped_per_month():
    personas = [
        MockPersona("p1", 10.0, 10.0),  # massive transmitter bounds break
        MockPersona("p2", 0.5, 0.5),
        MockPersona("p3", 0.5, 0.5),
        MockPersona("p4", 0.5, 0.5),
    ]
    pop = MockPopulation(personas)
    boosts = propagate_wom(pop, ["p1"], 1)
    for v in boosts.values():
        assert v <= 0.3


def test_wom_empty_adopter_list_returns_empty(mock_pop):
    boosts = propagate_wom(mock_pop, [], 1)
    assert len(boosts) == 0


def test_wom_deterministic_per_persona(mock_pop):
    b1 = propagate_wom(mock_pop, ["p1"], 1)
    b2 = propagate_wom(mock_pop, ["p1"], 1)
    assert b1 == b2
