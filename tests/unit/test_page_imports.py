"""Smoke tests for Streamlit page imports and question bank integrity (Sprint 14)."""

from __future__ import annotations

import ast

from src.probing.question_bank import get_tree_for_question, list_all_questions
from src.simulation.auto_variants import BusinessVariant, VariantBatch, generate_business_variants


def test_research_page_syntax():
    """Verify app/pages/2_research.py is syntactically valid."""
    with open("app/pages/2_research.py") as f:
        ast.parse(f.read())

def test_personas_page_syntax():
    """Verify app/pages/1_personas.py is syntactically valid."""
    with open("app/pages/1_personas.py") as f:
        ast.parse(f.read())

def test_auto_variants_importable():
    """Verify core auto-variant symbols are importable."""
    assert generate_business_variants is not None
    assert BusinessVariant is not None
    assert VariantBatch is not None

def test_question_bank_tree_resolution_all():
    """For every business question, verify the probing tree is valid and non-empty."""
    questions = list_all_questions()
    assert len(questions) > 0
    for q in questions:
        tree = get_tree_for_question(q.id)
        assert tree is not None
        assert len(tree.hypotheses) >= 1
        assert len(tree.probes) >= 1
        # Also check the problem statement is linked
        assert tree.problem is not None
        assert tree.problem.scenario_id == q.scenario_id

def test_results_page_syntax():
    """Verify app/pages/3_results.py is syntactically valid."""
    with open("app/pages/3_results.py") as f:
        ast.parse(f.read())

def test_interviews_deepdive_page_syntax():
    """Verify app/pages/4_interviews.py is syntactically valid."""
    with open("app/pages/4_interviews.py") as f:
        ast.parse(f.read())

def test_research_consolidator_importable():
    """Verify research consolidator symbols are correctly exposed."""
    from src.analysis.research_consolidator import consolidate_research, ConsolidatedReport
    assert consolidate_research is not None
    assert ConsolidatedReport is not None
