import pytest
from src.simulation.journey_result import aggregate_journeys, segment_by_reorder, find_conversion_tick, JourneyAggregate
from src.simulation.tick_engine import TickJourneyLog, TickSnapshot


def make_mock_log(persona_id, reordered, first_decision="buy", second_decision="buy", error=None):
    """Helper to create a minimal TickJourneyLog dict (as returned by to_dict())."""
    return {
        "persona_id": persona_id,
        "display_name": persona_id,
        "journey_id": "A",
        "total_ticks": 60,
        "reordered": reordered,
        "error": error,
        "final_decision": {"decision": second_decision, "confidence": 0.7,
                           "key_drivers": ["pediatrician"], "objections": [],
                           "willingness_to_pay_inr": 649} if not error else None,
        "snapshots": [
            {
                "tick": 20,
                "brand_trust": {"littlejoys": 0.6},
                "memories_count": 5,
                "cumulative_salience": 0.0,
                "reflected": False,
                "perception_results": [],
                "decision_result": {"decision": first_decision, "confidence": 0.8,
                                    "key_drivers": ["pediatrician"], "objections": [],
                                    "willingness_to_pay_inr": 649},
            },
            {
                "tick": 60,
                "brand_trust": {"littlejoys": 0.75},
                "memories_count": 12,
                "cumulative_salience": 0.0,
                "reflected": True,
                "perception_results": [],
                "decision_result": {"decision": second_decision, "confidence": 0.7,
                                    "key_drivers": ["habit"], "objections": [],
                                    "willingness_to_pay_inr": 649},
            },
        ],
        # Fields like trust_by_tick used by aggregation
        "trust_by_tick": {20: 0.6, 60: 0.75},
        "first_decision": {"decision": first_decision, "key_drivers": ["pediatrician"]},
        "second_decision": {"decision": second_decision, "key_drivers": ["habit"]},
    }


def test_aggregate_journeys_empty_list():
    result = aggregate_journeys([])
    assert isinstance(result, JourneyAggregate)
    assert result.total_personas == 0
    assert result.reorder_rate_pct == 0.0


def test_aggregate_journeys_all_errors():
    logs = [make_mock_log(f"p{i}", False, error="some error") for i in range(5)]
    result = aggregate_journeys(logs)
    assert result.errors == 5
    assert result.reorder_rate_pct == 0.0


def test_aggregate_journeys_computes_reorder_rate():
    logs = [
        make_mock_log("p1", reordered=True, first_decision="buy", second_decision="buy"),
        make_mock_log("p2", reordered=True, first_decision="buy", second_decision="buy"),
        make_mock_log("p3", reordered=False, first_decision="buy", second_decision="defer"),
        make_mock_log("p4", reordered=False, first_decision="trial", second_decision="reject"),
    ]
    result = aggregate_journeys(logs)
    # 2 reordered out of 4 = 50%
    assert result.reorder_rate_pct == pytest.approx(50.0)


def test_aggregate_journeys_returns_journey_aggregate():
    logs = [make_mock_log("p1", True)]
    result = aggregate_journeys(logs)
    assert isinstance(result, JourneyAggregate)
    assert result.journey_id == "A"


def test_segment_by_reorder_empty_list():
    result = segment_by_reorder([])
    assert result == {"reorderers": [], "lapsers": []}


def test_segment_by_reorder_splits_correctly():
    logs = [
        make_mock_log("p1", reordered=True),
        make_mock_log("p2", reordered=False),
        make_mock_log("p3", reordered=True),
        make_mock_log("p4", reordered=False, error="crash"),  # errors excluded
    ]
    result = segment_by_reorder(logs)
    assert set(result["reorderers"]) == {"p1", "p3"}
    assert set(result["lapsers"]) == {"p2"}  # p4 excluded (error)


def test_segment_by_reorder_excludes_errors():
    logs = [make_mock_log("p1", True, error="crash")]
    result = segment_by_reorder(logs)
    assert len(result["reorderers"]) == 0
    assert len(result["lapsers"]) == 0


def test_find_conversion_tick_empty_list():
    result = find_conversion_tick([])
    assert isinstance(result, dict)
    assert len(result) == 0


def test_aggregate_trust_by_tick_computed():
    logs = [
        make_mock_log("p1", True),
        make_mock_log("p2", False)
    ]
    # p1 trust: {20: 0.6, 60: 0.75}
    # p2 trust: {20: 0.6, 60: 0.75}
    result = aggregate_journeys(logs)
    assert 20 in result.trust_by_tick
    assert result.trust_by_tick[20] == 0.6
    assert 60 in result.trust_by_tick
    assert result.trust_by_tick[60] == 0.75
