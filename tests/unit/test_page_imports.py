"""Smoke tests for Streamlit page imports and question bank integrity (Sprint 14)."""

from __future__ import annotations

import ast

from src.probing.question_bank import get_tree_for_question, list_all_questions
from src.simulation.auto_variants import BusinessVariant, VariantBatch, generate_business_variants


def test_problem_page_syntax():
    """Verify app/pages/2_problem.py is syntactically valid."""
    with open("app/pages/2_problem.py") as f:
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

def test_decompose_page_syntax():
    """Verify app/pages/3_decompose.py is syntactically valid."""
    with open("app/pages/3_decompose.py") as f:
        ast.parse(f.read())

def test_finding_page_syntax():
    """Verify app/pages/4_finding.py is syntactically valid."""
    with open("app/pages/4_finding.py") as f:
        ast.parse(f.read())

def test_research_consolidator_importable():
    """Verify research consolidator symbols are correctly exposed."""
    from src.analysis.research_consolidator import ConsolidatedReport, consolidate_research
    assert consolidate_research is not None
    assert ConsolidatedReport is not None


def test_trajectory_clustering_importable():
    """Verify trajectory clustering symbols are correctly exposed."""
    from src.analysis.trajectory_clustering import (
        BehaviourCluster,
        TrajectoryClusterResult,
        cluster_trajectories,
    )
    assert TrajectoryClusterResult is not None
    assert BehaviourCluster is not None
    assert cluster_trajectories is not None


def test_event_engine_importable():
    """Verify event-level simulation symbols are correctly exposed."""
    from src.simulation.event_engine import EventSimulationResult, run_event_simulation
    from src.simulation.event_grammar import SimulationEvent
    from src.simulation.state_model import CanonicalState, initialize_state

    assert EventSimulationResult is not None
    assert run_event_simulation is not None
    assert SimulationEvent is not None
    assert CanonicalState is not None
    assert initialize_state is not None
