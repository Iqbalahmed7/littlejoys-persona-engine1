"""Tests for temporal persona trajectory clustering logic."""

from __future__ import annotations

import pytest

from src.analysis.trajectory_clustering import cluster_trajectories
from src.decision.scenarios import get_scenario
from src.generation.population import Population, PopulationGenerator
from src.simulation.temporal import extract_persona_trajectories


@pytest.fixture(scope="module")
def population() -> Population:
    """Generate a stable population for clustering tests."""
    return PopulationGenerator().generate(seed=42, size=100)


@pytest.fixture(scope="module")
def result(population):
    """Run baseline traversal on the target scenario."""
    scenario = get_scenario("nutrimix_2_6")
    trajectories = extract_persona_trajectories(
        population=population,
        scenario=scenario,
        months=6,
        seed=42,
    )
    return cluster_trajectories(trajectories, population)


def test_clustering_produces_clusters(result):
    assert len(result.clusters) > 0
    # Expected groups generally include "Never Reached", "Loyal Repeaters", etc.
    assert 3 <= len(result.clusters) <= 7


def test_all_personas_assigned(result, population):
    assigned_ids = []
    for cluster in result.clusters:
        assigned_ids.extend(cluster.persona_ids)

    # Assert each ID mapped exactly once
    assert len(assigned_ids) == len(population.personas)
    assert len(set(assigned_ids)) == len(population.personas)


def test_cluster_sizes_sum(result, population):
    total_size = sum(cluster.size for cluster in result.clusters)
    assert total_size == len(population.personas)
    assert result.population_size == total_size


def test_loyal_vs_fatigued_lifetime(result):
    loyal = next((c for c in result.clusters if c.cluster_name == "Loyal Repeaters"), None)
    fatigued = next(
        (c for c in result.clusters if c.cluster_name in ("Taste-Fatigued Droppers", "Forgot-to-Reorder", "Price-Triggered Switchers")),
        None
    )

    # Some distributions might not produce these exactly, but if both exist, loyal lifetime > fatgued lifetime.
    if loyal and fatigued:
        assert loyal.avg_lifetime_months > fatigued.avg_lifetime_months


def test_zero_adopters_edge_case(population):
    scenario = get_scenario("nutrimix_2_6")
    # Impossibly low marketing budget to guarantee 0 adoption, and remove trust signals
    scenario.marketing.awareness_budget = 0.0
    scenario.marketing.pediatrician_endorsement = False
    scenario.marketing.school_partnership = False
    scenario.marketing.influencer_campaign = False

    trajectories = extract_persona_trajectories(
        population=population,
        scenario=scenario,
        months=6,
        seed=42,
    )
    result = cluster_trajectories(trajectories, population)

    assert len(result.clusters) == 1
    assert result.clusters[0].cluster_name == "Never Reached"
    assert result.clusters[0].size == len(population.personas)


def test_cluster_dominant_attributes(result):
    for cluster in result.clusters:
        # Avoid forcing an entry if cluster size is 0, but clusters with members should have some diffs.
        if cluster.size > 0:
            assert isinstance(cluster.dominant_attributes, dict)
            assert len(cluster.dominant_attributes) > 0
