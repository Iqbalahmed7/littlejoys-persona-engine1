"""Unit tests for business question bank (Sprint 12)."""

from __future__ import annotations

import pytest
from src.constants import SCENARIO_IDS
from src.probing.question_bank import (
    get_question,
    get_questions_for_scenario,
    list_all_questions,
)
from src.probing.predefined_trees import get_problem_tree

def test_every_scenario_has_questions() -> None:
    """Each of the 4 scenario IDs has at least 3 questions."""
    for sid in SCENARIO_IDS:
        qs = get_questions_for_scenario(sid)
        assert len(qs) >= 3, f"Scenario {sid} only has {len(qs)} questions"

def test_no_duplicate_question_ids() -> None:
    """All question IDs across all scenarios are unique."""
    all_qs = list_all_questions()
    ids = [q.id for q in all_qs]
    assert len(ids) == len(set(ids))

def test_question_fields_populated() -> None:
    """Every BusinessQuestion has non-empty title, description, success_metric."""
    all_qs = list_all_questions()
    for q in all_qs:
        assert q.title
        assert q.description
        assert q.success_metric

def test_probing_tree_mapping() -> None:
    """For questions with a probing_tree_id, verify the tree exists."""
    all_qs = list_all_questions()
    for q in all_qs:
        if q.probing_tree_id:
            # Should not raise KeyError
            try:
                get_problem_tree(q.probing_tree_id)
            except KeyError:
                pytest.fail(f"Question {q.id} references missing tree {q.probing_tree_id}")

def test_get_question_by_id() -> None:
    """get_question returns the correct BusinessQuestion or raises KeyError."""
    all_qs = list_all_questions()
    if all_qs:
        target = all_qs[0]
        assert get_question(target.id).id == target.id
    
    with pytest.raises(KeyError):
        get_question("nonexistent_id_404")

def test_get_questions_for_scenario() -> None:
    """Returns only questions matching the given scenario_id."""
    for sid in SCENARIO_IDS:
        qs = get_questions_for_scenario(sid)
        for q in qs:
            assert q.scenario_id == sid

def test_scenario_id_valid() -> None:
    """Every question's scenario_id is one of the 4 valid scenario IDs."""
    all_qs = list_all_questions()
    for q in all_qs:
        assert q.scenario_id in SCENARIO_IDS
